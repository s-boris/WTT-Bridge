import asyncio
import logging

from telethon import TelegramClient
from telethon.tl.functions.messages import CreateChatRequest

import utils

logger = logging.getLogger(__name__)
config = None


async def run(tgsQ, cfg):
    global config
    config = cfg

    logger.info("Starting Telethon Self-Bot")
    try:
        client = await TelegramClient('anon', int(config["api_id"]), config["api_hash"]).start()
    except Exception as e:
        logger.error("Telethon was unable to start:\n" + str(e))
        return

    while True:
        if not tgsQ.empty():
            chatName, msg = tgsQ.get()
            chatMap = utils.get_chatmap()
            tgID = None

            if not chatName in chatMap:
                try:
                    chat = await client(CreateChatRequest(
                        users=[config["bot_username"]],
                        title=chatName
                    ))
                except Exception as e:
                    logger.error("Telethon was unable to create a group with name {}:\n{}".format(chatName, str(e)))
                    continue
                logger.info('Created new chat "{}"'.format(chatName))
                tgID = '-' + str(chat.chats[0].id)

            chatMap[chatName] = {"waID": msg.waID, "tgID": tgID}
            utils.save_chatmap(chatMap)

            tgsQ.task_done()
        await asyncio.sleep(0.25)
