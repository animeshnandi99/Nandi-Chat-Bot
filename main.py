"""
Nandi AI - Telegram Bot powered by Groq AI
Developer: Animesh Nandi
"""

import os
import sys
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from groq import Groq
from telegram import Update, BotCommand
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise EnvironmentError("TELEGRAM_BOT_TOKEN is not set. Add it to your Secrets.")
if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY is not set. Add it to your Secrets.")

# ─── Groq Client ──────────────────────────────────────────────────────────────
groq_client = Groq(api_key=GROQ_API_KEY)

# ─── Available Models ─────────────────────────────────────────────────────────
MODELS: dict[str, dict] = {
    "1": {
        "id": "llama-3.3-70b-versatile",
        "label": "LLaMA 3.3 70B Versatile",
        "description": "Most capable — best for complex reasoning and detailed answers",
    },
    "2": {
        "id": "llama-3.1-8b-instant",
        "label": "LLaMA 3.1 8B Instant",
        "description": "Lightweight & fast — best for quick, snappy replies",
    },
}

DEFAULT_MODEL_KEY = "1"

# ─── In-memory state per user ─────────────────────────────────────────────────
conversation_histories: dict[int, list[dict]] = {}
user_model_keys: dict[int, str] = {}

SYSTEM_PROMPT = (
    "You are Nandi AI, a helpful and friendly AI assistant built inside Telegram. "
    "You are created by Animesh Nandi. "
    "Answer questions clearly, concisely, and helpfully. "
    "When code is involved, use proper formatting."
)

MAX_HISTORY = 20

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_history(user_id: int) -> list[dict]:
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []
    return conversation_histories[user_id]


def trim_history(user_id: int) -> None:
    history = conversation_histories.get(user_id, [])
    if len(history) > MAX_HISTORY:
        conversation_histories[user_id] = history[-MAX_HISTORY:]


def get_model_key(user_id: int) -> str:
    return user_model_keys.get(user_id, DEFAULT_MODEL_KEY)


def get_model_id(user_id: int) -> str:
    return MODELS[get_model_key(user_id)]["id"]


async def get_ai_response(user_id: int, user_message: str) -> str:
    history = get_history(user_id)
    history.append({"role": "user", "content": user_message})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    response = groq_client.chat.completions.create(
        model=get_model_id(user_id),
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
    )

    ai_reply = response.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": ai_reply})
    trim_history(user_id)
    return ai_reply


# ─── Handlers ─────────────────────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome to *Nandi AI*, {user.first_name}!\n"
        "I'm your AI assistant developed by Animesh Nandi.\n\n"
        "Just send me any message and I'll reply using AI.",
        parse_mode="Markdown",
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🆘 *Nandi AI — Help*\n\n"
        "*Commands:*\n"
        "  /start — Welcome message\n"
        "  /help — Show this help menu\n"
        "  /model — View & switch AI models\n"
        "  /status — Show your current settings\n"
        "  /clear — Clear your conversation history\n\n"
        "*How to use:*\n"
        "Simply type any question or message and I'll respond using AI. "
        "I remember your conversation history during the session so you can ask follow-up questions naturally.\n\n"
        "*Switching models:*\n"
        "Use `/model 1` for the powerful 70B model or `/model 2` for the fast 8B model.\n\n"
        "*Developer:* Animesh Nandi",
        parse_mode="Markdown",
    )


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    model_key = get_model_key(user_id)
    model = MODELS[model_key]
    history_count = len(get_history(user_id))
    msg_word = "message" if history_count == 1 else "messages"

    await update.message.reply_text(
        "📊 *Your Current Status*\n\n"
        f"🤖 *Model:* {model['label']}\n"
        f"   _{model['description']}_\n\n"
        f"💬 *Conversation history:* {history_count} {msg_word}\n"
        f"   _(max {MAX_HISTORY} kept in memory)_\n\n"
        "Use /model to switch models or /clear to reset history.",
        parse_mode="Markdown",
    )


async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    conversation_histories[user_id] = []
    await update.message.reply_text(
        "🗑️ Conversation history cleared!\n"
        "Let's start fresh — what's on your mind?"
    )
    logger.info("User %d cleared their conversation history.", user_id)


async def model_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = context.args

    if args and args[0] in MODELS:
        chosen_key = args[0]
        user_model_keys[user_id] = chosen_key
        model = MODELS[chosen_key]
        conversation_histories[user_id] = []
        await update.message.reply_text(
            f"✅ Switched to *{model['label']}*\n"
            f"_{model['description']}_\n\n"
            "Conversation history cleared. Start chatting!",
            parse_mode="Markdown",
        )
        logger.info("User %d switched to model %s (%s)", user_id, chosen_key, model["id"])
        return

    current_key = get_model_key(user_id)
    lines = ["🤖 *Available Models*\n"]
    for key, model in MODELS.items():
        active = " ✅ *(active)*" if key == current_key else ""
        lines.append(
            f"*{key}.* {model['label']}{active}\n"
            f"   _{model['description']}_"
        )
    lines.append("\nReply with `/model 1` or `/model 2` to switch.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    user_message = update.message.text

    logger.info(
        "Message from %s (id=%d) [model=%s]: %s",
        user.first_name, user_id, get_model_id(user_id), user_message,
    )

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    try:
        ai_reply = await get_ai_response(user_id, user_message)
        await update.message.reply_text(ai_reply)
    except Exception as e:
        logger.error("Error generating AI response: %s", e)
        await update.message.reply_text(
            "⚠️ Sorry, I ran into an error while generating a response. "
            "Please try again in a moment."
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception: %s", context.error, exc_info=context.error)


# ─── Bot Menu Registration ─────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    commands = [
        BotCommand("start",  "👋 Welcome message"),
        BotCommand("help",   "🆘 Show all commands & usage guide"),
        BotCommand("model",  "🤖 View or switch AI model"),
        BotCommand("status", "📊 Show current model & history info"),
        BotCommand("clear",  "🗑️ Clear conversation history"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot command menu registered.")


# ─── Health Server ─────────────────────────────────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    """Lightweight HTTP handler that responds to keep-alive pings."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok","bot":"Nandi AI"}')

    def log_message(self, format, *args):
        logger.debug("Health ping: %s", args[0])


def start_health_server(port: int = 8080) -> None:
    """Run a non-blocking HTTP server in a daemon thread."""
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health server listening on port %d", port)


# ─── Supervisor Loop ───────────────────────────────────────────────────────────

def run_bot() -> None:
    """Start the Telegram bot (blocking call)."""
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start",  start_handler))
    app.add_handler(CommandHandler("help",   help_handler))
    app.add_handler(CommandHandler("model",  model_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("clear",  clear_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)

    logger.info("Bot polling started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def main() -> None:
    """Start the health server and supervise the bot with auto-restart."""
    logger.info("Starting Nandi AI bot supervisor...")

    # Start keep-alive HTTP server in background
    start_health_server(port=9000)

    restart_delay = 5  # seconds between restarts
    max_restarts = 0   # 0 = unlimited
    restart_count = 0

    while max_restarts == 0 or restart_count < max_restarts:
        try:
            run_bot()
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user. Exiting.")
            sys.exit(0)
        except Exception as exc:
            restart_count += 1
            logger.error("Bot crashed: %s", exc, exc_info=True)
            logger.info("Restarting in %d seconds... (restart #%d)", restart_delay, restart_count)
            time.sleep(restart_delay)
            # Exponential back-off up to 60s
            restart_delay = min(restart_delay * 2, 60)


if __name__ == "__main__":
    main()
