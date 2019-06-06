import time

from wtt.models import WTTMessage


class WABus:
    def __init__(self, wttQueue, ttwQueue):
        self.wttQ = wttQueue
        self.ttwQ = ttwQueue
        self.onTelegramMessage = None

    def run(self):
        while True:
            if not self.ttwQ.empty():
                event = self.ttwQ.get()
                self.onTelegramEvent(event)
                self.ttwQ.task_done()
            time.sleep(0.1)

    def onTelegramEvent(self, event):
        if isinstance(event, WTTMessage) and self.onTelegramMessage:
            self.onTelegramMessage(event)

    def emitEventToTelegram(self, event):
        self.wttQ.put(event)

    def setTgMessageListener(self, cb):
        self.onTelegramMessage = cb
