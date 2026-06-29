"""
Nandi AI - Telegram Bot powered by Groq AI
Developer: Animesh Nandi
"""

import os
import logging
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
# Conversation history:  { user_id: [ {"role": ..., "content": ...}, ... ] }
# Selected model key:    { user_id: "1" | "2" }
conversation_histories: dict[int, list[dict]] = {}
user_model_keys: dict[int, str] = {}

SYSTEM_PROMPT = (
    "You are Nandi AI, a helpful and friendly AI assistant built inside Telegram. "
    "You are created by Animesh Nandi. "
    "Answer questions clearly, concisely, and helpfully. "
    "When code is involved, use proper formatting."
)

MAX_HISTORY = 20  # Maximum number of messages to keep per user


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_history(user_id: int) -> list[dict]:
    """Return the conversation history for a user, initialising if needed."""
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []
    return conversation_histories[user_id]


def trim_history(user_id: int) -> None:
    """Keep history within MAX_HISTORY messages to avoid token overflow."""
    history = conversation_histories.get(user_id, [])
    if len(history) > MAX_HISTORY:
        conversation_histories[user_id] = history[-MAX_HISTORY:]


def get_model_key(user_id: int) -> str:
    """Return the model key currently selected by this user."""
    return user_model_keys.get(user_id, DEFAULT_MODEL_KEY)


def get_model_id(user_id: int) -> str:
    """Return the Groq model ID currently selected by this user."""
    return MODELS[get_model_key(user_id)]["id"]


async def get_ai_response(user_id: int, user_message: str) -> str:
    """Send the conversation to Groq and return the AI reply."""
    history = get_history(user_id)

    # Append the new user message
    history.append({"role": "user", "content": user_message})

    # Build the messages list with the system prompt prepended
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    # Call Groq API with the user's chosen model
    response = groq_client.chat.completions.create(
        model=get_model_id(user_id),
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
    )

    ai_reply = response.choices[0].message.content.strip()

    # Store the assistant reply in history
    history.append({"role": "assistant", "content": ai_reply})
    trim_history(user_id)

    return ai_reply


# ─── Handlers ─────────────────────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome to *Nandi AI*, {user.first_name}!\n"
        "I'm your AI assistant developed by Animesh Nandi.\n\n"
        "Just send me any message and I'll reply using AI.",
        parse_mode="Markdown",
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command — show full command reference."""
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
    """Handle the /status command — show current model and history size."""
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
    """Handle the /clear command — wipe the user's conversation history."""
    user_id = update.effective_user.id
    conversation_histories[user_id] = []
    await update.message.reply_text(
        "🗑️ Conversation history cleared!\n"
        "Let's start fresh — what's on your mind?"
    )
    logger.info("User %d cleared their conversation history.", user_id)


async def model_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /model command — list models or switch to a new one."""
    user_id = update.effective_user.id
    args = context.args  # words after /model

    # If the user passed a model number, switch to it
    if args and args[0] in MODELS:
        chosen_key = args[0]
        user_model_keys[user_id] = chosen_key
        model = MODELS[chosen_key]
        # Clear history so the new model starts fresh
        conversation_histories[user_id] = []
        await update.message.reply_text(
            f"✅ Switched to *{model['label']}*\n"
            f"_{model['description']}_\n\n"
            "Conversation history cleared. Start chatting!",
            parse_mode="Markdown",
        )
        logger.info("User %d switched to model %s (%s)", user_id, chosen_key, model["id"])
        return

    # Otherwise show the model list
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
    """Handle every incoming text message."""
    user = update.effective_user
    user_id = user.id
    user_message = update.message.text

    logger.info(
        "Message from %s (id=%d) [model=%s]: %s",
        user.first_name, user_id, get_model_id(user_id), user_message,
    )

    # Show typing indicator while processing
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
    """Log unhandled errors raised by the dispatcher."""
    logger.error("Unhandled exception: %s", context.error, exc_info=context.error)


# ─── Bot Menu Registration ─────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    """Register commands with Telegram so they appear in the / menu."""
    commands = [
        BotCommand("start",  "👋 Welcome message"),
        BotCommand("help",   "🆘 Show all commands & usage guide"),
        BotCommand("model",  "🤖 View or switch AI model"),
        BotCommand("status", "📊 Show current model & history info"),
        BotCommand("clear",  "🗑️ Clear conversation history"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot command menu registered.")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main() -> None:
    """Start the bot using long polling."""
    logger.info("Starting Nandi AI bot...")

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)   # registers the / menu on startup
        .build()
    )

    # Register handlers
    app.add_handler(CommandHandler("start",  start_handler))
    app.add_handler(CommandHandler("help",   help_handler))
    app.add_handler(CommandHandler("model",  model_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("clear",  clear_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
