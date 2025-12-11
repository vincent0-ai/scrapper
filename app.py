from flask import Flask, render_template, request, jsonify, send_file
import io
import os
import redis
from rq import Queue
from db import db_manager # Assuming db_manager is correctly implemented and handles data storage/retrieval
from worker import scrape_lyrics, scrape_medium as worker_scrape_medium, update_proxies as worker_update_proxies, search_simpmusic as worker_search_simpmusic

app = Flask(__name__)

redis_url = os.getenv('REDIS_URL')
conn = redis.from_url(redis_url)
q = Queue(connection=conn)

@app.route('/')
def index():
    return render_template('index.html') # This now points to our new file

@app.route('/search_lyrics', methods=['POST'])
def search_lyrics():
    query = request.form.get('query').lower()
    if not query:
        return jsonify({"error": "Search query is required."}), 400

    # Add to search history
    db_manager.add_to_search_history('lyrics', query)

    # Try to get from DB first
    cached_result = db_manager.get_lyrics(query)
    if cached_result:
        cached_result.pop('_id', None) # Remove MongoDB's internal _id field if present
        # Defensive check: Ensure expected fields are strings before rendering
        if isinstance(cached_result, dict):
            for key in ['title', 'lyrics', 'artist', 'source']:
                if key in cached_result:
                    if callable(cached_result[key]):
                        cached_result[key] = f"Invalid {key.capitalize()} (method object found)"
                    elif not isinstance(cached_result[key], str):
                        cached_result[key] = str(cached_result[key])

        cached_result['is_favorite'] = db_manager.is_favorite(query)
        return jsonify({"status": "SUCCESS", "result": render_template('lyrics_result.html', result=cached_result)})

    # If not in DB, start a background job
    # Enqueue the actual worker function, not the Flask route handler
    job = q.enqueue(scrape_lyrics, query, job_timeout=3600, meta={'template_name': 'lyrics_result.html'})
    return jsonify({"status": "PENDING", "task_id": job.get_id()})

@app.route('/search_simpmusic', methods=['POST'])
def search_simpmusic():
    query = request.form.get('query')
    search_type = request.form.get('type', 'song')
    if not query:
        return jsonify({"error": "Search query is required."}), 400

    job = q.enqueue(worker_search_simpmusic, query, search_type, job_timeout=3600, meta={'template_name': 'lyrics_result.html'})
    return jsonify({"status": "PENDING", "task_id": job.get_id()})

@app.route('/scrape_medium', methods=['POST'])
def scrape_medium():
    url = request.form.get('url')
    if not url:
        return jsonify({"error": "Medium URL is required."}), 400

    # Add to search history
    db_manager.add_to_search_history('medium', url)

    # Try to get from DB first
    cached_result = db_manager.get_article(url)
    if cached_result:
        cached_result.pop('_id', None)
        cached_result['is_favorite'] = db_manager.is_favorite(url)
        return jsonify({"status": "SUCCESS", "result": render_template('medium_result.html', article=cached_result)})

    # If not in DB, start a background job
    job = q.enqueue(worker_scrape_medium, url, job_timeout=3600, meta={'template_name': 'medium_result.html'})
    return jsonify({"status": "PENDING", "task_id": job.get_id()})

@app.route('/update_proxies', methods=['POST'])
def update_proxies_route():
    # Enqueue the proxy update job
    job = q.enqueue(worker_update_proxies, job_timeout=3600, meta={'template_name': 'proxy_result.html'})
    return jsonify({"status": "PENDING", "task_id": job.get_id()})

@app.route('/status/<job_id>')
def job_status(job_id):
    job = q.fetch_job(job_id)
    if job:
        if job.is_finished:
            result = job.result
            if result and not result.get("error"):
                template_name = job.meta.get('template_name', 'lyrics_result.html')
                if template_name == 'lyrics_result.html':
                    result['is_favorite'] = db_manager.is_favorite(result.get('query', ''))
                    html = render_template(template_name, result=result)
                elif template_name == 'proxy_result.html':
                    html = f'<div class="alert alert-success">{result.get("message", "Proxies updated!")}</div>'
                else:
                    result['is_favorite'] = db_manager.is_favorite(result.get('url', ''))
                    html = render_template(template_name, article=result)
                response = {'state': 'SUCCESS', 'result': html}
            elif result and result.get("error"):
                # If the scraper returned a specific error message
                error_message = result.get("error", "An unknown error occurred.")
                html = f'<div class="alert alert-danger">{error_message}</div>'
                response = {'state': 'SUCCESS', 'result': html}
            else:
                # This case handles when job.result is None or has no content
                html = '<div class="alert alert-warning">No content was found for the given URL. Please check the URL and try again.</div>'
                response = {'state': 'SUCCESS', 'result': html}
        elif job.is_failed:
            response = {'state': 'FAILED', 'status': 'Job failed.'}
        else:
            response = {'state': 'PENDING', 'status': 'Job is still running.'}
    else:
        response = {'state': 'FAILED', 'status': 'Job not found.'}
    return jsonify(response)


@app.route('/download_lyrics', methods=['POST'])
def download_lyrics():
    title = request.form.get('title', 'lyrics')
    # Ensure title is a string and safe for filenames
    if not isinstance(title, str):
        title = str(title)
    # Sanitize title for use as a filename
    title = "".join(c for c in title if c.isalnum() or c in (' ', '.', '_')).rstrip()
    if not title: # Fallback if sanitization results in an empty string
        title = 'lyrics'

    lyrics = request.form.get('lyrics', '')
    # Ensure lyrics is a string
    if not isinstance(lyrics, str):
        lyrics = str(lyrics)

    buffer = io.BytesIO()
    buffer.write(lyrics.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f'{title}.txt', mimetype='text/plain')

@app.route('/download_medium', methods=['POST'])
def download_medium():
    title = request.form.get('title', 'article')
    author = request.form.get('author', 'Unknown')
    content = request.form.get('content', '')
    url = request.form.get('url', '')
    published = request.form.get('published', '')
    tags = request.form.get('tags', '')
    
    # Sanitize title for use as a filename
    if not isinstance(title, str):
        title = str(title)
    title = "".join(c for c in title if c.isalnum() or c in (' ', '.', '_')).rstrip()
    if not title:
        title = 'article'
    
    # Build the file content
    file_content = f"""ARTICLE TITLE
{title}

AUTHOR
{author}

PUBLISHED
{published}

URL
{url}
"""
    
    if tags:
        file_content += f"\nTAGS\n{tags}\n"
    
    file_content += f"\n{'='*80}\n\nCONTENT\n\n{content}"
    
    buffer = io.BytesIO()
    buffer.write(file_content.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f'{title}.txt', mimetype='text/plain')

@app.route('/search_history')
def get_search_history():
    search_type = request.args.get('type')  # Optional: filter by type (lyrics, medium, simpmusic)
    history = db_manager.get_search_history(search_type)
    # Clean up for JSON serialization
    for item in history:
        item.pop('_id', None)
        item['timestamp'] = item['timestamp'].isoformat() if hasattr(item['timestamp'], 'isoformat') else str(item['timestamp'])
    return jsonify({"status": "SUCCESS", "history": history})

@app.route('/clear_search_history', methods=['POST'])
def clear_search_history():
    search_type = request.form.get('type')  # Optional: clear only specific type
    db_manager.clear_search_history(search_type)
    return jsonify({"status": "SUCCESS", "message": "Search history cleared"})

@app.route('/add_favorite', methods=['POST'])
def add_favorite():
    item_type = request.form.get('type')  # 'lyrics' or 'medium'
    item_id = request.form.get('item_id')  # query or url
    title = request.form.get('title')
    
    if not item_type or not item_id or not title:
        return jsonify({"error": "Missing required fields"}), 400
    
    db_manager.add_to_favorites(item_type, item_id, title)
    return jsonify({"status": "SUCCESS", "message": "Added to favorites"})

@app.route('/remove_favorite', methods=['POST'])
def remove_favorite():
    item_id = request.form.get('item_id')
    
    if not item_id:
        return jsonify({"error": "item_id is required"}), 400
    
    db_manager.remove_from_favorites(item_id)
    return jsonify({"status": "SUCCESS", "message": "Removed from favorites"})

@app.route('/favorites')
def get_favorites():
    item_type = request.args.get('type')  # Optional: filter by type
    favorites = db_manager.get_favorites(item_type)
    # Clean up for JSON serialization
    for item in favorites:
        item.pop('_id', None)
        item['timestamp'] = item['timestamp'].isoformat() if hasattr(item['timestamp'], 'isoformat') else str(item['timestamp'])
    return jsonify({"status": "SUCCESS", "favorites": favorites})

if __name__ == '__main__':
    app.run(debug=True)