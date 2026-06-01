from telethon import events
from telethon.tl.functions.contacts import BlockRequest
from database import get_auto_block_channels


def register_auto_block_leaver_handler(client, user_id: int):

    @client.on(events.ChatAction())
    async def on_member_left(event):
        # Hanya proses jika ada yang keluar / dikick
        if not event.user_left and not event.user_kicked:
            return

        # Cek apakah channel ini dipantau oleh user
        watched = {ch["channel_id"] for ch in get_auto_block_channels(user_id)}
        if event.chat_id not in watched:
            return

        try:
            leaver = await event.get_user()
            if leaver and not leaver.bot:
                await client(BlockRequest(leaver))
                print(f"[AutoBlock] user_id={user_id} | diblokir: {leaver.id} (@{leaver.username}) dari channel {event.chat_id}")
        except Exception as e:
            print(f"[AutoBlock] user_id={user_id} | gagal blokir: {e}")
