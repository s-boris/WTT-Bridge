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

__Working__:
- Messages from Whatsapp to Telegram (Supported: text, image, video, gif, audio, ptt, document, url, location, contact)
- Messages from Telegram to Whatsapp (Supported: text) 
- Sync contact pictures (on startup)
- Sync group titles & pictures (on startup, Whatsapp to Telegram only)
- Show participants (phone numbers only)
  
  
    
__TODOs__:

High Priority:
- Support for missing media
- Resolve participant names
- Full group title and picture sync
- Initiate chats from telegram
- Support for quoted messages

Low Priority:
- Sync owner profile picture
- Support for deleting messages
- Sync receipts 
- Sync online presence
- Support for stickers

