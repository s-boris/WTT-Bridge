import logging
import time
from io import BytesIO

import telegram
from PIL import Image
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import setup
from src.models import *

logger = logging.getLogger(__name__)

wttQ = None
ttwQ = None
tgsQ = None
config = None
dpg = None


def run(wttQueue, ttwQueue, tgsQueue, cfg):
    global wttQ, ttwQ, tgsQ, config, dpg
    config = cfg
    wttQ = wttQueue
    ttwQ = ttwQueue
    tgsQ = tgsQueue

    logger.info("Starting Telegram Bot")
    updater = Updater(config['bot_token'], use_context=True)
    dp = updater.dispatcher

    dp.add_error_handler(error)
    dp.add_handler(CommandHandler("participants", participants))
    dp.add_handler(MessageHandler(Filters.text, onMessage))
    updater.start_polling()

    dp.job_queue.run_repeating(wttMessageListener, 1)

    dpg = dp


def onMessage(update, context):
    tgID = update.effective_chat.id

    if update.message.from_user.is_bot:
        return

    if update.message.text:
        chatMap = setup.get_chatmap()
        for key in chatMap:
            if int(chatMap[key]["tgID"]) == tgID:
                # doesn't really matter if private or group message
                ttwQ.put(PrivateMessage('text', update.message.from_user.first_name, update.message.text,
                                        waID=chatMap[key]["waID"]))
                return


def wttMessageListener(context):
    if not wttQ.empty() and isinstance(wttQ.queue[0], PrivateMessage):
        msg = wttQ.get()
        sendWttMessage(context, "[WA]" + msg.author, msg)
        wttQ.task_done()
    elif not wttQ.empty() and isinstance(wttQ.queue[0], GroupMessage):
        msg = wttQ.get()
        sendWttMessage(context, "[WA]" + msg.title, msg)
        wttQ.task_done()


def sendWttMessage(context, toChannelName, msg):
    sent = False

    while not sent:
        chatMap = setup.get_chatmap()
        if toChannelName in chatMap:
            if msg.type == "text":
                context.bot.send_message(chat_id=chatMap[toChannelName]['tgID'],
                                         text="*{}*:\n{}".format(msg.author, msg.body),
                                         parse_mode=telegram.ParseMode.MARKDOWN)
            elif msg.type == "image":
                bio = BytesIO(msg.body)
                img = Image.open(bio)
                img.save(bio, 'JPEG')
                bio.seek(0)
                context.bot.send_photo(chat_id=chatMap[toChannelName]['tgID'], photo=bio, caption=msg.author)
            elif msg.type == "video" or msg.type == "gif":
                bio = BytesIO(msg.body)
                context.bot.send_video(chat_id=chatMap[toChannelName]['tgID'], video=bio, caption=msg.author)
            elif msg.type == "audio" or msg.type == "ptt":
                bio = BytesIO(msg.body)
                context.bot.send_audio(chat_id=chatMap[toChannelName]['tgID'], audio=bio, caption=msg.author,
                                       title=msg.filename)
            elif msg.type == "document":
                bio = BytesIO(msg.body)
                context.bot.send_document(chat_id=chatMap[toChannelName]['tgID'], document=bio, caption=msg.author,
                                          filename=msg.filename)
            sent = True
        else:
            if (toChannelName, msg) not in tgsQ.queue:
                tgsQ.put((toChannelName, msg))
            logger.info("Group not found, waiting for creation...")
            time.sleep(1)  # TODO we might get stuck in this loop....


def participants(update, context):
    """Send a message when the command /participants issued."""
    update.message.reply_text('Hi!')


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
