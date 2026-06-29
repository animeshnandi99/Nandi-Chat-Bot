import { Router, type IRouter, type Request, type Response } from "express";
import crypto from "node:crypto";

const router: IRouter = Router();

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN ?? "";
const BOT_USERNAME = process.env.TELEGRAM_BOT_USERNAME ?? "";

// Pre-compute the secret key once: SHA-256(bot_token)
const SECRET_KEY = crypto.createHash("sha256").update(BOT_TOKEN).digest();

// Max age (seconds) we accept for auth_date — 24 hours
const MAX_AUTH_AGE_SECONDS = 86_400;

interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
}

/**
 * Verify the data block sent by the Telegram Login Widget.
 * https://core.telegram.org/widgets/login#checking-authorization
 */
function verifyTelegramLogin(query: Record<string, string>): TelegramUser | null {
  const { hash, ...fields } = query;
  if (!hash) return null;

  // Build sorted key=value string
  const dataCheckString = Object.keys(fields)
    .sort()
    .map((k) => `${k}=${fields[k]}`)
    .join("\n");

  // Compute expected hash
  const expectedHash = crypto
    .createHmac("sha256", SECRET_KEY)
    .update(dataCheckString)
    .digest("hex");

  // Constant-time compare
  if (
    expectedHash.length !== hash.length ||
    !crypto.timingSafeEqual(Buffer.from(expectedHash), Buffer.from(hash))
  ) {
    return null;
  }

  // Check auth_date freshness
  const authDate = parseInt(fields.auth_date ?? "0", 10);
  const now = Math.floor(Date.now() / 1000);
  if (now - authDate > MAX_AUTH_AGE_SECONDS) return null;

  return {
    id: parseInt(fields.id!, 10),
    first_name: fields.first_name!,
    last_name: fields.last_name,
    username: fields.username,
    photo_url: fields.photo_url,
    auth_date: authDate,
  };
}

// ─── GET /api/login ───────────────────────────────────────────────────────────
// Serves the Telegram Login Widget page.
router.get("/login", (_req: Request, res: Response) => {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Nandi AI — Login</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
      color: #fff;
    }
    .card {
      background: rgba(255,255,255,0.07);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 20px;
      padding: 48px 40px;
      text-align: center;
      max-width: 380px;
      width: 90%;
      box-shadow: 0 24px 48px rgba(0,0,0,0.4);
    }
    .logo { font-size: 52px; margin-bottom: 12px; }
    h1 { font-size: 26px; font-weight: 700; margin-bottom: 6px; }
    p  { color: rgba(255,255,255,0.55); font-size: 14px; margin-bottom: 32px; line-height: 1.6; }
    .widget-wrap { display: flex; justify-content: center; }
    .footer {
      margin-top: 28px;
      font-size: 11px;
      color: rgba(255,255,255,0.25);
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">🤖</div>
    <h1>Nandi AI</h1>
    <p>Sign in with your Telegram account to continue.</p>
    <div class="widget-wrap">
      <script
        async
        src="https://telegram.org/js/telegram-widget.js?22"
        data-telegram-login="${BOT_USERNAME}"
        data-size="large"
        data-auth-url="/api/auth/telegram/callback"
        data-request-access="write"
      ></script>
    </div>
    <div class="footer">Powered by Groq &amp; Telegram · Built by Animesh Nandi</div>
  </div>
</body>
</html>`;
  res.setHeader("Content-Type", "text/html");
  res.send(html);
});

// ─── GET /api/auth/telegram/callback ─────────────────────────────────────────
// Telegram redirects here after the user authorises via the widget.
router.get("/auth/telegram/callback", (req: Request, res: Response) => {
  const query = req.query as Record<string, string>;
  const user = verifyTelegramLogin(query);

  if (!user) {
    res.status(401).setHeader("Content-Type", "text/html").send(`
      <!DOCTYPE html><html><head><meta charset="UTF-8"/>
      <title>Auth Failed</title>
      <style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;
      min-height:100vh;background:#0f0c29;color:#fff;flex-direction:column;gap:16px;}
      a{color:#54a3f5;}</style></head>
      <body><h2>❌ Authentication failed</h2>
      <p>The login data could not be verified or has expired.</p>
      <a href="/api/login">← Try again</a></body></html>
    `);
    return;
  }

  // Successful login — render a welcome page
  const displayName = [user.first_name, user.last_name].filter(Boolean).join(" ");
  const avatarHtml = user.photo_url
    ? `<img src="${user.photo_url}" alt="avatar"
            style="width:72px;height:72px;border-radius:50%;margin-bottom:16px;border:3px solid rgba(255,255,255,0.2);" />`
    : `<div style="font-size:52px;margin-bottom:12px;">👤</div>`;

  res.setHeader("Content-Type", "text/html").send(`
    <!DOCTYPE html><html lang="en"><head>
    <meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>Nandi AI — Welcome</title>
    <style>
      *{box-sizing:border-box;margin:0;padding:0;}
      body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
        min-height:100vh;display:flex;align-items:center;justify-content:center;
        background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;}
      .card{background:rgba(255,255,255,0.07);backdrop-filter:blur(16px);
        border:1px solid rgba(255,255,255,0.12);border-radius:20px;
        padding:48px 40px;text-align:center;max-width:380px;width:90%;
        box-shadow:0 24px 48px rgba(0,0,0,0.4);}
      h2{font-size:22px;font-weight:700;margin-bottom:8px;}
      .meta{color:rgba(255,255,255,0.45);font-size:13px;margin-bottom:24px;}
      .badge{display:inline-block;background:rgba(84,163,245,0.15);
        border:1px solid rgba(84,163,245,0.35);border-radius:8px;
        padding:10px 18px;font-size:13px;margin-bottom:8px;width:100%;text-align:left;}
      .badge span{color:rgba(255,255,255,0.5);font-size:11px;display:block;margin-bottom:2px;}
      a{display:block;margin-top:24px;color:rgba(255,255,255,0.35);font-size:12px;
        text-decoration:none;}
      a:hover{color:#fff;}
    </style>
    </head><body>
    <div class="card">
      ${avatarHtml}
      <h2>✅ Welcome, ${displayName}!</h2>
      <p class="meta">You've successfully signed in via Telegram.</p>
      <div class="badge"><span>Telegram ID</span>${user.id}</div>
      ${user.username ? `<div class="badge"><span>Username</span>@${user.username}</div>` : ""}
      <div class="badge"><span>Signed in at</span>${new Date(user.auth_date * 1000).toUTCString()}</div>
      <a href="/api/login">← Sign in with a different account</a>
    </div>
    </body></html>
  `);
});

// ─── POST /api/auth/telegram ──────────────────────────────────────────────────
// JSON API endpoint — verifies Telegram login data, returns user object.
router.post("/auth/telegram", (req: Request, res: Response) => {
  const body = req.body as Record<string, string>;
  const user = verifyTelegramLogin(body);

  if (!user) {
    res.status(401).json({ ok: false, error: "Invalid or expired Telegram login data." });
    return;
  }

  res.json({ ok: true, user });
});

export default router;
