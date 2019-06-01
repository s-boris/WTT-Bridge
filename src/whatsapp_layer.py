import sys
import time
from queue import Queue
from threading import Thread

from PIL import Image
from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_acks.protocolentities import OutgoingAckProtocolEntity
from yowsup.layers.protocol_groups.protocolentities import *
from yowsup.layers.protocol_media.protocolentities import *
from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity

from src.media_worker import MediaWorker
from src.models import *
from utils import *

logger = logging.getLogger(__name__)

groups = []
groups_ready = False

TEMPLOCATION = "temp"


class WhatsappLayer(YowInterfaceLayer):

    def __init__(self, wttQueue, ttwQueue):
        super().__init__()
        self.wttQ = wttQueue
        self.ttwQ = ttwQueue
        self.mediaWorker = None
        self.telegramMessageWorker = None
        self.offlineMsgQ = Queue()

        if not os.path.exists(TEMPLOCATION):
            os.makedirs(TEMPLOCATION)

    def telegramMessageListener(self):
        while True:
            if not self.ttwQ.empty():
                msg = self.ttwQ.get()
                if msg.type == "text":
                    outgoingMessageProtocolEntity = TextMessageProtocolEntity(msg.body, to=msg.waID)
                    self.toLower(outgoingMessageProtocolEntity)
                elif msg.type == "image":
                    filepath = TEMPLOCATION + "/" + str(time.time()) + msg.filename
                    img = Image.open(msg.body)
                    img.save(filepath, 'JPEG')
                    self.media_send(msg.waID, filepath, RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE)
                    # os.remove(temporarylocation)  # TODO Delete file when done

                self.ttwQ.task_done()

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        logger.info('Connected with WhatsApp servers')

        logger.info('Fetching Whatsapp groups')
        self.toLower(ListGroupsIqProtocolEntity())

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom(),
                                                'read', messageProtocolEntity.getParticipant())

        # wait for the groups to be fetched before handling any incoming messages
        if not groups_ready:
            logger.info("Waiting with message delivery, groups not ready")
            self.offlineMsgQ.put(messageProtocolEntity)
            return

        if isinstance(messageProtocolEntity, MediaMessageProtocolEntity):
            self.onMediaMessage(messageProtocolEntity)
            return
        elif isinstance(messageProtocolEntity, TextMessageProtocolEntity):
            self.sendToTelegram(messageProtocolEntity, messageProtocolEntity.getBody(), isMedia=False)
            logging.info("Received message from " + messageProtocolEntity.getNotify().encode(
                'latin-1').decode() + ": " + messageProtocolEntity.getBody())
        else:
            logger.error("Unknown message type %s " % str(messageProtocolEntity))
            return

        # confirm message received
        self.toLower(receipt)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", entity.getType(), entity.getFrom())
        self.toLower(ack)

    @ProtocolEntityCallback("failure")
    def onFailure(self, entity):
        logger.error("Login Failed, reason: %s" % entity.getReason())

    @ProtocolEntityCallback("iq")
    def onIq(self, entity):
        if isinstance(entity, ListGroupsResultIqProtocolEntity):
            self.onGroupListReceived(entity)
        elif isinstance(entity, ListParticipantsResultIqProtocolEntity):
            self.onGroupParticipantsReceived(entity)

    def media_send(self, waID, path, mediaType, caption=None):
        entity = RequestUploadIqProtocolEntity(mediaType, filePath=path)
        successFn = lambda successEntity, originalEntity: self.onRequestUploadResult(waID, mediaType, path,
                                                                                     successEntity, originalEntity,
                                                                                     caption)
        errorFn = lambda errorEntity, originalEntity: self.onRequestUploadError(waID, path, errorEntity,
                                                                                originalEntity)
        self._sendIq(entity, successFn, errorFn)

    def onRequestUploadResult(self, jid, mediaType, filePath, resultRequestUploadIqProtocolEntity,
                              requestUploadIqProtocolEntity, caption=None):

        if resultRequestUploadIqProtocolEntity.isDuplicate():
            self.doSendMedia(mediaType, filePath, resultRequestUploadIqProtocolEntity.getUrl(), jid,
                             resultRequestUploadIqProtocolEntity.getIp(), caption)
        else:
            successFn = lambda filePath, jid, url: self.doSendMedia(mediaType, filePath, url, jid,
                                                                    resultRequestUploadIqProtocolEntity.getIp(),
                                                                    caption)
            mediaUploader = WTTMediaUploader(jid, self.getOwnJid(), filePath,
                                             resultRequestUploadIqProtocolEntity.getUrl(),
                                             get_wa_config()["phone"],
                                             resumeOffset=resultRequestUploadIqProtocolEntity.getResumeOffset(),
                                             successClbk=successFn,
                                             errorClbk=self.onUploadError,
                                             progressCallback=self.onUploadProgress,
                                             asynchronous=False,
                                             )
            mediaUploader.start()

    def onRequestUploadError(self, jid, path, errorRequestUploadIqProtocolEntity, requestUploadIqProtocolEntity):
        logger.error("Request upload for file %s for %s failed" % (path, jid))

    def doSendMedia(self, mediaType, filePath, url, to, ip=None, caption=None):
        if mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE:
            entity = ImageDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to, caption=caption)
        elif mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_AUDIO:
            entity = AudioDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to)
        elif mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_VIDEO:
            entity = VideoDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to, caption=caption)
        self.toLower(entity)

    def onUploadError(self, filePath, jid, url):
        logger.error("Upload file %s to %s for %s failed!" % (filePath, url, jid))

    def onUploadProgress(self, filePath, jid, url, progress):
        sys.stdout.write("%s => %s, %d%% \r" % (os.path.basename(filePath), jid, progress))
        sys.stdout.flush()

    def sendToTelegram(self, messageProtocolEntity, body, isMedia=False, filename=None):
        msg = WTTMessage((messageProtocolEntity.media_type if isMedia else messageProtocolEntity.getType()),
                         messageProtocolEntity.getNotify().encode('latin-1').decode(),
                         body,
                         title=self.groupIdToSubject(messageProtocolEntity.getFrom()) or None,
                         isGroup=messageProtocolEntity.isGroupMessage(),
                         waID=messageProtocolEntity.getFrom(),
                         filename=filename)
        self.wttQ.put(msg)

    def onMediaMessage(self, messageProtocolEntity):
        if messageProtocolEntity.media_type in ("image", "audio", "video", "document", "gif", "ptt"):
            logger.info("Received media message")
            self.mediaWorker.enqueue(messageProtocolEntity)
        elif messageProtocolEntity.media_type == messageProtocolEntity.TYPE_MEDIA_URL:
            self.sendToTelegram(messageProtocolEntity, messageProtocolEntity.canonical_url, isMedia=True)
            return
        elif messageProtocolEntity.media_type == messageProtocolEntity.TYPE_MEDIA_LOCATION:
            logger.warning("Received Location message - not supported yet")
            return
        elif messageProtocolEntity.media_type == messageProtocolEntity.TYPE_MEDIA_CONTACT:
            logger.warning("Received vCard message - not supported yet")
            return
        else:
            logger.error("Unknown media type %s " % messageProtocolEntity.media_type)

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

        if self.mediaWorker and self.mediaWorker.isAlive():
            pass
        else:
            logger.info("Starting MediaWorker")
            self.mediaWorker = MediaWorker(self.wttQ, groups)
            self.mediaWorker.start()

        if self.telegramMessageWorker and self.telegramMessageWorker.isAlive():
            pass
        else:
            logger.info("Listening for Telegram messages")
            self.telegramMessageWorker = Thread(target=self.telegramMessageListener)
            self.telegramMessageWorker.start()

        logger.info("Processing offline messages...")
        self.processOfflineMessages()
        logger.info("Offline messages processed")

        # self.getGroupInfo()  # TODO listen to updates instead?
        logger.info("Groups updated")

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
        return False
