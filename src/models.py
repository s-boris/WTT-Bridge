class PrivateMessage:
    def __init__(self, type, author, body, waID=None, tgID=None):
        self.type = type
        self.author = author
        self.body = body
        self.waID = waID
        self.tgID = tgID


class GroupMessage:
    def __init__(self, type, author, body, title, waID=None, tgID=None):
        self.type = type
        self.author = author
        self.body = body
        self.title = title
        self.waID = waID
        self.tgID = tgID


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
