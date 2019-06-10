import logging

from yowsup.layers import YowLayerEvent
from yowsup.layers.network import YowNetworkLayer
from yowsup.stacks import YowStackBuilder

from wtt.whatsapp_client.wtt_layer import WTTLayer

logger = logging.getLogger(__name__)


class WTTStack(object):
    def __init__(self, profile):
        stackBuilder = YowStackBuilder()

        self._stack = stackBuilder \
            .pushDefaultLayers() \
            .push(WTTLayer) \
            .build()

        self._stack.setProfile(profile)

    def set_prop(self, key, val):
        self._stack.setProp(key, val)

    def start(self):
        self._stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
        self._stack.loop()


def run(waBus, config, dao):
    logger.info("Starting Whatsapp Self-Bot")
    stack = WTTStack(config["phone"])
    stack.set_prop("waBus", waBus)
    stack.set_prop("dao", dao)
    stack.start()
