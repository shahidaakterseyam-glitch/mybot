import os
import asyncio
from yt_dlp import YoutubeDL
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.error import Forbidden

# 🔑 Bot Configuration
TOKEN = os.getenv("BOT_TOKEN")  # Set BOT_TOKEN in environment (Replit Secret)
ADMIN_ID = 5997715263
DOWNLOAD_DIR = "./downloads"
MAX_SIZE_MB = 45

# 📁 Ensure download folder exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 📦 In-memory user list (can persist in DB later)
USERS = set()


# 🎬 Start Command
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USERS.add(user_id)
    await update.message.reply_text(
        "🎧 *Welcome to the Premium YouTube Audio Downloader!*\n\n"
        "🎵 Just send a YouTube link or use this:\n"
        "➡️ `/audio <youtube_url>`\n\n"
        "💫 I'll fetch the audio and send it to you in seconds!",
        parse_mode="Markdown")


# 📥 Download Function
def download_youtube(url: str, audio_only=False):
    opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "format": "bestaudio/best" if audio_only else "best[ext=mp4]/mp4",
        "quiet": True,
        "noplaylist": True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info), info.get("title")


# ⚙️ Handle Download Process
async def handle_download(update: Update,
                          context: ContextTypes.DEFAULT_TYPE,
                          audio_only=False):
    if not context.args:
        await update.message.reply_text("❗ Please send a valid YouTube link.")
        return

    url = context.args[0]
    await update.message.reply_text(
        "⬇️ *Downloading your track... Please wait...*", parse_mode="Markdown")

    loop = asyncio.get_running_loop()
    try:
        file_path, title = await loop.run_in_executor(None, download_youtube,
                                                      url, audio_only)
    except Exception as e:
        await update.message.reply_text(f"❌ *Error:* {e}",
                                        parse_mode="Markdown")
        return

    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        await update.message.reply_text(
            f"⚠️ File too large ({size_mb:.1f} MB). Can't send via Telegram.")
        return

    with open(file_path, "rb") as f:
        await update.message.reply_document(InputFile(
            f, filename=os.path.basename(file_path)),
                                            caption=f"✅ *{title}*",
                                            parse_mode="Markdown")
    os.remove(file_path)


# 🎵 Audio Download Command
async def audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_download(update, context, audio_only=True)


# 🧠 Hidden Admin Commands
async def admin_panel(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = ("🛠️ *Admin Control Panel*\n\n"
           "📢 `/broadcast <message>` — Send text broadcast\n"
           "📸 Send photo/video with caption `/broadcast` — Media broadcast\n"
           "📊 `/stats` — View bot stats\n")
    await update.message.reply_text(msg, parse_mode="Markdown")


# 📊 Admin Stats
async def stats(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"📈 *Bot Statistics:*\n\n"
        f"👥 Total Users: {len(USERS)}\n"
        f"🧑‍💻 Admin ID: `{ADMIN_ID}`",
        parse_mode="Markdown")


# 📢 Admin Broadcast (text or media)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.photo:
        file = update.message.photo[-1]
        caption = update.message.caption or "📢 New update available! Check it out 🔥"
        for uid in USERS:
            try:
                await context.bot.send_photo(uid,
                                             file.file_id,
                                             caption=caption)
            except Forbidden:
                continue
            except Exception:
                continue

    elif update.message.video:
        file = update.message.video
        caption = update.message.caption or "🎬 New feature added! Update your bot now ✨"
        for uid in USERS:
            try:
                await context.bot.send_video(uid,
                                             file.file_id,
                                             caption=caption)
            except Forbidden:
                continue
            except Exception:
                continue

    elif context.args:
        text = " ".join(context.args)
        fake_ads = (f"🎧 *Sponsored Update*\n\n"
                    f"{text}\n\n"
                    f"🔥 Enjoy unlimited music")
        for uid in USERS:
            try:
                await context.bot.send_message(uid,
                                               fake_ads,
                                               parse_mode="Markdown")
            except Forbidden:
                continue
            except Exception:
                continue

    await update.message.reply_text("✅ Broadcast sent successfully!",
                                    parse_mode="Markdown")


# 🚀 Main Function
def main():
    if not TOKEN:
        print("❌ Please set BOT_TOKEN environment variable.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    # Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("audio", audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, audio))

    # Hidden admin features
    app.add_handler(CommandHandler("panel", admin_panel))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, broadcast))

    print("🚀 Bot is live and running 24/7 🎧")
    app.run_polling()


# 🏁 Entry Point
if __name__ == "__main__":
    main()