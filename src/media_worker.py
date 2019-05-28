import base64
import logging
import threading
import time
from queue import Queue

import math
import requests
from tqdm import tqdm
from yowsup.layers.protocol_media.mediacipher import MediaCipher
from yowsup.layers.protocol_media.protocolentities \
    import ImageDownloadableMediaMessageProtocolEntity, AudioDownloadableMediaMessageProtocolEntity, \
    VideoDownloadableMediaMessageProtocolEntity, DocumentDownloadableMediaMessageProtocolEntity, \
    ContactMediaMessageProtocolEntity, DownloadableMediaMessageProtocolEntity

from src.models import GroupMessage, PrivateMessage

logger = logging.getLogger(__name__)


class MediaWorker(threading.Thread):
    def __init__(self, wttQueue, groups):
        super(MediaWorker, self).__init__()
        self.daemon = True
        self.wttQ = wttQueue
        self.groups = groups
        self._jobs = Queue()
        self._media_cipher = MediaCipher()

    def enqueue(self, media_message_protocolentity):
        self._jobs.put(media_message_protocolentity)

    def _create_progress_iterator(self, iterable, niterations, desc):
        return tqdm(
            iterable, total=niterations, unit='KB', dynamic_ncols=True,
            unit_scale=True, leave=True, desc=desc, ascii=True)

    def _download(self, url):
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        logger.debug("%s total size is %s, downloading" % (url, total_size))
        block_size = 1024
        wrote = 0
        enc_data = b""

        for data in self._create_progress_iterator(
                response.iter_content(block_size), math.ceil(total_size // block_size) + 1, "Download       ",
        ):
            wrote = wrote + len(data)
            enc_data = enc_data + data

        if total_size != 0 and wrote != total_size:
            logger.error("Something went wrong")
            return None

        return enc_data

    def _decrypt(self, ciphertext, ref_key, media_info):
        length_kb = int(math.ceil(len(ciphertext) / 1024))
        progress = self._create_progress_iterator(range(length_kb), length_kb, "Decrypt        ")
        try:
            plaintext = self._media_cipher.decrypt(ciphertext, ref_key, media_info)
            progress.update(length_kb)
            return plaintext
        except Exception as e:
            progress.set_description("Decrypt Error  ")
            logger.error(e)

        return None

    def _write(self, media_message_protocolentity, data, filename):
        # pack the message into our models
        if media_message_protocolentity.isGroupMessage():
            msg = GroupMessage(media_message_protocolentity.media_type, media_message_protocolentity.getNotify(), data,
                               self.groupIdToSubject(media_message_protocolentity.getFrom()),
                               waID=media_message_protocolentity.getFrom(), filename=filename)
        else:
            msg = PrivateMessage(media_message_protocolentity.media_type, media_message_protocolentity.getNotify(),
                                 data, waID=media_message_protocolentity.getFrom(), filename=filename)

        self.wttQ.put(msg)

        return None

    def run(self):
        logger.debug("MediaWorker started")
        while True:
            if self._jobs.empty():
                time.sleep(1)
                continue
            media_message_protocolentity = self._jobs.get()
            if media_message_protocolentity is None:
                logger.error("MediaMessageEntity is none")
                continue
            if isinstance(media_message_protocolentity, DownloadableMediaMessageProtocolEntity):
                logger.info(
                    "Processing [url=%s, media_key=%s]" %
                    (media_message_protocolentity.url, base64.b64encode(media_message_protocolentity.media_key))
                )
            else:
                logger.info("Processing %s" % media_message_protocolentity.media_type)

            filedata = None
            fileext = None
            if isinstance(media_message_protocolentity, ImageDownloadableMediaMessageProtocolEntity):
                media_info = MediaCipher.INFO_IMAGE
                filename = "image"
            elif isinstance(media_message_protocolentity, AudioDownloadableMediaMessageProtocolEntity):
                media_info = MediaCipher.INFO_AUDIO
                filename = "ptt" if media_message_protocolentity.ptt else "audio"
            elif isinstance(media_message_protocolentity, VideoDownloadableMediaMessageProtocolEntity):
                media_info = MediaCipher.INFO_VIDEO
                filename = "video"
            elif isinstance(media_message_protocolentity, DocumentDownloadableMediaMessageProtocolEntity):
                media_info = MediaCipher.INFO_DOCUM
                filename = media_message_protocolentity.file_name
            elif isinstance(media_message_protocolentity, ContactMediaMessageProtocolEntity):
                filename = media_message_protocolentity.display_name
                filedata = media_message_protocolentity.vcard
                fileext = "vcard"
            # elif isinstance(media_message_protocolentity, StickerDownloadableMediaMessageProtocolEntity):
            #     media_info = MediaCipher.INFO_IMAGE
            #     filename = "sticker"
            else:
                logger.error("Unsupported Media type: %s" % media_message_protocolentity.__class__)
                continue

            if filedata is None:
                enc_data = self._download(media_message_protocolentity.url)
                if enc_data is None:
                    logger.error("Download failed")
                    continue

                filedata = self._decrypt(enc_data, media_message_protocolentity.media_key, media_info)
                if filedata is None:
                    logger.error("Decrypt failed")
                    continue
            if not isinstance(media_message_protocolentity, DocumentDownloadableMediaMessageProtocolEntity):
                if fileext is None:
                    fileext = media_message_protocolentity.mimetype.split('/')[1].split(';')[0]
                filename_full = "%s.%s" % (filename, fileext)
            else:
                filename_full = filename
            if self._write(media_message_protocolentity, filedata, filename_full):
                logger.info("Pushing processed media...")
            else:
                continue

    def groupIdToSubject(self, groupId):
        rest = groupId.split('@', 1)[0]
        for group in self.groups:
            if group["groupId"] == rest:
                return group["subject"]
