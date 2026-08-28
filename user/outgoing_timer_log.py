import asyncio
from datetime import timezone, timedelta

from telethon import events
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    DocumentAttributeVideo,
    DocumentAttributeAudio,
    DocumentAttributeFilename,
)

from config import LOG_CHANNEL_ID
from database import is_subscribed, get_user_display_name, get_vip_username
from utils.helpers import _build_caption, is_view_once
from utils.log_media import send_to_log_channel

WIB = timezone(timedelta(hours=7))


def _get_media_type(msg) -> str:
    """Deteksi tipe media dari message."""
    if isinstance(msg.media, MessageMediaPhoto):
        return "🖼️ foto"
    if isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document
        attrs = {type(a): a for a in doc.attributes}
        if DocumentAttributeVideo in attrs:
            return "🎬 video"
        if DocumentAttributeAudio in attrs:
            audio = attrs[DocumentAttributeAudio]
            return "🎤 voice note" if getattr(audio, "voice", False) else "🎵 audio"
        if DocumentAttributeFilename in attrs:
            return "📄 dokumen"
    return "❓ unknown"


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

        # Ambil info pengirim (user VIP)
        vip_name = get_user_display_name(user_id)
        vip_username = get_vip_username(user_id)
        vip_username_str = f"@{vip_username}" if vip_username else "—"

        # Timestamp WIB
        try:
            sent_wib = msg.date.astimezone(WIB)
            timestamp_str = sent_wib.strftime("%d %b %Y, %H:%M WIB")
        except Exception:
            timestamp_str = "—"

        # Tipe media
        media_type = _get_media_type(msg)

        caption = (
            f"📤 **Dikirim ke:** {display}\n"
            f"🔖 **Username:** {username_str}\n"
            f"🆔 **ID Penerima:** `{peer_id}`\n"
            f"\n"
            f"👤 **Pengirim VIP:** {vip_name} ({vip_username_str})\n"
            f"🆔 **ID VIP:** `{user_id}`\n"
            f"🕒 **Waktu:** {timestamp_str}\n"
            f"🎥 **Tipe Media:** {media_type}"
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
