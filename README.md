# 🚆 PNR Watch Bot

An automated Indian Railways (IRCTC) PNR status monitor and Telegram notification bot.

It tracks your 10-digit PNR number, fetches live passenger booking/current status, confirmation predictions, and chart preparation status using the [RailRadar API](https://api.railradar.in). When changes are detected, it dispatches instant alerts to a designated Telegram chat.

Runs locally or entirely automated in the cloud via GitHub Actions.

---

## ✨ Features

- **PNR Tracking**: Monitor your 10-digit PNR status seamlessly.
- **Smart Change Detection**: Compares current passenger statuses and confirmation predictions with `state.json`. Alerts are sent only when there is an actual status change or confirmation prediction update.
- **Confirmation Probability**: Fetches RailRadar confirmation prediction percentage and probability assessment for waitlisted tickets.
- **Charting Status**: Monitors whether the reservation chart has been prepared.
- **Rich Telegram Alerts**: Delivers formatted status notifications directly to your chat or channel.
- **Zero-Server GitHub Actions Runner**: Runs periodically on GitHub Actions cron schedule (`0 */2 * * *` — every 2 hours) and commits the updated state back to the repository.

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
| `PNR` | **Yes** | 10-digit PNR number | `1234567890` |
| `TG_TOKEN` | **Yes** | Telegram Bot API token from [@BotFather](https://t.me/BotFather) | `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ` |
| `CHAT_ID` | **Yes** | Telegram Chat or Group ID to receive alerts | `12345678` or `-100123456789` |
| `RAILRADAR_API_KEY` | **Yes** | RailRadar API Bearer Token from [api.railradar.in](https://api.railradar.in) | `your_railradar_api_key` |

> [!NOTE]
> `RAPID_KEY` is also accepted as a fallback if `RAILRADAR_API_KEY` is not set. `PNR_LIST` is also accepted as a fallback for `PNR`.

---

## 🚀 Quick Start (Local)

### 1. Clone the repository
```bash
git clone https://github.com/kukadiajayesh/pnr-bot.git
cd pnr-bot
```

### 2. Set up Python virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests
```

### 3. Configure credentials
Copy the sample environment file and populate your details:
```bash
cp .env.example .env
```
Edit `.env`:
```env
PNR=1234567890
TG_TOKEN=your_telegram_bot_token_here
CHAT_ID=your_chat_id_here
RAILRADAR_API_KEY=your_railradar_api_key_here
```

### 4. Run the check
```bash
python check_pnr.py
```

---

## 🤖 Automated Execution with GitHub Actions

The repository includes a ready-to-use GitHub Actions workflow in [`.github/workflows/pnr_watch.yml`](.github/workflows/pnr_watch.yml).

### Schedule
- **Cron**: Runs every 2 hours (`0 */2 * * *`).
- **Manual Trigger**: Can be manually triggered anytime via GitHub's **Actions** tab using **Run workflow**.

### Setup Steps:
1. Fork or push this repository to GitHub.
2. Go to **Settings** > **Secrets and variables** > **Actions**.
3. Under **Repository secrets** (or **Variables**), add:
   - `PNR`
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
