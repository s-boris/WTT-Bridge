import asyncio

from telethon import TelegramClient
from telethon.tl.functions.messages import AddChatUserRequest, CreateChatRequest

config = None
creation_q = None


async def run(creation_queue, cfg):
    global config, creation_q
    config = cfg
    creation_q = creation_queue

    client = await TelegramClient('anon', config["api_id"], config["api_hash"]).start()

    while True:
        if not creation_q.empty():
            group = creation_q.get()
            chat = await client(CreateChatRequest(
                users=[config["bot_username"]],
                title=group
            ))
            group.task_done()
        await asyncio.sleep(0.5)
