import json
import logging
import os
import socket

from telethon.sync import TelegramClient
from yowsup.common.http import WARequest, JSONResponseParser
from yowsup.config.manager import ConfigManager
from yowsup.layers.protocol_media.mediauploader import MediaUploader

logger = logging.getLogger(__name__)

dir_path = os.path.dirname(os.path.realpath(__file__))
chatmap_path = dir_path + '/chatmap.json'

config = None


def loadConfig():
    global config
    with open(dir_path + '/config.json', 'r') as f:
        config = json.load(f)


async def ensureTelethonSession(phone=None, app_id=None, api_hash=None):
    if config:
        tgCfg = get_tg_config()
        waCfg = get_wa_config()
        cfgAppId = int(tgCfg["api_id"])
        cfgAppHash = tgCfg["api_hash"]
        cfgPhone = "+" + waCfg["phone"]

    try:
        client = await TelegramClient('anon', app_id or cfgAppId, api_hash or cfgAppHash).start(phone or cfgPhone)
    except Exception as e:
        logger.error("Failed initializing Telethon: " + str(e))
        return False
    await client.disconnect()
    return True

def get_chatmap():
    data = {}
    if os.path.isfile(chatmap_path):
        with open(chatmap_path, 'r') as file:
            data = json.load(file)
    else:
        with open(chatmap_path, 'w+') as outfile:
            json.dump(data, outfile)
    return data


def save_chatmap(data):
    with open(chatmap_path, 'w') as outfile:
        json.dump(data, outfile)


def get_tg_config():
    return config['Telegram']


def get_wa_config():
    return config['Whatsapp']


class WTTMediaUploader(MediaUploader):
    def __init__(self, jid, accountJid, sourcePath, uploadUrl, username, resumeOffset=0, successClbk=None,
                 errorClbk=None,
                 progressCallback=None, asynchronous=True):
        config = ConfigManager().load(username)
        WARequest.__init__(self, config)

        self.asynchronous = asynchronous
        self.jid = jid
        self.accountJid = accountJid
        self.sourcePath = sourcePath
        self.uploadUrl = uploadUrl
        self.resumeOffset = resumeOffset

        self.successCallback = successClbk
        self.errorCallback = errorClbk
        self.progressCallback = progressCallback

        self.pvars = ["name", "type", "size", "url", "error",
                      "mimetype", "filehash", "width", "height"]

        self.setParser(JSONResponseParser())

        self.sock = socket.socket()
