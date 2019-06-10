import logging
import time
from io import BytesIO
from threading import Thread

import telegram
import vobject
from PIL import Image
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import constants
from wtt.models import *

logger = logging.getLogger(__name__)

MAX_RETRIES = 10
CHAT_PREFIX = "[WA]"

tgBus = None
config = None
bot = None
dao = None


def run(telegramBus, cfg, daObject):
    global tgBus, config, bot, dao
    config = cfg
    tgBus = telegramBus
    dao = daObject

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
    global dao
    tgID = update.effective_chat.id

    if update.message.from_user.is_bot:
        return

    tgBus.emitEventToWhatsapp(
        WTTMessage('text', update.message.from_user.first_name, update.message.text, waID=dao.getWhatsappID(tgID)))


def onPhotoMessage(update, context):
    global dao
    tgID = update.effective_chat.id

    if update.message.from_user.is_bot:
        return

    fileID = update.message.photo[-1].file_id
    bio = BytesIO()
    file = context.bot.get_file(fileID)
    file.download(out=bio)
    filename = file.file_path.split('/')[-1]
    tgBus.emitEventToWhatsapp(
        WTTMessage('image', update.message.from_user.first_name, bio, waID=dao.getWhatsappID(tgID), filename=filename))


def onWhatsappMessage(msg):
    global tgBus, dao
    msg.tgID = dao.getTelegramID(msg.waID)

    def onChatCreationResult(ok):
        if ok:
            logger.info("Group has been created, forwarding message...")
            msg.tgID = dao.getTelegramID(msg.waID)
            sendMessage(msg)
        else:
            logger.error("Group creation failed, message could not be forwarded to telegram")

    if not msg.tgID:  # we need to create a telegram group first
        chatName = CHAT_PREFIX + (msg.subject if msg.isGroup else msg.author)
        todoChat = WTTCreateChat(chatName, waID=msg.waID)
        tgBus.emitCreateChat((todoChat, onChatCreationResult))
        logger.info("Group {} not found, waiting for creation...".format(chatName))


def sendMessage(msg):
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
        if msg.caption:
            bot.send_photo(chat_id=msg.tgID, photo=bio, caption="*{}*:  {}".format(msg.author, msg.caption),
                           parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            bot.send_photo(chat_id=msg.tgID, photo=bio, caption="*{}*".format(msg.author),
                           parse_mode=telegram.ParseMode.MARKDOWN)
    elif msg.type == "video" or msg.type == "gif":
        bio = BytesIO(msg.body)
        if msg.caption:
            bot.send_video(chat_id=msg.tgID, video=bio, caption="*{}*:  {}".format(msg.author, msg.caption),
                           parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            bot.send_video(chat_id=msg.tgID, video=bio, caption="*{}*".format(msg.author),
                           parse_mode=telegram.ParseMode.MARKDOWN)
    elif msg.type == "audio" or msg.type == "ptt":
        bio = BytesIO(msg.body)
        if msg.caption:
            bot.send_audio(chat_id=msg.tgID, audio=bio, caption="*{}*:  {}".format(msg.author, msg.caption),
                           parse_mode=telegram.ParseMode.MARKDOWN, title=msg.filename)
        else:
            bot.send_audio(chat_id=msg.tgID, audio=bio, caption="*{}*".format(msg.author),
                           parse_mode=telegram.ParseMode.MARKDOWN, title=msg.filename)
    elif msg.type == "document":
        bio = BytesIO(msg.body)
        if msg.caption:
            bot.send_document(chat_id=msg.tgID, document=bio,
                              caption="*{}*:  {}".format(msg.author, msg.caption),
                              parse_mode=telegram.ParseMode.MARKDOWN, filename=msg.filename)
        else:
            bot.send_document(chat_id=msg.tgID, document=bio, caption="*{}*".format(msg.author),
                              parse_mode=telegram.ParseMode.MARKDOWN, filename=msg.filename)
    elif msg.type == "location":
        if msg.caption["name"]:
            bot.send_location(chat_id=msg.tgID, latitude=msg.body["latitude"], longitude=msg.body["longitude"],
                              caption="*{}*:  {}".format(msg.author, "[{}]({})".format(msg.caption["name"],
                                                                                       msg.caption["url"])),
                              parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            bot.send_location(chat_id=msg.tgID, latitude=msg.body["latitude"], longitude=msg.body["longitude"],
                              caption="*{}*".format(msg.author),
                              parse_mode=telegram.ParseMode.MARKDOWN)
    elif msg.type == "contact":
        svCard = msg.body["vcard"].decode("utf-8")
        vcard = vobject.readOne(svCard)
        phoneNumber = ""
        for tel in vcard.contents['tel']:
            phoneNumber = tel.value
            break
        bot.send_contact(chat_id=msg.tgID,
                         first_name=msg.body["display_name"].partition(" ")[0],
                         last_name=msg.body["display_name"].partition(" ")[1] if len(
                             msg.body["display_name"].partition(" ")) > 1 else None,
                         phone_number=phoneNumber,
                         vcard=svCard,
                         parse_mode=telegram.ParseMode.MARKDOWN)
    else:
        logger.error("Message type unknown")


def onWhatsappChatPictureUpdate(update):
    global bot, dao

    tgID = dao.getTelegramID(update.waID)

    if not tgID:
        logger.debug("Received chat picture update from whatsapp but chat is not mapped to a telegram chat ({})".format(
            update.waID))
        return
    else:
        currentPic = dao.getChatPicture(waID=update.waID)

    if currentPic == update.picture:
        logger.debug(
            "Received chat picture update from whatsapp but telegram chat already has that picture ({})".format(
                update.waID))
    else:
        logger.info("Updating chat picture for {}...".format(tgID))
        bio = BytesIO(update.picture)
        img = Image.open(bio)
        img.save(bio, 'JPEG')
        bio.seek(0)
        bot.set_chat_photo(tgID, bio)
        dao.updatePicture(tgID, update.picture)
        logger.info("Updated chat picture for {}".format(tgID))


def onWhatsappChatSubjectUpdate(update):
    global bot, dao

    tgID = dao.getTelegramID(update.waID)

    if not tgID:
        logger.debug("Received chat subject update from whatsapp but chat is not mapped to a telegram chat ({})".format(
            update.waID))
        return
    else:
        currentSubj = dao.getChatSubject(waID=update.waID)

    if currentSubj == update.subject:
        logger.debug(
            "Received chat subject update from whatsapp but telegram chat already has that subject ({})".format(
                update.waID))
    else:
        logger.info("Updating chat subject for {}".format(tgID))
        bot.set_chat_title(tgID, CHAT_PREFIX + update.subject)
        logger.info(
            "Updated chat subject from {} to {}".format((CHAT_PREFIX + currentSubj), (CHAT_PREFIX + update.subject)))
        dao.updateSubject(tgID, update.subject)


def onWhatsappChatParticipantsUpdate(update):
    pass


def onParticipantsCommand(update, context):
    global dao

    msg = "Participants in this chat:\n"
    participants = dao.getChatParticipants(tgID=update.effective_chat.id)

    for p in participants:
        number = p[0].split('@')[0]
        paddedNumber = "{:<16}".format(number)
        msg += "[+{}](tel:+{})| {} \n".format(paddedNumber, number, "N/A")

    if len(msg) <= constants.MAX_MESSAGE_LENGTH:
        context.bot.send_message(chat_id=update.message.chat.id,
                                 text=msg,
                                 parse_mode=telegram.ParseMode.MARKDOWN)
    else:
        parts = []
        lines = msg.splitlines(True)
        part = ""
        while lines:
            if len(part + lines[0]) <= constants.MAX_MESSAGE_LENGTH:
                part += lines.pop(0)
            else:
                parts.append(part)
                part = ""

        for part in parts:
            context.bot.send_message(chat_id=update.message.chat.id,
                                     text=part,
                                     parse_mode=telegram.ParseMode.MARKDOWN)
            time.sleep(1)


def isGroup(waID):
    if '-' in waID:
        return True
    return False


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
