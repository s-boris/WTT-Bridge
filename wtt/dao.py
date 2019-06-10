import logging
import sqlite3
import threading
import time
from queue import Queue
from sqlite3 import Error
from threading import Thread

logger = logging.getLogger(__name__)

CREATE_CHATMAP_TABLE = "CREATE TABLE IF NOT EXISTS chatmap (tgID integer PRIMARY KEY, waID text NOT NULL, subject text, picture blob);"
CREATE_USERS_TABLE = "CREATE TABLE IF NOT EXISTS users (id integer PRIMARY KEY AUTOINCREMENT, waID text NOT NULL, name text);"
CREATE_CHATMAPUSERS_TABLE = "CREATE TABLE IF NOT EXISTS chatmapusers (pk integer PRIMARY KEY AUTOINCREMENT, chatID integer NOT NULL, userID text NOT NULL, CONSTRAINT fk_chat FOREIGN KEY (chatID) REFERENCES chatmap(tgID), CONSTRAINT fk_user FOREIGN KEY (userID) REFERENCES users(waID));"

lock = threading.Lock()


# noinspection PyPep8Naming
class WTTDao:
    def __init__(self, db_file):
        """ create a database connection to the SQLite database """
        self._writeQueue = Queue(maxsize=0)
        try:
            self._conn = sqlite3.connect(db_file, check_same_thread=False)
            self._cur = self._conn.cursor()
            self._cur.execute(CREATE_CHATMAP_TABLE)
            self._cur.execute(CREATE_USERS_TABLE)
            self._cur.execute(CREATE_CHATMAPUSERS_TABLE)
            self._conn.commit()

            self._writeThread = Thread(target=self._writeWorker, args=())
            self._writeThread.start()
        except Error as e:
            print(e)

    def _writeWorker(self):
        while True:
            if not self._writeQueue.empty():
                s, data, cb = self._writeQueue.get()
                try:
                    lock.acquire(True)
                    self._cur.execute(s, data)
                    self._conn.commit()
                    if cb:
                        if self._cur.rowcount == 0:
                            cb(False)
                        else:
                            cb(True)
                finally:
                    lock.release()
            time.sleep(0.1)

    def _enqueue(self, statement, data, cb=None):
        self._writeQueue.put((statement, data, cb))

    def createChat(self, tgID, waID, subject, picture=None, participants=None, cb=None):
        s = "INSERT INTO chatmap(tgID, waID, subject, picture, participants) VALUES(?,?,?,?,?)"
        if not self.chatRecordExists(tgID):
            self._enqueue(s, (tgID, waID, subject, picture, participants), cb=cb)
        else:
            logger.debug("Mapped chat for {} already exists".format(tgID))

    def createUser(self, waID, name=None, cb=None):
        s = "INSERT INTO users(waID, name) VALUES(?,?)"
        if not self.userRecordExists(waID):
            self._enqueue(s, (waID, name), cb=cb)
        else:
            logger.debug("User {} already exists".format(waID))

    def addParticipantToChat(self, chatWaID, userWaID, cb=None):
        s = "INSERT INTO chatmapusers(chatID, userID) VALUES(?,?)"
        chatTgID = self.getTelegramID(chatWaID)

        if not self.getUser(userWaID):
            self.createUser(userWaID)

        if chatTgID and not self.participantRecordExists(chatTgID, userWaID):
            self._enqueue(s, (chatTgID, userWaID), cb=cb)
        else:
            logger.debug(
                "Participant record for {} in {} already exists or the chat that he belongs to hasn't been mapped yet".format(
                    userWaID, chatWaID))

    def updatePicture(self, tgID, picture, cb=None):
        s = "UPDATE chatmap SET picture = ? WHERE tgID = ?"
        if self.chatRecordExists(tgID):
            self._enqueue(s, (picture, tgID), cb=cb)
        else:
            logger.error("Could not update picture for {} because no mapped chat exists".format(tgID))

    def updateSubject(self, tgID, subject, cb=None):
        s = "UPDATE chatmap SET subject = ? WHERE tgID = ?"
        if self.chatRecordExists(tgID):
            self._enqueue(s, (subject, tgID), cb=cb)
        else:
            logger.error("Could not update subject for {} because no mapped chat exists".format(tgID))

    def updateParticipants(self, tgID, participants, cb=None):
        s = "UPDATE chatmap SET participants = ? WHERE tgID = ?"
        if self.chatRecordExists(tgID):
            self._enqueue(s, (participants, tgID), cb=cb)
        else:
            logger.error("Could not update participants for {} because no mapped chat exists".format(tgID))

    def getWhatsappID(self, tgID):
        s = "SELECT waID FROM chatmap WHERE tgID=?;"
        try:
            lock.acquire(True)
            self._cur.execute(s, (tgID,))
            data = self._cur.fetchone()
        finally:
            lock.release()

        if data:
            return data[0]
        else:
            return None

    def getTelegramID(self, waID):
        s = "SELECT tgID FROM chatmap WHERE waID=? OR waID LIKE ? ;"
        try:
            lock.acquire(True)
            self._cur.execute(s, (waID, waID + '%'))
            data = self._cur.fetchone()
        finally:
            lock.release()

        if data:
            return data[0]
        else:
            return None

    def getMappedWaChatIDs(self):
        s = "SELECT waID FROM chatmap;"
        try:
            lock.acquire(True)
            self._cur.execute(s)
            data = self._cur.fetchall()
        finally:
            lock.release()

        return data

    def getChatPicture(self, tgID=None, waID=None):
        if not tgID:
            if not waID:
                logger.error("You have to provide either a telegramID or whatsappID")
                return False
            else:
                tgID = self.getTelegramID(waID)

        s = "SELECT picture FROM chatmap WHERE tgID=?;"
        try:
            lock.acquire(True)
            self._cur.execute(s, (tgID,))
            data = self._cur.fetchone()
        finally:
            lock.release()

        if data:
            return data[0]
        else:
            return None

    def getChatSubject(self, tgID=None, waID=None):
        if not tgID:
            if not waID:
                logger.error("You have to provide either a telegramID or whatsappID")
                return False
            else:
                tgID = self.getTelegramID(waID)

        s = "SELECT subject FROM chatmap WHERE tgID=?;"
        try:
            lock.acquire(True)
            self._cur.execute(s, (tgID,))
            data = self._cur.fetchone()
        finally:
            lock.release()

        if data:
            return data[0]
        else:
            return None

    def getChatParticipants(self, tgID=None, waID=None):
        if not tgID:
            if not waID:
                logger.error("You have to provide either a telegramID or whatsappID")
                return False
            else:
                tgID = self.getTelegramID(waID)

        s = "SELECT waID, name FROM users u LEFT JOIN chatmapusers cu ON cu.userID = u.waID WHERE cu.chatID = ?;"
        try:
            lock.acquire(True)
            self._cur.execute(s, (tgID,))
            data = self._cur.fetchall()
        finally:
            lock.release()

        if data:
            return data
        else:
            return None

    def getUser(self, waID):
        s = "SELECT * FROM users WHERE waID=?;"
        try:
            lock.acquire(True)
            self._cur.execute(s, (waID,))
            data = self._cur.fetchone()
        finally:
            lock.release()

        if data:
            return data[0]
        else:
            return None

    def chatRecordExists(self, tgID):
        s = "SELECT EXISTS(SELECT 1 FROM chatmap WHERE tgID=?);"
        try:
            lock.acquire(True)
            self._cur.execute(s, (tgID,))
            data = self._cur.fetchone()
        finally:
            lock.release()

        if data[0] is 0:
            return False
        else:
            return True

    def userRecordExists(self, waID):
        s = "SELECT EXISTS(SELECT 1 FROM users WHERE waID=?);"
        try:
            lock.acquire(True)
            self._cur.execute(s, (waID,))
            data = self._cur.fetchone()
        finally:
            lock.release()

        if data[0] is 0:
            return False
        else:
            return True

    def participantRecordExists(self, chatTgID, userWaID):
        s = "SELECT EXISTS(SELECT 1 FROM chatmapusers WHERE chatID=? AND userID=?);"
        try:
            lock.acquire(True)
            self._cur.execute(s, (chatTgID, userWaID))
            data = self._cur.fetchone()
        finally:
            lock.release()

        if data[0] is 0:
            return False
        else:
            return True
