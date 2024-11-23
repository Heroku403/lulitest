import logging 
import pymongo
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uvicorn
import telebot
from telebot.types import Message
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
import threading
import os
import re
from aiogram import Bot, types
from aiogram.filters import Command
from aiogram import Router

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

# Telegram bot setup 
bot_token = "6450878640:AAEkDXKORJvv-530GfG6OZYnZxfZgJ9f_FA"
bot = telebot.TeleBot(bot_token)

# MongoDB setup 
client = pymongo.MongoClient("mongodb+srv://itachiuchihablackcops:5412ascs@gamebot.dfp9j.mongodb.net/?retryWrites=true&w=majority&appName=GameBot")
db = client["skgamebot"]
group_collection = db.flappybird

# MongoDB connection check
def check_mongo_connection():
    try:
        client.admin.command('ping')
        logger.info("MongoDB connected successfully.")
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")

# Define the data model class
class UserData(BaseModel):
    score: int
    mongo_id: str
    first_name: str
    last_name: str
    user_id: str

# POST endpoint to update score
@app.post("/flappybird-update-score")
def update_score(user_data: UserData, background_tasks: BackgroundTasks):
    try:
        # Add task to the background queue to handle database insertion
        background_tasks.add_task(insert_score_to_db, user_data)
        return {"message": "Score update request received."}, 200  # Response with HTTP 200 status code
    except Exception as e:
        logger.error(f"Error updating score: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating score: {str(e)}")

# Background task to insert score in MongoDB
def insert_score_to_db(user_data: UserData):
    try:
        # Insert user data into MongoDB
        result = collection.insert_one(user_data.dict())
        logger.info(f"Score for {user_data.first_name} inserted with ID: {result.inserted_id}")
    except Exception as e:
        logger.error(f"Error inserting score for {user_data.first_name}: {e}")

# Start command handler for Telegram bot
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Welcome!")  # Corrected the link to use message.chat.id

# Scoreboard command handler for Telegram bot
@bot.message_handler(commands=["scoreboard", "scoreboard@game_test_robot"])
def scoreboard(message):
    if message.chat.type in ["group", "supergroup"]:
        chat_id = message.chat.id  # Use the chat ID from the message object
        pipeline = [
            {"$match": {"chat_id": chat_id}},
            {"$group": {"_id": "$user_id", "score": {"$max": "$score"}}},
            {"$sort": {"score": -1}},
            {"$limit": 5}
        ]
        top_scorers = group_collection.aggregate(pipeline)
        scorers_list = []
        for scorer in top_scorers:
            user_data = group_collection.find_one({"user_id": scorer["_id"]})
            scorers_list.append(f"{user_data['user_first_name']} - {scorer['score']}")
        bot.send_message(message.chat.id, "Top Scorers:\n" + "\n".join(scorers_list))

# GET endpoint to retrieve top scorers 
@app.get("/")
@app.get("/get-top-scorers/{chat_id}")
async def get_top_scorers(chat_id: str):
    pipeline = [
        {"$match": {"chat_id": int(chat_id)}},
        {"$group": {"_id": "$user_id", "score": {"$max": "$score"}}},
        {"$sort": {"score": -1}},
        {"$limit": 5}
    ]
    top_scorers = group_collection.aggregate(pipeline)
    scorers_list = []
    
    for scorer in top_scorers:
        user_data = group_collection.find_one({"user_id": scorer["_id"]})
        scorers_list.append({
            "user_id": scorer["_id"],
            "user_first_name": user_data["user_first_name"],
            "score": scorer["score"]
        })
    
    return {"top_scorers": scorers_list}

def run_bot():
    bot.polling()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
