import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz

st.set_page_config(page_title="SharpPicks AI", layout="wide")
st.title("📊 SharpPicks AI – Smart Bets + Live Odds (PT Time)")

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

def format_game_time(utc_str):
    utc_time = datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
    pt_time = utc_time.astimezone(pytz.timezone("US/Pacific"))
    return pt_time.strftime("%a, %b %d – %I:%M %p PT")

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
    game_time = format_game_time(commence)

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

    if max(ev1, ev2) > 0:
        if ev1 >= ev2:
            bet_team = team1
            opponent = team2
            odds = odds_map[team1]
            win_pct = round(prob1 * 100, 1)
            ev = round(ev1, 2)
        else:
            bet_team = team2
            opponent = team1
            odds = odds_map[team2]
            win_pct = round(prob2 * 100, 1)
            ev = round(ev2, 2)

        value_bets.append({
            "Matchup": f"{team1} vs {team2}",
            "✅ BET ON": bet_team,
            "Odds": f"{team1} ({odds_map[team1]}) | {team2} ({odds_map[team2]})",
            "Win %": win_pct,
            "EV": ev,
            "Game Time": game_time,
            "Sport": sport_choice
        })

if value_bets:
    df = pd.DataFrame(value_bets)
    st.subheader("🔥 Best +EV Picks (Updated)")
    st.dataframe(df)

    st.subheader("📊 EV by Team")
    st.bar_chart(df.set_index("✅ BET ON")["EV"])

    st.subheader("📈 EV Trend (if saved)")
    try:
        history = pd.read_csv("bet_history.csv")
        history["Saved"] = pd.to_datetime(history["Saved"])
        ev_trend = history.groupby("Saved")["EV"].sum().cumsum()
        st.line_chart(ev_trend)
    except:
        st.info("No history yet for EV chart.")

    if st.button("💾 Save These Picks"):
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
    st.info("No +EV picks found right now.")

st.subheader("📂 Bet History")
try:
    history = pd.read_csv("bet_history.csv")
    history["Saved"] = pd.to_datetime(history["Saved"])
    start_date = st.date_input("📅 Filter from date", value=pd.Timestamp.today() - pd.Timedelta(days=7))
    filtered = history[history["Saved"].dt.date >= start_date]
    st.dataframe(filtered.tail(50))
except:
    st.info("No saved history yet.")
