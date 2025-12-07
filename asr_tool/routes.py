import uuid
from pathlib import Path
from typing import Any, Dict

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:  # pragma: no cover - optional
    tk = None
    filedialog = None

from asr_tool.config import Config, SEGMENTS_DIR
from asr_tool.services import storage
from asr_tool.services.audio import convert_to_wav, iter_audio_files, segment_audio, AudioProcessingError
from asr_tool.services.model import load_model, transcribe_file, ModelError
from asr_tool.services.job_manager import get_job_manager, JobType

bp = Blueprint("api", __name__)


@bp.route("/")
def home():
    data = storage.load_state().to_dict(orient="records")
    return render_template("index.html", data=data, default_model=Config.DEFAULT_MODEL)


@bp.route("/results")
def results():
    return redirect(url_for("api.home"))


@bp.route("/api/jobs/transcribe", methods=["POST"])
def start_transcription():
    """Start a transcription job in the background."""
    try:
        payload: Dict[str, Any] = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    folder = payload.get("folder")
    model_name = payload.get("model_name") or Config.DEFAULT_MODEL
    
    if not folder:
        return jsonify({"error": "folder is required"}), 400
    
    if not isinstance(folder, str) or not folder.strip():
        return jsonify({"error": "folder must be a non-empty string"}), 400

    # Check if another transcription job is running
    job_manager = get_job_manager()
    can_start, active_job_id = job_manager.can_start_job(JobType.TRANSCRIBE)
    if not can_start:
        return jsonify({
            "error": "Another transcription job is already running",
            "active_job_id": active_job_id
        }), 409

    # Count files first
    try:
        files = list(iter_audio_files(folder))
        if not files:
            return jsonify({"error": "No audio files found in folder"}), 400
    except AudioProcessingError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to read folder: {str(e)}"}), 500

    job_id = str(uuid.uuid4())

    # Define the background task
    def transcription_task(job_id: str, job_manager):
        try:
            model, processor, device = load_model(model_name)
        except ModelError as e:
            raise Exception(f"Model loading failed: {str(e)}")
        
        total_segments = 0
        
        for idx, audio_file in enumerate(files):
            try:
                wav_path = convert_to_wav(Path(audio_file), job_id)
                segments = segment_audio(wav_path, job_id)
                total_segments += len(segments)
                wav_path.unlink(missing_ok=True)
                
                for segment in segments:
                    try:
                        text = transcribe_file(model, processor, device, str(segment))
                        storage.append_record(
                            {
                                "id": str(uuid.uuid4()),
                                "filename": str(segment),
                                "transcription": text,
                                "correct_transcripts": text,
                                "job_id": job_id,
                                "locked": False,
                                "locked_at": None,
                            }
                        )
                    except ModelError as e:
                        # Log but continue with other segments
                        print(f"Transcription error for {segment}: {str(e)}")
                        storage.append_record(
                            {
                                "id": str(uuid.uuid4()),
                                "filename": str(segment),
                                "transcription": f"[Error: {str(e)}]",
                                "correct_transcripts": "",
                                "job_id": job_id,
                                "locked": False,
                                "locked_at": None,
                            }
                        )
            except AudioProcessingError as e:
                print(f"Audio processing error for {audio_file}: {str(e)}")
                continue
            
            # Update progress after each file
            job_manager.update_progress(job_id, idx + 1, len(files))
        
        return {
            "files_processed": len(files),
            "segments_generated": total_segments,
            "records": total_segments,
        }

    # Start the job asynchronously
    try:
        job_info = job_manager.run_job_async(
            job_id=job_id,
            job_type=JobType.TRANSCRIBE,
            task_func=transcription_task,
            total_items=len(files),
            metadata={"folder": folder, "model_name": model_name}
        )

        return jsonify({
            "job_id": job_id,
            "status": "started",
            "total_files": len(files),
        })
    except Exception as e:
        return jsonify({"error": f"Failed to start job: {str(e)}"}), 500


@bp.route("/api/browse", methods=["GET"])
def browse_path():
    """
    Opens a native file/folder chooser on the host machine (best effort).
    kind=dir | excel
    """
    if not tk or not filedialog:
        return jsonify({"error": "Browsing not available in this environment"}), 400
    kind = request.args.get("kind", "dir")
    try:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        if kind == "excel":
            path = filedialog.askopenfilename(
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
            )
        else:
            path = filedialog.askdirectory()
        root.destroy()
        if not path:
            return jsonify({"error": "No selection made"}), 400
        return jsonify({"path": path})
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": str(exc)}), 500


@bp.route("/api/manual/import", methods=["POST"])
def manual_import():
    """Import pre-chunked audio with Excel in the background."""
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    chunk_folder = payload.get("chunk_folder")
    excel_path = payload.get("excel_path")
    
    if not chunk_folder or not excel_path:
        return jsonify({"error": "chunk_folder and excel_path are required"}), 400
    
    if not isinstance(chunk_folder, str) or not chunk_folder.strip():
        return jsonify({"error": "chunk_folder must be a non-empty string"}), 400
    
    if not isinstance(excel_path, str) or not excel_path.strip():
        return jsonify({"error": "excel_path must be a non-empty string"}), 400
    
    # Validate paths exist
    if not Path(chunk_folder).exists():
        return jsonify({"error": f"Chunk folder does not exist: {chunk_folder}"}), 400
    
    if not Path(excel_path).exists():
        return jsonify({"error": f"Excel file does not exist: {excel_path}"}), 400
    
    if not Path(excel_path).suffix.lower() in ['.xlsx', '.xls']:
        return jsonify({"error": "Excel file must be .xlsx or .xls format"}), 400

    # Check if another import job is running
    job_manager = get_job_manager()
    can_start, active_job_id = job_manager.can_start_job(JobType.MANUAL_IMPORT)
    if not can_start:
        return jsonify({
            "error": "Another import job is already running",
            "active_job_id": active_job_id
        }), 409

    job_id = str(uuid.uuid4())

    # Define the background task
    def import_task(job_id: str, job_manager):
        try:
            records = storage.import_manual(chunk_folder, excel_path, job_id)
            return {"records_imported": len(records)}
        except ValueError as e:
            raise Exception(f"Import validation error: {str(e)}")
        except Exception as exc:
            raise Exception(f"Import failed: {str(exc)}")

    # Start the job asynchronously
    try:
        job_info = job_manager.run_job_async(
            job_id=job_id,
            job_type=JobType.MANUAL_IMPORT,
            task_func=import_task,
            metadata={"chunk_folder": chunk_folder, "excel_path": excel_path}
        )

        return jsonify({
            "job_id": job_id,
            "status": "started",
        })
    except Exception as e:
        return jsonify({"error": f"Failed to start import: {str(e)}"}), 500


@bp.route("/api/jobs", methods=["GET"])
def list_jobs():
    """Get all jobs with their status."""
    job_manager = get_job_manager()
    jobs = job_manager.get_all_jobs()
    return jsonify([job.to_dict() for job in jobs])


@bp.route("/api/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id: str):
    """Get status of a specific job."""
    job_manager = get_job_manager()
    job = job_manager.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job.to_dict())


@bp.route("/api/records", methods=["GET"])
def list_records():
    df = storage.load_state()
    return jsonify(df.to_dict(orient="records"))


@bp.route("/api/records", methods=["POST"])
def save_record():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    record_id = payload.get("id")
    corrected = payload.get("corrected_transcription")
    
    if not record_id:
        return jsonify({"error": "id is required"}), 400
    
    if corrected is None:
        return jsonify({"error": "corrected_transcription is required"}), 400
    
    if not isinstance(corrected, str):
        return jsonify({"error": "corrected_transcription must be a string"}), 400
    
    try:
        storage.update_record(record_id, corrected)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": f"Failed to update record: {str(e)}"}), 500


@bp.route("/api/records/<record_id>/lock", methods=["POST"])
def lock_record(record_id: str):
    """Lock a record to prevent further edits."""
    try:
        storage.lock_record(record_id)
        return jsonify({"success": True, "locked": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/api/records/<record_id>/unlock", methods=["POST"])
def unlock_record(record_id: str):
    """Unlock a record to allow edits."""
    try:
        storage.unlock_record(record_id)
        return jsonify({"success": True, "locked": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/api/export", methods=["POST"])
def export_records():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    fmt = payload.get("format", "xlsx")
    
    if fmt not in ["csv", "xlsx"]:
        return jsonify({"error": "format must be 'csv' or 'xlsx'"}), 400
    
    try:
        path = storage.export_records(fmt)
        return send_file(path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500


@bp.route("/segments", defaults={"filename": None})
@bp.route("/segments/<path:filename>")
def serve_segment(filename: str | None):
    """
    Serve audio segments. Accepts either a path param or ?path=<absolute or relative>.
    Defaults to the managed segments directory for safety.
    """
    requested = request.args.get("path") if filename is None else filename
    if not requested:
        return jsonify({"error": "file not specified"}), 400

    candidate = Path(requested)
    if not candidate.exists():
        # Safe join with whitelist directory
        target = Path(requested).name
        base = SEGMENTS_DIR
        candidate = base / target
        if not candidate.exists():
            candidate = base / requested
    if not candidate.exists():
        return jsonify({"error": "file not found"}), 404
    return send_file(candidate)
