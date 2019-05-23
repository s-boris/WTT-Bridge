from src.whatsapp_layer import WhatsappLayer
from yowsup.layers import YowParallelLayer
from yowsup.layers.auth import YowAuthenticationProtocolLayer
from yowsup.layers.protocol_messages import YowMessagesProtocolLayer
from yowsup.layers.protocol_receipts import YowReceiptProtocolLayer
from yowsup.layers.protocol_acks import YowAckProtocolLayer
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.coder import YowCoderLayer
from yowsup.stacks import YowStack
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent
from yowsup.stacks import YowStack, YOWSUP_CORE_LAYERS
from yowsup.layers.axolotl import AxolotlControlLayer, AxolotlSendLayer, AxolotlReceivelayer
from yowsup.env import YowsupEnv

msg_q = None
CREDENTIALS = None


def run(q, config):
    global msg_q, CREDENTIALS
    msg_q = q
    CREDENTIALS = (config["phone"], config["password"])

    layers = (
                 WhatsappLayer,
                 YowParallelLayer([YowAuthenticationProtocolLayer, YowMessagesProtocolLayer, YowReceiptProtocolLayer,
                                   YowAckProtocolLayer]),
                 AxolotlControlLayer,
                 YowParallelLayer((AxolotlSendLayer, AxolotlReceivelayer)),
             ) + YOWSUP_CORE_LAYERS

    stack = YowStack(layers)
    stack.setProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS, CREDENTIALS)  # setting credentials
    stack.setProp(YowNetworkLayer.PROP_ENDPOINT, YowConstants.ENDPOINTS[0])  # whatsapp server address
    # stack.setProp(YowCoderLayer.PROP_DOMAIN, YowConstants.DOMAIN)
    # stack.setProp(YowCoderLayer.PROP_RESOURCE, YowsupEnv.getCurrent().getResource()) #info about us as WhatsApp client

    stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))  # sending the connect signal

    stack.loop()  # this is the program mainloop
