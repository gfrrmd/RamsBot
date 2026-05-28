import asyncio

from telethon import events

from client_manager import dl_locks, stop_client_for_user
from database import is_subscribed
from user.tasks import _active_tasks, _make_task_id
from utils.helpers import _build_caption, _dl_dedup_check, is_no_forward
from utils.media import _send_media_file
from utils.progress import download_bytes_with_progress


def register_download_handler(client, user_id: int):
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.dl$"))
    async def dl_handler(event):
        if not is_subscribed(user_id):
            await stop_client_for_user(user_id)
            await event.client.send_message("me", "❌ Langganan VIP kamu sudah habis atau dicabut.\nHubungi admin untuk memperpanjang.")
            return
        if _dl_dedup_check(user_id, event.id):
            return
        lock = dl_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            task_id = _make_task_id(user_id)
            task = asyncio.ensure_future(_process_dl(event, client, user_id, task_id))
            _active_tasks[task_id] = task
            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                _active_tasks.pop(task_id, None)


async def _process_dl(event, client, user_id, task_id: str):
    if not is_subscribed(user_id):
        await stop_client_for_user(user_id)
        await event.client.send_message("me", "❌ Langganan VIP kamu sudah habis atau dicabut.\nHubungi admin untuk memperpanjang.")
        return
    await event.delete()
    if not event.is_reply:
        return
    replied = await event.get_reply_message()
    if not replied or not replied.media:
        return

    sender = await replied.get_sender()
    caption = _build_caption(sender, msg=replied)
    status_msg = await client.send_message("me", "⏳ Sedang memproses...")
    is_view_once_media = bool(getattr(replied.media, "ttl_seconds", None))

    if not is_view_once_media and not is_no_forward(replied):
        try:
            await client.forward_messages("me", replied)
            await status_msg.edit(caption, parse_mode="markdown")
            return
        except Exception:
            pass
    try:
        media_bytes = await download_bytes_with_progress(client, replied.media, status_msg, task_id)
    except asyncio.CancelledError:
        try:
            await status_msg.edit(f"⛔ Unduhan `#{task_id}` dibatalkan.")
        except Exception:
            pass
        raise
    except Exception as e:
        await status_msg.edit(f"❌ Gagal mendownload: {e}")
        return
    if not media_bytes:
        await status_msg.delete(); return
    await _send_media_file(client, replied, media_bytes, status_msg, caption, task_id)
