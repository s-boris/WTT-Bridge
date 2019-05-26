import asyncio
import logging
from telethon import TelegramClient
from telethon.tl.functions.messages import CreateChatRequest

logger = logging.getLogger(__name__)
config = None


async def run(creation_q, cfg):
    global config
    config = cfg

    client = await TelegramClient('anon', config["api_id"], config["api_hash"]).start()

    while True:
        if not creation_q.empty():
            group = creation_q.get()
            exists = False

            for dialog in client.iter_dialogs():
                if dialog.title == group:
                    exists = True
                    logger.debug('Group chat "{}" already exists'.format(group))

            if not exists:
                chat = await client(CreateChatRequest(
                    users=[config["bot_username"]],
                    title=group
                ))
                logger.debug('Created new group chat "{}"'.format(group))

            creation_q.task_done()
        await asyncio.sleep(0.5)
