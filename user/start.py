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

    session = get_user_session(uid)
    client = active_clients.get(uid)
    if session and client and client.is_connected():
        status = "✅ *Aktif*"
    elif session:
        status = "⚠️ *Session tersimpan, client belum terhubung*"
    else:
        status = "❌ *Belum diatur*"

    if is_subscribed(uid):
        info = get_subscription_info(uid)
        expired = datetime.fromisoformat(info[1])
        sub_status = f"\n💳 Langganan: ✅ Aktif s/d *{expired.strftime('%d %b %Y')}*"
    else:
        sub_status = "\n💳 Langganan: ❌ Tidak aktif"

    await update.message.reply_text(
        f"👋 *Selamat datang di Rams VIP Bot!*\n\nStatus session: {status}{sub_status}\n\nPilih menu di bawah:",
        parse_mode="Markdown",
        reply_markup=main_keyboard(uid),
    )
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    clear_user_state(uid)
    await update.message.reply_text("❌ Dibatalkan. Kembali ke menu utama.", reply_markup=main_keyboard(uid))
    return ConversationHandler.END
