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

# Karakter yang wajib di-escape di MarkdownV2 (kecuali yang dipakai untuk formatting)
_MDV2_ESCAPE = re.compile(r'([_\-\.!\(\)\{\}\+\=\|<>&#~^])')


def _escape_mdv2(text: str) -> str:
    """Escape karakter spesial MarkdownV2, kecuali * ` [ ] yang dipakai formatting."""
    return _MDV2_ESCAPE.sub(r'\\\1', text)


def _convert_caption_to_mdv2(caption: str) -> str:
    """
    Konversi caption yang menggunakan Markdown biasa ke MarkdownV2.
    - Escape karakter spesial di teks biasa
    - Pertahankan **bold**, `code`, [text](url)
    """
    result = []
    # Proses per baris
    for line in caption.split("\n"):
        # Escape seluruh teks dulu, lalu restore formatting yang valid
        # Pendekatan: parse token per token
        # Pattern: **bold**, `code`, [text](url), teks biasa
        pattern = re.compile(r'(\*\*.*?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))')
        parts = pattern.split(line)
        new_parts = []
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                # Bold: **text** → *escaped_text*
                inner = part[2:-2]
                new_parts.append(f"*{_escape_mdv2(inner)}*")
            elif part.startswith('`') and part.endswith('`'):
                # Code: tetap apa adanya tapi escape isi
                inner = part[1:-1]
                new_parts.append(f"`{inner}`")
            elif part.startswith('[') and '](' in part:
                # Link: [text](url)
                m = re.match(r'\[([^\]]+)\]\(([^)]+)\)', part)
                if m:
                    link_text = _escape_mdv2(m.group(1))
                    url = m.group(2)  # URL tidak perlu di-escape
                    new_parts.append(f"[{link_text}]({url})")
                else:
                    new_parts.append(_escape_mdv2(part))
            else:
                new_parts.append(_escape_mdv2(part))
        result.append("".join(new_parts))
    return "\n".join(result)


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
    """Bangun caption log dengan dua expandable blockquote dalam MarkdownV2."""
    sub_name, sub_username = _get_subscriber_info(user_id)
    sub_name_escaped = _escape_mdv2(escape_md(sub_name))
    sub_username_str = _escape_mdv2(f"@{sub_username}") if sub_username else "—"
    sub_mention = f"[{sub_name_escaped}](tg://user?id={user_id})"

    # Quote pertama: info subscriber (pengguna bot)
    quote1_lines = [
        "📋 *Log Auto DL*",
        f"🧑\u200d💻 *Subscriber ID:* `{user_id}`",
        f"🔗 *Mention:* {sub_mention}",
        f"🔖 *Username:* {sub_username_str}",
    ]
    quote1 = "\n".join(f">{line}" for line in quote1_lines)

    # Quote kedua: info pengirim media — konversi dari Markdown biasa ke MarkdownV2
    sender_mdv2 = _convert_caption_to_mdv2(sender_caption)
    quote2_lines = sender_mdv2.split("\n")
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
