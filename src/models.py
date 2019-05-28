class PrivateMessage:
    def __init__(self, type, author, body, filename=None, waID=None, tgID=None):
        self.type = type
        self.author = author
        self.body = body
        self.waID = waID
        self.tgID = tgID
        self.filename = filename


class GroupMessage:
    def __init__(self, type, author, body, title, filename=None, waID=None, tgID=None):
        self.type = type
        self.author = author
        self.body = body
        self.title = title
        self.waID = waID
        self.tgID = tgID
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
