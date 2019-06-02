#!/bin/bash

echo '------------------'
echo ' WTT-Bridge Setup '
echo '------------------'

python_installation="ERROR"

declare -A python=( ["0"]=`python -c 'import sys; version=sys.version_info[:3]; print("{0}".format(version[0]))' || { echo "no py"; }` ["1"]=`python -c 'import sys; version=sys.version_info[:3]; print("{0}".format(version[1]))' || { echo "no py"; }` ["2"]=`python -c 'import sys; version=sys.version_info[:3]; print("{0}".format(version[2]))' || { echo "no py"; }` )
declare -A python3=( ["0"]=`python3 -c 'import sys; version=sys.version_info[:3]; print("{0}".format(version[1]))' || { echo "no py3"; }` ["1"]=`python3 -c 'import sys; version=sys.version_info[:3]; print("{0}".format(version[2]))' || { echo "no py3"; }` )

if hash python3.7 2>/dev/null; then
	python_installation="python3.7"
elif hash python3.6 2>/dev/null; then
	python_installation="python3.6"
elif hash python3 2>/dev/null; then
	if [ "${python3[1]}" -ge "5" ]; then # Python3 >= 3.6
		python_installation="python3"
	fi
elif hash python 2>/dev/null; then
	if [ "${python[0]}" -ge "3" ]; then # Python3 >= 3.6
		if [ "${python[1]}" -ge "5" ]; then # Python3 >= 3.6
			python_installation="python3"
		fi
	fi
fi

if [ "$python_installation" == "ERROR" ]; then
	echo "You are running an unsupported Python version."
	echo "Please use a version of Python above or equals 3.6"
	exit 1
fi

echo 'Creating virtual environment for python...'
eval "$python_installation -m venv __env"
source ./__env/bin/activate
eval "$python_installation -m pip install --upgrade pip"
eval "$python_installation -m pip install -r requirements.txt"
echo 'Done!'
echo ''

# 1.1) Telegram.bot_Token
echo -e 'Talk to the official Telegram \e[96m@BotFather\e[39m (\e[96m https://telegram.me/botfather \e[39m) to create a new bot.'
echo -e 'You can create a new bot by entering the command \e[33m/newbot\e[39m in the Telegram chat.'
echo 'Afterwards, you will be asked to give your bot a name. It has to be unique, we suggest something like WTT_yourname_Bot'
echo -e 'Paste the \e[4mAPI key\e[0m that you will be given here: (Shown as "Use this token to access the HTTP API")'
read bot_token
echo ''

# 1.2) Telegram.bot_username
echo -e 'Your bots \e[4musername\e[0m, without the @ symbol:'
read bot_name
echo ''

# 1.3) Telegram.api_id
echo 'You also need a so-called SelfBot, because this is the type of bot that can represent "you" and create new groups.'
echo -e 'Visit \e[96mhttps://my.telegram.org/\e[39m and login with your Telegram account.'
echo 'Under "API development tools" you can create a new app. Give any name/shortname.'
echo -e 'Enter your app \e[4mapi_id\e[0m:'
read app_id
export app_id
echo ''

# 1.4) Telegram.api_hash
echo -e 'Enter the app \e[4mapi_hash\e[0m:'
read app_hash
export app_hash

echo ''
echo 'Congratulations! We are almost done. After a quick whatsapp and telegram connectivity setup, you will be ready to rock!'
echo -e 'Find your "Mobile Country Code (\e[4mMCC\e[0m)" and "Mobile Network Code (\e[4mMNC\e[0m)" here:'
echo -e '\e[96mhttps://en.wikipedia.org/wiki/Mobile_country_code#National_operators\e[39m'
echo -e 'Find your country, remember the \e[4mMCC\e[0m and click on the link in the column Mobile Network Codes to find your \e[4mMNC\e[0m.'
echo ''
# 2.1) mcc
echo -e 'First enter your Mobile Country Code (\e[4mMCC\e[0m) (e.g. 228 for Switzerland):'
read mcc
echo ''

# 2.2) mnc
echo -e 'Enter your Mobile Network Code (\e[4mMNC\e[0m) (e.g. 02 for Sunrise in Switzerland):'
read mnc
echo ''

# 2.3) cc
echo -e 'Enter your \e[4mcountry-code\e[0m (e.g. 41 for Switzerland)'
read cc
echo ''
echo -e 'Enter your \e[4mphone number\e[0m without + or 0 at the beginning. Example: 411234567'
echo 'This is used to request a registration with the whatsapp AND telegram servers:'
read number

ensureTelethonSessionCmd="utils.ensureTelethonSession(phone=\"+$number\", app_id=$app_id, api_hash=\"$app_hash\")"
eval "$python_installation -c 'import utils;import asyncio; asyncio.get_event_loop().run_until_complete($ensureTelethonSessionCmd)'"


echo ''
echo 'Running yowsup registration...'
yowsup-cli registration --requestcode sms --config-phone $number --config-cc $cc --config-mcc $mcc --config-mnc $mnc
echo ''
echo -e 'Enter the code from whatsapp that you just received: (Looks like \e[36m123-456\e[39m, but please pass this as \e[36m123456\e[39m)'
read whatsapp_code
echo ''

echo 'Running yowsup-cli registration...'
yowsup-cli registration --register $whatsapp_code --config-phone $number

echo 'Finalizing your config.json...'
cp config_template.json config.json
sed -i -e "s/TELEGRAM_BOT_TOKEN/$bot_token/g" config.json
sed -i -e "s/TELEGRAM_BOT_NAME/$bot_name/g" config.json
sed -i -e "s/TELEGRAM_APP_ID/$app_id/g" config.json
sed -i -e "s/TELEGRAM_APP_HASH/$app_hash/g" config.json
sed -i -e "s/WHATSAPP_NUMBER/$number/g" config.json

echo -e '\e[92mSetup Successful! You can start WTT-Bridge by running:'
echo "./start.sh"
