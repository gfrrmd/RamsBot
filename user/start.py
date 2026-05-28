from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from auth.states import clear_user_state
from client_manager import active_clients
from database import get_subscription_info, get_user_session, is_subscribed, upsert_user
from keyboards import main_keyboard


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = update.effective_user
    clear_user_state(uid)
    upsert_user(uid, user.username, user.full_name)

    first_name = user.first_name or "Kamu"

    await update.message.reply_text(
        f"Halo, {first_name}! 👋\n"
        f"Aku adalah Bot Telegram pribadi dengan berbagai fitur eksklusif. ✨\n\n"
        f"Dengan bot ini kamu bisa *Download Media Timer* 📥, *Download Media Channel Private* 📣, "
        f"*Download Story* 🎥, *Broadcast Pesan* 📢, dan masih banyak lagi 🚀\n\n"
        f"👇 Pilih menu di bawah untuk mulai.",
        parse_mode="Markdown",
        reply_markup=main_keyboard(uid),
    )
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    clear_user_state(uid)
    await update.message.reply_text("❌ Dibatalkan. Kembali ke menu utama.", reply_markup=main_keyboard(uid))
    return ConversationHandler.END
