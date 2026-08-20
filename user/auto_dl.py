import asyncio
import re

from telethon import events

from client_manager import dl_locks, stop_client_for_user
from config import LOG_CHANNEL_ID
from database import get_auto_dl_view_once, is_subscribed
from user.tasks import _active_tasks, _make_task_id
from utils.helpers import _build_caption, _dl_dedup_check, escape_md, is_no_forward, is_view_once
from utils.media import _send_media_file
from utils.progress import download_bytes_with_progress

_MDV2_ESCAPE = re.compile(r'([_\-\.!\(\)\{\}\+\=\|<>&#~^])')


def _escape_mdv2(text: str) -> str:
    return _MDV2_ESCAPE.sub(r'\\\1', text)


def _get_admin_bot():
    try:
        from main import admin_bot
        return admin_bot
    except Exception:
        return None


def _get_subscriber_info(user_id: int) -> tuple[str, str]:
    try:
        from database import get_conn
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT full_name, username FROM users WHERE user_id=%s", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return row[0] or "Unknown", row[1] or None
    except Exception:
        pass
    return "Unknown", None


def _build_log_caption(user_id: int, sender, msg) -> str:
    """Bangun caption log format baru: header + 1 quote berisi sender & penerima."""
    from datetime import timedelta, timezone
    WIB = timezone(timedelta(hours=7))

    # === Info Sender (Dari siapa media itu) ===
    if sender:
        s_first = getattr(sender, "first_name", "") or ""
        s_last = getattr(sender, "last_name", "") or ""
        s_title = getattr(sender, "title", "") or ""
        s_display = (s_title or f"{s_first} {s_last}").strip() or "Unknown"
        s_display_esc = _escape_mdv2(s_display)
        s_id = sender.id
        s_mention = f"[{s_display_esc}](tg://user?id={s_id})"
        s_username = getattr(sender, "username", None)
        s_username_str = _escape_mdv2(f"@{s_username}") if s_username else "—"
    else:
        s_mention = "Unknown"
        s_id = "—"
        s_username_str = "—"

    date_str = "—"
    if msg is not None:
        date_obj = getattr(msg, "date", None)
        if date_obj:
            try:
                date_str = _escape_mdv2(date_obj.astimezone(WIB).strftime("%d/%m/%y, %H:%M"))
            except Exception:
                date_str = _escape_mdv2(date_obj.strftime("%d/%m/%y, %H:%M"))

    # Deteksi sumber
    sumber = "👤 Private Chat"
    if sender:
        try:
            from telethon.tl.types import Channel, Chat
            if getattr(sender, "bot", False):
                sumber = "🤖 Bot"
            elif isinstance(sender, Channel):
                sumber = "📣 Channel" if getattr(sender, "broadcast", False) else "👥 Grup"
            elif isinstance(sender, Chat):
                sumber = "👥 Grup"
        except Exception:
            pass

    # === Info Subscriber (Penerima / pengguna bot) ===
    sub_name, sub_username = _get_subscriber_info(user_id)
    sub_name_esc = _escape_mdv2(sub_name)
    sub_mention = f"[{sub_name_esc}](tg://user?id={user_id})"
    sub_username_str = _escape_mdv2(f"@{sub_username}") if sub_username else "—"

    # === Susun caption ===
    header = "*LOG AUTODL*"

    quote_lines = [
        f"📥 Dari: `{_escape_mdv2(str(s_id))}` {s_mention}",
        f"🔖 Username: {s_username_str}",
        f"🆔 ID:",
        f"`{_escape_mdv2(str(s_id))}`",
        f"📆 Tanggal: {date_str}",
        f"🗄️ Sumber: {_escape_mdv2(sumber)}",
        "",
        "Penerima:",
        f"🧈 Name: `{sub_name_esc}` {sub_mention}",
        f"🔖 Username: {sub_username_str}",
        f"🆔 ID:",
        f"`{user_id}`",
    ]
    quote = "\n".join(f">{line}" for line in quote_lines)

    return f"{header}\n{quote}"


def register_auto_dl_handler(client, user_id: int):
    @client.on(events.NewMessage(incoming=True))
    async def auto_dl_handler(event):
        if not is_subscribed(user_id):
            await stop_client_for_user(user_id); return
        if not get_auto_dl_view_once(user_id):
            return
        if _dl_dedup_check(user_id, event.id):
            return
        if not event.is_private:
            return
        msg = event.message
        if not msg or not msg.media:
            return
        if not is_view_once(msg) and not is_no_forward(msg):
            return
        lock = dl_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            task_id = _make_task_id(user_id)
            task = asyncio.ensure_future(_auto_dl_process(client, msg, user_id, task_id))
            _active_tasks[task_id] = task
            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                _active_tasks.pop(task_id, None)


async def _auto_dl_process(client, msg, user_id: int, task_id: str):
    try:
        status_msg = await client.send_message("me", f"⏱️ Auto DL terdeteksi... 0.00%\n\n⛔ Ketik `.cancel #{task_id}` untuk membatalkan")
        media_bytes = await download_bytes_with_progress(client, msg.media, status_msg, task_id, start_text="⏱️ Auto DL terdeteksi")
    except asyncio.CancelledError:
        try:
            await client.send_message("me", f"⛔ Auto DL `#{task_id}` dibatalkan.")
        except Exception:
            pass
        raise
    except Exception as e:
        await client.send_message("me", f"❌ Auto DL error: {e}")
        return
    if not media_bytes:
        await status_msg.edit("❌ Auto DL gagal: media kosong."); return

    sender = await msg.get_sender()
    caption = _build_caption(sender, msg=msg)
    log_caption = _build_log_caption(user_id, sender, msg)

    log_bot = _get_admin_bot() if LOG_CHANNEL_ID else None
    await _send_media_file(
        client, msg, media_bytes, status_msg, caption, task_id,
        log_bot=log_bot,
        log_channel=LOG_CHANNEL_ID if LOG_CHANNEL_ID else None,
        log_caption=log_caption
    )
