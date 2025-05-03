import random
import asyncio
import os
from pyrogram import idle
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import UserNotParticipant

loop = asyncio.get_event_loop()

# Bot API Information from environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
#ADMIN = os.getenv("ADMIN")
# Channel Information from environment variables
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
GIVEAWAY_CHANNEL_USERNAME = os.getenv("GIVEAWAY_CHANNEL_USERNAME")
REQUIRED_CHANNEL_USERNAME = os.getenv("REQUIRED_CHANNEL_USERNAME")
PORT = "8080"
# MongoDB URI from environment variables
DATABASE_URI = os.getenv("DATABASE_URI")
my_client = MongoClient(DATABASE_URI)
mydb = my_client["cluster0"]
participants = mydb["participants"]
broadcast = mydb["broadcast"]

app = Client("giveaway_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# --- MongoDB ---
async def add_user(user_id):
    try:
        participants.insert_one({'_id': user_id})
        return True
    except DuplicateKeyError:
        return False

async def get_user_count():
    return participants.count_documents({})

async def delete_user_data():
    participants.delete_many({})

async def get_broadcast_channels():
    channels = broadcast.find()
    return [doc["_id"] for doc in channels]
    
async def add_broadcast_channel(channel_id: int):
    try:
        broadcast.insert_one({"_id": channel_id})
        return True
    except DuplicateKeyError:
        return False
async def is_user_in_channels(bot, user_id):
    try:
        giveaway = await bot.get_chat_member(GIVEAWAY_CHANNEL_USERNAME, user_id)
        required = await bot.get_chat_member(REQUIRED_CHANNEL_USERNAME, user_id)

    except UserNotParticipant:
        pass
    except Exception as e:
        print(f"Error checking user membership: {e}")
    else:
        if giveaway.status != ChatMemberStatus.BANNED and required.status != ChatMemberStatus.BANNED:
            return True

    return False

# --- Command Handlers ---
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text("Welcome to the Giveaway Bot!")

@app.on_message(filters.command("giveaway"))
async def giveaway(client, message):
    user_id = message.from_user.id

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Giveaway", callback_data="join_giveaway")]
    ])
    # Check if the user is in both channels
    
    
    await client.send_message(
        chat_id=b_id,
        text=(
            f"Please Join Both Channels First To Participate ☺️:\n\n"
            f"@{GIVEAWAY_CHANNEL_USERNAME}\n"
            f"@{REQUIRED_CHANNEL_USERNAME}"
        ),
        reply_markup=keyboard
    )


@app.on_callback_query(filters.regex("join_giveaway"))
async def join_giveaway_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    is_in_both_channels = await is_user_in_channels(client, user_id)

    if not is_in_both_channels:
        await callback_query.answer(
            text=f"Please join both channels to participate ☺️",
            show_alert=True
        )
    else:
        added = await add_user(user_id)
        if not added:
            await callback_query.answer("You have already joined!", show_alert=True)
        else:
            await callback_query.answer("You're in the giveaway!", show_alert=True)

@app.on_message(filters.command("end"))
async def end_giveaway(client, message):
    try:
        number_to_pick = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.reply_text("Usage: /end <number>. Example: /end 5")
        return

    users = participants.find()
    participant_ids = [str(user['_id']) for user in users]
    total_users = len(participant_ids)

    valid_ids = []
    for user_id in participant_ids:
        try:
            in_giveaway = await is_user_in_channels(client, int(user_id))
           # in_required = await is_user_in_channels(client, int(user_id), REQUIRED_CHANNEL_ID, REQUIRED_CHANNEL_USERNAME)

            if in_giveaway: #and in_required:
                valid_ids.append(user_id)
            else:
                await delete_user(int(user_id))  # Remove from DB
        except Exception as e:
            print(f"Error checking user {user_id}: {e}")
            continue

    valid_count = len(valid_ids)

    if number_to_pick > valid_count:
        await message.reply_text(f"Not enough valid participants (have: {valid_count}).")
        return

    random.shuffle(valid_ids)
    selected_ids = random.sample(valid_ids, number_to_pick)

    winner_text = []
    for user_id in selected_ids:
        try:
            user = await app.get_users(int(user_id))
            username = f"@{user.username}" if user.username else "No Username"
            winner_text.append(f"User ID: {user_id}, Username: {username}")
        except Exception:
            winner_text.append(f"User ID: {user_id}, Username: Unknown")

    await client.send_message(
        CHANNEL_ID,
        f"Total Participants: {total_users}\n"
        f"Valid Participants: {valid_count}\n\n"
        f"Selected Winners:\n" + "\n".join(winner_text)
    )
    await delete_user_data()
    
@app.on_message(filters.command("bc"))
async def end_giveaway(client, message):
    try:
        channel_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.reply_text("Usage: /bc <id>. Example: /id -100xxxxxx5")
        return
    added = await add_broadcast_channel(channel_id)
    if added:
        await message.reply_text("Channel added to broadcast list.")
    else:
        await message.reply_text("Channel already exists.")


# --- Web Server (Optional) ---
async def web_handler(request):
    return web.Response(text="Giveaway bot running.")

async def web_server():
    app_web = web.Application()
    app_web.add_routes([web.get("/", web_handler)])
    return app_web

# --- Start the Bot ---
async def main():
    print("Starting bot...")
    
    print("Bot started.")
    
    print("Web server started.")
    await app.start()
    runner = web.AppRunner(await web_server())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await idle()  # Keeps the bot running until manually stopped
    await app.stop()
    print("Bot stopped.")
#----------------------

if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print('Service Stopped Bye 👋')
