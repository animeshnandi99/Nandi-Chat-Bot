# Nandi AI — Telegram Bot

A Telegram chatbot powered by **Groq AI** (LLaMA 3), built with `python-telegram-bot`.

**Developer:** Animesh Nandi

---

## Features

- 🤖 AI-powered replies via Groq (LLaMA 3 70B & 8B models)
- 🧠 Per-user conversation history during runtime
- ⌨️ Typing indicator before every response
- 🛡️ Graceful error handling with auto-restart
- 🔄 Model switching (`/model 1` or `/model 2`)
- 📊 Built-in health endpoint for uptime monitoring
- 📋 Native Telegram command menu (`/` button)

---

## Quick Start on Replit

1. **Add Secrets** — open the *Secrets* tab and add:
   - `TELEGRAM_BOT_TOKEN` — get it from [@BotFather](https://t.me/BotFather) on Telegram
   - `GROQ_API_KEY` — get it from [console.groq.com](https://console.groq.com)

2. **Run** — the *Nandi AI Bot* workflow starts automatically. The bot is ready to chat.

3. **Chat** — open Telegram, find your bot, and send `/start`.

---

## 24/7 Uptime

The bot includes an **auto-restart supervisor** — if it ever crashes, it restarts automatically after a brief delay.

For true 24/7 availability even when you close the tab, **publish/deploy the project** to Replit's always-on infrastructure.

---

## Local Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd nandi-ai

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
cp .env.example .env
# Edit .env and fill in TELEGRAM_BOT_TOKEN and GROQ_API_KEY

# 4. Run the bot
python main.py
```

> On Linux/macOS you can also `export` the variables directly in your shell instead of using a `.env` file.

---

## Project Structure

```
.
├── main.py           # Bot logic + auto-restart supervisor + health server
├── requirements.txt  # Python dependencies
├── .env.example      # Template for environment variables
└── README.md         # This file
```

---

## Environment Variables

| Variable             | Description                                   |
|----------------------|-----------------------------------------------|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather                         |
| `GROQ_API_KEY`       | API key from console.groq.com                 |

---

## Commands

| Command  | Description                        |
|----------|------------------------------------|
| `/start` | Welcome message                    |
| `/help`  | Full usage guide                   |
| `/model` | View or switch AI model            |
| `/status`| Current model & history count      |
| `/clear` | Clear conversation history         |

Any other text message is sent to Groq AI and the reply is returned to the user.

---

## Model Switching

The bot supports two Groq models:

| # | Model | Best for |
|---|-------|----------|
| 1 | LLaMA 3.3 70B Versatile *(default)* | Complex reasoning, detailed answers |
| 2 | LLaMA 3.1 8B Instant | Quick, snappy replies |

Use `/model 1` or `/model 2` to switch. History is cleared on switch.

---

## Health Endpoint

The bot exposes a lightweight HTTP health server on **port 9000**:

```
GET /
→ {"status":"ok","bot":"Nandi AI"}
```

You can use this with external ping services (e.g. UptimeRobot) to keep the bot awake and monitor uptime.

---

## Auto-Restart

The `main.py` entry point includes a **supervisor loop** that:

1. Starts the bot in a supervised process
2. If the bot crashes for any reason, waits briefly then **auto-restarts** it
3. Uses exponential back-off (capped at 60s) to avoid rapid restart loops
4. Gracefully exits on `Ctrl+C`

This means the bot recovers from unexpected errors without manual intervention.

---

## Configuration

You can tweak these constants at the top of `main.py`:

| Constant      | Default           | Description                          |
|---------------|-------------------|--------------------------------------|
| `MAX_HISTORY` | `20`              | Messages kept per user in memory     |
| `temperature` | `0.7`             | Response creativity (0.0 – 1.0)      |
| `max_tokens`  | `1024`            | Max tokens in each AI response       |

---

## License

MIT — feel free to fork and build on top of this.
