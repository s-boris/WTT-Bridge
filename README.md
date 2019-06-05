# WTT-Bridge

Synchronize your conversations between Whatsapp and Telegram. 

To make it as seamless as possible, WTT-Bridge will simulate conversations on Telegram by creating a separate group chat for each Whatsapp conversation and forward all messages accordingly.
Each such Whatsapp conversation on Telegram has the prefix "[WA]" in the title.

> TODO screenshot

## Installation

1. Download WTT-Bridge:
   
   ```bash
    sudo apt-get install git
    git clone https://github.com/Neolysion/WTT-Bridge.git WTT-Bridge
    cd WTT-Bridge
   ```

2. Make sure you have at least Python 3.6 with python-dev, pip and venv installed.
   Example for Ubuntu 16.04:
   
   ```bash
    sudo add-apt-repository ppa:jonathonf/python-3.6
    sudo apt-get update
    sudo apt-get install python3.6 python3.6-dev python3.6-venv
    wget https://bootstrap.pypa.io/get-pip.py
    sudo python3.6 get-pip.py
   ```

3. Run `./setup.sh` to start the setup assistant.

   **Note:** After the setup disable privacy mode on your bot using [@BotFather](https://telegram.me/botfather) or you won't be able to reply to Whatsapp messages.

## Notes

 Working:
- Messages from Whatsapp to Telegram (text, images, video, gif, audio, ptt, document, url)
- Messages from Telegram to Whatsapp (text) 
- Update contact pictures
- Update group titles (Whatsapp to Telegram only)
- Show participants
  
TODO:
- initiate chats from telegram
- location (live sharing?)
- Sync group info and pictures
- Sync profile picture
- Sync receipts

