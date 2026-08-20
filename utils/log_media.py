import io
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telethon.tl.types import DocumentAttributeVideo, MessageMediaDocument, MessageMediaPhoto

from database import get_user_display_name
from utils.helpers import get_file_name, get_video_attributes, is_sticker_doc


def _vip_button(vip_user_id: int) -> InlineKeyboardMarkup | None:
    """Buat inline button yang mengarah ke profil user VIP dengan nama depannya."""
    if not vip_user_id:
        return None
    display_name = get_user_display_name(vip_user_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            text=f"💬 Member VIP: {display_name}",
            url=f"tg://user?id={vip_user_id}"
        )]
    ])


async def send_to_log_channel(ptb_bot, log_channel_id: int, msg_or_media, media_bytes, caption: str = "", source_label: str = "", vip_user_id: int = 0):
    """
    Kirim media ke log channel admin menggunakan python-telegram-bot (PTB).
    Format dikirim sesuai tipe aslinya (foto, video, audio, dll).
    Info member VIP dikirim sebagai inline button dengan nama depan.

    :param ptb_bot: instance telegram.Bot dari PTB (app.bot)
    :param log_channel_id: ID channel log admin (int)
    :param msg_or_media: pesan asli (telethon Message) atau object media
    :param media_bytes: bytes hasil download, atau None jika forward biasa
    :param caption: caption info sender media yang sudah diformat
    :param source_label: label sumber, contoh: "Auto DL" / "DL Manual" / "Story"
    :param vip_user_id: Telegram user_id member VIP yang melakukan DL
    """
    if not ptb_bot or not log_channel_id:
        return

    header = f"📋 <b>LOG {source_label}</b>\n" if source_label else "📋 <b>LOG</b>\n"
    log_caption = header + _to_html(caption)
    reply_markup = _vip_button(vip_user_id)

    try:
        if media_bytes is None:
            await ptb_bot.send_message(
                chat_id=log_channel_id,
                text=log_caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            return

        media = getattr(msg_or_media, "media", msg_or_media)
        file_obj = io.BytesIO(media_bytes)

        if isinstance(media, MessageMediaPhoto):
            file_obj.name = "photo.jpg"
            await ptb_bot.send_photo(
                chat_id=log_channel_id, photo=file_obj,
                caption=log_caption, parse_mode="HTML",
                reply_markup=reply_markup
            )

        elif isinstance(media, MessageMediaDocument):
            doc = media.document
            mime = getattr(doc, "mime_type", "") or ""

            if is_sticker_doc(doc):
                file_obj.name = "sticker.webp"
                await ptb_bot.send_sticker(chat_id=log_channel_id, sticker=file_obj)
                await ptb_bot.send_message(
                    chat_id=log_channel_id,
                    text=log_caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )

            elif "video" in mime or "mp4" in mime:
                video_attr = get_video_attributes(doc)
                file_obj.name = get_file_name(doc) or "video.mp4"
                w = getattr(video_attr, "w", None) if video_attr else None
                h = getattr(video_attr, "h", None) if video_attr else None
                dur = int(getattr(video_attr, "duration", 0) or 0) if video_attr else 0
                await ptb_bot.send_video(
                    chat_id=log_channel_id, video=file_obj,
                    caption=log_caption, parse_mode="HTML",
                    duration=dur, width=w, height=h,
                    supports_streaming=True,
                    reply_markup=reply_markup
                )

            elif mime in ("image/jpeg", "image/png", "image/webp"):
                ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(mime, ".jpg")
                file_obj.name = "photo" + ext
                await ptb_bot.send_photo(
                    chat_id=log_channel_id, photo=file_obj,
                    caption=log_caption, parse_mode="HTML",
                    reply_markup=reply_markup
                )

            elif "audio" in mime:
                fname = get_file_name(doc) or "audio"
                ext = {"audio/mpeg": ".mp3", "audio/ogg": ".ogg"}.get(mime, "")
                if "." not in fname:
                    fname += ext
                file_obj.name = fname
                await ptb_bot.send_audio(
                    chat_id=log_channel_id, audio=file_obj,
                    caption=log_caption, parse_mode="HTML",
                    reply_markup=reply_markup
                )

            elif "gif" in mime or "image/gif" in mime:
                file_obj.name = "animation.gif"
                await ptb_bot.send_animation(
                    chat_id=log_channel_id, animation=file_obj,
                    caption=log_caption, parse_mode="HTML",
                    reply_markup=reply_markup
                )

            else:
                fname = get_file_name(doc) or "document"
                if "." not in fname:
                    fname += {"application/pdf": ".pdf", "video/webm": ".webm"}.get(mime, "")
                file_obj.name = fname
                await ptb_bot.send_document(
                    chat_id=log_channel_id, document=file_obj,
                    caption=log_caption, parse_mode="HTML",
                    reply_markup=reply_markup
                )

        else:
            file_obj.name = "media"
            await ptb_bot.send_document(
                chat_id=log_channel_id, document=file_obj,
                caption=log_caption, parse_mode="HTML",
                reply_markup=reply_markup
            )

    except Exception as e:
        print(f"[log_media] Gagal kirim ke log channel: {e}")


def _to_html(md_text: str) -> str:
    """Konversi markdown sederhana ke HTML untuk PTB."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", md_text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"\[(.+?)\]\((tg://[^)]+|https?://[^)]+)\)", r'<a href="\2">\1</a>', text)
    return text
