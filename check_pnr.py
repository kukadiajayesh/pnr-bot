import os, json, requests

# Automatically load variables from .env if present
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

PNR = os.environ.get("PNR") or os.environ.get("PNR_LIST", "")
if PNR:
    PNR = PNR.strip().split(",")[0].strip()
TG = os.environ.get("TG_TOKEN", "")
CHAT = os.environ.get("CHAT_ID", "")
API_KEY = os.environ.get("RAILRADAR_API_KEY") or os.environ.get("RAPID_KEY", "")
STATE_FILE = "state.json"

missing = [name for name, val in [("PNR", PNR), ("TG_TOKEN", TG), ("CHAT_ID", CHAT), ("RAILRADAR_API_KEY", API_KEY)] if not val]
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

def get_prediction(pnr):
    try:
        r = requests.get(
            f"https://api.railradar.in/v1/pnr/{pnr}/prediction",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=15,
        )
        if r.status_code == 200:
            res_json = r.json()
            if res_json.get("success") or res_json.get("status"):
                data = res_json.get("data") or {}
                header = data.get("header")
                prob = data.get("probability")
                prob_pct = data.get("probabilityPercent")
                if prob_pct is None and prob is not None:
                    prob_pct = round(prob * 100)

                if header and prob_pct is not None and f"{prob_pct}%" not in str(header):
                    return f"{header} ({prob_pct}%)"
                if header:
                    return str(header)
                if prob_pct is not None:
                    return f"{prob_pct}% confirmation chance"
        else:
            print(f"Prediction API HTTP {r.status_code} for PNR {pnr}: {r.text}")
    except Exception as e:
        print(f"Prediction request failed for PNR {pnr}: {e}")
    return None

print(f"Checking PNR: {PNR}...")
try:
    r = requests.get(
        f"https://api.railradar.in/v1/pnr/{PNR}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30,
    )
except Exception as e:
    print(f"Request failed for PNR {PNR}: {e}")
    notify(f"PNR {PNR}: Request exception: {e}")
    exit(1)

if r.status_code != 200:
    print(f"API HTTP error {r.status_code} for PNR {PNR}: {r.text}")
    notify(f"PNR {PNR}: API error {r.status_code}")
    exit(1)

res_json = r.json()
if not res_json.get("success") and not res_json.get("status"):
    error_info = res_json.get("error")
    if isinstance(error_info, dict):
        msg = error_info.get("message") or error_info.get("code") or "API returned failure"
    else:
        msg = res_json.get("message", "API returned failure")
    print(f"PNR {PNR}: API returned failure - {msg}")
    notify(f"PNR {PNR}: API error: {msg}")
    exit(1)

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

prediction_info = get_prediction(PNR)

prev = state.get(PNR)
prev_status = None
prev_pred = None
if isinstance(prev, list):
    prev_status = prev
elif isinstance(prev, dict):
    prev_status = prev.get("passengers", [])
    prev_pred = prev.get("prediction")

# If prediction call failed temporarily, retain previous prediction
if prediction_info is None and prev_pred is not None:
    prediction_info = prev_pred

has_changed = False
if prev is None:
    has_changed = True
elif isinstance(prev, list):
    # Migrating from legacy list format or status changed
    has_changed = True
elif prev_status != now:
    has_changed = True
elif prediction_info is not None and prev_pred != prediction_info:
    has_changed = True

pred_log = f", Prediction: {prediction_info}" if prediction_info else ""
chart_log = f", Chart: {chart_status}" if chart_status else ""
print(f"PNR {PNR} -> {train_name} ({train_number}), DOJ: {doj}{chart_log}{pred_log}, Status: {now}")

if has_changed:
    msg_lines = [
        f"PNR {PNR} — {train_name} ({train_number})",
        f"DOJ: {doj}",
    ]
    if chart_status:
        msg_lines.append(f"Chart: {chart_status}")
    if prediction_info:
        msg_lines.append(f"Prediction: {prediction_info}")
    msg_lines.extend(f"P{i+1}: {s}" for i, s in enumerate(now))
    notify("\n".join(msg_lines))
    state[PNR] = {
        "passengers": now,
        "prediction": prediction_info,
    }
else:
    print(f"No change in status for PNR {PNR}.")

with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)