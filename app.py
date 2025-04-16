import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SharpPicks AI", layout="wide")
st.title("📊 SharpPicks AI – Live MLB & Tennis EV Betting Bot")

# ⚙️ CONFIG
stake = 10
api_key = "8b1fc75ab32cdd60238394cfc0c88b83"  # ✅ your real API key
region = "us"
market = "h2h"

sport_map = {
    "MLB (Baseball)": "baseball_mlb",
    "Tennis (ATP/WTA)": "tennis"
}

@st.cache_data(ttl=300)
def get_live_odds(sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?regions={region}&markets={market}&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code != 200:
        st.error("❌ Failed to fetch live odds.")
        return []
    return response.json()

sport_choice = st.selectbox("Select Sport", list(sport_map.keys()))
sport_key = sport_map[sport_choice]
events = get_live_odds(sport_key)

if not events:
    st.warning(f"⚠️ No live {sport_choice} odds available right now.")
    st.stop()

st.subheader("🧠 Input Win Probabilities")
value_bets = []

for event in events:
    team1 = event.get("home_team", "Team A")
    team2 = event.get("away_team", "Team B")
    commence = event.get("commence_time", "")

    bookmakers = event.get("bookmakers", [])
    if not bookmakers:
        continue

    outcomes = bookmakers[0]["markets"][0]["outcomes"]
    odds_map = {o["name"]: o["price"] for o in outcomes}
    if team1 not in odds_map or team2 not in odds_map:
        continue

    prob1 = st.number_input(f"{team1} vs {team2} — Prob {team1} wins:", 0.0, 1.0, 0.5, 0.01, key=f"{team1}_{team2}")
    prob2 = 1 - prob1

    ev1 = prob1 * ((odds_map[team1] - 1) * stake) - prob2 * stake
    ev2 = prob2 * ((odds_map[team2] - 1) * stake) - prob1 * stake

    if ev1 > 0:
        value_bets.append({
            "Team": team1,
            "Opponent": team2,
            "Odds": odds_map[team1],
            "Prob": prob1,
            "EV": round(ev1, 2),
            "Sport": sport_choice,
            "Date": commence
        })
    if ev2 > 0:
        value_bets.append({
            "Team": team2,
            "Opponent": team1,
            "Odds": odds_map[team2],
            "Prob": prob2,
            "EV": round(ev2, 2),
            "Sport": sport_choice,
            "Date": commence
        })

if value_bets:
    df = pd.DataFrame(value_bets)
    st.subheader("💸 +EV Bets")
    st.dataframe(df)

    st.subheader("📊 Summary Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Bets", len(df))
    col2.metric("Total Risk", f"${len(df) * stake}")
    col3.metric("Total EV", f"${df['EV'].sum():.2f}")

    col4, col5, col6 = st.columns(3)
    max_win = sum((b['Odds'] - 1) * stake for _, b in df.iterrows())
    expected_win = sum(b['Prob'] * (b['Odds'] - 1) * stake for _, b in df.iterrows())
    expected_loss = sum((1 - b['Prob']) * stake for _, b in df.iterrows())
    col4.metric("Max Win", f"${max_win:.2f}")
    col5.metric("Expected Win", f"${expected_win:.2f}")
    col6.metric("Expected Loss", f"${expected_loss:.2f}")

    if st.button("💾 Save Bets to History"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df["Saved"] = now
        try:
            old = pd.read_csv("bet_history.csv")
            df = pd.concat([old, df], ignore_index=True)
        except FileNotFoundError:
            pass
        df.to_csv("bet_history.csv", index=False)
        st.success("Saved to bet_history.csv ✅")
else:
    st.info("No +EV bets found. Try adjusting win probabilities.")

st.subheader("📂 Bet History")
try:
    history = pd.read_csv("bet_history.csv")
    history["Saved"] = pd.to_datetime(history["Saved"])
    start_date = st.date_input("📅 Filter from date", value=pd.Timestamp.today() - pd.Timedelta(days=7))
    filtered = history[history["Saved"].dt.date >= start_date]
    st.dataframe(filtered.tail(50))
except:
    st.info("No saved history yet.")
