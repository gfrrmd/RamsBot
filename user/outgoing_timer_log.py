import asyncio

from telethon import events

from config import LOG_CHANNEL_ID
from database import is_subscribed
from utils.helpers import is_view_once
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

        if bot_client is None:
            print(f"[outgoing_timer_log] bot_client None untuk user {user_id}, log dilewati")
            return

        try:
            media_bytes = await client.download_media(msg.media, bytes)
        except Exception as e:
            print(f"[outgoing_timer_log] Gagal download media user {user_id}: {e}")
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
        except Exception as e:
            print(f"[outgoing_timer_log] Gagal ambil info peer user {user_id}: {e}")
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
