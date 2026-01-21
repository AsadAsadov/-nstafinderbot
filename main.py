import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

from aiohttp import web
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import db
import keyboards
import search


load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6086814445"))
RATE_LIMIT = 10

DEFAULT_TEXTS = {
    "welcome": "Salam! InstaFinderBot-a xoş gəldiniz. Aşağıdakı menyudan seçim edin.",
    "how_it_works": (
        "Bu bot açıq Google axtarışından istifadə edərək Instagram profillərini və postlarını tapır. "
        "Sadəcə ad və ya açar söz daxil edin, nəticələri gəzin və seçdiklərinizi yadda saxlayın."
    ),
    "rate_limited": "Bu gün üçün limitə çatdınız. Sabah yenidən cəhd edin.",
    "no_results": "Heç bir nəticə tapılmadı. Zəhmət olmasa fərqli sorğu sınayın.",
    "search_failed": "Axtarış zamanı problem oldu. Bir qədər sonra yenidən sınayın.",
}


async def start_health_server() -> None:
    app = web.Application()

    async def handle(_: web.Request) -> web.Response:
        return web.Response(text="OK")

    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


def get_text(key: str) -> str:
    return db.get_bot_text(key) or DEFAULT_TEXTS.get(key, "")


def get_last_message_id(context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    return context.user_data.get("last_message_id")


async def send_or_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None) -> None:
    message_id = get_last_message_id(context)
    if message_id and update.effective_chat:
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
        except Exception:
            message_id = None

    sent = await update.effective_chat.send_message(
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
    context.user_data["last_message_id"] = sent.message_id


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.init_db()
    db.reset_daily_searches()
    if update.effective_user:
        db.add_user(update.effective_user.id)
    reply_markup = keyboards.main_menu_keyboard(is_admin=update.effective_user.id == ADMIN_ID)
    await send_or_edit(update, context, get_text("welcome"), reply_markup=reply_markup)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    db.init_db()
    db.reset_daily_searches()
    db.add_user(update.effective_user.id)

    text = update.message.text.strip()
    state = context.user_data.get("state")

    if update.effective_user.id == ADMIN_ID and state == "admin_edit_texts":
        if "=" in text:
            key, value = text.split("=", 1)
            db.set_bot_text(key.strip(), value.strip())
            await send_or_edit(update, context, f"✅ '{key.strip()}' mətni yeniləndi.")
        else:
            await send_or_edit(update, context, "Format: key=new text")
        return

    if state == "awaiting_name":
        await handle_profile_search(update, context, text)
        return

    if state == "awaiting_keyword":
        await handle_post_search(update, context, text)
        return

    if text == "🔍 Ad / Profil axtar":
        context.user_data["state"] = "awaiting_name"
        await send_or_edit(update, context, "Tam adı daxil edin:")
        return

    if text == "🏷 Açar sözlə post tap":
        context.user_data["state"] = "awaiting_keyword"
        await send_or_edit(update, context, "Açar sözü daxil edin:")
        return

    if text == "⭐ Seçilmişlər":
        await show_favorites(update, context)
        return

    if text == "❓ Necə işləyir":
        await send_or_edit(update, context, get_text("how_it_works"))
        return

    if update.effective_user.id == ADMIN_ID and text == "📊 Statistikalar":
        total_users = db.get_total_users()
        today_searches = db.get_today_search_count()
        await send_or_edit(
            update,
            context,
            f"👥 Ümumi istifadəçilər: {total_users}\n🔎 Bu gün axtarışlar: {today_searches}",
        )
        return

    if update.effective_user.id == ADMIN_ID and text == "🛠 Mesajları redaktə et":
        context.user_data["state"] = "admin_edit_texts"
        await send_or_edit(update, context, "Dəyişmək üçün: key=new text formatında göndərin.")
        return

    await send_or_edit(update, context, "Zəhmət olmasa menyudan seçim edin.")


async def handle_profile_search(update: Update, context: ContextTypes.DEFAULT_TYPE, full_name: str) -> None:
    context.user_data["state"] = None
    if not update.effective_user:
        return

    if db.get_user(update.effective_user.id) is None:
        db.add_user(update.effective_user.id)

    if db.increment_search(update.effective_user.id) > RATE_LIMIT:
        await send_or_edit(update, context, get_text("rate_limited"))
        return

    await send_or_edit(update, context, "Axtarılır, zəhmət olmasa gözləyin...")
    try:
        results = await search.search_profiles(full_name)
    except Exception:
        await send_or_edit(update, context, get_text("search_failed"))
        return

    if not results:
        await send_or_edit(update, context, get_text("no_results"))
        return

    context.user_data["profile_results"] = results
    context.user_data["profile_index"] = 0
    await show_profile_result(update, context)


async def handle_post_search(update: Update, context: ContextTypes.DEFAULT_TYPE, keyword: str) -> None:
    context.user_data["state"] = None
    if not update.effective_user:
        return

    if db.get_user(update.effective_user.id) is None:
        db.add_user(update.effective_user.id)

    if db.increment_search(update.effective_user.id) > RATE_LIMIT:
        await send_or_edit(update, context, get_text("rate_limited"))
        return

    await send_or_edit(update, context, "Axtarılır, zəhmət olmasa gözləyin...")
    try:
        results = await search.search_posts(keyword)
    except Exception:
        await send_or_edit(update, context, get_text("search_failed"))
        return

    if not results:
        await send_or_edit(update, context, get_text("no_results"))
        return

    context.user_data["post_results"] = results
    context.user_data["post_index"] = 0
    await show_post_result(update, context)


async def show_profile_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    results = context.user_data.get("profile_results", [])
    index = context.user_data.get("profile_index", 0)
    if not results:
        await send_or_edit(update, context, get_text("no_results"))
        return
    index = max(0, min(index, len(results) - 1))
    context.user_data["profile_index"] = index
    result = results[index]
    text = (
        f"<b>Profil {index + 1}/{len(results)}</b>\n"
        f"İstifadəçi: <code>{result['username']}</code>\n"
        f"Link: {result['link']}"
    )
    await send_or_edit(update, context, text, reply_markup=keyboards.profile_nav_keyboard())


async def show_post_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    results = context.user_data.get("post_results", [])
    index = context.user_data.get("post_index", 0)
    if not results:
        await send_or_edit(update, context, get_text("no_results"))
        return
    index = max(0, min(index, len(results) - 1))
    context.user_data["post_index"] = index
    link = results[index]
    text = f"<b>Post {index + 1}/{len(results)}</b>\nLink: {link}"
    await send_or_edit(update, context, text, reply_markup=keyboards.post_nav_keyboard())


async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    items = db.list_favorites(update.effective_user.id)
    if not items:
        await send_or_edit(update, context, "Seçilmişlər boşdur.")
        return
    text_lines = ["<b>Seçilmişlər</b>"]
    for idx, (link, item_type) in enumerate(items, start=1):
        text_lines.append(f"{idx}. {item_type} — {link}")
    await send_or_edit(
        update,
        context,
        "\n".join(text_lines),
        reply_markup=keyboards.favorites_keyboard(items),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    data = query.data
    if data in {"profile_prev", "profile_next", "profile_open", "profile_fav"}:
        await handle_profile_callback(update, context, data)
    elif data in {"post_prev", "post_next", "post_open"}:
        await handle_post_callback(update, context, data)
    elif data.startswith("fav_remove:"):
        await handle_favorite_remove(update, context, data)


async def handle_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
    if data == "profile_prev":
        context.user_data["profile_index"] = context.user_data.get("profile_index", 0) - 1
        await show_profile_result(update, context)
        return
    if data == "profile_next":
        context.user_data["profile_index"] = context.user_data.get("profile_index", 0) + 1
        await show_profile_result(update, context)
        return
    results = context.user_data.get("profile_results", [])
    index = context.user_data.get("profile_index", 0)
    if not results:
        await send_or_edit(update, context, get_text("no_results"))
        return
    result = results[index]
    if data == "profile_open":
        await send_or_edit(update, context, f"Profil: {result['link']}")
        return
    if data == "profile_fav" and update.effective_user:
        db.add_favorite(update.effective_user.id, result["link"], "Profil")
        await send_or_edit(update, context, "✅ Profil seçilmişlərə əlavə edildi.")


async def handle_post_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
    if data == "post_prev":
        context.user_data["post_index"] = context.user_data.get("post_index", 0) - 1
        await show_post_result(update, context)
        return
    if data == "post_next":
        context.user_data["post_index"] = context.user_data.get("post_index", 0) + 1
        await show_post_result(update, context)
        return
    results = context.user_data.get("post_results", [])
    index = context.user_data.get("post_index", 0)
    if not results:
        await send_or_edit(update, context, get_text("no_results"))
        return
    link = results[index]
    if data == "post_open":
        await send_or_edit(update, context, f"Post: {link}")


async def handle_favorite_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
    if not update.effective_user:
        return
    items = db.list_favorites(update.effective_user.id)
    index = int(data.split(":", 1)[1])
    if index < 0 or index >= len(items):
        await send_or_edit(update, context, "Seçilmiş tapılmadı.")
        return
    link, _ = items[index]
    db.remove_favorite(update.effective_user.id, link)
    await show_favorites(update, context)


async def on_startup(_: Application) -> None:
    db.init_db()
    asyncio.create_task(start_health_server())


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.post_init = on_startup

    application.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
