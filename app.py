from flask import Flask, render_template, request, jsonify, send_file
from lyrics_scraper import search_song
from medium_scraper import MediumScraper
import io
from db import db_manager # Import the database manager

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search_lyrics', methods=['POST'])
def search_lyrics():
    query = request.form.get('query')
    if not query:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "Search query is required."}), 400
        return jsonify({"error": "Search query is required."}), 400

    # Try to get from DB first
    cached_result = db_manager.get_lyrics(query)
    if cached_result:
        cached_result.pop('_id', None) # Remove MongoDB's internal _id field before passing to template
        html = render_template('lyrics_result.html', result=cached_result)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return html
        return render_template('lyrics_result.html', result=cached_result)

    # If not in DB or expired, scrape
    scraped_result = search_song(query)
    if scraped_result:
        # The search_song function now handles saving to DB internally
        html = render_template('lyrics_result.html', result=scraped_result)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return html
        return render_template('lyrics_result.html', result=scraped_result)
    else:
        error_html = "<h1>No lyrics found.</h1>"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return error_html
        return error_html

@app.route('/scrape_medium', methods=['POST'])
def scrape_medium():
    url = request.form.get('url')
    if not url:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "Medium URL is required."}), 400
        return jsonify({"error": "Medium URL is required."}), 400

    # MediumScraper.scrape_single handles DB caching internally now
    result = MediumScraper().scrape_single(url)

    if result and not result.get('error'):
        html = render_template('medium_result.html', article=result)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return html
        return render_template('medium_result.html', article=result)
    else:
        error_html = f"<h1>Failed to scrape Medium article.</h1><p>{result.get('error', '')}</p>"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return error_html
        return error_html

@app.route('/download_lyrics', methods=['POST'])
def download_lyrics():
    title = request.form.get('title', 'lyrics')
    lyrics = request.form.get('lyrics', '')
    
    buffer = io.BytesIO()
    buffer.write(lyrics.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f'{title}.txt', mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True)