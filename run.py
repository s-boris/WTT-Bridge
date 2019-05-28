import asyncio
import logging
from queue import Queue
from threading import Thread

import setup
import src.telegram_bot as tg
import src.telegram_selfbot as tgs
import src.whatsapp_selfbot as wa

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

wttQ = Queue(maxsize=0)
tgsQ = Queue(maxsize=0)


def loopInThread(loop):
    loop.run_until_complete(tgs.run(tgsQ, setup.get_tg_config()))


if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    tgs_thread = Thread(target=loopInThread, args=(loop,))
    tg_thread = Thread(target=tg.run, args=(wttQ, tgsQ, setup.get_tg_config(),))
    wa_thread = Thread(target=wa.run, args=(wttQ, setup.get_wa_config(),))

    try:
        tgs_thread.start()
        tg_thread.start()
        wa_thread.start()
    except KeyboardInterrupt:
        tgs_thread.join()
        tg_thread.join()
        wa_thread.join()
        wttQ.join()
