from src.whatsapp_layer import WhatsappLayer
from yowsup.layers import YowParallelLayer
from yowsup.layers.auth import YowAuthenticationProtocolLayer
from yowsup.layers.protocol_messages import YowMessagesProtocolLayer
from yowsup.layers.protocol_receipts import YowReceiptProtocolLayer
from yowsup.layers.protocol_iq import YowIqProtocolLayer
from yowsup.layers.protocol_groups import YowGroupsProtocolLayer
from yowsup.layers.protocol_acks import YowAckProtocolLayer
from yowsup.layers.network import YowNetworkLayer
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent
from yowsup.stacks import YowStack, YOWSUP_CORE_LAYERS
from yowsup.layers.axolotl import AxolotlControlLayer, AxolotlSendLayer, AxolotlReceivelayer
from consonance.structs.keypair import KeyPair
import base64


def run(message_queue, config):
    keypair = KeyPair.from_bytes(
        base64.b64decode(config["password"])
    )

    CREDENTIALS = (config["phone"], keypair)

    layers = (
                 WhatsappLayer(message_queue=message_queue),
                 YowParallelLayer([YowAuthenticationProtocolLayer, YowMessagesProtocolLayer, YowReceiptProtocolLayer,
                                   YowAckProtocolLayer, YowIqProtocolLayer, YowGroupsProtocolLayer]),
                 AxolotlControlLayer,
                 YowParallelLayer((AxolotlSendLayer, AxolotlReceivelayer)),
             ) + YOWSUP_CORE_LAYERS

    stack = YowStack(layers)
    stack.setProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS, CREDENTIALS)  # setting credentials
    stack.setProp(YowNetworkLayer.PROP_ENDPOINT, YowConstants.ENDPOINTS[0])  # whatsapp server address
    # stack.setProp(YowCoderLayer.PROP_DOMAIN, YowConstants.DOMAIN)
    # stack.setProp(YowCoderLayer.PROP_RESOURCE, YowsupEnv.getCurrent().getResource()) #info about us as WhatsApp client

    stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))  # sending the connect signal

    stack.loop()
