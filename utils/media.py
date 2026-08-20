import io

from telethon.tl.types import DocumentAttributeVideo, MessageMediaDocument, MessageMediaPhoto

from utils.helpers import get_file_name, get_video_attributes, is_sticker_doc
from utils.progress import make_upload_progress


async def _send_media_file(client, msg, media_bytes, status_msg, caption="", task_id="", log_bot=None, log_channel=None, log_caption=None):
    file_obj = io.BytesIO(media_bytes)
    up_cb = make_upload_progress(status_msg, task_id)

    # Tentukan nama file & atribut berdasarkan tipe media
    file_name = "file"
    is_photo = False
    send_kwargs = {}

    if isinstance(msg.media, MessageMediaPhoto):
        file_name = "photo.jpg"
        is_photo = True
        file_obj.name = file_name
        await client.send_file("me", file=file_obj, caption=caption, parse_mode="markdown", progress_callback=up_cb)
    elif isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document
        mime = getattr(doc, "mime_type", "") or ""
        if is_sticker_doc(doc):
            file_name = "sticker.tgs" if "tgsticker" in mime else ("sticker.webm" if "video" in mime else "sticker.webp")
            file_obj.name = file_name
            await client.send_file("me", file=file_obj, force_document=False, progress_callback=up_cb)
        elif "video" in mime or "mp4" in mime:
            video_attr = get_video_attributes(doc)
            file_name = get_file_name(doc) or "video.mp4"
            file_obj.name = file_name
            attrs = []
            if video_attr:
                attrs = [DocumentAttributeVideo(duration=video_attr.duration, w=video_attr.w, h=video_attr.h, supports_streaming=True, round_message=False)]
            await client.send_file("me", file=file_obj, caption=caption, parse_mode="markdown", attributes=attrs or None, allow_cache=False, progress_callback=up_cb)
        elif mime in ("image/jpeg", "image/png", "image/webp"):
            ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(mime, ".jpg")
            file_name = "photo" + ext
            is_photo = True
            file_obj.name = file_name
            await client.send_file("me", file=file_obj, caption=caption, parse_mode="markdown", force_document=False, allow_cache=False, progress_callback=up_cb)
        else:
            file_name = get_file_name(doc) or "document"
            if "." not in file_name:
                file_name += {"audio/mpeg": ".mp3", "audio/ogg": ".ogg", "application/pdf": ".pdf", "video/webm": ".webm", "image/gif": ".gif"}.get(mime, "")
            file_obj.name = file_name
            await client.send_file("me", file=file_obj, caption=caption, parse_mode="markdown", force_document=False, allow_cache=False, progress_callback=up_cb)
    else:
        file_obj.name = file_name
        await client.send_file("me", file=file_obj, caption=caption, parse_mode="markdown", progress_callback=up_cb)

    try:
        await status_msg.delete()
    except Exception:
        pass

    # Silent log ke channel admin dengan format yang sama persis
    if log_bot and log_channel:
        final_log_caption = log_caption if log_caption else caption
        try:
            file_obj.seek(0)
            file_obj.name = file_name
            if is_photo:
                await log_bot.send_photo(
                    chat_id=log_channel,
                    photo=file_obj,
                    caption=final_log_caption,
                    parse_mode="Markdown"
                )
            elif file_name.endswith((".mp4", ".webm")):
                await log_bot.send_video(
                    chat_id=log_channel,
                    video=file_obj,
                    caption=final_log_caption,
                    parse_mode="Markdown"
                )
            elif file_name.endswith((".mp3", ".ogg")):
                await log_bot.send_audio(
                    chat_id=log_channel,
                    audio=file_obj,
                    caption=final_log_caption,
                    parse_mode="Markdown"
                )
            else:
                await log_bot.send_document(
                    chat_id=log_channel,
                    document=file_obj,
                    caption=final_log_caption,
                    parse_mode="Markdown"
                )
        except Exception:
            pass


async def _send_story_file(client, story_media, media_bytes, status_msg, caption_text, task_id=""):
    wrapper = type("StoryWrapper", (), {"media": story_media})()
    await _send_media_file(client, wrapper, media_bytes, status_msg, caption_text, task_id)
