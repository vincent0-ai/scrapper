from flask import Flask, render_template, request, jsonify, send_file
import io
import os
import redis
from rq import Queue
from db import db_manager
from worker import scrape_lyrics, scrape_medium

app = Flask(__name__)

redis_url = os.getenv('REDIS_URL')
conn = redis.from_url(redis_url)
q = Queue(connection=conn)

@app.route('/')
def index():
    return render_template('index.html') # This now points to our new file

@app.route('/search_lyrics', methods=['POST'])
def search_lyrics():
    query = request.form.get('query')
    if not query:
        return jsonify({"error": "Search query is required."}), 400

    # Try to get from DB first
    cached_result = db_manager.get_lyrics(query)
    if cached_result:
        cached_result.pop('_id', None)
        return jsonify({"status": "SUCCESS", "result": render_template('lyrics_result.html', result=cached_result)})

    # If not in DB, start a background job
    job = q.enqueue(scrape_lyrics, query, job_timeout=3600, meta={'template_name': 'lyrics_result.html'})
    return jsonify({"status": "PENDING", "task_id": job.get_id()})

@app.route('/scrape_medium', methods=['POST'])
def scrape_medium():
    url = request.form.get('url')
    if not url:
        return jsonify({"error": "Medium URL is required."}), 400

    # Try to get from DB first
    cached_result = db_manager.get_article(url)
    if cached_result:
        cached_result.pop('_id', None)
        return jsonify({"status": "SUCCESS", "result": render_template('medium_result.html', article=cached_result)})

    # If not in DB, start a background job
    job = q.enqueue(scrape_medium, url, job_timeout=3600, meta={'template_name': 'medium_result.html'})
    return jsonify({"status": "PENDING", "task_id": job.get_id()})

@app.route('/status/<job_id>')
def job_status(job_id):
    job = q.fetch_job(job_id)
    if job:
        if job.is_finished:
            if job.result:
                template_name = job.meta.get('template_name', 'lyrics_result.html')
                if template_name == 'lyrics_result.html':
                    html = render_template(template_name, result=job.result)
                else:
                    html = render_template(template_name, article=job.result)
                response = {'state': 'SUCCESS', 'result': html}
            else:
                # Job finished successfully, but the scraper found nothing.
                response = {'state': 'SUCCESS', 'result': '<div class="alert alert-warning">No results found.</div>'}
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
    lyrics = request.form.get('lyrics', '')
    
    buffer = io.BytesIO()
    buffer.write(lyrics.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f'{title}.txt', mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True)