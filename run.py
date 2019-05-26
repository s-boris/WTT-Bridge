from threading import Thread
from queue import Queue
import asyncio

import setup
import src.telegram_selfbot as tgs
import src.telegram_bot as tg
import src.whatsapp_selfbot as wa

msg_q = Queue(maxsize=0)
creation_q = Queue(maxsize=0)


def loop_in_thread(loop):
    loop.run_until_complete(tgs.run(creation_q, setup.get_tg_config()))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    tgs_thread = Thread(target=loop_in_thread, args=(loop,))
    tg_thread = Thread(target=tg.run, args=(msg_q, creation_q, setup.get_tg_config(),))
    wa_thread = Thread(target=wa.run, args=(msg_q, setup.get_wa_config(),))

    try:
        tgs_thread.start()
        tg_thread.start()
        wa_thread.start()
    except KeyboardInterrupt:
        tgs_thread.join()
        tg_thread.join()
        wa_thread.join()
        msg_q.join()
