import os
import json

dir_path = os.path.dirname(os.path.realpath(__file__))
chatmap_path = dir_path + '/chatmap.json'

with open(dir_path + '/config.json', 'r') as f:
    config = json.load(f)


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
