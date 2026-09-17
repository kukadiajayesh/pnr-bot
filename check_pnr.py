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
API_KEY = os.environ.get("RAILRADAR_API_KEY") or os.environ.get("RAPID_KEY", "")
STATE_FILE = "state.json"

missing = [name for name, val in [("PNR_LIST", PNRS), ("TG_TOKEN", TG), ("CHAT_ID", CHAT), ("RAILRADAR_API_KEY", API_KEY)] if not val]
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
            f"https://api.railradar.in/v1/pnr/{pnr}",
            headers={"Authorization": f"Bearer {API_KEY}"},
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
    if not res_json.get("success") and not res_json.get("status"):
        error_info = res_json.get("error")
        if isinstance(error_info, dict):
            msg = error_info.get("message") or error_info.get("code") or "API returned failure"
        else:
            msg = res_json.get("message", "API returned failure")
        print(f"PNR {pnr}: API returned failure - {msg}")
        notify(f"PNR {pnr}: API error: {msg}")
        continue

    d = res_json.get("data") or {}
    passenger_list = d.get("passengers") or d.get("PassengerStatus") or d.get("passengerList") or []
    now = []
    for p in passenger_list:
        curr = p.get("current")
        if isinstance(curr, dict):
            status_str = curr.get("formatted") or curr.get("status") or "?"
        elif curr:
            status_str = str(curr)
        else:
            status_str = p.get("CurrentStatus") or p.get("current_status") or "?"
        now.append(status_str)

    train = d.get("train") if isinstance(d.get("train"), dict) else {}
    train_name = train.get("name") or d.get("TrainName") or d.get("trainName", "")
    train_number = train.get("number") or d.get("TrainNo") or d.get("trainNumber", "")
    doj = train.get("journeyDate") or d.get("Doj") or d.get("dateOfJourney", "")
    charting = d.get("charting") if isinstance(d.get("charting"), dict) else {}
    chart_status = charting.get("status") or ("Chart Prepared" if d.get("ChartPrepared") else "")

    print(f"PNR {pnr} -> {train_name} ({train_number}), DOJ: {doj}, Chart: {chart_status}, Status: {now}")

    if state.get(pnr) != now:
        msg_lines = [
            f"PNR {pnr} — {train_name} ({train_number})",
            f"DOJ: {doj}",
        ]
        if chart_status:
            msg_lines.append(f"Chart: {chart_status}")
        msg_lines.extend(f"P{i+1}: {s}" for i, s in enumerate(now))
        notify("\n".join(msg_lines))
        state[pnr] = now
    else:
        print(f"No change in status for PNR {pnr}.")

with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)