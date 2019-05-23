import os
import json

dir_path = os.path.dirname(os.path.realpath(__file__))

with open(dir_path + '/config.json', 'r') as f:
    config = json.load(f)


def get_tg_config():
    return config['Telegram']


def get_wa_config():
    return config['Whatsapp']
