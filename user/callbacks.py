from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from client_manager import active_clients
from database import (
    bc_blacklist_get,
    get_auto_dl_view_once,
    get_user_session,
    is_subscribed,
    set_auto_dl_view_once,
    add_auto_block_channel,
    remove_auto_block_channel,
    get_auto_block_channels,
)
from keyboards import back_to_fitur_keyboard, bc_blacklist_keyboard, beli_keyboard, broadcast_keyboard, fitur_vip_keyboard, main_keyboard, timer_keyboard, tos_keyboard
from user.subscription import build_subscription_text
from utils.channel_scanner import get_admin_channels


async def _show_auto_block_menu(query, uid):
    client = active_clients.get(uid)
    if not client or not client.is_connected():
        await query.edit_message_text(
            "❌ Session belum aktif. Lakukan /setup dulu.",
            reply_markup=back_to_fitur_keyboard()
        )
        return

    # Kirim uid sebagai expected_user_id agar tidak bocor ke akun lain
    channels = await get_admin_channels(client, expected_user_id=uid)
    watched_ids = {ch["channel_id"] for ch in get_auto_block_channels(uid)}

    if not channels:
        await query.edit_message_text(
            "😔 *Auto Block Leaver*\n\nKamu tidak ditemukan sebagai admin di channel/grup manapun.",
            reply_markup=back_to_fitur_keyboard(),
            parse_mode="Markdown"
        )
        return

    buttons = []
    for ch in channels:
        status = "✅" if ch["id"] in watched_ids else "☑️"
        buttons.append([InlineKeyboardButton(
            f"{status} {ch['name']}",
            callback_data=f"abl_toggle_{ch['id']}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Kembali ke Fitur VIP", callback_data="menu_fitur")])

    await query.edit_message_text(
        "🔒 *Auto Block Leaver*\n\n"
        "Pilih channel yang ingin dipantau.\n"
        "Jika seseorang keluar dari channel yang aktif (✅), akun mereka akan otomatis diblokir dari akun Telegram kamu.\n\n"
        "✅ = aktif  |  ☑️ = nonaktif",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def user_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    if data == "menu_admin" or data.startswith("admin_") or data.startswith("bl_"):
        return
    await query.answer()

    if data == "menu_back":
        await query.edit_message_text("🏠 *Menu Utama*", reply_markup=main_keyboard(uid), parse_mode="Markdown"); return

    if data == "tos_close":
        try:
            await query.delete_message()
        except Exception:
            await query.edit_message_text("❌ Ditutup.", reply_markup=None)
        return

    if data == "menu_setup":
        has_session = bool(get_user_session(uid))
        if has_session:
            client = active_clients.get(uid)
            status = "🟢 Aktif" if client and client.is_connected() else "🔴 Tidak terhubung"
            await query.edit_message_text(
                f"⚙️ *Session kamu sudah terpasang*\nStatus: {status}\n\nKirim /setup untuk setup ulang.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "📋 *Kebijakan dan Ketentuan Penggunaan*\n\n"
                "Sebelum melanjutkan, harap baca dan pahami hal berikut:\n\n"
                "1. *Akses Sesi* — Kamu memberikan akses sesi login Telegram kamu kepada bot ini untuk menjalankan fitur VIP.\n\n"
                "2. *Tanggung Jawab* — Segala aktivitas yang dilakukan melalui sesi ini sepenuhnya menjadi tanggung jawab kamu. Risiko ditanggung sendiri.\n\n"
                "3. *Larangan* — Dilarang menggunakan fitur ini untuk spam, penipuan, atau aktivitas yang melanggar ketentuan Telegram maupun hukum yang berlaku.\n\n"
                "4. *Keamanan* — Kami tidak menyimpan password atau kode OTP kamu. Keamanan akun sepenuhnya menjadi tanggung jawab kamu.\n\n"
                "5. *Pencabutan Akses* — Kamu dapat menghapus sesi kapan saja melalui Pengaturan Telegram, menu Perangkat Aktif.\n\n"
                "Dengan menekan Saya Setuju, kamu menyatakan telah membaca dan menyetujui seluruh ketentuan di atas.",
                parse_mode="Markdown",
                reply_markup=tos_keyboard()
            )
        return

    if data == "menu_subscription":
        user = query.from_user
        text = build_subscription_text(uid, full_name=user.full_name, username=user.username)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard(uid)); return
    if data == "menu_fitur":
        await query.edit_message_text("✨ *Fitur VIP*\n\nPilih fitur di bawah:", reply_markup=fitur_vip_keyboard(), parse_mode="Markdown"); return
    if data == "menu_beli":
        await query.edit_message_text("💎 *Beli VIP*\n\nKlik tombol di bawah untuk menghubungi admin dan mendapatkan akses VIP.", parse_mode="Markdown", reply_markup=beli_keyboard()); return
    if data == "fitur_timer":
        await query.edit_message_text(
            "⏱️ *Download Media Timer & View Once*\n\n"
            "Simpan foto/video timer yang hanya bisa dilihat sekali (view once).\n\n"
            "📲 *Cara pakai - Manual:*\n"
            "Balas pesan view once/timer dengan perintah:\n"
            "`.dl`\n\n"
            "🤖 *Cara pakai - Auto DL (Otomatis):*\n"
            "Aktifkan Auto DL agar bot otomatis menyimpan setiap media view once yang masuk ke chat kamu.\n\n"
            "Gunakan tombol di bawah untuk ON/OFF.",
            reply_markup=timer_keyboard(uid), parse_mode="Markdown",
        ); return
    if data == "vip_toggle_auto_dl":
        current = get_auto_dl_view_once(uid)
        set_auto_dl_view_once(uid, not current)
        await query.edit_message_text(f"⏱️ *Auto DL View Once*\n\nSekarang: {'ON ✅' if not current else 'OFF ❌'}", reply_markup=timer_keyboard(uid), parse_mode="Markdown"); return
    if data == "fitur_copy":
        await query.edit_message_text(
            "📥 *Download dari Channel/Grup Private*\n\n"
            "Download pesan, foto, atau video dari channel/grup yang dibatasi (restricted/tidak bisa di-forward).\n\n"
            "📝 *Cara pakai:*\n"
            "Ketik dimanapun dengan command:\n"
            "`.copy (link postingan)`\n\n"
            "💡 *Contoh:*\n"
            "`.copy https://t.me/koleksijee/456`",
            reply_markup=back_to_fitur_keyboard(), parse_mode="Markdown",
        ); return
    if data == "fitur_story":
        await query.edit_message_text(
            "🎥 *Download Story*\n\n"
            "Download story Telegram milik orang lain langsung dari link story-nya.\n\n"
            "📝 *Cara pakai:*\n"
            "Kirim link story yang ingin didownload:\n"
            "`.story (link story)`\n\n"
            "💡 *Contoh:*\n"
            "`.story https://t.me/username/s/7`",
            reply_markup=back_to_fitur_keyboard(), parse_mode="Markdown",
        ); return
    if data == "fitur_ping":
        await query.edit_message_text(
            "🏓 *Ping*\n\n"
            "Cek apakah koneksi session Telethon kamu masih aktif dan berapa lama waktu responnya.\n\n"
            "📝 *Cara pakai:*\n"
            "Buka Saved Messages di Telegram kamu, lalu kirim:\n"
            "`.ping`\n\n"
            "💡 *Contoh hasil:*\n"
            "🏓 Pong! 42ms",
            reply_markup=back_to_fitur_keyboard(), parse_mode="Markdown",
        ); return
    if data == "fitur_broadcast":
        await query.edit_message_text(
            "📢 *Broadcast*\n\n"
            "Kirim pesan yang sama ke semua grup yang kamu join secara otomatis.\n\n"
            "📝 *Cara pakai:*\n"
            "Ketik command berikut dari chat manapun:\n"
            "`.bc (pesan kamu)`\n\n"
            "💡 *Contoh:*\n"
            "`.bc Hai, ada yang mau berteman?`\n\n"
            "🚫 *Batalkan broadcast:*\n"
            "`.cancel #task_id`",
            reply_markup=broadcast_keyboard(), parse_mode="Markdown",
        ); return
    if data == "fitur_acceptall":
        await query.edit_message_text(
            "✅ *Auto Approve*\n\n"
            "Approve semua join request di channel/grup kamu secara otomatis.\n\n"
            "📝 *Cara pakai:*\n"
            "Jalankan command di dalam channel, atau sertakan username/link:\n"
            "`.acceptall`\n"
            "`.acceptall (username/link channel)`\n\n"
            "💡 *Contoh:*\n"
            "`.acceptall @namaChannel`\n\n"
            "⏹ *Untuk stop:*\n"
            "`.stopaccept`",
            reply_markup=back_to_fitur_keyboard(), parse_mode="Markdown",
        ); return
    if data == "fitur_autoblock":
        await _show_auto_block_menu(query, uid)
        return
    if data.startswith("abl_toggle_"):
        channel_id = int(data.split("abl_toggle_")[1])
        watched = {ch["channel_id"] for ch in get_auto_block_channels(uid)}
        if channel_id in watched:
            remove_auto_block_channel(uid, channel_id)
        else:
            client = active_clients.get(uid)
            channel_name = ""
            if client:
                try:
                    entity = await client.get_entity(channel_id)
                    channel_name = getattr(entity, "title", "") or ""
                except Exception:
                    pass
            add_auto_block_channel(uid, channel_id, channel_name)
        await _show_auto_block_menu(query, uid)
        return
    if data == "bc_blacklist_menu":
        rows = bc_blacklist_get(uid)
        bl_text = "📋 Blacklist kamu kosong.\nSemua grup akan menerima broadcast." if not rows else f"🚫 *{len(rows)} grup diblacklist.*"
        await query.edit_message_text(
            f"⛔ *Blacklist Broadcast*\n\n{bl_text}\n\n"
            "Untuk mengelola blacklist, gunakan command:\n\n"
            "`.addbl` — Tambah ke blacklist\n"
            "`.addbl (ID Grup)` — Tambah ke blacklist by ID\n"
            "`.delbl` — Hapus blacklist\n"
            "`.delbl (ID Grup)` — Hapus blacklist by ID\n"
            "`.listbl` — Lihat list blacklist lengkap",
            reply_markup=bc_blacklist_keyboard(), parse_mode="Markdown",
        ); return
    if data == "bc_bl_list":
        rows = bc_blacklist_get(uid)
        if not rows:
            text = "📝 *Blacklist BC Kosong*\n\nSemua grup akan menerima broadcast kamu."
        else:
            lines = [f"🚫 *Blacklist BC* ({len(rows)} grup)\n"]
            for i, r in enumerate(rows, 1):
                lines.append(f"{i}. *{r['group_name'] or '—'}*\n   `{r['group_id']}` _({r.get('added_at', '')[:10]})_")
            text = "\n".join(lines)
        await query.edit_message_text(text, reply_markup=bc_blacklist_keyboard(), parse_mode="Markdown")
