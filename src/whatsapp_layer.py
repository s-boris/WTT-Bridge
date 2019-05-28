import base64
import logging
import time

from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_acks.protocolentities import OutgoingAckProtocolEntity
from yowsup.layers.protocol_groups.protocolentities import *
from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity

from src.models import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

groups = []
groups_ready = False


class WhatsappLayer(YowInterfaceLayer):

    def __init__(self, wttQueue):
        super().__init__()
        self.wttQ = wttQueue

        # msg = PrivateMessage('text', "Testboy7", "Testmessage", waID="1234")
        # self.wttQ.put(msg)

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        logger.info('Connected with WhatsApp servers')
        self.updateGroups()

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        # confirm message received
        receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom(),
                                                'read', messageProtocolEntity.getParticipant())
        self.toLower(receipt)

        # wait for the groups to be fetched before handling any incoming messages
        while not groups_ready:
            logger.debug("Groups not ready, retrying in 2sec...")
            time.sleep(2)

        mtype, body = self.parseMessage(messageProtocolEntity)
        logging.debug("Received message from " + messageProtocolEntity.getNotify() + ": " + body)

        # do stuff with the message
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

    def parseMessage(self, messageProtocolEntity):

        if messageProtocolEntity.getType() == 'text':
            return messageProtocolEntity.getType(), messageProtocolEntity.getBody()

        elif messageProtocolEntity.getType() == 'media':
            if messageProtocolEntity.media_type in ("image", "audio", "video", "document"):
                print("Received media")
                media = self.getDownloadableMediaMessageBody(messageProtocolEntity)
                return messageProtocolEntity.media_type, media

            elif messageProtocolEntity.media_type == "location":
                media = "location (%s, %s) to %s" % (
                    messageProtocolEntity.getLatitude(), messageProtocolEntity.getLongitude(),
                    messageProtocolEntity.getFrom(False))
                print(media)
                return messageProtocolEntity.media_type, media

            elif messageProtocolEntity.media_type == "contact":
                media = "contact (%s, %s) to %s" % (
                    messageProtocolEntity.getName(), messageProtocolEntity.getCardData(),
                    messageProtocolEntity.getFrom(False))
                print(media)
                return messageProtocolEntity.media_type, media
        else:
            logger.error("Unknown message type %s " % messageProtocolEntity.getType())

    def getDownloadableMediaMessageBody(self, message):
        return "[media_type={media_type}, length={media_size}, url={media_url}, key={media_key}]".format(
            media_type=message.media_type,
            media_size=message.file_length,
            media_url=message.url,
            media_key=base64.b64encode(message.media_key)
        )

    def getGroupInfo(self, groupId):
        entity = InfoGroupsIqProtocolEntity(groupId)
        self.toLower(entity)

    def updateGroups(self):
        def onGroupsListResult(successEntity, originalEntity):
            global groups, groups_ready

            for group in successEntity.getGroups():
                groups.append({"groupId": group.getId(), "subject": group.getSubject().encode('latin-1').decode()})

            groups_ready = True  # this is sufficient info to handle incoming messages

            # self.getGroupInfo()  # TODO listen to updates instead?
            logger.debug("Groups updated")

        def onGroupsListError(errorEntity, originalEntity):
            logger.error("Error retrieving groups")

        entity = ListGroupsIqProtocolEntity()
        self._sendIq(entity, onGroupsListResult, onGroupsListError)

    def groupIdToSubject(self, groupId):
        rest = groupId.split('@', 1)[0]
        for group in groups:
            if group["groupId"] == rest:
                return group["subject"]
