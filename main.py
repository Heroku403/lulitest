from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import telebot
from pymongo import MongoClient
from telebot import types

# Initialize FastAPI app, Telegram bot, and MongoDB client
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
bot = telebot.TeleBot("6450878640:AAEkDXKORJvv-530GfG6OZYnZxfZgJ9f_FA")
client = MongoClient("mongodb+srv://itachiuchihablackcops:5412ascs@gamebot.dfp9j.mongodb.net/?retryWrites=true&w=majority&appName=GameBot")
db = client["skgamebot"]
collection = db["flappybird"]

# Define data model
class UserData(BaseModel):
    score: int
    mongo_id: str
    first_name: str
    last_name: str
    user_id: str

# Define POST endpoint
@app.post("/flappybird-update-score")
async def update_score(user_data: UserData):
    # Insert data into MongoDB collection
    result = collection.insert_one(user_data.dict())
    
    return {"message": "Score updated successfully", "inserted_id": str(result.inserted_id)}

# Define /start command handler
@bot.message_handler(commands=['start'])
def start(message):
    # Replace 'chat_id' with the actual chat ID
    bot.send_message(message.chat.id, "Welcome!")

# Define /leaderboard command handler
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    # Aggregate pipeline to get top 10 unique user scores
    pipeline = [
        {"$sort": {"score": -1}},
        {"$group": {"_id": "$user_id", "name": {"$first": "$first_name"}, "score": {"$max": "$score"}}},
        {"$sort": {"score": -1}},
        {"$limit": 10}
    ]
    
    leaderboard = collection.aggregate(pipeline)
    
    # Convert to list for easier handling
    leaderboard = list(leaderboard)
    
    # Format leaderboard message
    msg = "Leaderboard:\n"
    for i, entry in enumerate(leaderboard):
        msg += f"{i+1}. {entry['name']} - {entry['score']}\n"
    
    # Replace 'chat_id' with the actual chat ID
    bot.send_message(message.chat.id, msg)

# Run Telegram bot in separate thread
import threading
def run_bot():
    bot.polling()

threading.Thread(target=run_bot).start()

# Run FastAPI app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
