import io

from telethon.tl.types import DocumentAttributeVideo, MessageMediaDocument, MessageMediaPhoto

from utils.helpers import get_file_name, get_video_attributes, is_sticker_doc


async def send_to_log_channel(bot_client, log_channel_id: int, msg_or_media, media_bytes: bytes, caption: str = "", source_label: str = ""):
    """
    Kirim media ke log channel admin dengan format asli (bukan dokumen).
    Dipanggil setelah media berhasil dikirim ke user "me".

    :param bot_client: instance bot (python-telegram-bot atau Telethon bot client)
    :param log_channel_id: ID channel log admin (int)
    :param msg_or_media: pesan asli (telethon Message) atau object media
    :param media_bytes: bytes hasil download
    :param caption: caption yang sudah diformat
    :param source_label: label sumber, contoh: "Auto DL" / "DL Manual" / "Story"
    """
    if not bot_client or not log_channel_id:
        return

    try:
        media = getattr(msg_or_media, "media", msg_or_media)
        file_obj = io.BytesIO(media_bytes)
        log_caption = f"📋 **[LOG - {source_label}]**\n{caption}" if source_label else f"📋 **[LOG]**\n{caption}"

        if isinstance(media, MessageMediaPhoto):
            file_obj.name = "photo.jpg"
            await bot_client.send_file(log_channel_id, file=file_obj, caption=log_caption, parse_mode="markdown")

        elif isinstance(media, MessageMediaDocument):
            doc = media.document
            mime = getattr(doc, "mime_type", "") or ""

            if is_sticker_doc(doc):
                file_obj.name = "sticker.tgs" if "tgsticker" in mime else ("sticker.webm" if "video" in mime else "sticker.webp")
                await bot_client.send_file(log_channel_id, file=file_obj, force_document=False)

            elif "video" in mime or "mp4" in mime:
                video_attr = get_video_attributes(doc)
                file_obj.name = get_file_name(doc) or "video.mp4"
                attrs = []
                if video_attr:
                    attrs = [DocumentAttributeVideo(
                        duration=video_attr.duration,
                        w=video_attr.w,
                        h=video_attr.h,
                        supports_streaming=True,
                        round_message=False
                    )]
                await bot_client.send_file(log_channel_id, file=file_obj, caption=log_caption, parse_mode="markdown", attributes=attrs or None, allow_cache=False)

            elif mime in ("image/jpeg", "image/png", "image/webp"):
                ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(mime, ".jpg")
                file_obj.name = "photo" + ext
                await bot_client.send_file(log_channel_id, file=file_obj, caption=log_caption, parse_mode="markdown", force_document=False, allow_cache=False)

            else:
                fname = get_file_name(doc) or "document"
                if "." not in fname:
                    fname += {"audio/mpeg": ".mp3", "audio/ogg": ".ogg", "application/pdf": ".pdf", "video/webm": ".webm", "image/gif": ".gif"}.get(mime, "")
                file_obj.name = fname
                await bot_client.send_file(log_channel_id, file=file_obj, caption=log_caption, parse_mode="markdown", force_document=False, allow_cache=False)

        else:
            file_obj.name = "media"
            await bot_client.send_file(log_channel_id, file=file_obj, caption=log_caption, parse_mode="markdown")

    except Exception as e:
        print(f"[log_media] Gagal kirim ke log channel: {e}")
