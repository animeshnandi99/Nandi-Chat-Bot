# Nandi AI — Telegram Bot

A Telegram chatbot powered by **Groq AI** (LLaMA 3), built with `python-telegram-bot`.

**Developer:** Animesh Nandi

---

## Features

- 🤖 AI-powered replies via Groq (LLaMA 3 8B)
- 🧠 Per-user conversation history during runtime
- ⌨️ Typing indicator before every response
- 🛡️ Graceful error handling
- 🚀 One-click run on Replit

---

## Quick Start on Replit

1. **Add Secrets** — open the *Secrets* tab and add:
   - `TELEGRAM_BOT_TOKEN` — get it from [@BotFather](https://t.me/BotFather) on Telegram
   - `GROQ_API_KEY` — get it from [console.groq.com](https://console.groq.com)

2. **Run** — click the **Run** button (or the *Nandi AI Bot* workflow). The bot starts automatically.

3. **Chat** — open Telegram, find your bot, and send `/start`.

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
├── main.py           # Bot logic (handlers, Groq integration, history)
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
| `/start` | Welcome message and instructions   |

Any other text message is sent to Groq AI and the reply is returned to the user.

---

## Configuration

You can tweak these constants at the top of `main.py`:

| Constant      | Default           | Description                          |
|---------------|-------------------|--------------------------------------|
| `MAX_HISTORY` | `20`              | Messages kept per user in memory     |
| `model`       | `llama3-8b-8192`  | Groq model to use                    |
| `temperature` | `0.7`             | Response creativity (0.0 – 1.0)      |
| `max_tokens`  | `1024`            | Max tokens in each AI response       |

---

## License

MIT — feel free to fork and build on top of this.
