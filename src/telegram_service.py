import logging
from telegram.ext import Updater, CommandHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

msg_q = None


def run(q, config):
    global msg_q
    msg_q = q

    updater = Updater(config['token'], use_context=True)
    dp = updater.dispatcher

    start_handler = CommandHandler('start', start)

    dp.add_handler(start_handler)
    dp.add_error_handler(error)

    updater.start_polling()


def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
