import logging
import base64
from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_groups.protocolentities import ListGroupsResultIqProtocolEntity, \
    ListParticipantsResultIqProtocolEntity, ListGroupsIqProtocolEntity, InfoGroupsIqProtocolEntity
from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities import OutgoingAckProtocolEntity

groups = []


class WhatsappLayer(YowInterfaceLayer):

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        # send receipt otherwise we keep receiving the same message over and over

        if True:
            receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom(),
                                                    'read', messageProtocolEntity.getParticipant())
            outgoingMessageProtocolEntity = TextMessageProtocolEntity(messageProtocolEntity.getBody(),
                                                                      to=messageProtocolEntity.getFrom())
            self.toLower(receipt)
            self.toLower(outgoingMessageProtocolEntity)

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        # confirm message received
        receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom(),
                                                'read', messageProtocolEntity.getParticipant())
        self.toLower(receipt)

        # do stuff with the message
        if messageProtocolEntity.getType() == 'text':
            self.onTextMessage(messageProtocolEntity)
        elif messageProtocolEntity.getType() == 'media':
            self.onMediaMessage(messageProtocolEntity)
        else:
            messageOut = "Unknown message type %s " % messageProtocolEntity.getType()
            print(messageOut.toProtocolTreeNode())

        # echo example
        # outgoingMessageProtocolEntity = TextMessageProtocolEntity(messageProtocolEntity.getBody(),
        #                                                          to=messageProtocolEntity.getFrom())
        # self.toLower(outgoingMessageProtocolEntity)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", entity.getType(), entity.getFrom())
        self.toLower(ack)

    @ProtocolEntityCallback("failure")
    def onFailure(self, entity):
        print("Login Failed, reason: %s" % entity.getReason())

    def onTextMessage(self, messageProtocolEntity):
        if not messageProtocolEntity.isGroupMessage():
            msg = WTTMessage(messageProtocolEntity.MESSAGE_TYPE_TEXT, messageProtocolEntity.getNotify(),
                             messageProtocolEntity.getBody())
        else:
            msg = WTTMessage(messageProtocolEntity.MESSAGE_TYPE_TEXT, messageProtocolEntity.getNotify(),
                             messageProtocolEntity.getBody(),
                             group=self.groupIdToAlias(messageProtocolEntity.getFrom()))
            self.get_group_info(messageProtocolEntity.getFrom())  # TODO

        self.message_queue.put(msg)

    def onMediaMessage(self, messageProtocolEntity):
        if messageProtocolEntity.media_type in ("image", "audio", "video", "document"):
            media = self.getDownloadableMediaMessageBody(messageProtocolEntity)
            print(media)
            msg = WTTMessage(messageProtocolEntity.media_type, messageProtocolEntity.getNotify(), media)
            self.message_queue.put(msg)
        elif messageProtocolEntity.media_type == "location":
            print("location (%s, %s) to %s" % (
                messageProtocolEntity.getLatitude(), messageProtocolEntity.getLongitude(),
                messageProtocolEntity.getFrom(False)))
            # TODO

        elif messageProtocolEntity.media_type == "contact":
            print("contact (%s, %s) to %s" % (
                messageProtocolEntity.getName(), messageProtocolEntity.getCardData(),
                messageProtocolEntity.getFrom(False)))
            # TODO

    def getDownloadableMediaMessageBody(self, message):
        return "[media_type={media_type}, length={media_size}, url={media_url}, key={media_key}]".format(
            media_type=message.media_type,
            media_size=message.file_length,
            media_url=message.url,
            media_key=base64.b64encode(message.media_key)
        )

    def get_group_info(self, groupId):
        entity = InfoGroupsIqProtocolEntity(groupId)
        self.toLower(entity)

    def update_groups(self):
        def onGroupsListResult(successEntity, originalEntity):
            global groups
            for group in successEntity.getGroups():
                groups.append({"groupId": group.getId(), "subject": group.getSubject()})

        def onGroupsListError(errorEntity, originalEntity):
            logger.error("Error retrieving groups")

        entity = ListGroupsIqProtocolEntity()
        self._sendIq(entity, onGroupsListResult, onGroupsListError)

    def groupIdToAlias(self, groupId):
        for group in groups:
            if group["groupId"] == groupId:
                return group["subject"]
