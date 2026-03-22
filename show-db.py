import os
import asyncio
import aiosqlite
from pprint import pprint

DB_FOLDER = 'db'
DB_FILE = os.path.join(DB_FOLDER, 'monitor.db')

if not os.path.exists(DB_FILE):
    print("Database not found:", DB_FILE)
    exit(1)

async def search_user_or_text(query: str, limit: int = 50):
    async with aiosqlite.connect(DB_FILE) as conn:
        if query.isdigit():
            cursor = await conn.execute('''
                SELECT username, first_name, last_name, phone
                FROM messages
                WHERE user_id = ?
                LIMIT 1
            ''', (int(query),))
        elif query.startswith("@") or not query.isdigit():  
            cursor = await conn.execute('''
                SELECT username, first_name, last_name, phone
                FROM messages
                WHERE username = ?
                LIMIT 1
            ''', (query,))
        profile = await cursor.fetchone()
        await cursor.close()

        if profile:
            profile_data = {
                "username": profile[0],
                "first_name": profile[1],
                "last_name": profile[2],
                "phone": profile[3]
            }
            print("----- Profile -----")
            pprint(profile_data)
        else:
            print("No profile found for this identifier. Searching messages by text...")

        if query.isdigit() or (profile is not None):
   
            condition = "user_id = ? OR username = ?"
            params = (int(query) if query.isdigit() else 0, query)
        else:

            condition = "message_text LIKE ?"
            params = (f"%{query}%",)

        async with conn.execute(f'''
            SELECT username, first_name, last_name, message_text, group_name, datetime, message_link
            FROM messages
            WHERE {condition}
            ORDER BY datetime DESC
            LIMIT ?
        ''', params + (limit,) if isinstance(params, tuple) else (params[0], limit)) as cursor:
            messages = await cursor.fetchall()

        if not messages:
            print("No messages found for this query.")
            return

        print("\n----- Messages -----")
        for i, (username, first_name, last_name, text, group, dt, link) in enumerate(messages, 1):
            sender_name = f"{first_name or ''} {last_name or ''}".strip() or username or "(Unknown)"
            text_preview = (text[:45] + "...") if text and len(text) > 45 else text
            print(f"{i}. [{dt}] ({group}) {sender_name}: {text_preview} | Link: {link}")

if __name__ == '__main__':
    query = input("Enter user_id, username, or text to search: ")
    asyncio.run(search_user_or_text(query))
