from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from auth.states import waiting_gift, waiting_restore, waiting_revoke
from config import ADMIN_ID
from database import blacklist_add, blacklist_remove
from keyboards import admin_keyboard, blacklist_keyboard
from admin.backup import _do_backup, _split_sql_statements
from admin.blacklist import build_blacklist_text
from admin.gift import _do_gift
from admin.vip import _do_revoke

waiting_bl_add: set[int] = set()
waiting_bl_remove: set[int] = set()


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    if uid != ADMIN_ID:
        await query.answer(); return
    if not (data == "menu_admin" or data.startswith("admin_") or data.startswith("bl_")):
        return
    await query.answer()

    if data == "menu_admin":
        await query.edit_message_text("👤 *Menu Admin*", reply_markup=admin_keyboard(), parse_mode="Markdown"); return
    if data == "admin_backup":
        await query.edit_message_text("⏳ Sedang membuat backup...")
        try:
            sql_bytes = await _do_backup(context)
            fname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            await context.bot.send_document(chat_id=uid, document=sql_bytes, filename=fname, caption="✅ Backup database berhasil!")
            await query.edit_message_text("✅ Backup selesai!", reply_markup=admin_keyboard())
        except Exception as e:
            await query.edit_message_text(f"❌ Backup gagal: {e}", reply_markup=admin_keyboard())
        return
    if data == "admin_restore":
        waiting_restore.add(uid)
        await query.edit_message_text("♻️ *Restore Database*\n\nKirim file `.sql` backup kamu sekarang.\nAtau ketik /cancel untuk batal.", parse_mode="Markdown"); return
    if data == "admin_gift":
        waiting_gift.add(uid)
        await query.edit_message_text("🎁 *Gift VIP*\n\nKirim: `<user_id atau @username> <jumlah_hari>`\nContoh: `123456789 30`\n\nAtau ketik /cancel untuk batal.", parse_mode="Markdown"); return
    if data == "admin_revoke":
        waiting_revoke.add(uid)
        await query.edit_message_text("🚫 *Revoke VIP*\n\nKirim user ID atau @username yang ingin dicabut VIP-nya.\nAtau ketik /cancel untuk batal.", parse_mode="Markdown"); return
    if data == "admin_blacklist":
        await query.edit_message_text("🔒 *Blacklist Channel*\n\nKelola daftar channel/grup yang diblokir dari .copy", reply_markup=blacklist_keyboard(), parse_mode="Markdown"); return
    if data == "bl_add":
        waiting_bl_add.add(uid)
        await query.edit_message_text("➕ *Tambah ke Blacklist*\n\nKirim username atau ID channel.\nFormat: `@username` atau `-100xxxxxxxxxx`\nBisa tambah catatan: `@username alasan`\n\nKetik /cancel untuk batal.", parse_mode="Markdown"); return
    if data == "bl_remove":
        waiting_bl_remove.add(uid)
        await query.edit_message_text("➖ *Hapus dari Blacklist*\n\nKirim username atau ID channel yang ingin dihapus.\nKetik /cancel untuk batal.", parse_mode="Markdown"); return
    if data == "bl_list":
        await query.edit_message_text(build_blacklist_text(), reply_markup=blacklist_keyboard(), parse_mode="Markdown"); return


async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
    in_any = uid in waiting_gift or uid in waiting_revoke or uid in waiting_restore or uid in waiting_bl_add or uid in waiting_bl_remove
    if not in_any:
        return

    if uid in waiting_restore:
        waiting_restore.discard(uid)
        if not update.message.document:
            await update.message.reply_text("❌ Kirim file .sql yang valid, atau ketik /cancel untuk batal.")
            waiting_restore.add(uid); return
        file = await context.bot.get_file(update.message.document.file_id)
        import io
        buf = io.BytesIO(); await file.download_to_memory(buf); sql = buf.getvalue().decode()
        try:
            from database import get_conn
            conn = get_conn(); cur = conn.cursor(); stmts = _split_sql_statements(sql)
            for stmt in stmts:
                cur.execute(stmt)
            conn.commit(); conn.close()
            await update.message.reply_text(f"✅ Restore berhasil! ({len(stmts)} statement dijalankan)", reply_markup=admin_keyboard())
        except Exception as e:
            await update.message.reply_text(f"❌ Restore gagal: {e}", reply_markup=admin_keyboard())
        return

    if uid in waiting_gift:
        waiting_gift.discard(uid)
        parts = (update.message.text.strip() if update.message.text else "").split()
        if not parts:
            await update.message.reply_text("❌ Input tidak valid. Ketik /cancel untuk batal."); waiting_gift.add(uid); return
        days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 30
        ok, msg = await _do_gift(parts[0], days, context)
        await update.message.reply_text(msg, reply_markup=admin_keyboard()); return

    if uid in waiting_revoke:
        waiting_revoke.discard(uid)
        text = update.message.text.strip() if update.message.text else ""
        if not text:
            await update.message.reply_text("❌ Input tidak valid. Ketik /cancel untuk batal."); waiting_revoke.add(uid); return
        ok, msg = await _do_revoke(text, context)
        await update.message.reply_text(msg, reply_markup=admin_keyboard()); return

    if uid in waiting_bl_add:
        waiting_bl_add.discard(uid)
        text = update.message.text.strip() if update.message.text else ""
        parts = text.split(maxsplit=1)
        if not parts:
            await update.message.reply_text("❌ Input tidak valid. Ketik /cancel untuk batal."); waiting_bl_add.add(uid); return
        identifier = parts[0].lstrip("@"); note = parts[1] if len(parts) > 1 else ""
        ok = blacklist_add(identifier, note)
        await update.message.reply_text(f"✅ `{identifier}` berhasil ditambahkan ke blacklist." if ok else f"⚠️ `{identifier}` sudah ada di blacklist.", parse_mode="Markdown", reply_markup=blacklist_keyboard())
        return

    if uid in waiting_bl_remove:
        waiting_bl_remove.discard(uid)
        identifier = (update.message.text.strip() if update.message.text else "").lstrip("@")
        if not identifier:
            await update.message.reply_text("❌ Input tidak valid. Ketik /cancel untuk batal."); waiting_bl_remove.add(uid); return
        ok = blacklist_remove(identifier)
        await update.message.reply_text(f"✅ `{identifier}` berhasil dihapus dari blacklist." if ok else f"❌ `{identifier}` tidak ditemukan di blacklist.", parse_mode="Markdown", reply_markup=blacklist_keyboard())
