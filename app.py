import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SharpPicks AI", layout="wide")
st.title("📊 SharpPicks AI – Live Odds + Auto EV Picks")

# ⚙️ CONFIG
stake = 10
api_key = "8b1fc75ab32cdd60238394cfc0c88b83"  # Your Odds API key
region = "us"
market = "h2h"

sport_map = {
    "MLB (Baseball)": "baseball_mlb",
    "Tennis (ATP)": "tennis_atp",
    "Tennis (WTA)": "tennis_wta"
}

@st.cache_data(ttl=300)
def get_live_odds(sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?regions={region}&markets={market}&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code != 200:
        st.error("❌ Failed to fetch live odds.")
        return []
    return response.json()

def implied_prob(decimal_odds):
    return 1 / decimal_odds if decimal_odds else 0

# 🎯 Sport selection
sport_choice = st.selectbox("Select Sport", list(sport_map.keys()))
sport_key = sport_map[sport_choice]
events = get_live_odds(sport_key)

if not events:
    st.warning(f"⚠️ No live {sport_choice} odds available right now.")
    st.stop()

value_bets = []

st.subheader("📈 Best +EV Picks")
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

    # ✅ Pick the better team only once
    if ev1 > 0 or ev2 > 0:
        if ev1 > ev2:
            value_bets.append({
                "Matchup": f"{team1} vs {team2}",
                "✅ BET ON": team1,
                "Opponent": team2,
                "Odds": odds_map[team1],
                "Win %": round(prob1 * 100, 1),
                "EV": round(ev1, 2),
                "Sport": sport_choice,
                "Date": commence
            })
        else:
            value_bets.append({
                "Matchup": f"{team1} vs {team2}",
                "✅ BET ON": team2,
                "Opponent": team1,
                "Odds": odds_map[team2],
                "Win %": round(prob2 * 100, 1),
                "EV": round(ev2, 2),
                "Sport": sport_choice,
                "Date": commence
            })

# 📊 Show the bets
if value_bets:
    df = pd.DataFrame(value_bets)
    st.dataframe(df)

    st.subheader("📊 Summary")
    st.metric("Total Bets", len(df))
    st.metric("Total Expected Value", f"${df['EV'].sum():.2f}")

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
    st.info("No +EV bets found. Try again later.")

# 📂 Bet history
st.subheader("📂 Bet History")
try:
    history = pd.read_csv("bet_history.csv")
    history["Saved"] = pd.to_datetime(history["Saved"])
    start_date = st.date_input("📅 Filter from date", value=pd.Timestamp.today() - pd.Timedelta(days=7))
    filtered = history[history["Saved"].dt.date >= start_date]
    st.dataframe(filtered.tail(50))
except:
    st.info("No saved history yet.")
