import logging
from queue import Queue
from threading import Thread

from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_acks.protocolentities import OutgoingAckProtocolEntity
from yowsup.layers.protocol_groups.protocolentities import *
from yowsup.layers.protocol_media.protocolentities import *
from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity

from src.media_worker import MediaWorker
from src.models import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

groups = []
groups_ready = False


class WhatsappLayer(YowInterfaceLayer):

    def __init__(self, wttQueue, ttwQueue):
        super().__init__()
        self.wttQ = wttQueue
        self.ttwQ = ttwQueue
        self.mediaWorker = None
        self.offlineMsgQ = Queue()

        # msg = PrivateMessage('text', "Testboy7", "Testmessage", waID="1234")
        # self.wttQ.put(msg)

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        logger.info('Connected with WhatsApp servers')

        logger.info('Fetching Whatsapp groups')
        self.toLower(ListGroupsIqProtocolEntity())

        logger.info("Starting MediaWorker")
        self.mediaWorker = MediaWorker(self.wttQ, groups)
        self.mediaWorker.start()

        logger.info("Listening for Telegram messages")
        tgListener = Thread(target=self.telegramMessageListener)
        tgListener.start()

    def telegramMessageListener(self):
        while True:
            if not self.ttwQ.empty():
                msg = self.ttwQ.get()
                outgoingMessageProtocolEntity = TextMessageProtocolEntity(msg.body, to=msg.waID)
                self.toLower(outgoingMessageProtocolEntity)
                self.ttwQ.task_done()

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        # confirm message received
        receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom(),
                                                'read', messageProtocolEntity.getParticipant())
        self.toLower(receipt)

        # wait for the groups to be fetched before handling any incoming messages
        if not groups_ready:
            logger.debug("Waiting with message delivery, groups not ready")
            self.offlineMsgQ.put(messageProtocolEntity)
            return

        # handle media messages
        if isinstance(messageProtocolEntity, MediaMessageProtocolEntity):
            self.onMediaMessage(messageProtocolEntity)
            return
        # handle all other kinds of messages
        elif messageProtocolEntity.getType() == 'text':
            mtype = messageProtocolEntity.getType()
            body = messageProtocolEntity.getBody()
            logging.info("Received message from " + messageProtocolEntity.getNotify() + ": " + body)
        elif messageProtocolEntity.media_type == "location":
            media = "location (%s, %s) to %s" % (
                messageProtocolEntity.getLatitude(), messageProtocolEntity.getLongitude(),
                messageProtocolEntity.getFrom(False))
            print(media)  # TODO handle this
            return
        elif messageProtocolEntity.media_type == "contact":
            media = "contact (%s, %s) to %s" % (
                messageProtocolEntity.getName(), messageProtocolEntity.getCardData(),
                messageProtocolEntity.getFrom(False))
            print(media)  # TODO handle this
            return
        else:
            logger.error("Unknown message type %s " % messageProtocolEntity.getType())
            return

        # pack the message into our models
        if messageProtocolEntity.isGroupMessage():
            msg = GroupMessage(mtype, messageProtocolEntity.getNotify(), body,
                               self.groupIdToSubject(messageProtocolEntity.getFrom()),
                               waID=messageProtocolEntity.getFrom())
        else:
            msg = PrivateMessage(mtype, messageProtocolEntity.getNotify(), body, waID=messageProtocolEntity.getFrom())

        self.wttQ.put(msg)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", entity.getType(), entity.getFrom())
        self.toLower(ack)

    @ProtocolEntityCallback("failure")
    def onFailure(self, entity):
        logger.error("Login Failed, reason: %s" % entity.getReason())

    def onMediaMessage(self, messageProtocolEntity):
        if messageProtocolEntity.media_type in ("image", "audio", "video", "document", "gif", "ptt"):
            logger.info("Received media message")
            self.mediaWorker.enqueue(messageProtocolEntity)
        else:
            logger.error("Unknown media type %s " % messageProtocolEntity.media_type)

    @ProtocolEntityCallback("iq")
    def onIq(self, entity):
        if isinstance(entity, ListGroupsResultIqProtocolEntity):
            self.onGroupListReceived(entity)
        elif isinstance(entity, ListParticipantsResultIqProtocolEntity):
            self.onGroupParticipantsReceived(entity)

    def processOfflineMessages(self):
        while not self.offlineMsgQ.empty():
            self.onMessage(self.offlineMsgQ.get())
            self.offlineMsgQ.task_done()

    def onGroupListReceived(self, entity):
        global groups_ready, groups
        for group in entity.getGroups():
            logger.debug('Received group info with id %s (owner %s, subject %s)', group.getId(), group.getOwner(),
                         group.getSubject())
            groups.append({"groupId": group.getId(), "subject": group.getSubject().encode('latin-1').decode()})
            # self.toLower(ParticipantsGroupsIqProtocolEntity(group.getId()))

        groups_ready = True  # this is sufficient info to handle incoming messages

        logger.info("Starting MediaWorker")
        self.mediaWorker = MediaWorker(self.wttQ, groups)
        self.mediaWorker.start()

        self.processOfflineMessages()
        # self.getGroupInfo()  # TODO listen to updates instead?
        logger.debug("Groups updated")

    def onGroupParticipantsReceived(self, entity):
        logger.debug('Received %d participants in group with id %s', len(entity.getParticipants()), entity.getFrom())
        # self._groups[entity.getFrom()]._participants = entity.getParticipants()

    def getGroupInfo(self, groupId):
        entity = InfoGroupsIqProtocolEntity(groupId)
        self.toLower(entity)

    def groupIdToSubject(self, groupId):
        rest = groupId.split('@', 1)[0]
        for group in groups:
            if group["groupId"] == rest:
                return group["subject"]
