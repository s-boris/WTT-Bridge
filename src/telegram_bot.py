import logging
import time

from telegram.ext import Updater, CommandHandler
from src.models import *
import setup

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
        send(context, "[WA]" + msg.group, msg)
        wttQ.task_done()


def send(context, toChannelName, msg):
    # lookup channel mapping
    chatMap = setup.get_chatmap()
    if toChannelName in chatMap:
        context.bot.send_message(chat_id=chatMap[toChannelName]['tgID'], text="{}:\n\n{}".format(msg.author, msg.body))
        return True
    else:
        tgsQ.put((toChannelName, msg))
        while toChannelName not in chatMap:  # TODO dirty
            chatMap = setup.get_chatmap()
            logger.info("Group not found, waiting for creation...")
            time.sleep(1)

    # we should be fine now
    context.bot.send_message(chat_id=chatMap[toChannelName]['tgID'], text="{}:\n\n{}".format(msg.author, msg.body))
    return True


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
