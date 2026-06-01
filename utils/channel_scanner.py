from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantCreator, ChannelParticipantAdmin


async def get_admin_channels(client) -> list[dict]:
    """Kembalikan semua channel/grup di mana user adalah Creator atau Admin."""
    result = []
    try:
        me = await client.get_me()
        async for dialog in client.iter_dialogs():
            if not dialog.is_channel:
                continue
            try:
                p = await client(GetParticipantRequest(dialog.id, me.id))
                if isinstance(p.participant, (ChannelParticipantCreator, ChannelParticipantAdmin)):
                    result.append({
                        "id": dialog.id,
                        "name": dialog.name or str(dialog.id),
                    })
            except Exception:
                continue
    except Exception as e:
        print(f"[ChannelScanner] Error: {e}")
    return result
