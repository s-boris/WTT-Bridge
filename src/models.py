class WTTMessage:
    def __init__(self, type, author, body, waID=None, tgID=None, title=None, isGroup=None, filename=None):
        self.type = type
        self.author = author
        self.body = body
        self.waID = waID
        self.tgID = tgID
        self.title = title
        self.isGroup = isGroup
        self.filename = filename


class CreateChat:
    def __init__(self, title, waID=None, tgID=None):
        self.title = title
        self.waID = waID
        self.tgID = tgID


class UpdateChat:
    def __init__(self, title, picture, participants, waID=None, tgID=None):
        self.title = title
        self.picture = picture
        self.participants = participants
        self.waID = waID
        self.tgID = tgID
