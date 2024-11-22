import logging
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uvicorn
from aiogram import Bot, types
from aiogram.filters import Command
from aiogram.utils.markdown import ParseMode
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.utils import executor
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
import os
import threading

# Initialize FastAPI app
app = FastAPI()

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot setup (using aiogram 3.15.0)
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=bot_token)
router = Router()

# MongoDB setup
client = AsyncIOMotorClient("mongodb+srv://itachiuchihablackcops:5412ascs@gamebot.dfp9j.mongodb.net/?retryWrites=true&w=majority&appName=GameBot")
db = client["skgamebot"]
collection = db["flappybird"]

# MongoDB connection check
async def check_mongo_connection():
    try:
        await client.admin.command('ping')
        logger.info("MongoDB connected successfully.")
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")

# Define the data model
class UserData(BaseModel):
    score: int
    mongo_id: str
    first_name: str
    last_name: str
    user_id: str

# POST endpoint to update score
@app.post("/flappybird-update-score")
async def update_score(user_data: UserData, background_tasks: BackgroundTasks):
    try:
        # Add task to the background queue to handle database insertion
        background_tasks.add_task(insert_score_to_db, user_data)
        return {"message": "Score update request received."}, 200  # Response with HTTP 200 status code
    except Exception as e:
        logger.error(f"Error updating score: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating score: {str(e)}")

# Background task to insert score in MongoDB
async def insert_score_to_db(user_data: UserData):
    try:
        # Insert user data into MongoDB
        result = await collection.insert_one(user_data.dict())
        logger.info(f"Score for {user_data.first_name} inserted with ID: {result.inserted_id}")
    except Exception as e:
        logger.error(f"Error inserting score for {user_data.first_name}: {e}")

# Command handler for /start
@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Welcome!")

# Function to fetch leaderboard from MongoDB (async)
async def fetch_leaderboard():
    pipeline = [
        {"$sort": {"score": -1}},
        {"$group": {"_id": "$user_id", "name": {"$first": "$first_name"}, "score": {"$max": "$score"}}},
        {"$sort": {"score": -1}},
        {"$limit": 10}
    ]
    try:
        leaderboard = await collection.aggregate(pipeline).to_list(length=10)
        return leaderboard
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        return None

# Command handler for /leaderboard
@router.message(Command("leaderboard"))
async def leaderboard(message: types.Message):
    try:
        leaderboard_data = await fetch_leaderboard()
        if not leaderboard_data:
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
        await message.answer(msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await message.answer(f"Error fetching leaderboard: {str(e)}")

# Bot setup
async def on_start():
    bot.router.include_router(router)

# Run the Telegram bot in a separate thread
def run_bot():
    asyncio.run(on_start())
    from aiogram import executor
    executor.start_polling(bot)

# Start the bot in a separate thread to avoid blocking FastAPI
threading.Thread(target=run_bot, daemon=True).start()

# Run FastAPI app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000, reload=True)
