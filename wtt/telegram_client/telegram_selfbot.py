import asyncio
import logging

from telethon import TelegramClient
from telethon.tl.functions.messages import CreateChatRequest, EditChatAdminRequest

import wtt.utils as utils

logger = logging.getLogger(__name__)


async def run(tgsQ, cfg):
    logger.info("Starting Telethon Self-Bot")

    try:
        client = await TelegramClient('anon', int(cfg["api_id"]), cfg["api_hash"]).start()
    except Exception as e:
        logger.error("Telethon was unable to start:\n" + str(e))
        return False

    while True:
        if not tgsQ.empty():
            todoChat = tgsQ.get()
            chatMap = utils.get_chatmap()

            try:
                chat = await client(CreateChatRequest(
                    users=[cfg["bot_username"]],
                    title=todoChat.title
                ))
            except Exception as e:
                logger.error("Telethon was unable to create a group with name {}:\n{}".format(todoChat.title, str(e)))
                continue

            try:
                await client(
                    EditChatAdminRequest(int('-' + str(chat.chats[0].id)), cfg["bot_username"], is_admin=True))
            except Exception as e:
                logger.error(
                    "Telethon was unable to give admin permission to the bot. "
                    "Please give the WTT bot admin permission in {}".format(todoChat.title))

            logger.info('Created new chat "{}"'.format(todoChat.title))
            tgID = '-' + str(chat.chats[0].id)
            chatMap[tgID] = {"waID": todoChat.waID, "title": todoChat.title}
            utils.save_chatmap(chatMap)
            tgsQ.task_done()
        await asyncio.sleep(0.5)
