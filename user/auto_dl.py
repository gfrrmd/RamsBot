import asyncio

from telethon import events

from client_manager import dl_locks, stop_client_for_user
from config import LOG_CHANNEL_ID
from database import get_auto_dl_view_once, is_subscribed
from user.tasks import _active_tasks, _make_task_id
from utils.helpers import _build_caption, _dl_dedup_check, escape_md, is_no_forward, is_view_once
from utils.media import _send_media_file
from utils.progress import download_bytes_with_progress


def _get_admin_bot():
    try:
        from main import admin_bot
        return admin_bot
    except Exception:
        return None


def _get_subscriber_info(user_id: int) -> tuple[str, str]:
    """Ambil full_name dan username subscriber dari database."""
    try:
        from database import get_conn
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT full_name, username FROM users WHERE user_id=%s", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            full_name = row[0] or "Unknown"
            username = row[1] or None
            return full_name, username
    except Exception:
        pass
    return "Unknown", None


def _build_log_caption(user_id: int, sender_caption: str) -> str:
    """Bangun caption log dengan dua expandable blockquote."""
    sub_name, sub_username = _get_subscriber_info(user_id)
    sub_name_escaped = escape_md(sub_name)
    sub_username_str = f"@{sub_username}" if sub_username else "—"
    sub_mention = f"[{sub_name_escaped}](tg://user?id={user_id})"

    # Quote pertama: info subscriber (pengguna bot)
    quote1_lines = [
        "📋 **Log Auto DL**",
        f"🧑\u200d💻 **Subscriber ID:** `{user_id}`",
        f"🔗 **Mention:** {sub_mention}",
        f"🔖 **Username:** {sub_username_str}",
    ]
    quote1 = "\n".join(f">{line}" for line in quote1_lines)

    # Quote kedua: info pengirim media (dari siapa media itu diterima)
    quote2_lines = sender_caption.split("\n")
    quote2 = "\n".join(f">{line}" for line in quote2_lines)

    return f"{quote1}\n\n{quote2}"


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
    log_caption = _build_log_caption(user_id, caption)

    log_bot = _get_admin_bot() if LOG_CHANNEL_ID else None
    await _send_media_file(
        client, msg, media_bytes, status_msg, caption, task_id,
        log_bot=log_bot,
        log_channel=LOG_CHANNEL_ID if LOG_CHANNEL_ID else None,
        log_caption=log_caption
    )
