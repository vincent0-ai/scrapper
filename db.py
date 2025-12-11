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

            # Index for search history - ordered by timestamp
            self.db.search_history.create_index([("timestamp", -1)])
            self.db.search_history.create_index([("type", 1), ("timestamp", -1)])

            # Index for favorites - ordered by timestamp
            self.db.favorites.create_index([("timestamp", -1)])
            self.db.favorites.create_index([("type", 1), ("timestamp", -1)])
            self.db.favorites.create_index([("item_id", 1)], unique=True)

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

    def add_to_search_history(self, search_type, query, metadata=None):
        if self.db is None: return
        history_entry = {
            "type": search_type,  # 'lyrics', 'medium', 'simpmusic'
            "query": query,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        self.db.search_history.insert_one(history_entry)

    def get_search_history(self, search_type=None, limit=20):
        if self.db is None: return []
        query_filter = {"type": search_type} if search_type else {}
        return list(self.db.search_history.find(query_filter).sort("timestamp", -1).limit(limit))

    def clear_search_history(self, search_type=None):
        if self.db is None: return
        query_filter = {"type": search_type} if search_type else {}
        self.db.search_history.delete_many(query_filter)

    def add_to_favorites(self, item_type, item_id, title, metadata=None):
        if self.db is None: return
        favorite_entry = {
            "type": item_type,  # 'lyrics', 'medium'
            "item_id": item_id,  # url or query
            "title": title,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        self.db.favorites.update_one(
            {"item_id": item_id},
            {"$set": favorite_entry},
            upsert=True
        )

    def remove_from_favorites(self, item_id):
        if self.db is None: return
        self.db.favorites.delete_one({"item_id": item_id})

    def get_favorites(self, item_type=None, limit=100):
        if self.db is None: return []
        query_filter = {"type": item_type} if item_type else {}
        return list(self.db.favorites.find(query_filter).sort("timestamp", -1).limit(limit))

    def is_favorite(self, item_id):
        if self.db is None: return False
        return self.db.favorites.find_one({"item_id": item_id}) is not None

# Initialize the DB manager globally
db_manager = MongoDBManager()