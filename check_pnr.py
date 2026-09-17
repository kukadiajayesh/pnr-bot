import os, json, requests

PNRS = os.environ["PNR_LIST"].split(",")
TG = os.environ["TG_TOKEN"]
CHAT = os.environ["CHAT_ID"]
STATE_FILE = "state.json"

state = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}

def notify(text):
    requests.post(f"https://api.telegram.org/bot{TG}/sendMessage",
                  json={"chat_id": CHAT, "text": text})

for pnr in PNRS:
    pnr = pnr.strip()
    r = requests.get(
        "https://irctc1.p.rapidapi.com/api/v3/getPNRStatus",
        params={"pnrNumber": pnr},
        headers={"X-RapidAPI-Key": os.environ["RAPID_KEY"],
                 "X-RapidAPI-Host": "irctc1.p.rapidapi.com"},
        timeout=30)

    if r.status_code != 200:
        notify(f"PNR {pnr}: API error {r.status_code}")
        continue

    d = r.json().get("data", {})
    now = [p.get("current_status", "?") for p in d.get("passengerList", [])]

    if state.get(pnr) != now:
        notify(f"PNR {pnr} — {d.get('trainName','')} ({d.get('trainNumber','')})\n"
               f"{d.get('dateOfJourney','')}\n" + "\n".join(
               f"P{i+1}: {s}" for i, s in enumerate(now)))
        state[pnr] = now

json.dump(state, open(STATE_FILE, "w"), indent=1)