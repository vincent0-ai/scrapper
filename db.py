import os
try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # If python-dotenv isn't installed, rely on environment variables already set
    pass
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
        # If pymongo is not installed, avoid attempting a DB connection
        if MongoClient is None:
            print("pymongo not installed — using no-op in-memory DB manager")
            self.client = None
            self.db = None
            self._store = {"articles": {}, "lyrics": {}}
            return

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
            self.db.favorites.create_index([("item_id", 1), ("user_id", 1)], unique=True)
            self.db.users.create_index([("username", 1)], unique=True)

            print("MongoDB TTL indexes created/updated.")

    def create_user(self, username, password_hash):
        if self.db is None: return None
        try:
            return self.db.users.insert_one({"username": username, "password": password_hash})
        except Exception:
            return None

    def get_user_by_username(self, username):
        if self.db is None: return None
        return self.db.users.find_one({"username": username})

    def get_user_by_id(self, user_id):
        if self.db is None: return None
        from bson.objectid import ObjectId
        try:
            return self.db.users.find_one({"_id": ObjectId(user_id)})
        except:
            return None

    def get_lyrics(self, query):
        if getattr(self, "db", None) is None:
            return getattr(self, "_store", {}).get("lyrics", {}).get(query)
        return self.db.lyrics.find_one({"query": query})

    def get_lyrics_multi(self, queries):
        if getattr(self, "db", None) is None:
            store = getattr(self, "_store", {}).get("lyrics", {})
            return [store.get(q) for q in queries if q in store]
        return list(self.db.lyrics.find({"query": {"$in": queries}}))

    def save_lyrics(self, query, lyrics_data):
        if getattr(self, "db", None) is None:
            self._store.setdefault("lyrics", {})[query] = {**lyrics_data, "query": query}
            return
        self.db.lyrics.update_one({"query": query}, {"$set": {**lyrics_data, "query": query, "timestamp": datetime.now()}}, upsert=True)

    def get_article(self, url):
        if getattr(self, "db", None) is None:
            return getattr(self, "_store", {}).get("articles", {}).get(url)
        return self.db.articles.find_one({"url": url})

    def get_articles(self, urls):
        if getattr(self, "db", None) is None:
            store = getattr(self, "_store", {}).get("articles", {})
            return [store.get(u) for u in urls if u in store]
        return list(self.db.articles.find({"url": {"$in": urls}}))

    def save_article(self, url, article_data):
        if getattr(self, "db", None) is None:
            self._store.setdefault("articles", {})[url] = {**article_data, "url": url}
            return
        self.db.articles.update_one({"url": url}, {"$set": {**article_data, "url": url, "timestamp": datetime.now()}}, upsert=True)

    def add_to_search_history(self, search_type, query, metadata=None, user_id=None):
        if self.db is None: return
        if not user_id: return  # Don't store history for unauthenticated users
        history_entry = {
            "type": search_type,  # 'lyrics', 'medium', 'simpmusic'
            "query": query,
            "timestamp": datetime.now(),
            "metadata": metadata or {},
            "user_id": user_id
        }
        self.db.search_history.insert_one(history_entry)

    def get_search_history(self, search_type=None, user_id=None, limit=20):
        if self.db is None: return []
        if not user_id: return []  # No history for unauthenticated users
        query_filter = {"user_id": user_id}
        if search_type:
            query_filter["type"] = search_type
        return list(self.db.search_history.find(query_filter).sort("timestamp", -1).limit(limit))

    def clear_search_history(self, search_type=None, user_id=None):
        if self.db is None: return
        query_filter = {}
        if search_type:
            query_filter["type"] = search_type
        if user_id:
            query_filter["user_id"] = user_id
        else:
            query_filter["user_id"] = None
        self.db.search_history.delete_many(query_filter)

    def add_to_favorites(self, item_type, item_id, title, metadata=None, user_id=None):
        if self.db is None: return
        if not user_id: return # Guests cannot save favorites in this design?
        
        favorite_entry = {
            "type": item_type,  # 'lyrics', 'medium'
            "item_id": item_id,  # url or query
            "title": title,
            "timestamp": datetime.now(),
            "metadata": metadata or {},
            "user_id": user_id
        }
        self.db.favorites.update_one(
            {"item_id": item_id, "user_id": user_id},
            {"$set": favorite_entry},
            upsert=True
        )

    def remove_from_favorites(self, item_id, user_id=None):
        if self.db is None or not user_id: return
        self.db.favorites.delete_one({"item_id": item_id, "user_id": user_id})

    def get_favorites(self, item_type=None, user_id=None, limit=100):
        if self.db is None or not user_id: return []
        query_filter = {"user_id": user_id}
        if item_type:
            query_filter["type"] = item_type
        return list(self.db.favorites.find(query_filter).sort("timestamp", -1).limit(limit))

    def is_favorite(self, item_id, user_id=None):
        if self.db is None or not user_id: return False
        return self.db.favorites.find_one({"item_id": item_id, "user_id": user_id}) is not None

# Initialize the DB manager globally
db_manager = MongoDBManager()