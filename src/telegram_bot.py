import logging
import time

from telegram.ext import Updater, CommandHandler

logger = logging.getLogger(__name__)

msg_q = None
creation_q = None
config = None
dpg = None


def run(message_queue, creation_queue, cfg):
    global msg_q, creation_q, config, dpg
    msg_q = message_queue
    config = cfg
    creation_q = creation_queue

    updater = Updater(config['bot_token'], use_context=True)
    dp = updater.dispatcher

    dp.add_error_handler(error)

    updater.start_polling()

    dp.job_queue.run_repeating(msg_listener, 5)

    dpg = dp


def msg_listener(context):
    if not msg_q.empty():
        msg = msg_q.get()

        if msg.group:
            send(context, msg.group, msg)
        else:
            send(context, msg.author, msg)
        msg_q.task_done()


def send(context, toChannelName, msg):
    # try sending
    for gId in dpg.groups:
        if context.bot.get_chat(gId).title == toChannelName:
            context.bot.send_message(chat_id=gId, text="{}:\n\n{}".format(msg.author, msg.body))
            return True

    # group not found
    creation_q.put(msg.group)
    while not creation_q.empty():
        logger.info("Group not found, initiated creation...")
        time.sleep(1)

    # try again
    for gId in dpg.groups:
        if context.bot.get_chat(gId).title == toChannelName:
            context.bot.send_message(chat_id=gId, text="{}:\n\n{}".format(msg.author, msg.body))
            return True


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
