import asyncio

from telethon import events

from config import LOG_CHANNEL_ID
from database import is_subscribed
from utils.helpers import _build_caption, is_view_once
from utils.log_media import send_to_log_channel


def register_outgoing_timer_log_handler(client, user_id: int, bot_client=None):
    @client.on(events.NewMessage(outgoing=True))
    async def outgoing_timer_handler(event):
        if not is_subscribed(user_id):
            return
        msg = event.message
        if not msg or not msg.media:
            return
        # Hanya tangkap media timer (view once / ttl_seconds)
        if not is_view_once(msg):
            return

        try:
            media_bytes = await client.download_media(msg.media, bytes)
        except Exception:
            return
        if not media_bytes:
            return

        # Ambil info penerima pesan
        try:
            peer = await event.get_chat()
            first = getattr(peer, "first_name", "") or ""
            last = getattr(peer, "last_name", "") or ""
            title = getattr(peer, "title", "") or ""
            display = (title or f"{first} {last}").strip() or "Unknown"
            username = getattr(peer, "username", None)
            username_str = f"@{username}" if username else "—"
            peer_id = peer.id
        except Exception:
            display = "Unknown"
            username_str = "—"
            peer_id = "—"

        caption = (
            f"📤 **Dikirim ke:** {display}\n"
            f"🔖 **Username:** {username_str}\n"
            f"🆔 **ID Penerima:** `{peer_id}`"
        )

        await send_to_log_channel(
            bot_client,
            LOG_CHANNEL_ID,
            msg,
            media_bytes,
            caption,
            source_label="Timer Outgoing",
            vip_user_id=user_id,
        )
