import logging
import time
from io import BytesIO

import telegram
from PIL import Image
from telegram.ext import Updater

import setup
from src.models import *

logger = logging.getLogger(__name__)

wttQ = None
tgsQ = None
config = None
dpg = None


def run(wttQueue, tgsQueue, cfg):
    global wttQ, tgsQ, config, dpg
    config = cfg
    wttQ = wttQueue
    tgsQ = tgsQueue

    logger.info("Starting Telegram Bot")
    updater = Updater(config['bot_token'], use_context=True)
    dp = updater.dispatcher

    dp.add_error_handler(error)
    updater.start_polling()

    dp.job_queue.run_repeating(msgListener, 1)

    dpg = dp


def msgListener(context):
    if not wttQ.empty() and isinstance(wttQ.queue[0], PrivateMessage):
        msg = wttQ.get()
        send(context, "[WA]" + msg.author, msg)
        wttQ.task_done()
    elif not wttQ.empty() and isinstance(wttQ.queue[0], GroupMessage):
        msg = wttQ.get()
        send(context, "[WA]" + msg.title, msg)
        wttQ.task_done()


def send(context, toChannelName, msg):
    sent = False

    while not sent:
        chatMap = setup.get_chatmap()
        if toChannelName in chatMap:
            if msg.type == "text":
                context.bot.send_message(chat_id=chatMap[toChannelName]['tgID'],
                                         text="*{}*:\n\n{}".format(msg.author, msg.body),
                                         parse_mode=telegram.ParseMode.MARKDOWN)
            elif msg.type == "image":
                bio = BytesIO(msg.body)
                img = Image.open(bio)
                img.save(bio, 'JPEG')
                bio.seek(0)
                context.bot.send_photo(chat_id=chatMap[toChannelName]['tgID'], photo=bio, caption=msg.author)
            elif msg.type == "video":
                bio = BytesIO(msg.body)
                # TODO
                # context.bot.send_video(chat_id=chatMap[toChannelName]['tgID'], video=bio, caption=msg.author)
            sent = True
        else:
            if (toChannelName, msg) not in tgsQ.queue:
                tgsQ.put((toChannelName, msg))
            logger.info("Group not found, waiting for creation...")
            time.sleep(1)  # TODO we might get stuck in this loop....


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
