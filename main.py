import asyncio
import time

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from admin.callbacks import admin_callback_handler, admin_message_handler
from admin.gift import cmd_gift
from admin.vip import cmd_revoke
from auth.setup import cmd_setup, register_telethon_handlers, setup_code, setup_password, setup_phone
from auth.states import CODE_STEP, PASSWORD_STEP, PHONE_STEP
from client_manager import _start_time, active_clients, build_client, dl_locks
from config import API_ID, API_HASH, BOT_TOKEN
from database import get_conn, init_db, is_subscribed
from user.callbacks import user_callback_handler
from user.start import cmd_cancel, cmd_start


async def post_init(app):
    try:
        init_db()
        print("\u2705 Database siap.")
    except Exception as e:
        print(f"\u274c Gagal init database: {e}"); return
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT user_id, string_session FROM sessions")
        rows = cur.fetchall(); conn.close()
    except Exception as e:
        print(f"\u274c Gagal load sessions: {e}"); return
    if not rows:
        print("\u2139\ufe0f Tidak ada session tersimpan."); return
    print(f"\U0001f504 Memuat {len(rows)} session tersimpan...")
    for row in rows:
        user_id, string_session = row[0], row[1]
        if not is_subscribed(user_id):
            print(f"\u23ed\ufe0f Skip session user {user_id} (VIP tidak aktif)"); continue
        try:
            # Semua session menggunakan API_ID & API_HASH admin dari env
            client = build_client(API_ID, API_HASH, string_session)
            dl_locks.setdefault(user_id, asyncio.Lock())
            await client.start()
            _start_time[user_id] = time.monotonic()
            register_telethon_handlers(client, user_id)
            active_clients[user_id] = client
            asyncio.ensure_future(client.run_until_disconnected())
            print(f"\u2705 Session user {user_id} berhasil dimuat.")
        except Exception as e:
            print(f"\u26a0\ufe0f Gagal load session user {user_id}: {e}")
    print("\u2705 Semua session berhasil dimuat!")


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    setup_conv = ConversationHandler(
        entry_points=[CommandHandler("setup", cmd_setup)],
        states={
            PHONE_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_phone)],
            CODE_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_code)],
            PASSWORD_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_password)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("gift", cmd_gift))
    app.add_handler(CommandHandler("revoke", cmd_revoke))
    app.add_handler(setup_conv)
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern=r"^(menu_admin|admin_|bl_)"))
    app.add_handler(CallbackQueryHandler(user_callback_handler))
    app.add_handler(MessageHandler(filters.ALL, admin_message_handler), group=2)
    print("\U0001f916 Bot berjalan...")
    app.run_polling()


if __name__ == "__main__":
    main()
