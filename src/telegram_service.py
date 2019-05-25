import logging
from telegram.ext import Updater, CommandHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

msg_q = None


def run(message_queue, config):
    global msg_q
    msg_q = message_queue

    updater = Updater(config['token'], use_context=True)
    dp = updater.dispatcher

    start_handler = CommandHandler('start', start)

    dp.add_handler(start_handler)
    dp.add_error_handler(error)

    updater.start_polling()

    dp.job_queue.run_repeating(msg_listener, 5)


def msg_listener(context):
    if not msg_q.empty():
        msg = msg_q.get()
        if msg.group:
            context.bot.send_message(chat_id=user_id, text="{}: @ {}\n\n{}".format(msg.author, msg.group, msg.body))
        else:
            context.bot.send_message(chat_id=user_id, text="{}:\n\n{}".format(msg.author, msg.body))
        msg_q.task_done()


def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
