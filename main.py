import logging 
import pymongo
from pymongo.errors import PyMongoError
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
collection = db["flappybird"]

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
    bot.send_message(message.chat.id, "Welcome!!")  # Corrected the link to use message.chat.id

# Scoreboard command handler for Telegram bot
@bot.message_handler(commands=["scoreboard", "scoreboard@yterhbot"])
def scoreboard(message):
    if message.chat.type in ["group", "supergroup"]:
        chat_id = message.chat.id  # Use the chat ID from the message object
        
        # Pipeline to get the top 10 scorers
        pipeline = [
            {"$match": {"chat_id": chat_id}},  # Match the chat_id
            {"$group": {"_id": "$user_id", "score": {"$max": "$score"}}},  # Group by user_id and get the highest score
            {"$sort": {"score": -1}},  # Sort by score in descending order
            {"$limit": 10}  # Limit to the top 10 scorers
        ]

        try:
            top_scorers = group_collection.aggregate(pipeline)
            scorers_list = []
            requesting_user = str(message.from_user.id)  # Get the user ID of the person who requested the scoreboard
            rank_of_requesting_user = None
            score_of_requesting_user = None

            # Loop through the top scorers and format the message
            for idx, scorer in enumerate(top_scorers):
                # Fetch user data for each scorer (first name, last name, etc.)
                user_data = group_collection.find_one({"user_id": scorer["_id"]})
                if user_data:
                    rank = idx + 1
                    score = int(scorer["score"])  # Ensure score is treated as an integer

                    # Add emojis for the top 3 users
                    if rank == 1:
                        emoji = "🥇"
                    elif rank == 2:
                        emoji = "🥈"
                    elif rank == 3:
                        emoji = "🥉"
                    else:
                        emoji = ""

                    # Add to the scorers list
                    scorers_list.append(f"{user_data['first_name']} {emoji} - {score}")

                    # Check if the requesting user is in the top 10
                    if str(scorer["_id"]) == requesting_user:
                        rank_of_requesting_user = rank
                        score_of_requesting_user = score

            # Handle the case where the requesting user is not in the top 10
            if rank_of_requesting_user is None:
                # Fetch the user's rank and score if they're not in the top 10
                user_data = group_collection.find_one({"user_id": requesting_user})
                if user_data:
                    score_of_requesting_user = user_data["score"]
                    # Find the rank of the requesting user
                    user_rank_pipeline = [
                        {"$match": {"chat_id": chat_id}},  # Match the chat_id
                        {"$group": {"_id": "$user_id", "score": {"$max": "$score"}}},  # Group by user_id and get the highest score
                        {"$sort": {"score": -1}}  # Sort by score in descending order
                    ]
                    rank_data = group_collection.aggregate(user_rank_pipeline)
                    rank_of_requesting_user = sum(1 for r in rank_data if r["_id"] == requesting_user) + 1

            # Send the top scorers list
            bot.send_message(message.chat.id, "Top 10 Scorers:\n" + "\n".join(scorers_list))
            
            # Add a blank line
            bot.send_message(message.chat.id, "\n")

            # If the requesting user is not in the top 10, display their rank and score
            if rank_of_requesting_user is not None:
                bot.send_message(
                    message.chat.id,
                    f"Your Rank: #{rank_of_requesting_user} with a score of {score_of_requesting_user}",
                )
            else:
                bot.send_message(
                    message.chat.id,
                    f"Your score is {score_of_requesting_user}. You are not in the top 10.",
                )

        except Exception as e:
            bot.send_message(message.chat.id, f"Error fetching scoreboard: {str(e)}")

@app.get("/")
@app.get("/get-top-scorers/{chat_id}")
async def get_top_scorers(chat_id: str):
    try:
        # MongoDB aggregation pipeline to fetch top 10 scorers
        pipeline = [
            {"$match": {"chat_id": int(chat_id)}},  # Match the chat_id
            {"$group": {"_id": "$user_id", "score": {"$max": "$score"}}},  # Group by user_id and get the highest score
            {"$sort": {"score": -1}},  # Sort by score in descending order
            {"$limit": 10},  # Limit to top 10
        ]
        
        top_scorers = group_collection.aggregate(pipeline)
        scorers_list = []
        rank_of_requesting_user = None
        score_of_requesting_user = None

        for idx, scorer in enumerate(top_scorers):
            # Fetch user data for each scorer
            user_data = group_collection.find_one({"user_id": str(scorer["_id"])})
            if user_data:
                rank = idx + 1
                score = int(scorer["score"])

                # Add emojis for the top 3 users
                if rank == 1:
                    emoji = "🥇"
                elif rank == 2:
                    emoji = "🥈"
                elif rank == 3:
                    emoji = "🥉"
                else:
                    emoji = ""

                scorers_list.append({
                    "user_id": scorer["_id"],
                    "user_first_name": user_data["first_name"],
                    "score": score,
                    "emoji": emoji
                })

        return {"top_scorers": scorers_list}

    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"MongoDB error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

def run_bot():
    bot.polling()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
