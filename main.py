import logging
import asyncio
import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uvicorn
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from motor.motor_asyncio import AsyncIOMotorClient
from threading import Thread

# Initialize FastAPI app
app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot setup using python-telegram-bot
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

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

# Define the data model for the user score
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
        # Add task to background queue to handle database insertion
        background_tasks.add_task(insert_score_to_db, user_data)
        return {"message": "Score update request received."}, 200
    except Exception as e:
        logger.error(f"Error updating score: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating score: {str(e)}")

# Background task to insert score in MongoDB
async def insert_score_to_db(user_data: UserData):
    try:
        result = await collection.insert_one(user_data.dict())
        logger.info(f"Score for {user_data.first_name} inserted with ID: {result.inserted_id}")
    except Exception as e:
        logger.error(f"Error inserting score for {user_data.first_name}: {e}")

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
        return []

# Command handler for /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Welcome!")

# Command handler for /leaderboard
async def leaderboard(update: Update, context: CallbackContext) -> None:
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
        
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error fetching leaderboard: {str(e)}")

# Run the Telegram bot asynchronously
async def run_telegram_bot():
    # Initialize the bot application
    application = Application.builder().token(bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("leaderboard", leaderboard))

    # Start polling the bot (this will run asynchronously)
    await application.run_polling()

# Main entry function to run FastAPI and Telegram bot
async def main():
    # Start FastAPI in the background using uvicorn
    from fastapi import FastAPI
    import uvicorn

    # Run FastAPI app in the background using threading
    def start_fastapi():
        uvicorn.run(app, host="0.0.0.0", port=10000)

    fastapi_thread = Thread(target=start_fastapi)
    fastapi_thread.daemon = True
    fastapi_thread.start()

    # Run the Telegram bot in the same event loop as FastAPI
    await run_telegram_bot()

# Entry point for running the app
if __name__ == "__main__":
    # Start the FastAPI app and Telegram bot with asyncio
    asyncio.run(main())
