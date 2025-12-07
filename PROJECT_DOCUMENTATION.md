# Speech Annotation Tool - Technical Documentation

> Complete technical documentation for developers, maintainers, and contributors

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Data Model](#data-model)
4. [API Reference](#api-reference)
5. [Background Job System](#background-job-system)
6. [Frontend Architecture](#frontend-architecture)
7. [Storage & Persistence](#storage--persistence)
8. [Security Considerations](#security-considerations)
9. [Deployment Guide](#deployment-guide)
10. [Development Guide](#development-guide)
11. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### High-Level Architecture

The Speech Annotation Tool is built as a modern web application with a clean separation of concerns:

![Architecture](./static/images/Architecture.png)

### Design Principles

1. **Simplicity First**: No heavy dependencies (Redis, Celery). Threading-based background processing.
2. **Single User Optimized**: CSV-based storage with file locking for concurrent access.
3. **Streaming Architecture**: FFmpeg streaming for large file processing without memory bloat.
4. **Progressive Enhancement**: Works with basic features, enhanced with JavaScript.
5. **Separation of Concerns**: Clean layering between routes, services, and storage.

---

## System Components

### Directory Structure

```
Speech-Annotation-Tool/
├── app.py                          # Application entry point
├── requirements.txt                # Python dependencies
├── README.md                       # High-level overview
├── PROJECT_DOCUMENTATION.md        # This file
├── asr_tool/                       # Main application package
│   ├── __init__.py                 # App factory
│   ├── config.py                   # Configuration management
│   ├── routes.py                   # HTTP endpoints
│   └── services/                   # Business logic layer
│       ├── __init__.py
│       ├── audio.py                # Audio processing (FFmpeg)
│       ├── model.py                # Whisper model management
│       ├── storage.py              # Data persistence (CSV)
│       └── job_manager.py          # Background job orchestration
├── static/                         # Frontend assets
│   ├── css/
│   │   └── style.css               # Application styles
│   ├── js/
│   │   └── script.js               # Frontend logic
│   └── images/                     # Static images
├── templates/                      # Jinja2 templates
│   ├── base.html                   # Base layout
│   └── index.html                  # Main application page
└── data/                           # Runtime data (created automatically)
    ├── segments/                   # Audio segments (by job_id)
    ├── exports/                    # Exported files (CSV/XLSX)
    ├── transcriptions.csv          # Main data store
    └── jobs.json                   # Job status tracking
```

### Core Components

#### 1. **Audio Processing** (`services/audio.py`)

**Purpose**: Handle audio file conversion, segmentation, and validation.

**Key Functions**:
- `iter_audio_files(folder_path)`: Recursively find audio files, skip non-audio
- `convert_to_wav(source_path, job_id)`: Convert any audio format to 16kHz mono WAV
- `segment_audio(wav_path, job_id, segment_seconds=30)`: Split into fixed-duration segments

**Technology**: 
- FFmpeg for conversion and segmentation
- Streaming approach avoids loading entire files into memory

**Example**:
```python
# Convert and segment a large audio file
wav = convert_to_wav(Path("interview.mp3"), job_id="abc-123")
segments = segment_audio(wav, job_id="abc-123", segment_seconds=30)
# Result: data/segments/abc-123/interview/000.wav, 001.wav, ...
```

#### 2. **Model Layer** (`services/model.py`)

**Purpose**: Manage Whisper model loading and transcription.

**Key Functions**:
- `load_model(model_name)`: Load and cache Whisper model (LRU cached)
- `transcribe_file(model, processor, device, wav_path)`: Transcribe single segment

**Features**:
- LRU cache prevents reloading models
- Automatic GPU detection (CUDA)
- Forced decoder IDs disabled for flexibility

**Supported Models**:
- `openai/whisper-tiny`: Fastest, least accurate
- `openai/whisper-base`: Balanced
- `openai/whisper-small`: Default, good accuracy
- Custom models supported via Hugging Face

#### 3. **Job Manager** (`services/job_manager.py`)

**Purpose**: Orchestrate background jobs with progress tracking and type-based locking.

**Architecture**:
```python
JobManager (Singleton)
  ├── _jobs: Dict[job_id, JobInfo]
  ├── _active_jobs_by_type: Dict[JobType, job_id]
  └── _jobs_file: JSON persistence
```

**Job Lifecycle**:
1. **Create**: `create_job()` - Register new job
2. **Start**: `start_job()` - Check locks, mark as running
3. **Update**: `update_progress()` - Report progress
4. **Complete**: `complete_job()` or `fail_job()` - Finalize

**Locking Strategy**:
- Only one job of each type (TRANSCRIBE, MANUAL_IMPORT) can run simultaneously
- Prevents resource conflicts and ensures queue discipline
- Jobs tracked across restarts via JSON persistence

**Example**:
```python
manager = get_job_manager()
job_info = manager.run_job_async(
    job_id="xyz-789",
    job_type=JobType.TRANSCRIBE,
    task_func=my_background_task,
    total_items=100
)
```

#### 4. **Storage Layer** (`services/storage.py`)

**Purpose**: Persist transcription records with CSV backend.

**Schema**:
```
id, filename, transcription, correct_transcripts, job_id, locked, locked_at
```

**Key Functions**:
- `load_state()`: Load CSV with thread safety
- `save_state(df)`: Write CSV with locking
- `append_record(record)`: Add new transcription
- `update_record(id, corrected)`: Update correction (checks lock)
- `lock_record(id)`: Lock record from edits
- `unlock_record(id)`: Unlock record
- `import_manual(folder, excel, job_id)`: Bulk import from Excel

**Thread Safety**: Uses `threading.RLock()` for concurrent access.

---

## Data Model

### Transcription Record

| Field                | Type      | Description                           | Required |
|---------------------|-----------|---------------------------------------|----------|
| `id`                | UUID      | Unique record identifier              | Yes      |
| `filename`          | String    | Path to audio segment                 | Yes      |
| `transcription`     | String    | Original AI-generated transcript      | Yes      |
| `correct_transcripts`| String   | User-corrected transcript             | Yes      |
| `job_id`            | UUID      | Job that created this record          | Yes      |
| `locked`            | Boolean   | Whether record is locked              | Yes      |
| `locked_at`         | ISO 8601  | Timestamp of lock                     | No       |

### Job Information

| Field             | Type      | Description                           |
|-------------------|-----------|---------------------------------------|
| `job_id`          | UUID      | Unique job identifier                 |
| `job_type`        | Enum      | TRANSCRIBE or MANUAL_IMPORT           |
| `status`          | Enum      | pending/running/completed/failed      |
| `progress`        | Integer   | 0-100 percentage                      |
| `total_items`     | Integer   | Total items to process                |
| `processed_items` | Integer   | Items completed so far                |
| `created_at`      | Timestamp | Job creation time                     |
| `started_at`      | Timestamp | Job start time (nullable)             |
| `completed_at`    | Timestamp | Job completion time (nullable)        |
| `error`           | String    | Error message if failed (nullable)    |
| `result`          | JSON      | Result data (nullable)                |
| `metadata`        | JSON      | Job-specific metadata (nullable)      |

---

## API Reference

### Job Management

#### `POST /api/jobs/transcribe`

Start a background transcription job.

**Request**:
```json
{
  "folder": "/path/to/audio/files",
  "model_name": "openai/whisper-small"
}
```

**Response** (200):
```json
{
  "job_id": "abc-123",
  "status": "started",
  "total_files": 15
}
```

**Response** (409 - Job Already Running):
```json
{
  "error": "Another transcription job is already running",
  "active_job_id": "def-456"
}
```

#### `POST /api/manual/import`

Import pre-chunked audio with Excel transcripts.

**Request**:
```json
{
  "chunk_folder": "/path/to/chunks",
  "excel_path": "/path/to/transcripts.xlsx"
}
```

**Response** (200):
```json
{
  "job_id": "xyz-789",
  "status": "started"
}
```

#### `GET /api/jobs/{job_id}`

Get status of a specific job.

**Response**:
```json
{
  "job_id": "abc-123",
  "job_type": "transcribe",
  "status": "running",
  "progress": 65,
  "total_items": 100,
  "processed_items": 65,
  "created_at": 1701234567.89,
  "started_at": 1701234568.12,
  "metadata": {
    "folder": "/audio",
    "model_name": "openai/whisper-small"
  }
}
```

#### `GET /api/jobs`

List all jobs (most recent first, limit 50).

**Response**: Array of job objects.

### Record Management

#### `GET /api/records`

Get all transcription records.

**Response**:
```json
[
  {
    "id": "record-uuid",
    "filename": "/path/segment.wav",
    "transcription": "Original text",
    "correct_transcripts": "Corrected text",
    "job_id": "job-uuid",
    "locked": false,
    "locked_at": null
  }
]
```

#### `POST /api/records`

Update a record's corrected transcript.

**Request**:
```json
{
  "id": "record-uuid",
  "corrected_transcription": "New corrected text"
}
```

**Response** (200):
```json
{
  "success": true
}
```

**Response** (403 - Record Locked):
```json
{
  "error": "Record is locked and cannot be edited"
}
```

#### `POST /api/records/{record_id}/lock`

Lock a record to prevent edits.

**Response**:
```json
{
  "success": true,
  "locked": true
}
```

#### `POST /api/records/{record_id}/unlock`

Unlock a record to allow edits.

**Response**:
```json
{
  "success": true,
  "locked": false
}
```

### Export

#### `POST /api/export`

Export all records to file.

**Request**:
```json
{
  "format": "xlsx"  // or "csv"
}
```

**Response**: File download (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet or text/csv)

### Utility

#### `GET /api/browse?kind={dir|excel}`

Open native file browser (requires tkinter).

**Response**:
```json
{
  "path": "/selected/path"
}
```

#### `GET /segments?path={filename}`

Serve audio segment file.

**Response**: Audio file (audio/wav)

---

## Background Job System

### Threading Architecture

Jobs run in daemon threads to avoid blocking the main Flask process:

```python
def run_job_async(self, job_id, job_type, task_func, total_items, metadata):
    job_info = self.create_job(job_id, job_type, total_items, metadata)
    
    def wrapper():
        if not self.start_job(job_id):
            self.fail_job(job_id, "Another job is running")
            return
        
        try:
            result = task_func(job_id, self)
            self.complete_job(job_id, result)
        except Exception as e:
            self.fail_job(job_id, str(e))
    
    thread = Thread(target=wrapper, daemon=True)
    thread.start()
    return job_info
```

### Progress Reporting

Tasks report progress by calling `job_manager.update_progress()`:

```python
def transcription_task(job_id, job_manager):
    for idx, file in enumerate(files):
        # Process file...
        job_manager.update_progress(job_id, idx + 1, len(files))
```

Frontend polls `/api/jobs/{job_id}` every 2 seconds to update UI.

### Job Type Locking

Only one job per type can run:

```python
# Example: Starting a second transcribe job while one is running
can_start, active_job_id = manager.can_start_job(JobType.TRANSCRIBE)
if not can_start:
    return jsonify({"error": "Job already running", "active_job_id": active_job_id}), 409
```

---

## Frontend Architecture

### Technology Stack

- **Vanilla JavaScript (ES6+)**: No framework dependencies
- **Bootstrap 5**: Responsive UI components
- **localStorage**: Persistent correction tracking
- **Fetch API**: Modern HTTP requests

### Class Structure

#### `CorrectionTracker`

Manages localStorage-based correction history:

```javascript
class CorrectionTracker {
    markCorrected(recordId, originalText, correctedText)
    isCorrected(recordId)
    getCorrection(recordId)
    getStats() // Returns {total, corrected}
}
```

**Purpose**: Track which records have been edited, persist across sessions.

#### `JobTracker`

Manages active job progress display:

```javascript
class JobTracker {
    startTracking(jobId)
    stopTracking()
    updateBanner(jobInfo)
    startPolling() // Poll every 2s
}
```

**Purpose**: Display real-time job progress banner with percentage and status.

#### `ASRApp`

Main application controller:

```javascript
class ASRApp {
    init() // Setup listeners, start auto-refresh
    refreshRecords(silent) // Fetch and render records
    saveRecord(row) // Save edited record
    lockRecord(row) / unlockRecord(row)
    exportRecords(format)
}
```

### Auto-Refresh Strategy

Records table auto-refreshes every 10 seconds (silent, no user notification):

```javascript
setInterval(() => {
    this.refreshRecords(true); // Silent refresh
}, 10000);
```

### localStorage Schema

```json
{
  "asr_corrections_tracker": {
    "record-uuid-1": {
      "corrected": true,
      "originalText": "Original text",
      "correctedText": "Corrected text",
      "timestamp": "2025-12-07T10:30:00.000Z"
    }
  }
}
```

---

## Storage & Persistence

### CSV Format

The main data file (`data/transcriptions.csv`) uses UTF-8 encoding:

```csv
id,filename,transcription,correct_transcripts,job_id,locked,locked_at
uuid1,/path/segment.wav,Original text,Corrected text,job-uuid,False,
uuid2,/path/segment2.wav,Text 2,Text 2 edited,job-uuid,True,2025-12-07T10:30:00
```

### File Locking

Thread-safe operations using `threading.RLock()`:

```python
_lock = RLock()

def update_record(record_id, corrected_text):
    with _lock:
        df = load_state()
        df.loc[df["id"] == record_id, "correct_transcripts"] = corrected_text
        save_state(df)
```

### Export Formats

- **CSV**: Plain text, UTF-8, cross-platform
- **XLSX**: Excel format with openpyxl, supports formulas

---

## Security Considerations

### Path Traversal Prevention

Segment serving is restricted to whitelisted directory:

```python
candidate = Path(requested)
if not candidate.exists():
    # Fallback to safe segments directory
    candidate = SEGMENTS_DIR / Path(requested).name
```

### Input Validation

- Folder/file paths: Validated before processing
- Job IDs: UUID format enforced
- Record IDs: UUID lookup with no user-controlled SQL

### Recommendations for Production

1. **Add authentication**: Implement user login system
2. **Use HTTPS**: Configure TLS certificates
3. **Rate limiting**: Prevent abuse of job creation
4. **File size limits**: Prevent DoS via large uploads
5. **Database migration**: Move from CSV to PostgreSQL for multi-user

### Background Job Processing

**Current Implementation**: Python Threading
- Jobs run in daemon threads using Python's built-in `threading` module
- Suitable for single-server deployments
- No additional dependencies or services required
- Jobs are isolated and don't block the main application

**For Distributed Processing**: Consider migrating to Celery in future
- Celery with Redis/RabbitMQ for message broker
- Supports multiple workers across multiple servers
- Better for high-volume production environments
- Requires additional infrastructure setup

The current threading-based approach is sufficient for most use cases and keeps the deployment simple.

---

## Deployment Guide

### Prerequisites

1. **System Requirements**:
   - Python 3.10+
   - FFmpeg installed and in PATH
   - 4GB+ RAM recommended
   - GPU optional (CUDA for faster transcription)

2. **Install FFmpeg**:
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/Speech-Annotation-Tool.git
cd Speech-Annotation-Tool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Set environment variables:

```bash
export FLASK_SECRET_KEY="your-secret-key-here"
export ASR_MODEL="openai/whisper-small"
```

### Running

**Development**:
```bash
python app.py
# Runs on http://localhost:5000
```

**Production** (using Gunicorn):
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**Production** (using systemd):

Create `/etc/systemd/system/asr-tool.service`:
```ini
[Unit]
Description=Speech Annotation Tool
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/Speech-Annotation-Tool
Environment="PATH=/path/to/venv/bin"
Environment="FLASK_SECRET_KEY=your-secret-key"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable asr-tool
sudo systemctl start asr-tool
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    client_max_body_size 100M;
}
```

---

## Development Guide

### Setting Up Development Environment

```bash
# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# Run tests
pytest tests/ -v

# Format code
black asr_tool/ --line-length 100

# Lint
flake8 asr_tool/ --max-line-length 100
```

### Project Standards

1. **Code Style**: PEP 8, enforced by Black
2. **Type Hints**: Use Python type hints where possible
3. **Docstrings**: Google-style docstrings for functions
4. **Testing**: Aim for 80%+ coverage
5. **Git**: Conventional commits (feat, fix, docs, etc.)

### Adding a New Feature

1. **Backend**: Add service function in `services/`
2. **API**: Add route in `routes.py`
3. **Frontend**: Add handler in `script.js`
4. **UI**: Update templates and CSS
5. **Docs**: Update this documentation

### Testing

Example test structure:

```python
def test_audio_conversion():
    wav = convert_to_wav(Path("test.mp3"), job_id="test")
    assert wav.exists()
    assert wav.suffix == ".wav"
```

---

## Troubleshooting

### Common Issues

#### 1. FFmpeg not found

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`

**Solution**: Install FFmpeg and ensure it's in PATH:
```bash
which ffmpeg  # Should show path
ffmpeg -version  # Should show version
```

#### 2. CUDA out of memory

**Error**: `RuntimeError: CUDA out of memory`

**Solution**: Use a smaller model or CPU:
```python
# Force CPU usage
export CUDA_VISIBLE_DEVICES=""
```

#### 3. Job stuck in "running" status

**Cause**: Application restarted while job was running

**Solution**: Jobs don't auto-resume. Restart the job or manually update `data/jobs.json`.

#### 4. CSV corruption

**Error**: `pandas.errors.ParserError`

**Solution**: Restore from backup or fix manually. Enable auto-backups:
```python
# Add to storage.py
shutil.copy(STATE_FILE, f"{STATE_FILE}.backup")
```

#### 5. Port already in use

**Error**: `OSError: [Errno 48] Address already in use`

**Solution**:
```bash
# Find process
lsof -i :5000
# Kill process
kill -9 <PID>
```

---

## Performance Optimization

### For Large Datasets

1. **Batch Processing**: Process files in chunks
2. **Model Caching**: Keep model loaded (LRU cache does this)
3. **Segment Size**: Adjust segment duration (default 30s)
4. **Concurrent Jobs**: Increase if resources allow

### Background Job Processing: Threading vs Celery

**Current Implementation (Threading)**:
- Uses Python's built-in `threading` module
- No additional services required
- Perfect for single-server deployments
- Easy to deploy and maintain
- Suitable for most use cases

**Future: Celery Migration** (for distributed processing):
- Requires Redis or RabbitMQ as message broker
- Supports multiple workers across servers
- Better for high-volume production environments
- More complex infrastructure requirements

**When to migrate to Celery**:
- Processing >1000 files per hour
- Need to scale horizontally across multiple servers
- Require advanced job scheduling features
- Need job result persistence beyond current session

### Database Migration

For >10,000 records, consider migrating to SQLite:

```python
# Replace storage.py with SQLite backend
import sqlite3

def load_state():
    conn = sqlite3.connect('data/transcriptions.db')
    return pd.read_sql('SELECT * FROM transcriptions', conn)
```

---

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Review Checklist

- [ ] Code follows project standards
- [ ] Tests pass and coverage maintained
- [ ] Documentation updated
- [ ] No security vulnerabilities introduced
- [ ] Performance impact considered

---

## License

[Specify your license here]

---

## Support

For issues, questions, or contributions:

- **GitHub Issues**: [https://github.com/inboxpraveen/Speech-Annotation-Tool/issues](https://github.com/inboxpraveen/Speech-Annotation-Tool/issues)
- **Documentation**: This file

---

**Last Updated**: December 2025
**Version**: 2.0.0
