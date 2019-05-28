import asyncio
import logging

from telethon import TelegramClient
from telethon.tl.functions.messages import CreateChatRequest

import setup

logger = logging.getLogger(__name__)
config = None


async def run(tgsQ, cfg):
    global config
    config = cfg

    logger.info("Starting Telegram Self-Bot")
    client = await TelegramClient('anon', int(config["api_id"]), config["api_hash"]).start()

    while True:
        if not tgsQ.empty():
            chatName, msg = tgsQ.get()
            chatMap = setup.get_chatmap()
            tgID = None

            if not chatName in chatMap:
                chat = await client(CreateChatRequest(
                    users=[config["bot_username"]],
                    title=chatName
                ))
                logger.debug('Created new group chat "{}"'.format(chatName))
                tgID = '-' + str(chat.chats[0].id)

            # async for dialog in client.iter_dialogs():
            #     if dialog.title == chatName:
            #         exists = True
            #         logger.debug('Group chat "{}" already exists'.format(chatName))
            #         tgID = dialog.id

            chatMap[chatName] = {"waID": msg.waID, "tgID": tgID}
            setup.save_chatmap(chatMap)

            tgsQ.task_done()
        await asyncio.sleep(0.25)
