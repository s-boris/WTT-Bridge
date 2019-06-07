import logging
import os
import sys
import time
from queue import Queue
from threading import Thread

from PIL import Image
from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_acks.protocolentities import *
from yowsup.layers.protocol_groups.protocolentities import *
from yowsup.layers.protocol_media.protocolentities import *
from yowsup.layers.protocol_messages.protocolentities import *
from yowsup.layers.protocol_profiles.protocolentities import *
from yowsup.layers.protocol_receipts.protocolentities import *

import wtt.utils as utils
from wtt.models import *
from wtt.whatsapp_client.media_worker import MediaWorker

logger = logging.getLogger(__name__)

TEMPLOCATION = "temp"
CHAT_TEMPLATE = {"subject": None, "participants": None, "picture": None}


class WTTLayer(YowInterfaceLayer):

    def __init__(self):
        super().__init__()

        self._mediaWorker = None
        self._offlineMsgQ = Queue()
        self.chats = {}
        self.ready = False

        self._waBus = None
        self._waBusThread = None

        if not os.path.exists(TEMPLOCATION):
            os.makedirs(TEMPLOCATION)

    def onTelegramMessage(self, msg):
        if msg.type == "text":
            outgoingMessageProtocolEntity = TextMessageProtocolEntity(msg.body, to=msg.waID)
            self.toLower(outgoingMessageProtocolEntity)
        elif msg.type == "image":
            filepath = TEMPLOCATION + "/" + str(time.time()) + msg.filename
            img = Image.open(msg.body)
            img.save(filepath, 'JPEG')
            self.media_send(msg.waID, filepath, RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE)
            # os.remove(temporarylocation)  # TODO Delete file when done

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        logger.info('Connected with WhatsApp servers')

        self._waBus = self.getProp("waBus")
        self._waBus.setTgMessageListener(self.onTelegramMessage)

        self._waBusThread = Thread(target=self._waBus.run, args=())
        self._waBusThread.start()

        self.toLower(ListGroupsIqProtocolEntity())  # startup will proceed with onGroupListReceived

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom(),
                                                'read', messageProtocolEntity.getParticipant())

        if not self.ready:
            logger.info("Waiting with message ({}) delivery, groups not loaded yet...".format(
                messageProtocolEntity.getNotify().encode('latin-1').decode()))
            self._offlineMsgQ.put(messageProtocolEntity)
            return

        if isinstance(messageProtocolEntity, MediaMessageProtocolEntity):
            self.onMediaMessage(messageProtocolEntity)
            return
        elif isinstance(messageProtocolEntity, TextMessageProtocolEntity):
            self.forwardMessageToTelegram(messageProtocolEntity, messageProtocolEntity.getBody(), isMedia=False)
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
            logger.debug("Received ListGroupsResultIqProtocolEntity")
            self.onGroupListReceived(entity)

    # WIP Media sending stuff
    # ------------------------------------------------------------

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
            mediaUploader = utils.WTTMediaUploader(jid, self.getOwnJid(), filePath,
                                                   resultRequestUploadIqProtocolEntity.getUrl(),
                                                   utils.get_wa_config()["phone"],
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

    # --------------------------------------------------------------

    def onMediaMessage(self, messageProtocolEntity):
        if messageProtocolEntity.media_type in ("image", "audio", "video", "document", "gif", "ptt"):
            logger.debug("Received media message")
            self._mediaWorker.enqueue(messageProtocolEntity)
        elif messageProtocolEntity.media_type == messageProtocolEntity.TYPE_MEDIA_URL:
            logger.debug("Received url message")
            self.forwardMessageToTelegram(messageProtocolEntity, messageProtocolEntity.canonical_url, isMedia=True)
            return
        elif messageProtocolEntity.media_type == messageProtocolEntity.TYPE_MEDIA_LOCATION:
            location = messageProtocolEntity.message_attributes.location
            latitude = location.degrees_latitude
            longitude = location.degrees_longitude
            name = location.name
            url = location.url
            msg = WTTMessage(messageProtocolEntity.media_type,
                             messageProtocolEntity.getNotify().encode('latin-1').decode(),
                             {"longitude": longitude, "latitude": latitude},
                             waID=messageProtocolEntity.getFrom(),
                             title=(self.groupIdToSubject(
                                 messageProtocolEntity.getFrom()) if messageProtocolEntity.isGroupMessage() else None),
                             isGroup=messageProtocolEntity.isGroupMessage(),
                             filename=None,
                             caption={"name": name, "url": url})
            self._waBus.emitEventToTelegram(msg)
            return
        elif messageProtocolEntity.media_type == messageProtocolEntity.TYPE_MEDIA_CONTACT:
            logger.warning("Received vCard message - not supported yet")
            return
        else:
            logger.error("Unknown media type %s " % messageProtocolEntity.media_type)

    def forwardMessageToTelegram(self, messageProtocolEntity, body, isMedia=False, filename=None):
        msg = WTTMessage((messageProtocolEntity.media_type if isMedia else messageProtocolEntity.getType()),
                         messageProtocolEntity.getNotify().encode('latin-1').decode(),
                         body,
                         title=self.groupIdToSubject(messageProtocolEntity.getFrom()) or None,
                         isGroup=messageProtocolEntity.isGroupMessage(),
                         waID=messageProtocolEntity.getFrom(),
                         filename=filename)
        self._waBus.emitEventToTelegram(msg)

    def processOfflineMessages(self):
        logger.info("Processing offline messages...")
        while not self._offlineMsgQ.empty():
            self.onMessage(self._offlineMsgQ.get())
            self._offlineMsgQ.task_done()
        logger.info("Offline messages processed")

    def onGroupListReceived(self, entity):
        for group in entity.getGroups():
            logger.debug('Received group info with id %s (owner %s, subject %s)', group.getId(), group.getOwner(),
                         group.getSubject())
            if not group.getId() in self.chats:
                self.chats[group.getId()] = CHAT_TEMPLATE
            if not self.chats[group.getId()]["subject"] == group.getSubject().encode('latin-1').decode():
                self.chats[group.getId()]["subject"] = group.getSubject().encode('latin-1').decode()
                self._waBus.emitEventToTelegram(
                    WTTUpdateChatSubject(group.getSubject().encode('latin-1').decode(), waID=group.getId()))
            if not self.chats[group.getId()]["participants"] == group.getParticipants():
                self.chats[group.getId()]["participants"] = group.getParticipants()
                self._waBus.emitEventToTelegram(
                    WTTUpdateChatParticipants(group.getParticipants(), waID=group.getId()))

            # testid = group.getId()
            # time.sleep(0.5)
        # self.toLower(InfoGroupsIqProtocolEntity(testid))

        logger.info("Group preload done")

        if not self.ready:
            # this is the first time we received group infos and have sufficient info to handle incoming messages,
            # which means we will finish the startup procedure
            self.ready = True
            self.startMediaWorker()
            self.processOfflineMessages()
            self.updateMappedChatPictures()

    def startMediaWorker(self):
        if self._mediaWorker and self._mediaWorker.isAlive():
            pass
        else:
            logger.info("Starting MediaWorker")
            self._mediaWorker = MediaWorker(self._waBus, self.chats)
            self._mediaWorker.start()

    def updateMappedChatPictures(self):
        chatMap = utils.get_chatmap()
        for tgID in chatMap:
            if chatMap[tgID]["waID"]:
                entity = GetPictureIqProtocolEntity(chatMap[tgID]["waID"], preview=False)
                self._sendIq(entity, self.onGetContactPictureResult)
                time.sleep(1)

    def onGetContactPictureResult(self, resultGetPictureIqProtocolEntity, getPictureIqProtocolEntity):
        if not resultGetPictureIqProtocolEntity.getFrom() in self.chats:
            self.chats[resultGetPictureIqProtocolEntity.getFrom()] = CHAT_TEMPLATE

        if not self.chats[resultGetPictureIqProtocolEntity.getFrom()][
                   "picture"] == resultGetPictureIqProtocolEntity.getPictureData():
            self.chats[resultGetPictureIqProtocolEntity.getFrom()] = {
                "picture": resultGetPictureIqProtocolEntity.getPictureData()}

            self._waBus.emitEventToTelegram(
                WTTUpdateChatPicture(resultGetPictureIqProtocolEntity.getPictureData(),
                                     waID=resultGetPictureIqProtocolEntity.getFrom()))

            logger.info("Updated picture for {}".format(resultGetPictureIqProtocolEntity.getFrom()))

    def groupIdToSubject(self, groupId):
        rest = groupId.split('@', 1)[0]
        for key in self.chats:
            if self.chats[key] == rest:
                return self.chats[key]["subject"]
        return False
