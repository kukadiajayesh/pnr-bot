import os
import sys
import time
import threading
import requests
from check_pnr import (
    load_env,
    get_state,
    save_state,
    fetch_pnr_status,
    get_prediction,
    parse_pnr_data,
    format_status_message,
    process_pnr,
    notify,
)

load_env()

TG_TOKEN = os.environ.get("TG_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
API_KEY = os.environ.get("RAILRADAR_API_KEY") or os.environ.get("RAPID_KEY", "")
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "60"))

state_lock = threading.Lock()

def reply_telegram(chat_id, text, reply_to_message_id=None, parse_mode="Markdown"):
    """Send a reply message back to Telegram."""
    if not TG_TOKEN:
        print("Error: TG_TOKEN is missing.")
        return
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json=payload,
            timeout=15,
        )
        if r.status_code != 200:
            # Retry without markdown if markdown parsing fails
            if parse_mode:
                payload.pop("parse_mode", None)
                requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                    json=payload,
                    timeout=15,
                )
    except Exception as e:
        print(f"Failed to send Telegram reply: {e}")

def is_authorized(from_chat_id):
    """Check if the sender matches configured CHAT_ID (if CHAT_ID is set)."""
    if not CHAT_ID:
        return True
    return str(from_chat_id).strip() == str(CHAT_ID).strip()

def handle_command(text, chat_id, message_id):
    """Process incoming bot command or text."""
    parts = text.strip().split()
    cmd = parts[0].lower() if parts else ""
    # Strip bot username if mentioned (e.g. /check@bot_name)
    if "@" in cmd:
        cmd = cmd.split("@")[0]

    # Quick check if user just sent a 10-digit number
    if text.strip().isdigit() and len(text.strip()) == 10:
        pnr = text.strip()
        do_check(pnr, chat_id, message_id)
        return

    if cmd in ("/start", "/help"):
        help_msg = (
            "🚆 *PNR Watch Bot*\n\n"
            "*Commands:*\n"
            "• `/check <PNR>` — Check live status instantly\n"
            "• `/track <PNR>` — Start monitoring PNR for changes\n"
            "• `/untrack <PNR>` — Stop monitoring PNR\n"
            "• `/list` — List all tracked PNRs\n"
            "• `/help` — Show this guide\n\n"
            "💡 _Tip: You can also simply send a 10-digit PNR directly!_"
        )
        reply_telegram(chat_id, help_msg, reply_to_message_id=message_id)

    elif cmd == "/check":
        if len(parts) < 2:
            reply_telegram(chat_id, "⚠️ Usage: `/check <10-digit PNR>`", reply_to_message_id=message_id)
            return
        pnr = parts[1].strip()
        do_check(pnr, chat_id, message_id)

    elif cmd == "/track":
        if len(parts) < 2:
            reply_telegram(chat_id, "⚠️ Usage: `/track <10-digit PNR>`", reply_to_message_id=message_id)
            return
        pnr = parts[1].strip()
        do_track(pnr, chat_id, message_id)

    elif cmd == "/untrack":
        if len(parts) < 2:
            reply_telegram(chat_id, "⚠️ Usage: `/untrack <10-digit PNR>`", reply_to_message_id=message_id)
            return
        pnr = parts[1].strip()
        do_untrack(pnr, chat_id, message_id)

    elif cmd == "/list":
        do_list(chat_id, message_id)

    else:
        reply_telegram(
            chat_id,
            "❓ Unknown command. Send `/help` for available commands, or enter a 10-digit PNR.",
            reply_to_message_id=message_id,
        )

def do_check(pnr, chat_id, message_id):
    if not (pnr.isdigit() and len(pnr) == 10):
        reply_telegram(chat_id, f"⚠️ Invalid PNR `{pnr}`. PNR must be a 10-digit number.", reply_to_message_id=message_id)
        return

    reply_telegram(chat_id, f"🔍 Checking status for PNR `{pnr}`...", reply_to_message_id=message_id)
    success, res = fetch_pnr_status(pnr, API_KEY)
    if not success:
        reply_telegram(chat_id, f"❌ Failed to fetch PNR {pnr}:\n{res}", reply_to_message_id=message_id)
        return

    parsed = parse_pnr_data(res)
    pred = get_prediction(pnr, API_KEY)
    msg = format_status_message(pnr, parsed, pred)
    reply_telegram(chat_id, msg, reply_to_message_id=message_id)

def do_track(pnr, chat_id, message_id):
    if not (pnr.isdigit() and len(pnr) == 10):
        reply_telegram(chat_id, f"⚠️ Invalid PNR `{pnr}`. PNR must be a 10-digit number.", reply_to_message_id=message_id)
        return

    reply_telegram(chat_id, f"⏳ Adding PNR `{pnr}` to watch list and fetching initial status...", reply_to_message_id=message_id)
    with state_lock:
        state = get_state()
        success, _, msg = process_pnr(pnr, state, API_KEY, TG_TOKEN, chat_id, force_notify=False)
        save_state(state)

    if success:
        reply_telegram(
            chat_id,
            f"✅ *Tracking enabled for PNR {pnr}*.\nYou will be alerted automatically when your status changes.\n\n{msg}",
            reply_to_message_id=message_id,
        )
    else:
        reply_telegram(chat_id, f"❌ Could not track PNR {pnr}:\n{msg}", reply_to_message_id=message_id)

def do_untrack(pnr, chat_id, message_id):
    with state_lock:
        state = get_state()
        if pnr in state:
            del state[pnr]
            save_state(state)
            reply_telegram(chat_id, f"🗑 Stopped tracking PNR `{pnr}`.", reply_to_message_id=message_id)
        else:
            reply_telegram(chat_id, f"ℹ️ PNR `{pnr}` was not in the tracking list.", reply_to_message_id=message_id)

def do_list(chat_id, message_id):
    with state_lock:
        state = get_state()

    if not state:
        reply_telegram(
            chat_id,
            "📭 No PNRs currently tracked.\n\nUse `/track <PNR>` to start monitoring a ticket.",
            reply_to_message_id=message_id,
        )
        return

    lines = ["📋 *Currently Tracked PNRs:*\n"]
    for pnr, info in state.items():
        if isinstance(info, dict):
            train = info.get("train_name", "")
            train_no = info.get("train_number", "")
            passengers = ", ".join(info.get("passengers", [])) or "No status recorded"
            pred = f" | {info.get('prediction')}" if info.get("prediction") else ""
            train_desc = f" ({train} {train_no})" if train or train_no else ""
            lines.append(f"• `{pnr}`{train_desc}\n   ↳ {passengers}{pred}")
        elif isinstance(info, list):
            lines.append(f"• `{pnr}`\n   ↳ {', '.join(info)}")

    reply_telegram(chat_id, "\n\n".join(lines), reply_to_message_id=message_id)

def background_watcher():
    """Periodically check all tracked PNRs in state.json."""
    interval_secs = max(CHECK_INTERVAL_MINUTES, 5) * 60
    print(f"[Watcher] Background watcher started (checking every {CHECK_INTERVAL_MINUTES} minutes).")
    while True:
        time.sleep(interval_secs)
        with state_lock:
            state = get_state()
            pnrs = list(state.keys())
            if pnrs:
                print(f"[Watcher] Running scheduled check for {len(pnrs)} PNR(s): {', '.join(pnrs)}")
                for pnr in pnrs:
                    process_pnr(pnr, state, API_KEY, TG_TOKEN, CHAT_ID)
                save_state(state)

def run_bot():
    if not TG_TOKEN:
        print("Error: Missing TG_TOKEN in environment or .env file.")
        sys.exit(1)
    if not API_KEY:
        print("Error: Missing RAILRADAR_API_KEY in environment or .env file.")
        sys.exit(1)

    print("=" * 50)
    print("🤖 PNR Telegram Bot is starting...")
    if CHAT_ID:
        print(f"🔒 Authorized Chat ID: {CHAT_ID}")
    else:
        print("⚠️ Warning: CHAT_ID is not set. The bot will accept commands from any chat.")
    print("=" * 50)

    # Start background watcher daemon
    watcher_thread = threading.Thread(target=background_watcher, daemon=True)
    watcher_thread.start()

    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset

            r = requests.get(
                f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                params=params,
                timeout=40,
            )

            if r.status_code == 200:
                data = r.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    if not msg or "text" not in msg:
                        continue

                    sender_chat_id = msg["chat"]["id"]
                    msg_id = msg["message_id"]
                    text = msg["text"]

                    if not is_authorized(sender_chat_id):
                        print(f"Ignored unauthorized message from chat {sender_chat_id}: {text}")
                        reply_telegram(
                            sender_chat_id,
                            f"⛔ Unauthorized access. Your Chat ID is `{sender_chat_id}`.",
                            reply_to_message_id=msg_id,
                        )
                        continue

                    print(f"[Command] Received: '{text}' from chat {sender_chat_id}")
                    handle_command(text, sender_chat_id, msg_id)

            elif r.status_code == 409:
                print("Error: Conflict (409). Another bot instance is polling this token. Waiting 10s...")
                time.sleep(10)
            else:
                print(f"getUpdates error HTTP {r.status_code}: {r.text}")
                time.sleep(5)

        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ConnectionError:
            print("Network connection error. Retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error in polling loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\nBot stopped by user. Goodbye!")
