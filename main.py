import logging
import asyncio
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn
from telebot import TeleBot
from telebot.types import Message
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
import threading
import os


# Initialize FastAPI app
app = FastAPI()

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Can specify exact domains
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (including OPTIONS)
    allow_headers=["*"],  # Allow all headers
)

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot setup
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")  # It's better to store tokens in environment variables
bot = telebot.TeleBot(bot_token)

# MongoDB setup
client = AsyncIOMotorClient("mongodb+srv://itachiuchihablackcops:5412ascs@gamebot.dfp9j.mongodb.net/?retryWrites=true&w=majority&appName=GameBot")
db = client["skgamebot"]
collection = db["flappybird"]

# MongoDB connection check
async def check_mongo_connection():
    try:
        # Ping the MongoDB server to verify the connection
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
async def update_score(user_data: UserData):
    try:
        # Insert data into MongoDB collection asynchronously
        result = await collection.insert_one(user_data.dict())
        return {"message": "Score updated successfully", "inserted_id": str(result.inserted_id)}
    except Exception as e:
        logger.error(f"Error updating score: {e}")
        return {"message": "Error updating score", "error": str(e)}

# Start command handler for Telegram bot
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Welcome!")












# Function to fetch leaderboard from MongoDB (async)
async def fetch_leaderboard():
    pipeline = [
        {"$sort": {"score": -1}},
        {"$group": {
            "_id": "$user_id",
            "name": {"$first": "$first_name"},
            "score": {"$max": "$score"}
        }},
        {"$sort": {"score": -1}},
        {"$limit": 10}
    ]
    
    try:
        leaderboard = await collection.aggregate(pipeline).to_list(length=10)  # Async aggregation
        return leaderboard
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        return None

# Leaderboard command handler for Telegram bot
@bot.message_handler(commands=['leaderboard'])
async def leaderboard(message: Message):  # Make this function asynchronous
    try:
        # Use asyncio to run the async MongoDB aggregation
        leaderboard_data = await fetch_leaderboard()

        if not leaderboard_data:
            msg = "No scores available yet."
        else:
            msg = "Flappy Bird Leaderboard:\n"
            for i, entry in enumerate(leaderboard_data):
                # Adding crown and medals for top 3 players
                if i == 0:
                    emoji = "👑"  # Crown for 1st place
                elif i == 1:
                    emoji = "🥈"  # Silver for 2nd place
                elif i == 2:
                    emoji = "🥉"  # Bronze for 3rd place
                else:
                    emoji = ""  # No emoji for others
                
                msg += f"{i+1}. **{entry['name']}** {emoji} - {entry['score']}\n"

        # Send the message with MarkdownV2 formatting
        await bot.send_message(message.chat.id, msg, parse_mode="MarkdownV2")
    except Exception as e:
        await bot.send_message(message.chat.id, f"Error fetching leaderboard: {str(e)}")




















# Run the Telegram bot in a separate thread
def run_bot():
    bot.polling()

# Start the bot in a separate thread to avoid blocking FastAPI
threading.Thread(target=run_bot, daemon=True).start()

# Run FastAPI app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
