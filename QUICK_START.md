# Quick Start Guide

Get the ASR Accuracy Tool running in 5 minutes.

## Prerequisites

- Python 3.10 or higher
- FFmpeg installed
- 4GB RAM minimum

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/inboxpraveen/ASR-Accuracy-Tool.git
cd ASR-Accuracy-Tool

# 2. Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify FFmpeg is installed
ffmpeg -version
```

## Install FFmpeg

### Windows
1. Download from https://ffmpeg.org/download.html
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to PATH environment variable
4. Restart terminal and verify: `ffmpeg -version`

### macOS
```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

## Run the Application

```bash
python app.py
```

Open your browser to: **http://localhost:5000**

## First Use

### Workflow 1: Review & Correct
1. Click "Review & Correct" card
2. Browse for chunked audio folder
3. Browse for Excel file (requires `filename` and `transcription` columns)
4. Click "Load for Review"
5. Edit transcripts in the table
6. Click "Save" after each correction
7. Lock finalized rows
8. Export when done

### Workflow 2: Auto-Transcribe
1. Click "Auto-Transcribe" card
2. Browse for audio folder
3. Select Whisper model
4. Click "Start Transcription"
5. Monitor progress in banner
6. Review results when complete

## Background Jobs

The application uses **Python threading** for background processing:
- No additional services required (no Redis, RabbitMQ, or Celery needed)
- Jobs run automatically when you start a transcription or import
- Progress updates appear in the top banner
- Only one job per type can run at a time

**Note**: For high-volume distributed processing across multiple servers, consider migrating to Celery in the future. See [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for details.

## Troubleshooting

### FFmpeg not found
```bash
# Verify installation
ffmpeg -version

# If not found, see installation steps above
```

### Port already in use
```bash
# Change port in app.py or:
python app.py --port 8000
```

### Out of memory
- Use smaller Whisper model (`tiny` or `base`)
- Process fewer files at once
- Increase system RAM

## Next Steps

- Read [README.md](README.md) for detailed features
- Read [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for technical details
- Read [CONTRIBUTING.md](CONTRIBUTING.md) to contribute

## Support

- Issues: https://github.com/inboxpraveen/ASR-Accuracy-Tool/issues
- Documentation: [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)
