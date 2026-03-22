import telebot
import sqlite3
import logging
from telebot import types
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import threading
import asyncio,os,json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TELEGRAM_TOKEN = 'Token Bot'
DB_FILE = 'db/monitor.db'
ADMIN_ID = 123456789
MAX_LIMIT = 50
bot = telebot.TeleBot(TELEGRAM_TOKEN)
ACCOUNTS_FOLDER = 'accounts'
os.makedirs(ACCOUNTS_FOLDER, exist_ok=True)
ACCOUNTS_FILE = os.path.join(ACCOUNTS_FOLDER, 'accounts.json')
user_steps = {}  
search_cache = {} 
cooldowns = {}
logging.basicConfig(level=logging.INFO)

def check_admin_permission(user_id):
    return user_id == ADMIN_ID  

def rate_limit(user_id):
    import time
    now = time.time()
    if user_id in cooldowns and now - cooldowns[user_id] < 2:
        return False
    cooldowns[user_id] = now
    return True

def send_long_message(chat_id, text, reply_markup=None):
    MAX_LENGTH = 4000 
    
    for i in range(0, len(text), MAX_LENGTH):
        chunk = text[i:i + MAX_LENGTH]
        bot.send_message(
            chat_id,
            chunk,
            parse_mode="HTML",
            reply_markup=reply_markup if i == 0 else None
        )

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id

    if message.chat.type == 'private':
        markup = types.InlineKeyboardMarkup()
        help_button = types.InlineKeyboardButton("Help", callback_data="help")
        search_text_button = types.InlineKeyboardButton("Search by Text", callback_data="search_text")
        search_id_button = types.InlineKeyboardButton("Search by ID", callback_data="search_id")

        if check_admin_permission(user_id):
            panel_button = types.InlineKeyboardButton("Panel", callback_data="panel")
            markup.add(help_button, search_text_button, search_id_button, panel_button)
        else:
            markup.add(help_button, search_text_button, search_id_button)

        bot.reply_to(message, "Welcome to the Scraper Bot! Choose an option:", reply_markup=markup)
    else:
        bot.reply_to(message, "Welcome! Please use /search or /text commands to search messages.")

@bot.callback_query_handler(func=lambda call: call.data == "help")
def handle_help(call):

    help_text = (
        "This bot allows you to search for messages in a database.\n\n"
        "You can search by text or by user ID.\n\n"
        "Commands:\n"
        "/text <query> <limit> - Search messages by text (e.g., /text Hello 10)\n"
        "/search <@username or chat_id> <limit> - Search messages from a specific user or chat (e.g., /search @username 10)\n\n"
        "Choose an option below to start searching."
    )
    
    markup = types.InlineKeyboardMarkup()
    back_button = types.InlineKeyboardButton("Back", callback_data="back_to_main")
    markup.add(back_button)

    bot.edit_message_text(help_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = (
        "This bot allows you to search for messages in a database.\n\n"
        "You can search by text or by user ID.\n\n"
        "Commands:\n"
        "/text <query> <limit> - Search messages by text (e.g., /text Hello 10)\n"
        "/search <@username or chat_id> <limit> - Search messages from a specific user or chat (e.g., /search @username 10)\n\n"
        "Choose an option below to start searching."
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['text'])
def search_text_cmd(message):
    if not rate_limit(message.from_user.id):
        return

    try:
        parts = message.text.split(' ', 2)
        query = parts[1]
        limit = int(parts[2]) if len(parts) > 2 else 10
        limit = min(limit, MAX_LIMIT)

        results = search_text_messages(query, limit)
        search_cache[message.from_user.id] = {
            "type": "text",
            "query": query,
            "limit": limit,
            "offset": 0
        }

        if results:
            bot.send_message(
                message.chat.id,
                format_results(results, query),
                parse_mode='HTML',
                reply_markup=pagination_keyboard(message.from_user.id)
            )
        else:
            bot.send_message(message.chat.id, "❌ No results found.")

    except Exception as e:
        logging.error(str(e))
        bot.send_message(message.chat.id, "Error occurred.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("next_", "prev_")))
def handle_pagination(call):
    user_id = int(call.data.split("_")[1])

    if user_id not in search_cache:
        return

    data = search_cache[user_id]

    if call.data.startswith("next_"):
        data["offset"] += data["limit"]
    else:
        data["offset"] = max(0, data["offset"] - data["limit"])

    if data["type"] == "text":
        results = search_text_messages(data["query"], data["limit"], data["offset"])
    else:
        results = search_user_messages(data["query"], data["limit"], data["offset"])

    if results:
        bot.edit_message_text(
            format_results(results, data["query"]),
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=pagination_keyboard(user_id)
        )


@bot.message_handler(commands=['search'])
def search_by_user_command(message):
    try:
        parts = message.text.split(' ', 2)
        user_identifier = parts[1]
        limit = int(parts[2]) if len(parts) > 2 else 10
        limit = min(limit, MAX_LIMIT)
        results = search_user_messages(user_identifier, limit)

        if results:
            response = f"Found {len(results)} messages for '{user_identifier}':\n\n"
            for idx, (username, first_name, last_name, message_text, message_link, group_name) in enumerate(results):
                user_display = username if username else (f"{first_name or ''} {last_name or ''}" if first_name or last_name else 'None')
                response += f"{idx + 1}. {user_display}: {message_text}\n"
                response += f"Link: <a href='{message_link}'>Click here</a>\nGroup: {group_name}\n\n"
            
            bot.send_long_message(message.chat.id, response)
        else:
            bot.send_message(message.chat.id, f"No results found for '{user_identifier}'.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "search_text")
def search_by_text(call):
    msg = bot.send_message(call.message.chat.id, "Enter the text you want to search for:")
    bot.register_next_step_handler(msg, handle_text_query)

def handle_text_query(message):
    query = message.text
    msg = bot.send_message(message.chat.id, "How many results would you like to see? (Default: 10)")
    bot.register_next_step_handler(msg, handle_text_limit, query)

def handle_text_limit(message, query):
    try:
        limit = int(message.text)
    except ValueError:
        limit = 10  

    results = search_text_messages(query, limit)

    if results:
        response = f"Found {len(results)} results for '{query}':\n\n"
        for idx, (username, first_name, last_name, message_text, message_link, group_name) in enumerate(results):
            user_display = username if username else (f"{first_name or ''} {last_name or ''}" if first_name or last_name else 'None')
            response += f"{idx + 1}. {user_display}: {message_text}\n"
            response += f"Link: <a href='{message_link}'>Click here</a>\nGroup: {group_name}\n\n"
        
        bot.send_long_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, f"No results found for '{query}'.")

@bot.callback_query_handler(func=lambda call: call.data == "search_id")
def search_by_id(call):
    msg = bot.send_message(call.message.chat.id, "Enter the username (@username) or chat ID you want to search for:")
    bot.register_next_step_handler(msg, handle_id_query)

def handle_id_query(message):
    user_identifier = message.text
    msg = bot.send_message(message.chat.id, "How many results would you like to see? (Default: 10)")
    bot.register_next_step_handler(msg, handle_id_limit, user_identifier)

def handle_id_limit(message, user_identifier):
    try:
        limit = int(message.text)
    except ValueError:
        limit = 10  

    results = search_user_messages(user_identifier, limit)

    if results:
        response = f"Found {len(results)} messages for '{user_identifier}':\n\n"
        for idx, (username, first_name, last_name, message_text, message_link, group_name) in enumerate(results):
            user_display = username if username else (f"{first_name or ''} {last_name or ''}" if first_name or last_name else 'None')
            response += f"{idx + 1}. {user_display}: {message_text}\n"
            response += f"Link: <a href='{message_link}'>Click here</a>\nGroup: {group_name}\n\n"
        
        bot.send_long_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, f"No results found for '{user_identifier}'.")

@bot.callback_query_handler(func=lambda call: call.data == "panel")
def panel(call):
    if not check_admin_permission(call.from_user.id):
        return

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Add Account", callback_data="add_accounts"))
    kb.add(InlineKeyboardButton("📄 List Accounts", callback_data="list_accounts"))
    kb.add(InlineKeyboardButton("📊 Stats", callback_data="stats"))
    bot.send_message(call.message.chat.id, "Admin Panel", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats(call):
    if not check_admin_permission(call.from_user.id):
        return
    total = get_stats()
    bot.send_message(call.message.chat.id, f"📊 Total Messages in DB: {total}")

def format_results(results, query):
    response = f"🔎 Results for: {query}\n\n"
    for idx, (username, first_name, last_name, message_text, message_link, group_name) in enumerate(results, 1):
        user_display = username if username else (f"{first_name or ''} {last_name or ''}".strip() or "None")
        response += f"{idx}. {user_display}: {message_text[:200]}\n"
        response += f"<a href='{message_link}'>Link</a> | {group_name}\n\n"
    return response

def pagination_keyboard(user_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("⬅ Prev", callback_data=f"prev_{user_id}"),
        InlineKeyboardButton("Next ➡", callback_data=f"next_{user_id}")
    )
    return kb

def search_text_messages(query, limit=10, offset=0):
    limit = min(limit, MAX_LIMIT)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT username, first_name, last_name, message_text, message_link, group_name
        FROM messages
        WHERE message_text LIKE ?
        ORDER BY datetime DESC
        LIMIT ? OFFSET ?
    ''', ('%' + query + '%', limit, offset))
    results = cursor.fetchall()
    conn.close()
    return results

def search_user_messages(user_identifier, limit=10, offset=0):
    limit = min(limit, MAX_LIMIT)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if user_identifier.startswith('@'):
        cursor.execute('''
            SELECT username, first_name, last_name, message_text, message_link, group_name
            FROM messages
            WHERE username = ?
            ORDER BY datetime DESC
            LIMIT ? OFFSET ?
        ''', (user_identifier[1:], limit, offset))
    else:
        cursor.execute('''
            SELECT username, first_name, last_name, message_text, message_link, group_name
            FROM messages
            WHERE group_id = ?
            ORDER BY datetime DESC
            LIMIT ? OFFSET ?
        ''', (user_identifier, limit, offset))

    results = cursor.fetchall()
    conn.close()
    return results

def get_stats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages")
    total = cursor.fetchone()[0]
    conn.close()
    return total


def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return {"accounts": []}
    with open(ACCOUNTS_FILE, 'r') as f:
        return json.load(f)

def save_accounts(data):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Add Account", callback_data="add_accounts"))
    kb.add(InlineKeyboardButton("📄 List Accounts", callback_data="list_accounts"))
    return kb

telethon_loop = asyncio.new_event_loop()

def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

t = threading.Thread(target=start_loop, args=(telethon_loop,), daemon=True)
t.start()

async def telethon_send_code(phone, api_id, api_hash, state):
    session_file = f"session_{phone.replace('+','')}"
    client = TelegramClient(os.path.join(ACCOUNTS_FOLDER, session_file), api_id, api_hash, loop=telethon_loop)
    await client.connect()
    await client.send_code_request(phone)
    state["client"] = client

async def telethon_finish_login(state, code, password=None):
    client = state["client"]

    if password:
        await client.sign_in(password=password)
    else:
        try:
            await client.sign_in(state["phone"], code)
        except SessionPasswordNeededError:
            state["need_password"] = True
            return "PASSWORD_REQUIRED"

    me = await client.get_me()

    name = me.username if me.username else me.first_name if me.first_name else "nop"

    data = load_accounts()
    account_info = {
        "name": name,
        "id": me.id,
        "phone": state["phone"],
        "api_id": state["api_id"],
        "api_hash": state["api_hash"],
        "session_file": f"session_{state['phone'].replace('+','')}"
    }

    data["accounts"].append(account_info)
    save_accounts(data)

    await client.disconnect()
    return "OK"

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    user_id = call.from_user.id
    if not check_admin_permission(user_id):
        return
    if call.data == "add_accounts":
        user_steps[user_id] = {"step": "phone"}
        bot.send_message(call.message.chat.id, "📱 Send phone number with +")

    elif call.data == "list_accounts":
        data = load_accounts()
        accounts = data.get("accounts", [])
        if not accounts:
            bot.send_message(call.message.chat.id, "❌ No accounts found")
            return

        msg = "📄 Accounts List:\n\n"
        kb = InlineKeyboardMarkup()

        for i, a in enumerate(accounts, 1):
            status_emoji = "✅" if a.get("status", True) else "❌"
            msg += f"{i}) {a['phone']} | {a['name']} | {a['id']} | {status_emoji}\n"

            kb.add(InlineKeyboardButton(f"{status_emoji} Toggle {a['name']}", callback_data=f"toggle_{i-1}"))

        send_long_message(call.message.chat.id, msg, reply_markup=kb)

    elif call.data.startswith("toggle_"):
        idx = int(call.data.split("_")[1])
        data = load_accounts()
        accounts = data.get("accounts", [])

        if 0 <= idx < len(accounts):
            accounts[idx]["status"] = not accounts[idx].get("status", True)
            save_accounts(data)
            status_emoji = "✅" if accounts[idx]["status"] else "❌"
            bot.answer_callback_query(call.id, f"Status changed to {status_emoji}")

            bot.delete_message(call.message.chat.id, call.message.message_id)
            call.data = "list_accounts"
            callbacks(call)
            
@bot.message_handler(func=lambda m: True)
def steps(msg):
    user_id = msg.from_user.id
    text = msg.text

    if user_id not in user_steps:
        return

    state = user_steps[user_id]
    step = state["step"]

    if step == "phone":
        state["phone"] = text
        state["step"] = "api_id"
        bot.send_message(msg.chat.id, "🔑 Send API ID:")

    elif step == "api_id":
        try:
            state["api_id"] = int(text)
        except:
            bot.send_message(msg.chat.id, "❌ API ID must be number")
            return
        state["step"] = "api_hash"
        bot.send_message(msg.chat.id, "🧩 Send API HASH:")

    elif step == "api_hash":
        state["api_hash"] = text
        state["step"] = "code"
        bot.send_message(msg.chat.id, "📩 Sending login code...")

        fut = asyncio.run_coroutine_threadsafe(
            telethon_send_code(state["phone"], state["api_id"], state["api_hash"], state),
            telethon_loop
        )

        bot.send_message(msg.chat.id, "✉️ Send login code:")

    elif step == "code":
        code = text

        fut = asyncio.run_coroutine_threadsafe(
            telethon_finish_login(state, code),
            telethon_loop
        )

        result = fut.result()

        if result == "PASSWORD_REQUIRED":
            state["step"] = "password"
            bot.send_message(msg.chat.id, "🔐 Two-step verification enabled\nSend account password:")
            return

        bot.send_message(msg.chat.id, "✅ Account added successfully!", reply_markup=main_menu())
        user_steps.pop(user_id)

    elif step == "password":
        password = text

        fut = asyncio.run_coroutine_threadsafe(
            telethon_finish_login(state, code=None, password=password),
            telethon_loop
        )

        fut.result()

        bot.send_message(msg.chat.id, "✅ Account added successfully!", reply_markup=main_menu())
        user_steps.pop(user_id)


bot.polling(non_stop=True)
