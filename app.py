import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SharpPicks AI", layout="wide")
st.title("📊 SharpPicks AI – Live Auto Picks + Charts (Updated Every 60s)")

# ⚙️ CONFIG
stake = 10
api_key = "8b1fc75ab32cdd60238394cfc0c88b83"
region = "us"
market = "h2h"

sport_map = {
    "MLB (Baseball)": "baseball_mlb",
    "Tennis (ATP)": "tennis_atp",
    "Tennis (WTA)": "tennis_wta"
}

@st.cache_data(ttl=60)
def get_live_odds(sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?regions={region}&markets={market}&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code != 200:
        st.error("❌ Failed to fetch live odds.")
        return []
    return response.json()

def implied_prob(decimal_odds):
    return 1 / decimal_odds if decimal_odds else 0

sport_choice = st.selectbox("Select Sport", list(sport_map.keys()))
sport_key = sport_map[sport_choice]

st.markdown("⏱️ Auto-refreshing every 60 seconds")
st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

events = get_live_odds(sport_key)
value_bets = []

if not events:
    st.warning("⚠️ No live events available.")
    st.stop()

for event in events:
    team1 = event.get("home_team", "Team A")
    team2 = event.get("away_team", "Team B")
    commence = event.get("commence_time", "")
    event_id = event.get("id", f"{team1}_{team2}_{commence}")
    bookmakers = event.get("bookmakers", [])
    if not bookmakers:
        continue

    outcomes = bookmakers[0]["markets"][0]["outcomes"]
    odds_map = {o["name"]: o["price"] for o in outcomes}
    if team1 not in odds_map or team2 not in odds_map:
        continue

    prob1 = implied_prob(odds_map[team2])
    prob2 = implied_prob(odds_map[team1])

    ev1 = prob1 * ((odds_map[team1] - 1) * stake) - (1 - prob1) * stake
    ev2 = prob2 * ((odds_map[team2] - 1) * stake) - (1 - prob2) * stake

    if ev1 > ev2 and ev1 > 0:
        value_bets.append({
            "Matchup": f"{team1} vs {team2}",
            "✅ BET ON": team1,
            "Odds": odds_map[team1],
            "Win %": round(prob1 * 100, 1),
            "EV": round(ev1, 2),
            "Sport": sport_choice,
            "Date": commence
        })
    elif ev2 > ev1 and ev2 > 0:
        value_bets.append({
            "Matchup": f"{team1} vs {team2}",
            "✅ BET ON": team2,
            "Odds": odds_map[team2],
            "Win %": round(prob2 * 100, 1),
            "EV": round(ev2, 2),
            "Sport": sport_choice,
            "Date": commence
        })

if value_bets:
    df = pd.DataFrame(value_bets)
    st.subheader("💸 Best Picks Right Now")
    st.dataframe(df)

    st.subheader("📊 EV Summary")
    st.metric("Total Bets", len(df))
    st.metric("Total Expected Value", f"${df['EV'].sum():.2f}")

    # 📈 Live Chart 1: EV by Team (Bar Chart)
    st.subheader("📉 Expected Value by Team")
    st.bar_chart(data=df.set_index("✅ BET ON")["EV"])

    # 📈 Live Chart 2: EV Over Time (if saved)
    try:
        history = pd.read_csv("bet_history.csv")
        history["Saved"] = pd.to_datetime(history["Saved"])
        history_sorted = history.sort_values("Saved")
        ev_trend = history_sorted.groupby("Saved")["EV"].sum().cumsum()
        st.subheader("📈 EV Over Time")
        st.line_chart(ev_trend)
    except:
        st.info("No history yet for EV chart.")

    if st.button("💾 Save Picks"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df["Saved"] = now
        try:
            history = pd.read_csv("bet_history.csv")
            df = pd.concat([history, df], ignore_index=True)
        except FileNotFoundError:
            pass
        df.to_csv("bet_history.csv", index=False)
        st.success("Saved to bet_history.csv ✅")

else:
    st.info("No +EV bets found right now.")

# 📂 History Display
st.subheader("📂 Bet History")
try:
    history = pd.read_csv("bet_history.csv")
    history["Saved"] = pd.to_datetime(history["Saved"])
    start_date = st.date_input("📅 Filter from date", value=pd.Timestamp.today() - pd.Timedelta(days=7))
    filtered = history[history["Saved"].dt.date >= start_date]
    st.dataframe(filtered.tail(50))
except:
    st.info("No saved history yet.")
