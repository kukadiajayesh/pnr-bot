import os
import sys
import json
import requests

STATE_FILE = "state.json"

def load_env(env_path=".env"):
    """Load environment variables from a .env file if present."""
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))

load_env()

def get_state(state_file=STATE_FILE):
    """Load tracking state from json file."""
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.pop("", None)
                    return data
        except Exception as e:
            print(f"Warning: Failed to load {state_file}: {e}")
    return {}

def save_state(state, state_file=STATE_FILE):
    """Persist tracking state to json file."""
    try:
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error saving {state_file}: {e}")

def get_target_pnrs(cli_args=None, state=None):
    """
    Determine the list of PNRs to check from:
    1. CLI arguments (e.g. python check_pnr.py 1234567890 9876543210)
    2. Environment variable PNR or PNR_LIST (comma/space separated)
    3. Existing keys in state.json
    """
    if cli_args is None:
        cli_args = sys.argv[1:]

    pnrs = []
    # 1. Parse CLI arguments
    for arg in cli_args:
        for item in arg.replace(",", " ").split():
            clean = item.strip()
            if clean.isdigit() and len(clean) == 10:
                pnrs.append(clean)

    if pnrs:
        return list(dict.fromkeys(pnrs))

    # 2. Parse environment variables
    env_pnr = os.environ.get("PNR") or os.environ.get("PNR_LIST", "")
    if env_pnr:
        for item in env_pnr.replace(",", " ").split():
            clean = item.strip()
            if clean.isdigit() and len(clean) == 10:
                pnrs.append(clean)
        if pnrs:
            return list(dict.fromkeys(pnrs))

    # 3. Fallback to existing tracked PNRs in state
    if state:
        for k in state.keys():
            clean = str(k).strip()
            if clean.isdigit() and len(clean) == 10:
                pnrs.append(clean)

    return list(dict.fromkeys(pnrs))

def notify(text, tg_token=None, chat_id=None):
    """Send a Telegram alert."""
    token = tg_token or os.environ.get("TG_TOKEN", "")
    chat = chat_id or os.environ.get("CHAT_ID", "")
    print(f"[Telegram Notification]\n{text}\n")
    if not token or not chat:
        print("Skipping Telegram send: TG_TOKEN or CHAT_ID not provided.")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text},
            timeout=15,
        )
        if r.status_code != 200:
            print(f"Telegram API error {r.status_code}: {r.text}")
            return False
        else:
            print("Telegram message sent successfully (status 200).")
            return True
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
        return False

def get_prediction(pnr, api_key=None):
    """Fetch waitlist confirmation probability from RailRadar API."""
    key = api_key or os.environ.get("RAILRADAR_API_KEY") or os.environ.get("RAPID_KEY", "")
    if not key:
        return None
    try:
        r = requests.get(
            f"https://api.railradar.in/v1/pnr/{pnr}/prediction",
            headers={"Authorization": f"Bearer {key}"},
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

def fetch_pnr_status(pnr, api_key=None):
    """Fetch current PNR details from RailRadar API."""
    key = api_key or os.environ.get("RAILRADAR_API_KEY") or os.environ.get("RAPID_KEY", "")
    if not key:
        return False, "Missing RAILRADAR_API_KEY"
    try:
        r = requests.get(
            f"https://api.railradar.in/v1/pnr/{pnr}",
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        )
        if r.status_code != 200:
            return False, f"API HTTP error {r.status_code}: {r.text}"
        res_json = r.json()
        if not res_json.get("success") and not res_json.get("status"):
            error_info = res_json.get("error")
            if isinstance(error_info, dict):
                msg = error_info.get("message") or error_info.get("code") or "API returned failure"
            else:
                msg = res_json.get("message", "API returned failure")
            return False, msg
        return True, res_json
    except Exception as e:
        return False, f"Request failed: {e}"

def parse_pnr_data(api_response):
    """Extract standard fields from RailRadar PNR response."""
    d = api_response.get("data") or {}
    passenger_list = d.get("passengers") or d.get("PassengerStatus") or d.get("passengerList") or []
    passengers = []
    for p in passenger_list:
        curr = p.get("current")
        if isinstance(curr, dict):
            status_str = curr.get("formatted") or curr.get("status") or "?"
        elif curr:
            status_str = str(curr)
        else:
            status_str = p.get("CurrentStatus") or p.get("current_status") or "?"
        passengers.append(status_str)

    train = d.get("train") if isinstance(d.get("train"), dict) else {}
    train_name = train.get("name") or d.get("TrainName") or d.get("trainName", "")
    train_number = train.get("number") or d.get("TrainNo") or d.get("trainNumber", "")
    doj = train.get("journeyDate") or d.get("Doj") or d.get("dateOfJourney", "")
    charting = d.get("charting") if isinstance(d.get("charting"), dict) else {}
    chart_status = charting.get("status") or ("Chart Prepared" if d.get("ChartPrepared") else "")

    return {
        "train_name": train_name,
        "train_number": train_number,
        "doj": doj,
        "chart_status": chart_status,
        "passengers": passengers,
    }

def format_status_message(pnr, parsed_info, prediction_info=None):
    """Construct formatted text message for Telegram alerts."""
    train_name = parsed_info.get("train_name", "")
    train_number = parsed_info.get("train_number", "")
    doj = parsed_info.get("doj", "")
    chart_status = parsed_info.get("chart_status", "")
    passengers = parsed_info.get("passengers", [])

    lines = [f"PNR {pnr} — {train_name} ({train_number})".strip()]
    if doj:
        lines.append(f"DOJ: {doj}")
    if chart_status:
        lines.append(f"Chart: {chart_status}")
    if prediction_info:
        lines.append(f"Prediction: {prediction_info}")
    for i, s in enumerate(passengers):
        lines.append(f"P{i+1}: {s}")
    return "\n".join(lines)

def process_pnr(pnr, state, api_key=None, tg_token=None, chat_id=None, force_notify=False):
    """
    Process a single PNR check, update state, and send Telegram notification if changed or forced.
    Returns: (success: bool, changed: bool, message: str)
    """
    print(f"Checking PNR: {pnr}...")
    success, res = fetch_pnr_status(pnr, api_key)
    if not success:
        err_msg = f"PNR {pnr}: {res}"
        print(err_msg)
        if force_notify:
            notify(err_msg, tg_token, chat_id)
        return False, False, err_msg

    parsed = parse_pnr_data(res)
    prediction_info = get_prediction(pnr, api_key)

    now = parsed["passengers"]
    train_name = parsed["train_name"]
    train_number = parsed["train_number"]
    doj = parsed["doj"]
    chart_status = parsed["chart_status"]

    prev = state.get(pnr)
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
        has_changed = True
    elif prev_status != now:
        has_changed = True
    elif prediction_info is not None and prev_pred != prediction_info:
        has_changed = True

    pred_log = f", Prediction: {prediction_info}" if prediction_info else ""
    chart_log = f", Chart: {chart_status}" if chart_status else ""
    print(f"PNR {pnr} -> {train_name} ({train_number}), DOJ: {doj}{chart_log}{pred_log}, Status: {now}")

    msg = format_status_message(pnr, parsed, prediction_info)

    if has_changed or force_notify:
        notify(msg, tg_token, chat_id)
        state[pnr] = {
            "passengers": now,
            "prediction": prediction_info,
            "train_name": train_name,
            "train_number": train_number,
            "doj": doj,
            "chart_status": chart_status,
        }
    else:
        print(f"No change in status for PNR {pnr}.")

    return True, has_changed, msg

def main():
    tg_token = os.environ.get("TG_TOKEN", "")
    chat_id = os.environ.get("CHAT_ID", "")
    api_key = os.environ.get("RAILRADAR_API_KEY") or os.environ.get("RAPID_KEY", "")

    state = get_state()
    pnrs = get_target_pnrs(state=state)

    missing = []
    if not api_key:
        missing.append("RAILRADAR_API_KEY")
    if not pnrs:
        missing.append("PNR (via CLI, env, or state.json)")

    if missing:
        print(f"Error: Missing required parameters: {', '.join(missing)}")
        print("Usage:")
        print("  python check_pnr.py <PNR_1> <PNR_2> ...")
        print("  Or set PNR in .env or environment variable.")
        sys.exit(1)

    print(f"Monitoring {len(pnrs)} PNR(s): {', '.join(pnrs)}")

    for pnr in pnrs:
        process_pnr(pnr, state, api_key, tg_token, chat_id)

    save_state(state)

if __name__ == "__main__":
    main()