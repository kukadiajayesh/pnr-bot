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

if not TG or not CHAT or not PNRS:
    print("Error: Missing required environment variables (PNR_LIST, TG_TOKEN, CHAT_ID).")
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
    # Dummy IRCTC response for testing Telegram sendMessage feature
    res_json = {
        "status": True,
        "message": "Success",
        "data": {
            "Pnr": pnr,
            "TrainNo": "12951",
            "TrainName": "MUMBAI RAJDHANI",
            "Doj": "25-10-2026",
            "PassengerStatus": [
                {"Passenger": 1, "CurrentStatus": "CNF / B1 / 21"},
                {"Passenger": 2, "CurrentStatus": "CNF / B1 / 22"},
            ],
        },
    }

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