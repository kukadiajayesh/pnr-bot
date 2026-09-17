import os, json, requests

# Automatically load variables from .env if present
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

PNRS = [p.strip() for p in os.environ.get("PNR_LIST", "").split(",") if p.strip()]
TG = os.environ.get("TG_TOKEN", "")
CHAT = os.environ.get("CHAT_ID", "")
RAPID_KEY = os.environ.get("RAPID_KEY", "")
STATE_FILE = "state.json"

missing = [name for name, val in [("PNR_LIST", PNRS), ("TG_TOKEN", TG), ("CHAT_ID", CHAT), ("RAPID_KEY", RAPID_KEY)] if not val]
if missing:
    print(f"Error: Missing required environment variables: {', '.join(missing)}")
    exit(1)

state = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}
state.pop("", None)

def notify(text):
    print(f"[Telegram Notification]\n{text}\n")
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG}/sendMessage",
            json={"chat_id": CHAT, "text": text},
            timeout=15,
        )
        if r.status_code != 200:
            print(f"Telegram API error {r.status_code}: {r.text}")
        else:
            print(f"Telegram message sent successfully (status 200).")
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")

for pnr in PNRS:
    print(f"Checking PNR: {pnr}...")
    try:
        r = requests.get(
            "https://irctc1.p.rapidapi.com/api/v3/getPNRStatus",
            params={"pnrNumber": pnr},
            headers={
                "X-RapidAPI-Key": RAPID_KEY,
                "X-RapidAPI-Host": "irctc1.p.rapidapi.com",
            },
            timeout=30,
        )
    except Exception as e:
        print(f"Request failed for PNR {pnr}: {e}")
        notify(f"PNR {pnr}: Request exception: {e}")
        continue

    if r.status_code != 200:
        print(f"API HTTP error {r.status_code} for PNR {pnr}: {r.text}")
        notify(f"PNR {pnr}: API error {r.status_code}")
        continue

    res_json = r.json()
    if not res_json.get("status"):
        msg = res_json.get("message", "API returned failure")
        print(f"PNR {pnr}: API returned status false - {msg}")
        notify(f"PNR {pnr}: API error: {msg}")
        continue

    d = res_json.get("data") or {}
    passenger_list = d.get("PassengerStatus") or d.get("passengerList") or []
    now = [
        p.get("CurrentStatus") or p.get("current_status") or "?"
        for p in passenger_list
    ]

    train_name = d.get("TrainName") or d.get("trainName", "")
    train_number = d.get("TrainNo") or d.get("trainNumber", "")
    doj = d.get("Doj") or d.get("dateOfJourney", "")

    print(f"PNR {pnr} -> {train_name} ({train_number}), DOJ: {doj}, Status: {now}")

    if state.get(pnr) != now:
        notify(f"PNR {pnr} — {train_name} ({train_number})\n"
               f"{doj}\n" + "\n".join(
               f"P{i+1}: {s}" for i, s in enumerate(now)))
        state[pnr] = now
    else:
        print(f"No change in status for PNR {pnr}.")

with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)