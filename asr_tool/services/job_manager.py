"""Background job management with progress tracking and locking."""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Callable, Dict, List, Optional

from asr_tool.config import DATA_DIR


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Types of jobs that can be executed."""
    TRANSCRIBE = "transcribe"
    MANUAL_IMPORT = "manual_import"


@dataclass
class JobInfo:
    """Job metadata and status information."""
    job_id: str
    job_type: JobType
    status: JobStatus
    progress: int  # 0-100
    total_items: int
    processed_items: int
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type.value,
            "status": self.status.value,
            "progress": self.progress,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "result": self.result,
            "metadata": self.metadata,
        }


class JobManager:
    """
    Manages background jobs with progress tracking and type-based locking.
    Ensures only one job of each type runs at a time.
    """

    def __init__(self):
        self._jobs: Dict[str, JobInfo] = {}
        self._lock = Lock()
        self._active_jobs_by_type: Dict[JobType, str] = {}
        self._jobs_file = DATA_DIR / "jobs.json"
        self._load_jobs()

    def _load_jobs(self) -> None:
        """Load job history from disk."""
        if self._jobs_file.exists():
            try:
                with open(self._jobs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for job_data in data:
                        job_type = JobType(job_data["job_type"])
                        status = JobStatus(job_data["status"])
                        job_info = JobInfo(
                            job_id=job_data["job_id"],
                            job_type=job_type,
                            status=status,
                            progress=job_data.get("progress", 0),
                            total_items=job_data.get("total_items", 0),
                            processed_items=job_data.get("processed_items", 0),
                            created_at=job_data.get("created_at", time.time()),
                            started_at=job_data.get("started_at"),
                            completed_at=job_data.get("completed_at"),
                            error=job_data.get("error"),
                            result=job_data.get("result"),
                            metadata=job_data.get("metadata"),
                        )
                        self._jobs[job_info.job_id] = job_info
            except Exception:
                pass  # Start fresh if file is corrupted

    def _save_jobs(self) -> None:
        """Persist job history to disk."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(self._jobs_file, "w", encoding="utf-8") as f:
                json.dump([job.to_dict() for job in self._jobs.values()], f, indent=2)
        except Exception:
            pass  # Best effort

    def create_job(self, job_id: str, job_type: JobType, total_items: int = 0, metadata: Optional[Dict] = None) -> JobInfo:
        """Create a new job entry."""
        with self._lock:
            job_info = JobInfo(
                job_id=job_id,
                job_type=job_type,
                status=JobStatus.PENDING,
                progress=0,
                total_items=total_items,
                processed_items=0,
                created_at=time.time(),
                metadata=metadata,
            )
            self._jobs[job_id] = job_info
            self._save_jobs()
            return job_info

    def can_start_job(self, job_type: JobType) -> tuple[bool, Optional[str]]:
        """
        Check if a job of this type can be started.
        Returns (can_start, active_job_id).
        """
        with self._lock:
            active_job_id = self._active_jobs_by_type.get(job_type)
            if active_job_id and active_job_id in self._jobs:
                job = self._jobs[active_job_id]
                if job.status == JobStatus.RUNNING:
                    return False, active_job_id
            return True, None

    def start_job(self, job_id: str) -> bool:
        """Mark a job as started. Returns False if another job of same type is running."""
        with self._lock:
            if job_id not in self._jobs:
                return False
            
            job = self._jobs[job_id]
            can_start, active_job_id = self.can_start_job(job.job_type)
            
            if not can_start:
                return False
            
            job.status = JobStatus.RUNNING
            job.started_at = time.time()
            self._active_jobs_by_type[job.job_type] = job_id
            self._save_jobs()
            return True

    def update_progress(self, job_id: str, processed: int, total: Optional[int] = None) -> None:
        """Update job progress."""
        with self._lock:
            if job_id not in self._jobs:
                return
            
            job = self._jobs[job_id]
            job.processed_items = processed
            if total is not None:
                job.total_items = total
            
            if job.total_items > 0:
                job.progress = int((processed / job.total_items) * 100)
            else:
                job.progress = 0
            
            self._save_jobs()

    def complete_job(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark a job as completed."""
        with self._lock:
            if job_id not in self._jobs:
                return
            
            job = self._jobs[job_id]
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()
            job.progress = 100
            job.result = result
            
            # Release the job type lock
            if self._active_jobs_by_type.get(job.job_type) == job_id:
                del self._active_jobs_by_type[job.job_type]
            
            self._save_jobs()

    def fail_job(self, job_id: str, error: str) -> None:
        """Mark a job as failed."""
        with self._lock:
            if job_id not in self._jobs:
                return
            
            job = self._jobs[job_id]
            job.status = JobStatus.FAILED
            job.completed_at = time.time()
            job.error = error
            
            # Release the job type lock
            if self._active_jobs_by_type.get(job.job_type) == job_id:
                del self._active_jobs_by_type[job.job_type]
            
            self._save_jobs()

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Get job information."""
        with self._lock:
            return self._jobs.get(job_id)

    def get_all_jobs(self, limit: int = 50) -> List[JobInfo]:
        """Get all jobs, most recent first."""
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return jobs[:limit]

    def get_active_job(self, job_type: JobType) -> Optional[JobInfo]:
        """Get currently active job of a specific type."""
        with self._lock:
            job_id = self._active_jobs_by_type.get(job_type)
            if job_id:
                return self._jobs.get(job_id)
            return None

    def run_job_async(
        self, 
        job_id: str, 
        job_type: JobType,
        task_func: Callable[[str, 'JobManager'], Dict[str, Any]],
        total_items: int = 0,
        metadata: Optional[Dict] = None
    ) -> JobInfo:
        """
        Run a job asynchronously in a background thread.
        task_func should accept (job_id, job_manager) and return result dict.
        """
        job_info = self.create_job(job_id, job_type, total_items, metadata)
        
        def wrapper():
            if not self.start_job(job_id):
                self.fail_job(job_id, f"Another {job_type.value} job is already running")
                return
            
            try:
                result = task_func(job_id, self)
                self.complete_job(job_id, result)
            except Exception as e:
                self.fail_job(job_id, str(e))
        
        thread = Thread(target=wrapper, daemon=True)
        thread.start()
        
        return job_info


# Global singleton instance
_job_manager: Optional[JobManager] = None
_manager_lock = Lock()


def get_job_manager() -> JobManager:
    """Get the global job manager instance."""
    global _job_manager
    if _job_manager is None:
        with _manager_lock:
            if _job_manager is None:
                _job_manager = JobManager()
    return _job_manager
