import logging
import time
from io import BytesIO

import telegram
from PIL import Image
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import utils
from src.models import *

logger = logging.getLogger(__name__)

MAX_RETRIES = 10

wttQ = None
ttwQ = None
tgsQ = None
config = None


def run(wttQueue, ttwQueue, tgsQueue, cfg):
    global wttQ, ttwQ, tgsQ, config
    config = cfg
    wttQ = wttQueue
    ttwQ = ttwQueue
    tgsQ = tgsQueue

    logger.info("Starting Telegram Bot")
    updater = Updater(config['bot_token'], use_context=True)
    dp = updater.dispatcher

    dp.add_error_handler(error)
    dp.add_handler(CommandHandler("participants", participants))
    dp.add_handler(MessageHandler(Filters.text, onTextMessage))
    dp.add_handler(MessageHandler(Filters.photo, onPhotoMessage))
    updater.start_polling()

    dp.job_queue.run_repeating(whatsappMessageListener, 1)


def onTextMessage(update, context):
    tgID = update.effective_chat.id

    if update.message.from_user.is_bot:
        return

    chatMap = utils.get_chatmap()
    for key in chatMap:
        if int(key) == tgID:
            ttwQ.put(
                WTTMessage('text', update.message.from_user.first_name, update.message.text, waID=chatMap[key]["waID"]))
            return


def onPhotoMessage(update, context):
    pass
    # tgID = update.effective_chat.id
    #
    # if update.message.from_user.is_bot:
    #     return
    #
    # chatMap = utils.get_chatmap()
    # for key in chatMap:
    #     if int(chatMap[key]["tgID"]) == tgID:
    #         fileID = update.message.photo[-1].file_id
    #         bio = BytesIO()
    #         file = context.bot.get_file(fileID)
    #         file.download(out=bio)
    #         filename = file.file_path.split('/')[-1]
    #         # doesn't really matter if private or group message
    #         ttwQ.put(WTTMessage('image', update.message.from_user.first_name, bio, waID=chatMap[key]["waID"],
    #                             filename=filename))


def whatsappMessageListener(context):
    if not wttQ.empty():
        msg = wttQ.get()
        sendToTelegram(context, msg)
        wttQ.task_done()


def sendToTelegram(context, msg):
    sent = False
    tries = 0
    isQueued = False

    while not sent and tries < MAX_RETRIES:
        msg.tgID = getTelegramChatID(msg.waID)
        tries += 1

        if not msg.tgID:  # we need to create a telegram group first
            chatName = "[WA]" + (msg.title if msg.isGroup else msg.author)
            if not isQueued:
                todoChat = CreateChat(chatName, waID=msg.waID)
                tgsQ.put(todoChat)
            logger.info("Group {} not found, waiting for creation...".format(chatName))
            time.sleep(1)
        else:
            if msg.type == "text":
                context.bot.send_message(chat_id=msg.tgID,
                                         text="*{}*:\n{}".format(msg.author, msg.body),
                                         parse_mode=telegram.ParseMode.MARKDOWN)
            elif msg.type == "image":
                bio = BytesIO(msg.body)
                img = Image.open(bio)
                img.save(bio, 'JPEG')
                bio.seek(0)
                context.bot.send_photo(chat_id=msg.tgID, photo=bio, caption=msg.author)
            elif msg.type == "video" or msg.type == "gif":
                bio = BytesIO(msg.body)
                context.bot.send_video(chat_id=msg.tgID, video=bio, caption=msg.author)
            elif msg.type == "audio" or msg.type == "ptt":
                bio = BytesIO(msg.body)
                context.bot.send_audio(chat_id=msg.tgID, audio=bio, caption=msg.author,
                                       title=msg.filename)
            elif msg.type == "document":
                bio = BytesIO(msg.body)
                context.bot.send_document(chat_id=msg.tgID, document=bio, caption=msg.author,
                                          filename=msg.filename)
            sent = True
    if not tries < MAX_RETRIES:
        logger.error("Group creation timeout. Message could not be delivered.\n{}:{}".format(msg.author, msg.body))


def getTelegramChatID(waID):
    chatMap = utils.get_chatmap()
    for tgID in chatMap:
        if chatMap[tgID]['waID'] == waID:
            return tgID
    return False


def participants(update, context):
    """Send a message when the command /participants issued."""
    update.message.reply_text('Hi!')


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
