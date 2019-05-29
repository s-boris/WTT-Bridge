# WTT-Bridge (WIP)

Synchronize your conversations between Whatsapp and Telegram. 

To make it as seamless as possible, WTT-Bridge will simulate conversations on Telegram by creating a separate group chat for each Whatsapp conversation and forward all messages accordingly.
Each such Whatsapp conversation on Telegram has the prefix "[WA]" in the title.
>TODO screenshot

## Installation

1. Download WTT-Bridge:

    ```bash
    sudo apt-get install git
    git clone https://github.com/Neolysion/WTT-Bridge.git WTT-Bridge
    cd WTT-Bridge
 
    ```

2. Make sure you have at least Python 3.6 with python-dev and pip installed.
    Example for Ubuntu 16.04:
    
    ```bash
    sudo add-apt-repository ppa:jonathonf/python-3.6
    sudo apt-get update
    sudo apt-get install python3.6
    sudo apt-get install python3.6-dev
    wget https://bootstrap.pypa.io/get-pip.py
    sudo python3.6 get-pip.py
 
    ```

3. Install the libraries:
    
    ```bash
    sudo pip3.6 install -r requirements.txt
 
    ```
    
4. Check the next section on how to setup your config file. When you're done you can start the bot with:
 
     ```bash
    python3.6 run.py
 
    ```

## Configuration

You have to rename the config_template.json to config.json and fill in all the values to run the bot. Here is as some info how you can find each value:

#### Telegram: 

- "bot_token": Talk to https://telegram.me/botfather and create a bot to get a token

- "bot_username": The username you gave your bot (with the @ in front)

- "api_id" and "api_hash": Visit https://my.telegram.org/

Note: Disable privacy mode on your bot using @botfather or you won't be able to reply to Whatsapp messages in Telegram.

#### Whatsapp:

- "phone": your phone number with country code but without + or 0 at the beginning

- "client_static_keypar": to get your keypair do the following: 

1. Run ```yowsup-cli registration --requestcode sms --config-phone 49XXXXXXXXXXX --config-cc 49 --config-mcc 228 --config-mnc 02``` to start the registration. 
You can find your MMC and MNC codes here:
https://en.wikipedia.org/wiki/Mobile_country_code

2. When you receive the verification sms, run ```yowsup-cli registration --register 123456 --config-phone 49XXXXXXXX``` to verify your number.

3. If the verification was successfull you should now be able to see your client_static_keypair in the console. Copy it into the config.json 



## Notes
 
 Working:
 - Messages from Whatsapp to Telegram (text, images, video, gif, audio, ptt, document)
 - Messages from Telegram to Whatsapp (text) 
 
 
 TODO:
 - show participants
 - initiate chats from telegram
 - location (live sharing?)
 - contacts
 - Sync receipts
 - Sync group info and pictures
