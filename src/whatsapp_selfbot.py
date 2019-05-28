import base64
import logging

from consonance.structs.keypair import KeyPair
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent
from yowsup.layers import YowParallelLayer
from yowsup.layers.auth import YowAuthenticationProtocolLayer
from yowsup.layers.axolotl import AxolotlControlLayer, AxolotlSendLayer, AxolotlReceivelayer
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.protocol_acks import YowAckProtocolLayer
from yowsup.layers.protocol_groups import YowGroupsProtocolLayer
from yowsup.layers.protocol_iq import YowIqProtocolLayer
from yowsup.layers.protocol_media import *
from yowsup.layers.protocol_messages import YowMessagesProtocolLayer
from yowsup.layers.protocol_receipts import YowReceiptProtocolLayer
from yowsup.stacks import YowStack, YOWSUP_CORE_LAYERS

from src.whatsapp_layer import WhatsappLayer

logger = logging.getLogger(__name__)


def run(wttQueue, ttwQueue, config):
    logger.info("Starting Whatsapp Self-Bot")

    keypair = KeyPair.from_bytes(
        base64.b64decode(config["client_static_keypair"])
    )

    credentials = (config["phone"], keypair)

    layers = (
                 WhatsappLayer(wttQueue, ttwQueue),
                 YowParallelLayer([YowAuthenticationProtocolLayer, YowMessagesProtocolLayer, YowReceiptProtocolLayer,
                                   YowAckProtocolLayer, YowIqProtocolLayer, YowGroupsProtocolLayer,
                                   YowMediaProtocolLayer]),
                 AxolotlControlLayer,
                 YowParallelLayer((AxolotlSendLayer, AxolotlReceivelayer)),
             ) + YOWSUP_CORE_LAYERS

    stack = YowStack(layers)
    stack.setProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS, credentials)  # setting credentials
    stack.setProp(YowNetworkLayer.PROP_ENDPOINT, YowConstants.ENDPOINTS[0])  # whatsapp server address
    # stack.setProp(YowCoderLayer.PROP_DOMAIN, YowConstants.DOMAIN)
    # stack.setProp(YowCoderLayer.PROP_RESOURCE, YowsupEnv.getCurrent().getResource()) #info about us as WhatsApp client

    stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))  # sending the connect signal

    stack.loop()
