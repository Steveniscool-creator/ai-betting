import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="AI Betting Bot", layout="wide")
st.title("🎯 AI Value Betting Dashboard")

sports_map = {
    "MLB (Baseball)": "baseball/mlb",
    "Tennis (ATP/WTA)": "tennis",
}
stake = 10

@st.cache_data(ttl=300)
def get_bovada_data(sport_path):
    url = f"https://www.bovada.lv/services/sports/event/v2/events/A/description/{sport_path}"
    try:
        res = requests.get(url)
        return res.json()
    except:
        return None

sport_choice = st.selectbox("Select Sport", list(sports_map.keys()))
sport_path = sports_map[sport_choice]

data = get_bovada_data(sport_path)
events = data[0]["events"] if data and isinstance(data, list) else []

if not events:
    st.warning("⚠️ No upcoming events found.")
    st.stop()

st.subheader(f"🧠 Input Your Win Probabilities – {sport_choice}")
value_bets = []

for event in events:
    competitors = event.get("competitors", [])
    if len(competitors) < 2:
        continue

    team1 = competitors[0].get("name", "Team 1")
    team2 = competitors[1].get("name", "Team 2")

    market = next(
        (m for g in event.get("displayGroups", []) for m in g.get("markets", [])
         if m.get("description") == "Moneyline"), None)
    if not market:
        continue

    outcomes = market.get("outcomes", [])
    odds_map = {}
    for o in outcomes:
        name = o.get("description")
        decimal = float(o["price"]["decimal"])
        odds_map[name] = decimal

    if team1 not in odds_map or team2 not in odds_map:
        continue

    prob1 = st.number_input(f"{team1} vs {team2} — Prob {team1} wins:", 0.0, 1.0, 0.5, 0.01, key=f"{team1}_{team2}")
    prob2 = 1 - prob1

    ev1 = prob1 * ((odds_map[team1] - 1) * stake) - prob2 * stake
    ev2 = prob2 * ((odds_map[team2] - 1) * stake) - prob1 * stake

    if ev1 > 0:
        value_bets.append({"Team": team1, "Opponent": team2, "Odds": odds_map[team1], "Prob": prob1, "EV": round(ev1, 2)})
    if ev2 > 0:
        value_bets.append({"Team": team2, "Opponent": team1, "Odds": odds_map[team2], "Prob": prob2, "EV": round(ev2, 2)})

if not value_bets:
    st.info("No +EV bets found yet. Try adjusting your win probabilities.")
else:
    st.subheader("📈 +EV Bets")
    df = pd.DataFrame(value_bets)
    st.dataframe(df)

    st.subheader("💰 Summary Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Bets", len(df))
    col2.metric("Total Risk", f"${len(df)*stake}")
    col3.metric("Total EV", f"${df['EV'].sum():.2f}")

    col4, col5, col6 = st.columns(3)
    max_win = sum((b['Odds'] - 1) * stake for b in value_bets)
    expected_win = sum(b['Prob'] * (b['Odds'] - 1) * stake for b in value_bets)
    expected_loss = sum((1 - b['Prob']) * stake for b in value_bets)
    col4.metric("Max Win", f"${max_win:.2f}")
    col5.metric("Expected Win", f"${expected_win:.2f}")
    col6.metric("Expected Loss", f"${expected_loss:.2f}")

    if st.button("💾 Save Bets to History"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df['Date'] = now
        df['Sport'] = sport_choice
        try:
            history = pd.read_csv("bet_history.csv")
            df = pd.concat([history, df], ignore_index=True)
        except FileNotFoundError:
            pass
        df.to_csv("bet_history.csv", index=False)
        st.success("Saved to bet_history.csv ✅")

st.subheader("📜 Bet History")
try:
    history = pd.read_csv("bet_history.csv")
    history["Date"] = pd.to_datetime(history["Date"])
    start_date = st.date_input("📅 Filter from date", value=pd.Timestamp.today() - pd.Timedelta(days=7))
    filtered = history[history["Date"].dt.date >= start_date]
    st.dataframe(filtered.tail(50))
except:
    st.info("No bet history saved yet.")
