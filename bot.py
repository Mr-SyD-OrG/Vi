import random
import asyncio
import os
from aiohttp import web
from pyrogram.idle import idle
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError


# Bot API Information from environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
#ADMIN = os.getenv("ADMIN")
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

    users = participants.find()
    participant_ids = [str(user['_id']) for user in users]
    total_users = len(participant_ids)

    valid_ids = []
    for user_id in participant_ids:
        try:
            in_giveaway = await is_user_in_channels(client, int(user_id), GIVEAWAY_CHANNEL_ID, GIVEAWAY_CHANNEL_USERNAME)
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


# --- Web Server (Optional) ---
async def web_handler(request):
    return web.Response(text="Giveaway bot running.")

async def run_web():
    app_web = web.Application()
    app_web.add_routes([web.get("/", web_handler)])
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()

# --- Start the Bot ---
async def main():
    print("Starting bot...")
    await app.start()
    print("Bot started.")
    await run_web()
    print("Web server started.")


    await idle()  # Keeps the bot running until manually stopped
    await app.stop()
    print("Bot stopped.")
#----------------------

if __name__ == "__main__":
    asyncio.run(main())
