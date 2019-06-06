import time

from wtt.models import *


class TGBus:
    def __init__(self, wttQueue, ttwQueue, tgsQueue):
        self.wttQ = wttQueue
        self.ttwQ = ttwQueue
        self.tgsQ = tgsQueue
        self.onWhatsappMessage = None
        self.onWhatsappChatPictureUpdate = None
        self.onWhatsappChatSubjectUpdate = None
        self.onWhatsappChatParticipantsUpdate = None

    def run(self):
        while True:
            if not self.wttQ.empty():
                event = self.wttQ.get()
                self.onEvent(event)
                self.wttQ.task_done()
            time.sleep(0.1)

    def onEvent(self, event):
        if isinstance(event, WTTMessage) and self.onWhatsappMessage:
            self.onWhatsappMessage(event)
        elif isinstance(event, WTTUpdateChatPicture):
            self.onWhatsappChatPictureUpdate(event)
        elif isinstance(event, WTTUpdateChatSubject):
            self.onWhatsappChatSubjectUpdate(event)
        elif isinstance(event, WTTUpdateChatParticipants):
            self.onWhatsappChatParticipantsUpdate(event)

    def emitEventToWhatsapp(self, event):
        self.ttwQ.put(event)

    def emitCreateChat(self, chat):
        self.tgsQ.put(chat)

    def setWaMessageListener(self, cb):
        self.onWhatsappMessage = cb

    def setWaChatPictureUpdateListener(self, cb):
        self.onWhatsappChatPictureUpdate = cb

    def setWaChatSubjectUpdateListener(self, cb):
        self.onWhatsappChatSubjectUpdate = cb

    def setWaChatParticipantsUpdateListener(self, cb):
        self.onWhatsappChatParticipantsUpdate = cb
