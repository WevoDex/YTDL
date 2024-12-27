from flask import Flask, request, jsonify, render_template, send_file
import yt_dlp
import threading
import os
import re

app = Flask(__name__, template_folder='templates')

# Globals to store download progress
download_progress = {}
video_files = {}

# Function to extract video ID from URL
def extract_video_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

# Callback to update progress
def progress_hook(d):
    video_id = d['info_dict']['id'] if 'info_dict' in d else "unknown"
    if d['status'] == 'downloading':
        download_progress[video_id] = d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 100
    elif d['status'] == 'finished':
        download_progress[video_id] = 100
        video_files[video_id] = d['info_dict']['_filename']

# Download function
def download_video(video_url, use_cookies, video_id):
    ydl_opts = {
        'progress_hooks': [progress_hook],
        'outtmpl': f'downloads/{video_id}_%(title)s.%(ext)s'
    }

    if use_cookies:
        ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except yt_dlp.utils.DownloadError as e:
        download_progress[video_id] = f"Error: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_download', methods=['POST'])
def start_download():
    video_url = request.json.get('video_url')
    use_cookies = request.json.get('use_cookies', True)

    if not video_url:
        return jsonify({'error': 'Video URL is required.'}), 400

    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL.'}), 400

    download_progress[video_id] = 0

    thread = threading.Thread(target=download_video, args=(video_url, use_cookies, video_id))
    thread.start()

    return jsonify({'message': 'Download started.', 'video_id': video_id})

@app.route('/progress/<video_id>', methods=['GET'])
def get_progress(video_id):
    progress = download_progress.get(video_id, None)
    if progress is None:
        return jsonify({'error': 'Video not found or progress not available.'}), 404

    return jsonify({'progress': progress})

@app.route('/download/<video_id>', methods=['GET'])
def download_file(video_id):
    filepath = video_files.get(video_id)
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'File not found.'}), 404

    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    os.makedirs('downloads', exist_ok=True)
    app.run(debug=True)
