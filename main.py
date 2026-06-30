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
from flask import Flask
from datetime import datetime
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
import state

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

OWNER_USER_ID = 8504907703

SYSTEM_PROMPT = (
    "You are Nandi AI, a helpful and friendly AI assistant built inside Telegram. "
    "You are created by Animesh Nandi. "
    "Answer questions clearly, concisely, and helpfully. "
    "When code is involved, use proper formatting."
)

MAX_HISTORY = 20

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_history(user_id: int) -> list[dict]:
    if user_id not in state.conversation_histories:
        state.conversation_histories[user_id] = []
    return state.conversation_histories[user_id]


def trim_history(user_id: int) -> None:
    history = state.conversation_histories.get(user_id, [])
    if len(history) > MAX_HISTORY:
        state.conversation_histories[user_id] = history[-MAX_HISTORY:]


def get_model_key(user_id: int) -> str:
    return state.user_model_keys.get(user_id, state.DEFAULT_MODEL_KEY)


def get_model_id(user_id: int) -> str:
    return state.MODELS[get_model_key(user_id)]["id"]


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


# ─── Handlers ──────────────────────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    state.started_users.add(user.id)
    state.all_users.add(user.id)
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
    model = state.MODELS[model_key]
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
    state.conversation_histories[user_id] = []
    await update.message.reply_text(
        "🗑️ Conversation history cleared!\n"
        "Let's start fresh — what's on your mind?"
    )
    logger.info("User %d cleared their conversation history.", user_id)


async def model_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = context.args

    if args and args[0] in state.MODELS:
        chosen_key = args[0]
        state.user_model_keys[user_id] = chosen_key
        model = state.MODELS[chosen_key]
        state.conversation_histories[user_id] = []
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
    for key, model in state.MODELS.items():
        active = " ✅ *(active)*" if key == current_key else ""
        lines.append(
            f"*{key}.* {model['label']}{active}\n"
            f"   _{model['description']}_"
        )
    lines.append("\nReply with `/model 1` or `/model 2` to switch.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_USER_ID


async def users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("This command is only for the bot owner.")
        return

    if not state.all_users:
        await update.message.reply_text("No users yet.")
        return

    lines = [f"All Users ({len(state.all_users)} total)"]
    for uid in sorted(state.all_users):
        is_online = "[ON]" if uid in state.active_users else "[OFF]"
        started = " [START]" if uid in state.started_users else ""
        key = state.user_model_keys.get(uid, state.DEFAULT_MODEL_KEY)
        model_label = state.MODELS[key]["label"]
        msg_count = len(state.conversation_histories.get(uid, []))
        lines.append(f"  {is_online} {uid}{started} -- {model_label} ({msg_count} msgs)")

    lines.append(f"\nTotal messages: {state.total_messages_received}")
    lines.append(f"Active now: {len(state.active_users)}")
    lines.append(f"Started bot: {len(state.started_users)}")
    lines.append(f"Errors: {state.errors_count}")
    await update.message.reply_text("\n".join(lines))


async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("🚫 This command is only for the bot owner.")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "📢 *Broadcast*\n"
            "Usage: `/broadcast <message>`\n"
            "Sends your message to *all users* (online and offline).",
            parse_mode="Markdown",
        )
        return

    message_text = " ".join(args)
    sent_count = 0
    failed_count = 0

    for uid in state.all_users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 *Broadcast*\n{message_text}", parse_mode="Markdown")
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.warning("Broadcast failed to user %d: %s", uid, e)

    await update.message.reply_text(
        f"✅ Broadcast sent!\n"
        f"  📥 Sent to: {sent_count} users\n"
        f"  ❌ Failed: {failed_count} users\n"
        f"  👥 Total users: {len(state.all_users)}",
        parse_mode="Markdown",
    )
    logger.info("Owner broadcasted to %d/%d users", sent_count, len(state.all_users))


async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text(
            "💬 *Send Feedback*\n"
            "Usage: `/feedback <your message>`\n"
            "We read every message — thanks for helping us improve!",
            parse_mode="Markdown",
        )
        return

    feedback_text = " ".join(args)
    from datetime import datetime
    state.user_feedbacks.append({
        "user_id": user_id,
        "text": feedback_text,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    await update.message.reply_text(
        "✅ Thank you for your feedback! \u2764\ufe0f\n"
        "We've received your message and will review it soon.",
    )
    logger.info("Feedback received from user %d: %s", user_id, feedback_text)


async def feedbacks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("🚫 This command is only for the bot owner.")
        return

    if not state.user_feedbacks:
        await update.message.reply_text("📁 No feedback received yet.")
        return

    lines = [f"📁 *All Feedback* ({len(state.user_feedbacks)} total)\n"]
    for i, fb in enumerate(state.user_feedbacks, 1):
        preview = fb["text"][:80] + "..." if len(fb["text"]) > 80 else fb["text"]
        lines.append(f"  `{i}.` User `{fb['user_id']}` — {fb['time']}\n     _{preview}_")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n\n… (truncated)"
    await update.message.reply_text(text, parse_mode="Markdown")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    user_message = update.message.text

    # Update shared state for dashboard
    state.total_messages_received += 1
    state.active_users.add(user_id)
    state.all_users.add(user_id)

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
        state.errors_count += 1
        logger.error("Error generating AI response: %s", e)
        await update.message.reply_text(
            "⚠️ Sorry, I ran into an error while generating a response. "
            "Please try again in a moment."
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    state.errors_count += 1
    logger.error("Unhandled exception: %s", context.error, exc_info=context.error)


# ─── Bot Menu Registration ─────────────────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    commands = [
        BotCommand("start",     "👋 Welcome message"),
        BotCommand("help",      "🆘 Show all commands & usage guide"),
        BotCommand("model",     "🤖 View or switch AI model"),
        BotCommand("status",    "📊 Show current model & history info"),
        BotCommand("clear",     "🗑️ Clear conversation history"),
        BotCommand("feedback",  "💬 Send feedback to developer"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot command menu registered.")


# ─── Health Server ──────────────────────────────────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok","bot":"Nandi AI"}')

    def log_message(self, format, *args):
        logger.debug("Health ping: %s", args[0])


def start_health_server(port: int = 9000) -> None:
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health server listening on port %d", port)


# ─── Dashboard (Flask) ──────────────────────────────────────────────────────────

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD") or os.environ.get("SESSION_SECRET", "nandi-ai-admin")

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Nandi AI — Admin Login</title>
  <style>
    :root { --bg: #0f172a; --card: #1e293b; --text: #f1f5f9; --muted: #94a3b8; --accent: #10b981; --border: #334155; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
    .login-card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 2.5rem; width: 100%; max-width: 360px; }
    .login-card h1 { font-size: 1.4rem; margin-bottom: 1.5rem; text-align: center; }
    .login-card input { width: 100%; padding: 0.75rem 1rem; margin-bottom: 1rem; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); font-size: 1rem; }
    .login-card input:focus { outline: none; border-color: var(--accent); }
    .login-card button { width: 100%; padding: 0.75rem; background: var(--accent); color: #fff; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; }
    .login-card button:hover { opacity: .9; }
    .error { color: var(--danger); font-size: 0.85rem; text-align: center; margin-bottom: 0.75rem; }
    .hint { color: var(--muted); font-size: 0.75rem; text-align: center; margin-top: 1rem; }
  </style>
</head>
<body>
  <div class="login-card">
    <h1>🔐 Nandi AI Dashboard</h1>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="post" action="/login">
      <input type="password" name="password" placeholder="Enter password" required autofocus>
      <button type="submit">Sign In</button>
    </form>
    <p class="hint">Set DASHBOARD_PASSWORD in Secrets to change this password.</p>
  </div>
</body>
</html>"""



flask_app = Flask(__name__)
flask_app.secret_key = os.environ.get("SESSION_SECRET", "nandi-ai-default-secret")
dashboard_start_time = time.time()


def fmt_uptime(seconds: float) -> str:
    hrs, rem = divmod(int(seconds), 3600)
    mins, secs = divmod(rem, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def get_dashboard_data() -> dict:
    import json
    uptime = time.time() - dashboard_start_time

    model_user_counts = {"1": 0, "2": 0}
    for uid, key in state.user_model_keys.items():
        if key in model_user_counts:
            model_user_counts[key] += 1

    conversations = []
    for uid, hist in state.conversation_histories.items():
        if not hist:
            continue
        key = state.user_model_keys.get(uid, state.DEFAULT_MODEL_KEY)
        model_name = state.MODELS[key]["label"]
        last = hist[-1]
        last_text = last["content"][:60] + "..." if len(last["content"]) > 60 else last["content"]
        conversations.append({
            "user_id": uid,
            "model": model_name,
            "message_count": len(hist),
            "last_message": last_text,
        })

    models = []
    for key, m in state.MODELS.items():
        models.append({
            "id": m["id"],
            "label": m["label"],
            "description": m["description"],
            "active_users": model_user_counts.get(key, 0),
        })

    users = []
    for uid in sorted(state.all_users):
        key = state.user_model_keys.get(uid, state.DEFAULT_MODEL_KEY)
        users.append({
            "id": uid,
            "online": uid in state.active_users,
            "started": uid in state.started_users,
            "model": state.MODELS[key]["label"],
            "messages": len(state.conversation_histories.get(uid, [])),
        })

    feedbacks = []
    for i, fb in enumerate(state.user_feedbacks, 1):
        feedbacks.append({
            "idx": i,
            "user_id": fb["user_id"],
            "time": fb["time"],
            "text": fb["text"][:200],
        })

    return {
        "stats": {
            "active_users": len(state.active_users),
            "all_users": len(state.all_users),
            "started_users": len(state.started_users),
            "total_messages": state.total_messages_received,
            "errors": state.errors_count,
            "uptime": fmt_uptime(uptime),
            "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "models": models,
        "conversations": conversations,
        "users": users,
        "users_json": json.dumps(users),
        "feedbacks": feedbacks,
    }


def check_auth():
    from flask import request, session, redirect, url_for
    if session.get("authenticated"):
        return None
    if request.form.get("password") == DASHBOARD_PASSWORD:
        session["authenticated"] = True
        return None
    return redirect(url_for("login_page"))


@flask_app.route("/login", methods=["GET", "POST"])
def login_page():
    from flask import request, session, render_template_string, redirect, url_for
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        return render_template_string(LOGIN_HTML, error="Incorrect password. Try again.")
    return render_template_string(LOGIN_HTML)


@flask_app.route("/logout")
def logout_page():
    from flask import session, redirect, url_for
    session.pop("authenticated", None)
    return redirect(url_for("login_page"))


@flask_app.route("/")
def dashboard():
    from flask import render_template_string, session, redirect, url_for
    if not session.get("authenticated"):
        return redirect(url_for("login_page"))
    data = get_dashboard_data()
    with open("dashboard.html", "r", encoding="utf-8") as f:
        template = f.read()
    return render_template_string(template, **data)


@flask_app.route("/api/stats")
def api_stats():
    from flask import jsonify, session, redirect, url_for
    if not session.get("authenticated"):
        return redirect(url_for("login_page"))
    return jsonify({"status": "ok", "bot": "Nandi AI", **get_dashboard_data()})


@flask_app.route("/api/broadcast", methods=["POST"])
def api_broadcast():
    from flask import request, jsonify, session
    if not session.get("authenticated"):
        return jsonify({"ok": False, "error": "Not authenticated"}), 401
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    scope = data.get("scope", "all")
    if not message:
        return jsonify({"ok": False, "error": "Empty message"})

    import asyncio
    target_set = state.active_users if scope == "active" else state.all_users
    sent = 0
    failed = 0
    for uid in target_set:
        try:
            asyncio.run(app.bot.send_message(chat_id=uid, text="[Admin]\n" + message))
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning("Dashboard broadcast failed to %d: %s", uid, e)
    logger.info("Dashboard broadcast: %d/%d users", sent, len(target_set))
    return jsonify({"ok": True, "sent": sent, "failed": failed})


@flask_app.route("/api/health")
def api_health():
    from flask import jsonify
    return jsonify({"status": "ok"})


def start_dashboard(port: int = 5001) -> None:
    thread = threading.Thread(
        target=lambda: flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    logger.info("Dashboard server listening on port %d", port)


# ─── Supervisor Loop ──────────────────────────────────────────────────────────

def run_bot() -> None:
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start",      start_handler))
    app.add_handler(CommandHandler("help",       help_handler))
    app.add_handler(CommandHandler("model",      model_handler))
    app.add_handler(CommandHandler("status",     status_handler))
    app.add_handler(CommandHandler("clear",      clear_handler))
    app.add_handler(CommandHandler("feedback",   feedback_handler))
    app.add_handler(CommandHandler("users",      users_handler))
    app.add_handler(CommandHandler("broadcast",  broadcast_handler))
    app.add_handler(CommandHandler("feedbacks",  feedbacks_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)

    logger.info("Bot polling started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def main() -> None:
    logger.info("Starting Nandi AI bot + dashboard...")
    start_health_server(port=9000)
    start_dashboard(port=5001)

    restart_delay = 5
    restart_count = 0

    while True:
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
            restart_delay = min(restart_delay * 2, 60)


if __name__ == "__main__":
    main()
