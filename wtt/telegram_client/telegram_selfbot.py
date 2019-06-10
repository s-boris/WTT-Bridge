import asyncio
import logging

from telethon import TelegramClient
from telethon.tl.functions.messages import CreateChatRequest, EditChatAdminRequest

logger = logging.getLogger(__name__)


async def run(tgsQ, cfg, dao):
    logger.info("Starting Telethon Self-Bot")

    try:
        client = await TelegramClient('anon', int(cfg["api_id"]), cfg["api_hash"]).start()
    except Exception as e:
        logger.error("Telethon was unable to start:\n" + str(e))
        return False

    while True:
        if not tgsQ.empty():
            todoChat, cb = tgsQ.get()

            try:
                chat = await client(CreateChatRequest(
                    users=[cfg["bot_username"]],
                    title=todoChat.subject
                ))
            except Exception as e:
                logger.error("Telethon was unable to create a group with name {}:\n{}".format(todoChat.subject, str(e)))
                continue

            try:
                await client(
                    EditChatAdminRequest(int('-' + str(chat.chats[0].id)), cfg["bot_username"], is_admin=True))
            except Exception as e:
                logger.error(
                    "Telethon was unable to give admin permission to the bot. "
                    "Please give the WTT bot admin permission in {}".format(todoChat.subject))

            logger.info('Created new chat "{}"'.format(todoChat.subject))
            tgID = '-' + str(chat.chats[0].id)
            dao.createChat(tgID, todoChat.waID, todoChat.subject, cb=cb)
            tgsQ.task_done()
        await asyncio.sleep(0.1)
