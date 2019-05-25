class WTTMessage:
    def __init__(self, type, author, body, group=None):
        self.type = type
        self.author = author
        self.group = group
        self.body = body
