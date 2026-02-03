# 🔍 Web Scraper Dashboard

A Flask-based web scraping application that allows users to scrape lyrics, Medium articles, and Freedium content with a modern, responsive UI.

## ✨ Features

- **🎵 Lyrics Scraper** - Search and retrieve song lyrics from multiple sources
- **📰 Medium Article Scraper** - Scrape and save Medium articles in markdown format
- **📰 Freedium Scraper** - Bypass Medium paywall using Freedium
- **🎶 SimpMusic API** - Search lyrics via the SimpMusic API
- **🔗 Proxy Scraper** - Update proxy list for scraping operations (auto-updates every 2 hours)
- **📋 Search History** - Track your search history (per-user)
- **⭐ Favorites** - Save your favorite results for quick access
- **👤 User Authentication** - Register, login, and personalized experience
- **⏰ Scheduled Tasks** - Automatic proxy updates every 2 hours via APScheduler

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **Database**: MongoDB
- **Task Queue**: Redis + RQ (Redis Queue)
- **Scheduler**: APScheduler (background tasks)
- **Frontend**: Bootstrap 5, vanilla JavaScript
- **Web Server**: Gunicorn (production)

## 📋 Prerequisites

- Python 3.8+
- MongoDB instance (local or cloud like MongoDB Atlas)
- Redis server

## 🚀 Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd scraper/scrapper
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the `scrapper` directory:

```env
# MongoDB connection
MONGO_URL=mongodb://localhost:27017
DB_NAME=scrapper_db

# Redis connection
REDIS_URL=redis://localhost:6379

# Flask secret key (change in production!)
SECRET_KEY=your-super-secret-key

# Optional: TTL for database entries (default: 7 days)
DB_TTL_DAYS=7
```

### 5. Start Redis server

```bash
# Windows (using WSL or Redis for Windows)
redis-server

# Linux/Mac
sudo systemctl start redis
# or
redis-server
```

### 6. Run the application

**Development mode:**

```bash
# Terminal 1 - Start Flask app
python app.py

# Terminal 2 - Start RQ worker
python worker.py
```

**Production mode (using Honcho):**

```bash
honcho start
```

Or using Gunicorn directly:

```bash
gunicorn --timeout 120 --bind 0.0.0.0:8000 app:app
```

## 📁 Project Structure

```
scrapper/
├── app.py                 # Main Flask application
├── worker.py              # RQ worker for background tasks
├── db.py                  # MongoDB database manager
├── common.py              # Shared utilities (FlareSolverr integration)
├── lyrics_scraper.py      # Lyrics scraping logic
├── medium_scraper.py      # Medium article scraper
├── freedium_scraper.py    # Freedium article scraper
├── proxy_scraper.py       # Proxy list updater
├── requirements.txt       # Python dependencies
├── Procfile               # Process definitions for Honcho/Heroku
├── proxies.txt            # Proxy list file
├── static/
│   ├── style.css          # Main stylesheet
│   └── styles.css         # Additional styles
└── templates/
    ├── base.html          # Base template with navbar & sidebar
    ├── index.html         # Main dashboard page
    ├── login.html         # Login page
    ├── register.html      # Registration page
    ├── lyrics_result.html # Lyrics display template
    ├── medium_result.html # Medium article template
    └── freedium_result.html # Freedium article template
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URL` | MongoDB connection string | Required |
| `DB_NAME` | Database name | `scrapper_db` |
| `REDIS_URL` | Redis connection string | Required |
| `SECRET_KEY` | Flask secret key | `supersecretkey` |
| `DB_TTL_DAYS` | Data retention period (days) | `7` |

## 📖 Usage

1. **Register/Login** - Create an account or login to access personalized features
2. **Search Lyrics** - Enter a song title or artist name to find lyrics
3. **Scrape Articles** - Paste a Medium or Freedium URL to scrape the article
4. **View History** - Access your search history from the sidebar
5. **Save Favorites** - Click the star icon on any result to save it

## 🚢 Deployment

### Using Captain Definition (CapRover)

The project includes a `captain-definition` file for easy deployment on CapRover.

### Using Heroku

```bash
heroku create your-app-name
heroku addons:create mongolab
heroku addons:create heroku-redis
git push heroku main
```

### Using Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "--timeout", "120", "--bind", "0.0.0.0:8000", "app:app"]
```

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/login` | GET/POST | User login |
| `/register` | GET/POST | User registration |
| `/logout` | GET | User logout |
| `/search_lyrics` | POST | Search for lyrics |
| `/search_simpmusic` | POST | Search SimpMusic API |
| `/scrape_medium` | POST | Scrape Medium article |
| `/scrape_freedium` | POST | Scrape Freedium article |
| `/update_proxies` | POST | Update proxy list |
| `/status/<job_id>` | GET | Check job status |
| `/search_history` | GET | Get user's search history |
| `/favorites` | GET | Get user's favorites |
| `/add_favorite` | POST | Add to favorites |
| `/remove_favorite` | POST | Remove from favorites |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is for educational purposes. Please respect the terms of service of the websites being scraped.

## ⚠️ Disclaimer

This tool is intended for personal use and educational purposes only. Always respect website terms of service and robots.txt files. The developers are not responsible for any misuse of this software.
