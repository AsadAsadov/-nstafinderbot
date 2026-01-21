from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    buttons = [
        ["🔍 Ad / Profil axtar", "🏷 Açar sözlə post tap"],
        ["⭐ Seçilmişlər", "❓ Necə işləyir"],
    ]
    if is_admin:
        buttons.append(["📊 Statistikalar", "🛠 Mesajları redaktə et"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def profile_nav_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Əvvəlki", callback_data="profile_prev"),
            InlineKeyboardButton("➡️ Növbəti", callback_data="profile_next"),
        ],
        [
            InlineKeyboardButton("🔗 Profilə bax", callback_data="profile_open"),
            InlineKeyboardButton("⭐ Seç", callback_data="profile_fav"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def post_nav_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Əvvəlki", callback_data="post_prev"),
            InlineKeyboardButton("➡️ Növbəti", callback_data="post_next"),
        ],
        [InlineKeyboardButton("🔗 Postu aç", callback_data="post_open")],
    ]
    return InlineKeyboardMarkup(keyboard)


def favorites_keyboard(items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    buttons = []
    for idx, (link, item_type) in enumerate(items, start=1):
        buttons.append(
            [
                InlineKeyboardButton(f"{idx}. {item_type}", url=link),
                InlineKeyboardButton("🗑 Sil", callback_data=f"fav_remove:{idx - 1}"),
            ]
        )
    return InlineKeyboardMarkup(buttons) if buttons else InlineKeyboardMarkup([])
