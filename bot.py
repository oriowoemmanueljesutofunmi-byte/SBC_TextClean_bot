import logging
import os
import re
from collections import Counter

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_NAME = "SBC24 Text Cleaner"
MAX_OUTPUT_CHARS = 3900

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def clean_line(line: str) -> str:
    """Normalize whitespace and common copied-list formatting."""
    line = line.replace("\u00a0", " ")
    line = re.sub(r"[ \t]+", " ", line)
    line = re.sub(r"^\s*(?:[-*•▪◦]+|\d+[.)])\s*", "", line)
    return line.strip()


def clean_text(text: str) -> str:
    """Clean a text block while preserving line order."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [clean_line(line) for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def dedupe_text(text: str, case_insensitive: bool = True) -> tuple[str, int, int]:
    """Remove duplicate lines while preserving the first occurrence."""
    lines = text.splitlines()
    seen = set()
    unique = []

    for line in lines:
        key = re.sub(r"\s+", " ", line.strip())
        if case_insensitive:
            key = key.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(line.strip())

    return "\n".join(unique), len(lines), len(unique)


def process(text: str, mode: str) -> tuple[str, dict]:
    original_lines = len(text.splitlines())
    if mode == "clean":
        result = clean_text(text)
        return result, {
            "original_lines": original_lines,
            "final_lines": len(result.splitlines()) if result else 0,
            "duplicates_removed": 0,
        }

    cleaned = clean_text(text)
    result, before, after = dedupe_text(cleaned)
    return result, {
        "original_lines": original_lines,
        "final_lines": after,
        "duplicates_removed": max(0, before - after),
    }


def menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🧹 Clean Text", callback_data="clean"),
            InlineKeyboardButton("🔄 Remove Duplicates", callback_data="dedupe"),
        ],
        [InlineKeyboardButton("✨ Clean + Deduplicate", callback_data="both")],
        [InlineKeyboardButton("📊 Text Statistics", callback_data="stats")],
    ])


def mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧹 Clean", callback_data="clean")],
        [InlineKeyboardButton("🔄 Remove Duplicates", callback_data="dedupe")],
        [InlineKeyboardButton("✨ Clean + Deduplicate", callback_data="both")],
    ])


WELCOME = (
    "<b>Welcome to SBC24 Text Cleaner 👋</b>\n\n"
    "I clean messy text and remove duplicate lines quickly.\n\n"
    "<b>Choose an action:</b>\n"
    "🧹 Clean Text — normalize spaces, blank lines and list numbering.\n"
    "🔄 Remove Duplicates — keep only the first copy of each line.\n"
    "✨ Clean + Deduplicate — do both in one step.\n"
    "📊 Text Statistics — count lines, words and characters.\n\n"
    "You can also simply paste text here and choose what to do."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("mode", None)
    await update.message.reply_text(WELCOME, parse_mode="HTML", reply_markup=menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "<b>SBC24 Commands</b>\n\n"
        "/start — open the main menu\n"
        "/clean — clean text\n"
        "/dedupe — remove duplicate lines\n"
        "/both — clean and remove duplicates\n"
        "/stats — show text statistics\n"
        "/cancel — return to the main menu\n\n"
        "Tip: you can paste a text file (.txt) too.",
        parse_mode="HTML",
        reply_markup=menu_keyboard(),
    )


async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str) -> None:
    context.user_data["mode"] = mode
    labels = {
        "clean": "🧹 <b>Clean Text</b>",
        "dedupe": "🔄 <b>Remove Duplicates</b>",
        "both": "✨ <b>Clean + Deduplicate</b>",
        "stats": "📊 <b>Text Statistics</b>",
    }
    await update.message.reply_text(
        f"{labels[mode]}\n\nSend or paste your text now.",
        parse_mode="HTML",
        reply_markup=mode_keyboard(),
    )


async def clean_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_mode(update, context, "clean")


async def dedupe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_mode(update, context, "dedupe")


async def both_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_mode(update, context, "both")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_mode(update, context, "stats")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("mode", None)
    await update.message.reply_text("Back to the main menu 👌", reply_markup=menu_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    mode = query.data
    context.user_data["mode"] = mode
    labels = {
        "clean": "🧹 <b>Clean Text</b>",
        "dedupe": "🔄 <b>Remove Duplicates</b>",
        "both": "✨ <b>Clean + Deduplicate</b>",
        "stats": "📊 <b>Text Statistics</b>",
    }
    await query.message.reply_text(
        f"{labels.get(mode, 'Choose an action')}\n\nSend or paste your text now.",
        parse_mode="HTML",
        reply_markup=mode_keyboard(),
    )


async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    mode = context.user_data.get("mode")
    if not mode:
        await update.message.reply_text(
            "What would you like me to do with this text?",
            reply_markup=menu_keyboard(),
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    if mode == "stats":
        lines = len(text.splitlines())
        words = len(re.findall(r"\S+", text))
        characters = len(text)
        unique_lines = len(set(line.strip().casefold() for line in text.splitlines() if line.strip()))
        await update.message.reply_text(
            f"📊 <b>Text Statistics</b>\n\n"
            f"Lines: <b>{lines}</b>\n"
            f"Unique lines: <b>{unique_lines}</b>\n"
            f"Words: <b>{words}</b>\n"
            f"Characters: <b>{characters}</b>",
            parse_mode="HTML",
        )
        return

    result, info = process(text, mode)
    if not result:
        await update.message.reply_text("⚠️ I couldn't find any usable text to return.")
        return

    if len(result) <= MAX_OUTPUT_CHARS:
        output = result
        await update.message.reply_text(output)
    else:
        # Telegram message limit is much larger, but keeping output compact makes it easier to copy.
        await update.message.reply_document(
            document=result.encode("utf-8"),
            filename="sbc24_cleaned.txt",
            caption="📄 Your cleaned text is attached as a .txt file.",
        )

    summary = f"\n\n✅ <b>Done</b> — {info['final_lines']} lines remaining."
    if mode == "both":
        summary += f"\n🔄 {info['duplicates_removed']} duplicate lines removed."
    await update.message.reply_text(summary, parse_mode="HTML")
    context.user_data.pop("mode", None)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.text:
        await process_message(update, context, update.message.text)


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.document:
        return
    document = update.message.document
    if document.file_size and document.file_size > 5 * 1024 * 1024:
        await update.message.reply_text("⚠️ Please keep text files under 5 MB.")
        return
    if not (document.file_name or "").lower().endswith(".txt"):
        await update.message.reply_text("Please send a plain .txt file.")
        return

    mode = context.user_data.get("mode")
    if not mode:
        await update.message.reply_text("Choose an action first:", reply_markup=menu_keyboard())
        return

    file = await document.get_file()
    data = await file.download_as_bytearray()
    try:
        text = bytes(data).decode("utf-8-sig")
    except UnicodeDecodeError:
        text = bytes(data).decode("latin-1")
    await process_message(update, context, text)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled bot error", exc_info=context.error)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clean", clean_command))
    application.add_handler(CommandHandler("dedupe", dedupe_command))
    application.add_handler(CommandHandler("both", both_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_error_handler(error_handler)

    logger.info("Starting %s", BOT_NAME)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
