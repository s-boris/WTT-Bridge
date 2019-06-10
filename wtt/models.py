class WTTMessage:
    def __init__(self, type, author, body, waID=None, tgID=None, subject=None, isGroup=None, filename=None, caption=None):
        self.type = type
        self.author = author
        self.subject = subject
        self.body = body
        self.waID = waID
        self.tgID = tgID
        self.isGroup = isGroup
        self.filename = filename
        self.caption = caption


class WTTCreateChat:
    def __init__(self, subject, waID=None, tgID=None):
        self.subject = subject
        self.waID = waID
        self.tgID = tgID


class WTTUpdateChatPicture:
    def __init__(self, picture, waID=None, tgID=None):
        self.picture = picture
        self.waID = waID
        self.tgID = tgID


class WTTUpdateChatParticipants:
    def __init__(self, participants, waID=None, tgID=None):
        self.participants = participants
        self.waID = waID
        self.tgID = tgID


class WTTUpdateChatSubject:
    def __init__(self, subject, waID=None, tgID=None):
        self.subject = subject
        self.waID = waID
        self.tgID = tgID
