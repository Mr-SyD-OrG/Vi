import random
import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot API Information from environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Channel Information from environment variables
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
GIVEAWAY_CHANNEL_USERNAME = os.getenv("GIVEAWAY_CHANNEL_USERNAME")
REQUIRED_CHANNEL_USERNAME = os.getenv("REQUIRED_CHANNEL_USERNAME")

# MongoDB URI from environment variables
DATABASE_URI = os.getenv("DATABASE_URI")
my_client = MongoClient(DATABASE_URI)
mydb = my_client["bot_database_name"]
participants = mydb["participants"]


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
    
async def is_user_in_channels(client, user_id):
    try:
        # Check if the user is a member of both channels
        is_member_giveaway = await client.get_chat_member(GIVEAWAY_CHANNEL_USERNAME, user_id)
        is_member_required = await client.get_chat_member(REQUIRED_CHANNEL_USERNAME, user_id)

        # If the user is in both channels
        if is_member_giveaway.status in ("member", "administrator", "creator") and \
           is_member_required.status in ("member", "administrator", "creator"):
            return True
        return False
    except Exception as e:
        print(f"Error checking user membership: {e}")
        return False
# --- Command Handlers ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Welcome to the Giveaway Bot!")

@app.on_message(filters.command("giveaway"))
async def giveaway(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Giveaway", callback_data="join_giveaway")]
    ])
    await client.send_message(
        chat_id=CHANNEL_ID,
        text=f"Click to join the giveaway!\n\nJoin @{GIVEAWAY_CHANNEL_USERNAME}\nJoin @{REQUIRED_CHANNEL_USERNAME}",
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
            await callback_query.answer("You already joined!", show_alert=True)
        else:
            await callback_query.answer("You're in the giveaway!", show_alert=True)

@app.on_message(filters.command("end"))
async def end_giveaway(client, message):
    try:
        number_to_pick = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.reply_text("Usage: /end <number>. Example: /end 5")
        return

    # Get all users who participated
    users = participants.find()
    participant_ids = [str(user['_id']) for user in users]

    if number_to_pick > len(participant_ids):
        await message.reply_text("Not enough participants.")
        return

    selected_ids = random.sample(participant_ids, number_to_pick)
    
    winner_text = []
    for user_id in selected_ids:
        user = await app.get_users(int(user_id))
        username = user.username if user.username else "No Username"
        winner_text.append(f"User ID: {user_id}, Username: @{username}")

    await client.send_message(CHANNEL_ID, f"Selected Winners:\n" + "\n".join(winner_text))

# --- Start the Bot ---
async def main():
    await app.start()
    print("Bot started.")
    await asyncio.Future()  # Keep the bot running

if __name__ == "__main__":
    asyncio.run(main())
