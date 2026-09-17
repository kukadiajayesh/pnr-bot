# 🚆 PNR Watch Bot

An automated Indian Railways (IRCTC) PNR status monitor and Telegram notification bot.

It tracks your 10-digit PNR number, fetches live passenger booking/current status, confirmation predictions, and chart preparation status using the [RailRadar API](https://api.railradar.in). When changes are detected, it dispatches instant alerts to a designated Telegram chat.

Runs locally or entirely automated in the cloud via GitHub Actions.

---

## ✨ Features

- **Dynamic PNR Tracking**: Monitor one or multiple 10-digit PNRs simultaneously via CLI arguments, environment variables, or interactive chat commands.
- **Interactive Telegram Bot**: Send `/check <PNR>` for instant status, `/track <PNR>` to monitor, and `/list` to view active tickets.
- **Smart Change Detection**: Compares current passenger statuses and confirmation predictions with `state.json`. Alerts are sent only when there is an actual status change or confirmation prediction update.
- **Confirmation Probability**: Fetches RailRadar confirmation prediction percentage and probability assessment for waitlisted tickets.
- **Charting Status**: Monitors whether the reservation chart has been prepared.
- **Rich Telegram Alerts**: Delivers formatted status notifications directly to your chat or channel.
- **Zero-Server GitHub Actions Runner**: Runs periodically on GitHub Actions cron schedule (`0 */2 * * *` — every 2 hours) or manually with dynamic PNR inputs, committing the updated state back to the repository.

---

## 📲 Telegram Notification Preview

```text
PNR 1234567890 — GUJARAT SF EXP (22954)
DOJ: 2026-09-20
Chart: Chart Not Prepared
Prediction: High (92%)
P1: CNF / B3 / 45
P2: CNF / B3 / 48
```

---

## ⚙️ Environment Variables

Configure these variables locally in a `.env` file or as GitHub Repository Secrets / Variables:

| Variable | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `PNR` | **Yes** | 10-digit PNR number(s) (single or comma-separated) | `1234567890` or `1234567890,9876543210` |
| `TG_TOKEN` | **Yes** | Telegram Bot API token from [@BotFather](https://t.me/BotFather) | `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ` |
| `CHAT_ID` | **Yes** | Telegram Chat or Group ID to receive alerts / authorized chat | `12345678` or `-100123456789` |
| `RAILRADAR_API_KEY` | **Yes** | RailRadar API Bearer Token from [api.railradar.in](https://api.railradar.in) | `your_railradar_api_key` |
| `CHECK_INTERVAL_MINUTES` | No | Periodic check frequency for `bot.py` (default: 60) | `60` |

> [!NOTE]
> `RAPID_KEY` is also accepted as a fallback if `RAILRADAR_API_KEY` is not set. `PNR_LIST` is also accepted as a fallback for `PNR`.

---

## 🚀 Usage

### 1. Configure credentials
Copy the sample environment file and populate your details:
```bash
cp .env.example .env
```
Edit `.env`:
```env
PNR=1234567890,9876543210
TG_TOKEN=your_telegram_bot_token_here
CHAT_ID=your_chat_id_here
RAILRADAR_API_KEY=your_railradar_api_key_here
```

### 2. Option A: CLI PNR Checker (`check_pnr.py`)

Run one-off checks or periodic cron jobs:

```bash
# Check PNRs defined in .env / state.json
python check_pnr.py

# Check specific PNR(s) dynamically via command-line arguments
python check_pnr.py 1234567890
python check_pnr.py 1234567890 9876543210
```

### 3. Option B: Interactive Telegram Bot (`bot.py`)

Run an interactive 24/7 Telegram bot that responds to commands and automatically monitors tracked PNRs in the background:

```bash
python bot.py
```

**Supported Commands in Telegram:**
- `/check <PNR>` — Query current status immediately (does not add to tracking).
- `/track <PNR>` — Add PNR to persistent `state.json` and watch for changes.
- `/untrack <PNR>` — Stop monitoring a PNR.
- `/list` — View all monitored PNRs and their latest statuses.
- `/help` — Display bot commands.
- *Or simply paste any 10-digit PNR into the chat to check it!*

---

## 🤖 Automated Execution with GitHub Actions

The repository includes a ready-to-use GitHub Actions workflow in [`.github/workflows/pnr_watch.yml`](.github/workflows/pnr_watch.yml).

### Execution Triggers:
- **Scheduled Cron**: Runs every 2 hours (`0 */2 * * *`) across all PNRs configured in repository secrets/variables or stored in `state.json`.
- **Manual Workflow Dispatch**: Run on-demand anytime from the GitHub Actions tab. You can optionally enter custom PNR number(s) directly in the **"PNR number(s) to check"** input field!

### Setup Steps:
1. Fork or push this repository to GitHub.
2. Go to **Settings** > **Secrets and variables** > **Actions**.
3. Under **Repository secrets** (or **Variables**), add:
   - `PNR` (optional if provided manually in dispatch or in `state.json`)
   - `TG_TOKEN`
   - `CHAT_ID`
   - `RAILRADAR_API_KEY`
4. **Enable Workflow Write Permissions** (required for committing `state.json` updates):
   - Go to **Settings** > **Actions** > **General**.
   - Under **Workflow permissions**, select **Read and write permissions**.
   - Click **Save**.

---

## 💾 State Persistence (`state.json`)

The bot persists the last-observed status for each PNR in `state.json`:
```json
{
  "1234567890": {
    "passengers": [
      "RAC/64",
      "RAC/65"
    ],
    "prediction": "High (92%)"
  }
}
```
When GitHub Actions runs, any updates to `state.json` are automatically committed and pushed back to the `main` branch to ensure continuity across runs.

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
