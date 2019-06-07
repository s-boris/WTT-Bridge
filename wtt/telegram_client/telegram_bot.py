import logging
import time
from io import BytesIO
from threading import Thread

import telegram
from PIL import Image
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import wtt.utils as utils
from wtt.models import *

logger = logging.getLogger(__name__)

MAX_RETRIES = 10
CHAT_PREFIX = "[WA]"

tgBus = None
whatsappChats = {}
config = None
bot = None


def run(telegramBus, cfg):
    global tgBus, config, bot
    config = cfg
    tgBus = telegramBus

    logger.info("Starting Telegram Bot")
    updater = Updater(config['bot_token'], use_context=True)
    dp = updater.dispatcher

    dp.add_error_handler(error)
    dp.add_handler(CommandHandler("participants", onParticipantsCommand))
    dp.add_handler(MessageHandler(Filters.text, onTextMessage))
    dp.add_handler(MessageHandler(Filters.photo, onPhotoMessage))

    tgBus.setWaMessageListener(onWhatsappMessage)
    tgBus.setWaChatPictureUpdateListener(onWhatsappChatPictureUpdate)
    tgBus.setWaChatSubjectUpdateListener(onWhatsappChatSubjectUpdate)
    tgBus.setWaChatParticipantsUpdateListener(onWhatsappChatParticipantsUpdate)

    bot = dp.bot

    tgBusThread = Thread(target=tgBus.run, args=())
    tgBusThread.start()

    updater.start_polling()


def onTextMessage(update, context):
    tgID = update.effective_chat.id

    if update.message.from_user.is_bot:
        return

    chatMap = utils.get_chatmap()
    for key in chatMap:
        if int(key) == tgID:
            tgBus.emitEventToWhatsapp(
                WTTMessage('text', update.message.from_user.first_name, update.message.text, waID=chatMap[key]["waID"]))
            return


def onPhotoMessage(update, context):
    pass
    tgID = update.effective_chat.id

    if update.message.from_user.is_bot:
        return

    chatMap = utils.get_chatmap()
    for key in chatMap:
        if int(chatMap[key]["tgID"]) == tgID:
            fileID = update.message.photo[-1].file_id
            bio = BytesIO()
            file = context.bot.get_file(fileID)
            file.download(out=bio)
            filename = file.file_path.split('/')[-1]
            # doesn't really matter if private or group message
            tgBus.emitEventToWhatsapp(
                WTTMessage('image', update.message.from_user.first_name, bio, waID=chatMap[key]["waID"],
                           filename=filename))


def onWhatsappMessage(msg):
    global tgBus, bot
    sent = False
    tries = 0
    isQueued = False

    while not sent and tries < MAX_RETRIES:
        msg.tgID = getMappedTelegramID(msg.waID)  # loads the id from chatmap.json
        tries += 1

        if not msg.tgID:  # we need to create a telegram group first
            chatName = CHAT_PREFIX + (msg.title if msg.isGroup else msg.author)
            if not isQueued:
                todoChat = WTTCreateChat(chatName, waID=msg.waID)
                tgBus.emitCreateChat(todoChat)
                isQueued = True
            logger.info("Group {} not found, waiting for creation...".format(chatName))
            time.sleep(1)
        else:
            if msg.type == "text":
                if msg.isGroup:
                    bot.send_message(chat_id=msg.tgID,
                                     text="*{}*:\n{}".format(msg.author, msg.body),
                                     parse_mode=telegram.ParseMode.MARKDOWN)
                else:
                    bot.send_message(chat_id=msg.tgID,
                                     text="{}".format(msg.body),
                                     parse_mode=telegram.ParseMode.MARKDOWN)
            elif msg.type == "image":
                bio = BytesIO(msg.body)
                img = Image.open(bio)
                img.save(bio, 'JPEG')
                bio.seek(0)
                bot.send_photo(chat_id=msg.tgID, photo=bio, caption=msg.author)
            elif msg.type == "video" or msg.type == "gif":
                bio = BytesIO(msg.body)
                bot.send_video(chat_id=msg.tgID, video=bio, caption=msg.author)
            elif msg.type == "audio" or msg.type == "ptt":
                bio = BytesIO(msg.body)
                bot.send_audio(chat_id=msg.tgID, audio=bio, caption=msg.author,
                               title=msg.filename)
            elif msg.type == "document":
                bio = BytesIO(msg.body)
                bot.send_document(chat_id=msg.tgID, document=bio, caption=msg.author,
                                  filename=msg.filename)
            sent = True
    if not tries < MAX_RETRIES:
        logger.error("Group creation timeout. Message could not be delivered.\n{}:{}".format(msg.author, msg.body))


def onWhatsappChatPictureUpdate(update):
    global whatsappChats, bot
    tgID = getMappedTelegramID(update.waID)

    if update.waID not in whatsappChats:
        whatsappChats[update.waID] = {"subject": None, "participants": None, "picture": None}

    if whatsappChats[update.waID]["picture"] == update.picture:
        logger.debug(
            "Received chat picture update from whatsapp but telegram chat already has that picture ({})".format(
                update.waID))
        return

    if tgID:
        logger.info("Updating chat picture for {}...".format(tgID))
        bio = BytesIO(update.picture)
        img = Image.open(bio)
        img.save(bio, 'JPEG')
        bio.seek(0)
        bot.set_chat_photo(tgID, bio)
        whatsappChats[update.waID]["picture"] = update.picture
        logger.info("Updated chat picture for {}".format(tgID))
    else:
        logger.debug("Received chat picture update from whatsapp but chat is not mapped to a telegram chat ({})".format(
            update.waID))


def onWhatsappChatSubjectUpdate(update):
    global whatsappChats, bot
    tgID = getMappedTelegramID(update.waID)

    if update.waID not in whatsappChats:
        whatsappChats[update.waID] = {"subject": None, "participants": None, "picture": None}

    if whatsappChats[update.waID]["subject"] == update.subject:
        logger.debug(
            "Received chat subject update from whatsapp but telegram chat already has that subject ({})".format(
                update.waID))
        return

    if tgID:
        logger.info("Updating chat subject for {}".format(tgID))
        chat = bot.getChat(tgID)
        if not chat.title == (CHAT_PREFIX + update.subject):
            bot.set_chat_title(tgID, CHAT_PREFIX + update.subject)
            logger.info("Updated chat subject from {} to {}".format(chat.title, (CHAT_PREFIX + update.subject)))
        whatsappChats[update.waID]["subject"] = update.subject
    else:
        whatsappChats[update.waID]["subject"] = update.subject
        logger.debug("Received chat subject update from whatsapp but chat is not mapped to a telegram chat ({})".format(
            update.waID))


def onWhatsappChatParticipantsUpdate(update):
    global whatsappChats
    tgID = getMappedTelegramID(update.waID)

    if update.waID not in whatsappChats:
        whatsappChats[update.waID] = {"subject": None, "participants": None, "picture": None}

    if whatsappChats[update.waID]["participants"] == update.participants:
        logger.debug(
            "Received chat participants update from whatsapp but telegram chat already has the same participants ({})".format(
                update.waID))
        return

    if tgID:
        whatsappChats[update.waID]["participants"] = update.participants
        logger.info("Updated chat participants for {}".format(tgID))
    else:
        whatsappChats[update.waID]["participants"] = update.participants
        logger.debug(
            "Received chat participants update from whatsapp but chat is not mapped to a telegram chat ({})".format(
                update.waID))


def onParticipantsCommand(update, context):
    """Send a message when the command /participants issued."""
    msg = "Participants in this chat:\n"
    group = getWhatsappGroup(update.message.chat.id)

    if group:
        for p in group["participants"]:
            paddedNumber = "{:<16}".format(p.split('@')[0])
            msg += "[+{}](tel:+{})| {} \n".format(paddedNumber, p.split('@')[0], "N/A")
        context.bot.send_message(chat_id=update.message.chat.id,
                                 text=msg,
                                 parse_mode=telegram.ParseMode.MARKDOWN)


def getMappedTelegramID(waID):
    chatMap = utils.get_chatmap()
    for tgID in chatMap:
        if chatMap[tgID]['waID'] == waID:
            return tgID
    return False


def getWhatsappGroup(tgID):
    global whatsappChats
    chatMap = utils.get_chatmap()
    for groupID in whatsappChats:
        if chatMap[str(tgID)]["waID"].startswith(groupID):
            return whatsappChats[groupID]
    return None


def getWhatsappContact(tgID):
    global whatsappChats
    chatMap = utils.get_chatmap()
    for groupID in whatsappChats:
        if chatMap[str(tgID)]["waID"].startswith(
                groupID) and '-' not in groupID:  # group id's have a '-' between two phone numbers
            return whatsappChats[groupID]
    return None


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
