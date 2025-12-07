# Changelog

All notable changes to the ASR Accuracy Tool will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-12-07

### 🎉 Major Release

Enhanced ASR Accuracy Tool with background processing, modern UI, and comprehensive documentation.

### Added

#### Background Processing & Job Management
- **Background job execution system** using threading for non-blocking operations
- **Job queue management** with type-based locking (only one job per type can run)
- **Real-time progress tracking** with percentage completion and item counters
- **Job status persistence** across application restarts via JSON storage
- **Progress polling API** for real-time UI updates
- **Job history** tracking with detailed metadata

#### User Interface Enhancements
- **Complete UI redesign** with modern, responsive Bootstrap 5 layout
- **Feature separation** with distinct primary (Review & Correct) and secondary (Auto-Transcribe) workflows
- **Live progress banner** that auto-appears during job execution
- **Statistics dashboard** showing total, corrected, and locked records
- **Auto-refresh table** (10-second interval) with manual refresh button
- **Visual status indicators** for locked and corrected rows
- **Responsive design** works perfectly on desktop, tablet, and mobile

#### Record Management Features
- **Row locking system** - Lock finalized records to prevent accidental edits
- **Unlock capability** - Re-enable editing when needed
- **Lock status persistence** - Locked state saved in CSV
- **Visual lock indicators** - Yellow background for locked rows
- **Lock timestamp tracking** - Know when records were locked

#### Session Persistence
- **localStorage correction tracking** - Remembers which records you've corrected
- **Cross-session persistence** - Data survives browser refresh and restarts
- **Correction statistics** - Track completion progress locally
- **Visual correction indicators** - See which records have been edited

#### Error Handling & Validation
- **Comprehensive error handling** in all services and routes
- **Custom exception classes** (AudioProcessingError, ModelError)
- **Input validation** for all API endpoints
- **Detailed error messages** for troubleshooting
- **Graceful failure handling** - Single file failures don't stop entire jobs
- **Path validation** - Verify folders and files exist before processing
- **Format validation** - Check Excel files have required columns

#### Documentation
- **Complete PROJECT_DOCUMENTATION.md** - Detailed technical documentation with:
  - Architecture diagrams
  - Complete API reference
  - Development guide
  - Deployment instructions
  - Troubleshooting section
- **Enhanced README.md** - High-level overview with:
  - Quick start guide
  - Feature showcase
  - Usage examples
  - Configuration options
- **CONTRIBUTING.md** - Contribution guidelines for open source
- **CHANGELOG.md** - This file
- **Inline code documentation** - Comprehensive docstrings

#### Code Quality
- **Services layer refactoring** - Clean separation of concerns
- **Job manager abstraction** - Centralized background job orchestration
- **Thread-safe operations** - Proper locking for concurrent access
- **Type hints** - Better IDE support and type checking
- **Error recovery** - Jobs can partially fail without losing all progress

### Changed

#### Architecture
- **Refactored to package structure** - `asr_tool/` package with submodules
- **Services layer** - Business logic isolated from routes
- **Background processing** - Jobs no longer block HTTP requests
- **Frontend rewrite** - Modern ES6+ JavaScript with class-based architecture
- **CSV schema** - Added `locked` and `locked_at` columns

#### API Changes
- **Job creation returns immediately** - Jobs run in background
- **New job status endpoints** - `/api/jobs` and `/api/jobs/{id}`
- **Lock/unlock endpoints** - `/api/records/{id}/lock` and `/api/records/{id}/unlock`
- **Enhanced error responses** - More detailed error information
- **409 Conflict responses** - When job of same type is already running

#### User Experience
- **Non-blocking operations** - UI remains responsive during processing
- **Real-time feedback** - Progress updates every 2 seconds
- **Better error messages** - User-friendly error descriptions
- **Export improvements** - Clearer export buttons and feedback
- **Table improvements** - Better column widths, numbering, and audio players

### Fixed

- **Large file handling** - FFmpeg streaming prevents memory issues
- **Concurrent access** - Thread-safe CSV operations
- **Audio format support** - Better format detection and conversion
- **Job recovery** - Failed jobs no longer block system
- **Path handling** - Cross-platform path support
- **Excel import validation** - Better error messages for invalid Excel files

### Security

- **Path traversal protection** - Restricted audio serving to whitelisted directory
- **Input sanitization** - All user inputs validated
- **Error message safety** - No sensitive information leaked in errors
- **Job isolation** - Jobs run in isolated threads

### Performance

- **LRU model caching** - Models loaded once and reused
- **Streaming audio processing** - Large files processed without full load
- **Efficient polling** - Smart refresh intervals
- **Lazy loading** - Audio players use `preload="none"`
- **Optimized CSV operations** - Minimal disk I/O

### Dependencies

- Upgraded to **Bootstrap 5** from Bootstrap 4
- Removed jQuery dependency from base template
- All Python dependencies pinned in requirements.txt

---

## [1.0.0] - 2023-XX-XX

### Initial Release

- Basic transcription workflow
- Manual audio chunk import
- Simple correction interface
- CSV export functionality
- jQuery-based frontend

---

## Future Releases

### [2.1.0] - Planned

- [ ] SQLite/PostgreSQL storage backend option
- [ ] User authentication and multi-user support
- [ ] WebSocket real-time updates (replace polling)
- [ ] Batch operations (lock/unlock multiple rows)
- [ ] Advanced filtering and search
- [ ] Audio playback speed control
- [ ] Keyboard shortcuts for efficiency

### [2.2.0] - Planned

- [ ] Docker and Docker Compose support
- [ ] Kubernetes deployment templates
- [ ] Redis caching layer
- [ ] Celery integration for distributed job processing (currently uses threading)
- [ ] S3 integration for audio storage
- [ ] API token authentication

**Note**: Background jobs currently use Python threading, which is suitable for most deployments. Celery integration is planned for high-volume distributed processing scenarios.

### [3.0.0] - Future

- [ ] Speaker diarization support
- [ ] Custom model fine-tuning interface
- [ ] Real-time collaborative editing
- [ ] Advanced analytics and reporting
- [ ] Plugin system for extensibility
- [ ] GraphQL API option

---

## Version History

- **2.0.0** - Complete rewrite with modern architecture
- **1.0.0** - Initial release

---

**Note**: This project follows [Semantic Versioning](https://semver.org/):
- **Major** version for incompatible API changes
- **Minor** version for backwards-compatible functionality additions
- **Patch** version for backwards-compatible bug fixes
