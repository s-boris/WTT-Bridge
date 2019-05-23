from threading import Thread
import logging
from queue import Queue

import setup
import src.telegram_service as tg
import src.whatsapp_service as wa

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger("WTT-Bridge")

msg_q = Queue(maxsize=0)

if __name__ == "__main__":
    tg_thread = Thread(target=tg.run, args=(msg_q, setup.get_tg_config(),))
    wa_thread = Thread(target=wa.run, args=(msg_q, setup.get_wa_config(),))

    try:
        tg_thread.start()
        wa_thread.start()
    except KeyboardInterrupt:
        tg_thread.join()
        wa_thread.join()
        msg_q.join()
