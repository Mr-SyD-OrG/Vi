import os
import random
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import FloodWait

API_ID = 26320112
API_HASH = "73adebcbc5ae76e8f66f3d848359ebe1"
BOT_TOKEN = "8163418521:AAFbLakx4_DDCfsBfGPguoc07GjVCxfhHzM"

CHANNEL_ID = -1002189391854
GIVEAWAY_CHANNEL_USERNAME = "KLandGiveAway"
REQUIRED_CHANNEL_USERNAME = "DumbCoconut"

PARTICIPANTS_FILE = "participants.txt"
first_round_numbers = []

app = Client("giveaway_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def add_participant(user_id):
    with open(PARTICIPANTS_FILE, "a") as f:
        f.write(str(user_id) + "\n")

def is_participant(user_id):
    if not os.path.exists(PARTICIPANTS_FILE):
        return False
    with open(PARTICIPANTS_FILE, "r") as f:
        return str(user_id) in f.read().splitlines()

def get_participant_count():
    if not os.path.exists(PARTICIPANTS_FILE):
        return 0
    with open(PARTICIPANTS_FILE, "r") as f:
        return len(f.read().splitlines())

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
        text=f"Click to join the giveaway!\n\nJoin @{GIVEAWAY_CHANNEL_USERNAME}\nJoin @{REQUIRED_CHANNEL_USERNAME}\n\nParticipants: {get_participant_count()}",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex("join_giveaway"))
async def join_giveaway_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if is_participant(user_id):
        await callback_query.answer("You already joined!", show_alert=True)
    else:
        add_participant(user_id)
        await callback_query.answer("You're in the giveaway!", show_alert=True)

@app.on_message(filters.command("random"))
async def random_numbers(client, message):
    global first_round_numbers
    try:
        number_to_pick = int(message.text.split()[1])
    except:
        await message.reply_text("Usage: /random <number>")
        return

    if not os.path.exists(PARTICIPANTS_FILE):
        await message.reply_text("No participants yet.")
        return

    with open(PARTICIPANTS_FILE) as f:
        participants = f.read().splitlines()

    if number_to_pick > len(participants):
        await message.reply_text("Not enough participants.")
        return

    first_round_numbers = random.sample([int(pid) for pid in participants], number_to_pick)
    await client.send_message(CHANNEL_ID, f"Winners: {', '.join(map(str, first_round_numbers))}")

@app.on_message(filters.command("pick"))
async def pick_numbers(client, message):
    global first_round_numbers
    if not first_round_numbers:
        await message.reply_text("Use /random first.")
        return
    try:
        number_to_pick = int(message.text.split()[1])
    except:
        await message.reply_text("Usage: /pick <number>")
        return

    if number_to_pick > len(first_round_numbers):
        await message.reply_text("Not enough winners in first round.")
        return

    picked = random.sample(first_round_numbers, number_to_pick)
    await client.send_message(CHANNEL_ID, f"Final picks: {', '.join(map(str, picked))}")

# Web server to keep Koyeb app alive
async def web_handler(request):
    return web.Response(text="Bot is running!")

async def run_web():
    app_web = web.Application()
    app_web.add_routes([web.get("/", web_handler)])
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()

async def main():
    await app.start()
    print("Bot started.")
    await asyncio.gather(
        run_web(),
        asyncio.Future()
    )

if __name__ == "__main__":
    asyncio.run(main())
