import os
from pymongo import MongoClient
from datetime import datetime, timedelta

# Environment variables for MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "scrapper_db")

# TTL for database entries (e.g., 7 days)
# Data older than this will be automatically removed by MongoDB's TTL index
DB_TTL_DAYS = int(os.environ.get("DB_TTL_DAYS", 7))

class MongoDBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBManager, cls).__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        try:
            self.client = MongoClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print(f"Connected to MongoDB: {MONGO_URL}, database: {DB_NAME}")
            self._setup_indexes()
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            self.client = None
            self.db = None

    def _setup_indexes(self):
        if self.db is not None:
            # Index for lyrics collection, unique by query, with TTL
            self.db.lyrics.create_index([("query", 1)], unique=True)
            self.db.lyrics.create_index([("timestamp", 1)], expireAfterSeconds=DB_TTL_DAYS * 24 * 60 * 60)

            # Index for articles collection, unique by url, with TTL
            self.db.articles.create_index([("url", 1)], unique=True)
            self.db.articles.create_index([("timestamp", 1)], expireAfterSeconds=DB_TTL_DAYS * 24 * 60 * 60)

            print("MongoDB TTL indexes created/updated.")

    def get_lyrics(self, query):
        if self.db is None: return None
        return self.db.lyrics.find_one({"query": query})

    def save_lyrics(self, query, lyrics_data):
        if self.db is None: return
        self.db.lyrics.update_one({"query": query}, {"$set": {**lyrics_data, "query": query, "timestamp": datetime.now()}}, upsert=True)

    def get_article(self, url):
        if self.db is None: return None
        return self.db.articles.find_one({"url": url})

    def save_article(self, url, article_data):
        if self.db is None: return
        self.db.articles.update_one({"url": url}, {"$set": {**article_data, "url": url, "timestamp": datetime.now()}}, upsert=True)

# Initialize the DB manager globally
db_manager = MongoDBManager()