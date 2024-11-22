import logging
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize FastAPI app
app = FastAPI()

# Telegram bot setup with aiogram
bot_token = "YOUR_BOT_TOKEN"
bot = Bot(token=bot_token, parse_mode="Markdown")  # Use "Markdown" instead of ParseMode.MARKDOWN

# Initialize Dispatcher with bot
dp = Dispatcher()

# MongoDB setup
client = AsyncIOMotorClient("mongodb+srv://itachiuchihablackcops:5412ascs@gamebot.dfp9j.mongodb.net/?retryWrites=true&w=majority&appName=GameBot")
db = client["skgamebot"]
collection = db["flappybird"]

# MongoDB connection check
async def check_mongo_connection():
    try:
        await client.admin.command('ping')
        logging.info("MongoDB connected successfully.")
    except Exception as e:
        logging.error(f"Error connecting to MongoDB: {e}")

# Define the data model
class UserData(BaseModel):
    score: int
    mongo_id: str
    first_name: str
    last_name: str
    user_id: str

# POST endpoint to update score
@app.post("/flappybird-update-score")
async def update_score(user_data: UserData):
    try:
        result = await collection.insert_one(user_data.dict())
        logging.info(f"Score updated for {user_data.user_id}")
        return {"message": "Score updated successfully", "inserted_id": str(result.inserted_id)}
    except Exception as e:
        logging.error(f"Error updating score: {e}")
        return {"message": "Error updating score", "error": str(e)}

# Function to fetch leaderboard from MongoDB (async)
async def fetch_leaderboard():
    logging.info("Fetching leaderboard from MongoDB...")
    pipeline = [
        {"$sort": {"score": -1}},
        {"$group": {"_id": "$user_id", "name": {"$first": "$first_name"}, "score": {"$max": "$score"}}},
        {"$sort": {"score": -1}},
        {"$limit": 10}
    ]
    try:
        leaderboard = await collection.aggregate(pipeline).to_list(length=10)
        logging.info(f"Leaderboard fetched successfully: {len(leaderboard)} entries")
        return leaderboard
    except Exception as e:
        logging.error(f"Error fetching leaderboard from MongoDB: {str(e)}")
        return None

# /start command handler for Telegram bot
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Welcome to the Flappy Bird Game Bot! Type /leaderboard to see the scores.")

# /leaderboard command handler for Telegram bot
@dp.message(Command("leaderboard"))
async def leaderboard(message: Message):
    try:
        logging.info("Leaderboard command received")
        
        # Fetch leaderboard asynchronously
        leaderboard_data = await fetch_leaderboard()
        
        if not leaderboard_data:
            logging.info("No leaderboard data found")
            msg = "No scores available yet."
        else:
            msg = "Flappy Bird Leaderboard:\n"
            for i, entry in enumerate(leaderboard_data):
                emoji = ""
                if i == 0:
                    emoji = "👑"
                elif i == 1:
                    emoji = "🥈"
                elif i == 2:
                    emoji = "🥉"
                
                msg += f"{i+1}. {entry['name']} {emoji} - {entry['score']}\n"
        
        # Send the message with Markdown formatting
        await message.answer(msg)
        logging.info("Leaderboard message sent")

    except Exception as e:
        logging.error(f"Error handling leaderboard command: {str(e)}")
        await message.answer(f"Error fetching leaderboard: {str(e)}")

# Run FastAPI and aiogram together
async def on_startup():
    await check_mongo_connection()

# Main entry point to start FastAPI and Telegram bot
async def main():
    loop = asyncio.get_event_loop()

    # Ensure MongoDB connection before starting the server
    await on_startup()

    # Run FastAPI in the background with Uvicorn
    loop.create_task(uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True))

    # Run aiogram bot with start_polling
    await dp.start_polling()

if __name__ == "__main__":
    # Start everything using asyncio
    asyncio.run(main())
