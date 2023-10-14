from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask import send_from_directory

from celery import Celery
from redis import Redis
import pandas as pd

import os
import subprocess
import threading

from utils import *
from speech import *

app = Flask(__name__)

# Celery configuration
app.config['CELERY_BROKER_URL'] = 'redis://127.0.0.1:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://127.0.0.1:6379/0'

# Initialize Redis
redis = Redis(host='localhost', port=6379, db=0)

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Global lock for DataFrame operations
lock = threading.Lock()

columns = ['filename', 'transcription', 'correct_transcripts']
df = pd.DataFrame(columns=columns)
last_sent_row = 0
total_files, processed_files = 0, 0

excel_file = generate_excel_name()
if os.path.exists(excel_file):
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        print(f"Error reading Excel file: {e}")

if not os.path.exists(os.path.join(os.getcwd(),"wav_temp")):
    os.makedirs(os.path.join(os.getcwd(),"wav_temp"))

if not os.path.exists(os.path.join(os.getcwd(),"temp")):
    os.makedirs(os.path.join(os.getcwd(),"temp"))


@app.route('/temp/<path:filename>', methods=['GET'])
def serve_audio(filename):
    """
    Serves audio files from a specific directory.

    Parameters:
    - filename (str): The name of the file to be served.

    Returns:
    - Flask Response: A response serving the requested file.

    Example:
    GET /temp/my_audio.wav will serve my_audio.wav from the specified directory.
    """
    directory = os.path.join(os.getcwd(), "temp", "temp_cropped_audio")
    return send_from_directory(directory, filename)


@app.route('/get-latest-data', methods=['GET'])
def get_latest_data():
    """
    Fetches the latest transcribed data from the Excel file and returns it as JSON.

    Returns:
    - JSON: Either new rows of data or a message saying all records are processed.

    Example:
    GET /get-latest-data might return [{"filename": "audio1.wav", "transcription": "hello"}].
    """

    global df, last_sent_row, lock
    
    # Load the dataframe from the Excel file
    excel_file = generate_excel_name()
    if os.path.exists(excel_file):
        with lock:
            try:
                df = pd.read_excel(excel_file)
            except Exception as e:
                print(f"Error reading Excel file: {e}")
    all_done = False
    
    with lock:
        new_rows = df.iloc[last_sent_row:].to_dict(orient='records')
        if last_sent_row == len(df):
            all_done = True
        else:
            last_sent_row = len(df)
    if all_done:
        return jsonify("All_Records_Processed")
    else:
        return jsonify(new_rows)


@celery.task(bind=True)
def process_audio(self, file_path):
    """
    Processes audio files asynchronously using Celery.
    
    Parameters:
    - self: The Celery task instance.
    - file_path (str): Path to the audio file.

    Returns:
    - None

    Example:
    process_audio.delay("/path/to/audio.mp3")
    """

    global df, lock, processed_files, total_files
    model, tokenizer, device = load_model_and_tokenizer("openai/whisper-tiny")
    if model is not None and tokenizer is not None:
        print("Intialized Speech Model Successfully.")
    else:
        print("Invalid choice or unsupported model.")
        import sys
        sys.exit()

    wav_filepath = convert_audio_to_wav(file_path)
    all_crops = crop_into_segments(wav_filepath)
    
    # total_files += len(all_crops)
    redis.incr('total_files', len(all_crops))

    for chunk_path in all_crops:
        print("Processing Chunk :", chunk_path)
        transcription = transcribe(model, tokenizer, device, chunk_path)
        print("Finished Processing this chunk...")
        print()
        new_data = {
            "filename": chunk_path,
            "transcription": transcription,
            "correct_transcripts": transcription
        }
        df.loc[len(df)] = new_data

        with lock:
            try:
                df.to_excel(generate_excel_name(), index=False)
            except Exception as e:
                print(f"Error writing to Excel file: {e}")
        
        redis.incr('processed_files')

    if os.path.exists(wav_filepath):
        os.remove(wav_filepath)
    
    clear_memory(model, tokenizer)


def convert_audio_to_wav(input_file_path):

    """
    Converts an audio file to WAV format using ffmpeg.

    Parameters:
    - input_file_path (str): The path of the input audio file.

    Returns:
    - str: The path of the converted WAV file.

    Example:
    convert_audio_to_wav("/path/to/audio.mp3") returns "/path/to/audio.wav"
    """

    filename = ".".join(os.path.basename(input_file_path).split(".")[:-1])

    output_file_path = os.path.join(os.path.join(os.getcwd(),"wav_temp"),filename + ".wav")
    command = [
        "ffmpeg", "-i", input_file_path, "-ac", "1",
        "-ar", "16000", "-acodec", "pcm_s16le", output_file_path, "-y"
    ]
    try:
        subprocess.run(command, check=True)
        return output_file_path
    except subprocess.CalledProcessError as e:
        print("Error while converting using ffmpeg:", e)
        return ""


@app.route('/')
def index():
    """
    Serves the index page of the application.

    Returns:
    - HTML: The rendered index page.

    Example:
    GET / returns the index.html page.
    """
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def start_processing():
    """
    Initiates the audio processing tasks.

    Parameters:
    - None

    Returns:
    - Flask Response: A redirect to the results page.

    Example:
    POST /process initiates audio processing and redirects to /results.
    """
    global total_files
    folder_path = request.form.get('folderPath')
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(('.mp3', '.wav', '.wma', '.mpeg', '.opus')):
                process_audio.delay(os.path.join(root, file))

    return redirect(url_for('results'))


@app.route('/results')
def results():
    """
    Serves the results page containing transcribed data.

    Returns:
    - HTML: The rendered results page.

    Example:
    GET /results returns the results.html page.
    """
    global df
    return render_template('results.html', data=df.to_dict(orient='records'))


@app.route('/get-progress', methods=['GET'])
def get_progress():
    """
    A Flask API endpoint that retrieves the progress of a long-running task.
    It calculates the progress as the percentage of processed files against the total files.
    Stores and fetches these metrics from a Redis database.

    Request Method: 
    - GET

    Returns:
    - JSON: A JSON object containing the 'progress' as a percentage. Returns 0 if 'total_files' is zero.

    Example:
    GET request to '/get-progress'
    If Redis stores total_files as 10 and processed_files as 5, then the returned JSON will be:
    {"progress": 50.0}

    Debug:
    Logs the current state (total_files and processed_files) and progress to the console.
    """
    print("Called GET PROGRESS API Backend")
    total_files = int(redis.get('total_files') or 0)
    processed_files = int(redis.get('processed_files') or 0)
    print(f"Total Files, Processed Files : {total_files, processed_files}")
    if total_files == 0:
        return jsonify({"progress": 0})
    progress = (processed_files / total_files) * 100
    return jsonify({"progress": progress})


@app.route('/save-edits', methods=['POST'])
def save_edits():
    """
    Saves the edited transcriptions.

    Parameters:
    - None

    Returns:
    - JSON: A JSON object indicating success.

    Example:
    POST /save-edits with JSON payload to save the edited transcriptions.
    """
    requestData = request.get_json()
    filename = requestData['filename']
    corrected_transcription = requestData['corrected_transcription']

    global df

    with lock:
        df.loc[df['filename'] == filename, 'correct_transcripts'] = corrected_transcription
        try:
            df.to_excel(generate_excel_name(), index=False)
        except Exception as e:
            print(f"Error writing to Excel file: {e}")

    return jsonify(success=True)


if __name__ == "__main__":
    app.run(debug=True, threaded=False)

