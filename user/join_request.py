import asyncio
from telethon import events
from telethon.tl.functions.messages import GetChatInviteImportersRequest
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import Channel, InputPeerEmpty
from telethon.errors import (
    FloodWaitError,
    ChatAdminRequiredError,
    UserPrivacyRestrictedError,
    UserKickedError,
    UserNotMutualContactError,
    InputUserDeactivatedError,
    PeerFloodError,
)

running_tasks = {}

# Error yang tidak bisa di-approve, langsung skip
SKIP_ERRORS = (
    UserPrivacyRestrictedError,
    UserKickedError,
    UserNotMutualContactError,
    InputUserDeactivatedError,  # Deleted account
)


def register_join_request_handler(client, user_id: int):

    @client.on(events.NewMessage(pattern=r"^\.acceptall(?:\s+(.+))?$", outgoing=True))
    async def handle_accept_all(event):
        channel_input = event.pattern_match.group(1)

        try:
            if channel_input:
                channel = await client.get_entity(channel_input.strip())
            else:
                channel = await event.get_chat()
        except Exception as e:
            await event.reply(f"❌ Gagal resolve channel: `{e}`")
            return

        if not isinstance(channel, Channel):
            await event.reply("❌ Ini bukan channel. Jalankan command di dalam channel.")
            return

        task_key = (user_id, channel.id)
        if task_key in running_tasks:
            await event.reply("⚠️ Proses sudah berjalan. Ketik `.stopaccept` untuk stop.")
            return

        msg = await event.reply(
            f"🔄 Memulai approve join requests...\n"
            f"📢 **{channel.title}**\n"
            f"⚡ Mode: Batch 5 concurrent\n"
            f"⏹ `.stopaccept` untuk batal."
        )

        approved = 0
        skipped = 0
        failed = 0
        running_tasks[task_key] = True
        sem = asyncio.Semaphore(5)

        offset_date = 0
        offset_user = InputPeerEmpty()
        consecutive_empty = 0  # Guard kalau pagination stuck

        async def approve_one(importer):
            nonlocal approved, skipped, failed
            async with sem:
                try:
                    await client(InviteToChannelRequest(
                        channel=channel,
                        users=[importer.user_id]
                    ))
                    approved += 1
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds + 2)
                    try:
                        await client(InviteToChannelRequest(
                            channel=channel,
                            users=[importer.user_id]
                        ))
                        approved += 1
                    except SKIP_ERRORS:
                        skipped += 1
                    except Exception:
                        failed += 1
                except PeerFloodError:
                    # Akun kena flood global, tunggu lebih lama
                    await asyncio.sleep(30)
                    failed += 1
                except SKIP_ERRORS:
                    # Deleted account / privacy / limit — skip saja
                    skipped += 1
                except Exception:
                    failed += 1

        try:
            while running_tasks.get(task_key):
                try:
                    result = await client(GetChatInviteImportersRequest(
                        peer=channel,
                        requested=True,
                        offset_date=offset_date,
                        offset_user=offset_user,
                        limit=100,
                    ))
                except ChatAdminRequiredError:
                    await msg.edit("❌ Akun bukan admin atau tidak punya izin manage members.")
                    return
                except Exception as e:
                    await msg.edit(f"❌ Error saat fetch requests: `{e}`")
                    return

                if not result.importers:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        break  # Benar-benar sudah habis
                    await asyncio.sleep(2)
                    continue

                consecutive_empty = 0

                # Update cursor SEBELUM approve supaya tidak stuck
                last = result.importers[-1]
                offset_date = last.date
                try:
                    offset_user = await client.get_input_entity(last.user_id)
                except Exception:
                    offset_user = InputPeerEmpty()

                tasks = [approve_one(imp) for imp in result.importers]
                await asyncio.gather(*tasks)

                await msg.edit(
                    f"🔄 Progress approve...\n"
                    f"✅ Approved: **{approved}** | ⏩ Skip: **{skipped}** | ❌ Gagal: **{failed}**"
                )

                await asyncio.sleep(1)

        finally:
            running_tasks.pop(task_key, None)

        await msg.edit(
            f"✅ **Selesai!**\n\n"
            f"📢 **{channel.title}**\n"
            f"👥 Approved: **{approved}**\n"
            f"⏩ Diskip (deleted/limit): **{skipped}**\n"
            f"❌ Gagal: **{failed}**"
        )

    @client.on(events.NewMessage(pattern=r"^\.stopaccept$", outgoing=True))
    async def handle_stop_accept(event):
        channel = await event.get_chat()
        task_key = (user_id, channel.id)
        if task_key in running_tasks:
            running_tasks[task_key] = False
            await event.reply("🛑 Proses dihentikan.")
        else:
            await event.reply("ℹ️ Tidak ada proses yang berjalan di channel ini.")
