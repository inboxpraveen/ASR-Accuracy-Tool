/**
 * Speech Annotation Tool - Frontend Application
 * Handles job management, progress tracking, localStorage persistence, and record locking
 */

// LocalStorage Manager for tracking corrections
class CorrectionTracker {
    constructor() {
        this.storageKey = 'asr_corrections_tracker';
        this.data = this.load();
    }

    load() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            return stored ? JSON.parse(stored) : {};
        } catch (e) {
            console.error('Failed to load correction tracker:', e);
            return {};
        }
    }

    save() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.data));
        } catch (e) {
            console.error('Failed to save correction tracker:', e);
        }
    }

    markCorrected(recordId, originalText, correctedText) {
        this.data[recordId] = {
            corrected: true,
            originalText: originalText,
            correctedText: correctedText,
            timestamp: new Date().toISOString(),
        };
        this.save();
    }

    isCorrected(recordId) {
        return this.data[recordId]?.corrected || false;
    }

    getCorrection(recordId) {
        return this.data[recordId];
    }

    clear() {
        this.data = {};
        this.save();
    }

    getStats() {
        return {
            total: Object.keys(this.data).length,
            corrected: Object.values(this.data).filter(d => d.corrected).length,
        };
    }
}

// Job Status Tracker
class JobTracker {
    constructor() {
        this.currentJobId = null;
        this.pollInterval = null;
        this.pollingFrequency = 2000; // 2 seconds
    }

    startTracking(jobId) {
        this.currentJobId = jobId;
        this.showJobBanner();
        this.startPolling();
    }

    stopTracking() {
        this.currentJobId = null;
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    showJobBanner() {
        document.getElementById('jobStatusBanner').style.display = 'block';
    }

    hideJobBanner() {
        document.getElementById('jobStatusBanner').style.display = 'none';
        this.stopTracking();
    }

    updateBanner(jobInfo) {
        const statusText = document.getElementById('jobStatusText');
        const progressBar = document.getElementById('jobProgressBar');
        const progressText = document.getElementById('jobProgressText');

        const statusMessages = {
            pending: 'Job pending...',
            running: `Processing ${jobInfo.job_type}...`,
            completed: 'Job completed successfully!',
            failed: 'Job failed',
            cancelled: 'Job cancelled',
        };

        statusText.textContent = statusMessages[jobInfo.status] || 'Processing...';
        progressBar.style.width = `${jobInfo.progress}%`;
        progressText.textContent = `${jobInfo.processed_items} / ${jobInfo.total_items} items processed`;

        if (jobInfo.status === 'completed') {
            progressBar.classList.remove('progress-bar-animated');
            progressBar.classList.add('bg-success');
            setTimeout(() => {
                this.hideJobBanner();
                app.refreshRecords();
            }, 3000);
        } else if (jobInfo.status === 'failed') {
            progressBar.classList.remove('progress-bar-animated');
            progressBar.classList.add('bg-danger');
            statusText.textContent = `Error: ${jobInfo.error || 'Unknown error'}`;
        }
    }

    async startPolling() {
        if (!this.currentJobId) return;

        this.pollInterval = setInterval(async () => {
            if (!this.currentJobId) {
                this.stopTracking();
                return;
            }

            try {
                const response = await fetch(`/api/jobs/${this.currentJobId}`);
                if (response.ok) {
                    const jobInfo = await response.json();
                    this.updateBanner(jobInfo);

                    if (jobInfo.status === 'completed' || jobInfo.status === 'failed') {
                        this.stopTracking();
                    }
                }
            } catch (e) {
                console.error('Failed to poll job status:', e);
            }
        }, this.pollingFrequency);
    }
}

// Main Application
class ASRApp {
    constructor() {
        this.correctionTracker = new CorrectionTracker();
        this.jobTracker = new JobTracker();
        this.autoRefreshInterval = null;
        this.refreshFrequency = 10000; // 10 seconds
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startAutoRefresh();
        this.refreshRecords();
        this.updateStats();
    }

    setupEventListeners() {
        // Browse buttons
        document.getElementById('browseAudio')?.addEventListener('click', () => this.browseFolder('folderPath'));
        document.getElementById('browseChunk')?.addEventListener('click', () => this.browseFolder('chunkFolder'));
        document.getElementById('browseExcel')?.addEventListener('click', () => this.browseExcel('excelPath'));

        // Form submissions
        document.getElementById('start-transcribe-form')?.addEventListener('submit', (e) => this.handleTranscribeSubmit(e));
        document.getElementById('manual-load-form')?.addEventListener('submit', (e) => this.handleManualLoadSubmit(e));

        // Export buttons
        document.getElementById('exportXlsx')?.addEventListener('click', () => this.exportRecords('xlsx'));
        document.getElementById('exportCsv')?.addEventListener('click', () => this.exportRecords('csv'));

        // Refresh button
        document.getElementById('refreshRecords')?.addEventListener('click', () => this.refreshRecords());

        // Job status dismiss
        document.getElementById('dismissJobStatus')?.addEventListener('click', () => this.jobTracker.hideJobBanner());

        // Table event delegation
        const table = document.getElementById('transcriptionTable');
        if (table) {
            table.addEventListener('click', (e) => this.handleTableClick(e));
        }
    }

    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(() => {
            this.refreshRecords(true); // Silent refresh
        }, this.refreshFrequency);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }

    async browseFolder(inputId) {
        try {
            const response = await fetch('/api/browse?kind=dir');
            const data = await response.json();
            if (response.ok && data.path) {
                document.getElementById(inputId).value = data.path;
            } else {
                this.showToast(data.error || 'Failed to browse', 'warning');
            }
        } catch (e) {
            this.showToast('Browse not available in this environment. Please type the path manually.', 'info');
        }
    }

    async browseExcel(inputId) {
        try {
            const response = await fetch('/api/browse?kind=excel');
            const data = await response.json();
            if (response.ok && data.path) {
                document.getElementById(inputId).value = data.path;
            } else {
                this.showToast(data.error || 'Failed to browse', 'warning');
            }
        } catch (e) {
            this.showToast('Browse not available. Please type the path manually.', 'info');
        }
    }

    async handleTranscribeSubmit(e) {
        e.preventDefault();
        
        const folder = document.getElementById('folderPath').value;
        const modelName = document.getElementById('modelName').value;

        if (!folder) {
            this.showToast('Please select an audio folder', 'warning');
            return;
        }

        const btn = e.target.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Starting...';

        try {
            const response = await fetch('/api/jobs/transcribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ folder, model_name: modelName }),
            });

            const data = await response.json();

            if (response.ok) {
                this.showToast(`Transcription job started! Processing ${data.total_files} file(s)`, 'success');
                this.jobTracker.startTracking(data.job_id);
                e.target.reset();
            } else if (response.status === 409) {
                this.showToast(`Another transcription job is already running (ID: ${data.active_job_id})`, 'warning');
            } else {
                this.showToast(data.error || 'Failed to start transcription', 'danger');
            }
        } catch (e) {
            this.showToast('Failed to start transcription: ' + e.message, 'danger');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="me-2" viewBox="0 0 16 16"><path d="M11.596 8.697l-6.363 3.692c-.54.313-1.233-.066-1.233-.697V4.308c0-.63.692-1.01 1.233-.696l6.363 3.692a.802.802 0 0 1 0 1.393z"/></svg>Start Transcription';
        }
    }

    async handleManualLoadSubmit(e) {
        e.preventDefault();
        
        const chunkFolder = document.getElementById('chunkFolder').value;
        const excelPath = document.getElementById('excelPath').value;

        if (!chunkFolder || !excelPath) {
            this.showToast('Please select both chunk folder and Excel file', 'warning');
            return;
        }

        const btn = e.target.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';

        try {
            const response = await fetch('/api/manual/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chunk_folder: chunkFolder, excel_path: excelPath }),
            });

            const data = await response.json();

            if (response.ok) {
                this.showToast('Import job started successfully!', 'success');
                this.jobTracker.startTracking(data.job_id);
                e.target.reset();
            } else if (response.status === 409) {
                this.showToast(`Another import job is already running (ID: ${data.active_job_id})`, 'warning');
            } else {
                this.showToast(data.error || 'Failed to import', 'danger');
            }
        } catch (e) {
            this.showToast('Failed to import: ' + e.message, 'danger');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="me-2" viewBox="0 0 16 16"><path d="M11 5a3 3 0 1 1-6 0 3 3 0 0 1 6 0ZM8 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm.256 7a4.474 4.474 0 0 1-.229-1.004H3c.001-.246.154-.986.832-1.664C4.484 10.68 5.711 10 8 10c.26 0 .507.009.74.025.226-.341.496-.65.804-.918C9.077 9.038 8.564 9 8 9c-5 0-6 3-6 4s1 1 1 1h5.256Z"/><path d="M16 12.5a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Zm-1.993-1.679a.5.5 0 0 0-.686.172l-1.17 1.95-.547-.547a.5.5 0 0 0-.708.708l.774.773a.75.75 0 0 0 1.174-.144l1.335-2.226a.5.5 0 0 0-.172-.686Z"/></svg>Load for Review';
        }
    }

    async refreshRecords(silent = false) {
        try {
            const response = await fetch('/api/records');
            if (!response.ok) {
                if (!silent) this.showToast('Failed to fetch records', 'danger');
                return;
            }

            const records = await response.json();
            this.renderRecords(records);
            this.updateStats();
        } catch (e) {
            if (!silent) this.showToast('Failed to refresh records: ' + e.message, 'danger');
        }
    }

    renderRecords(records) {
        const tbody = document.querySelector('#transcriptionTable tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        records.forEach((record, index) => {
            const tr = document.createElement('tr');
            tr.dataset.id = record.id;
            tr.dataset.filename = record.filename;
            
            const isLocked = record.locked === true || record.locked === 'True' || record.locked === 1;
            const isCorrected = this.correctionTracker.isCorrected(record.id);
            
            if (isLocked) {
                tr.classList.add('locked-row');
            }

            tr.innerHTML = `
                <td class="text-muted">${index + 1}</td>
                <td>
                    <audio controls preload="none" class="w-100">
                        <source src="${this.buildSegmentUrl(record.filename)}" type="audio/wav">
                    </audio>
                </td>
                <td class="original-text">${this.escapeHtml(record.transcription || '')}</td>
                <td contenteditable="${!isLocked}" 
                    class="editable ${isLocked ? 'locked' : ''} ${isCorrected ? 'corrected' : ''}" 
                    data-original="${this.escapeHtml(record.correct_transcripts || '')}">${this.escapeHtml(record.correct_transcripts || '')}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-success save-btn" ${isLocked ? 'disabled' : ''}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 0 1 .02-.022z"/>
                            </svg>
                            Save
                        </button>
                        ${isLocked ? `
                            <button class="btn btn-sm btn-outline-warning unlock-btn">
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                                    <path d="M11 1a2 2 0 0 0-2 2v4a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h5V3a3 3 0 0 1 6 0v4a.5.5 0 0 1-1 0V3a2 2 0 0 0-2-2z"/>
                                </svg>
                                Unlock
                            </button>
                        ` : `
                            <button class="btn btn-sm btn-outline-secondary lock-btn">
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                                    <path d="M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2zm3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/>
                                </svg>
                                Lock
                            </button>
                        `}
                    </div>
                </td>
            `;

            tbody.appendChild(tr);
        });
    }

    async handleTableClick(e) {
        const row = e.target.closest('tr');
        if (!row || !row.dataset.id) return;

        if (e.target.closest('.save-btn')) {
            await this.saveRecord(row);
        } else if (e.target.closest('.lock-btn')) {
            await this.lockRecord(row);
        } else if (e.target.closest('.unlock-btn')) {
            await this.unlockRecord(row);
        }
    }

    async saveRecord(row) {
        const recordId = row.dataset.id;
        const editableCell = row.querySelector('.editable');
        const correctedText = editableCell.textContent.trim();
        const originalText = editableCell.dataset.original;

        try {
            const response = await fetch('/api/records', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: recordId,
                    corrected_transcription: correctedText,
                }),
            });

            if (response.ok) {
                row.classList.add('save-success');
                setTimeout(() => row.classList.remove('save-success'), 1200);
                
                // Track correction in localStorage
                this.correctionTracker.markCorrected(recordId, originalText, correctedText);
                editableCell.classList.add('corrected');
                
                this.showToast('Record saved successfully', 'success');
                this.updateStats();
            } else {
                const data = await response.json();
                this.showToast(data.error || 'Failed to save record', 'danger');
            }
        } catch (e) {
            this.showToast('Failed to save: ' + e.message, 'danger');
        }
    }

    async lockRecord(row) {
        const recordId = row.dataset.id;

        try {
            const response = await fetch(`/api/records/${recordId}/lock`, {
                method: 'POST',
            });

            if (response.ok) {
                this.showToast('Record locked successfully', 'success');
                await this.refreshRecords(true);
            } else {
                const data = await response.json();
                this.showToast(data.error || 'Failed to lock record', 'danger');
            }
        } catch (e) {
            this.showToast('Failed to lock: ' + e.message, 'danger');
        }
    }

    async unlockRecord(row) {
        const recordId = row.dataset.id;

        try {
            const response = await fetch(`/api/records/${recordId}/unlock`, {
                method: 'POST',
            });

            if (response.ok) {
                this.showToast('Record unlocked successfully', 'success');
                await this.refreshRecords(true);
            } else {
                const data = await response.json();
                this.showToast(data.error || 'Failed to unlock record', 'danger');
            }
        } catch (e) {
            this.showToast('Failed to unlock: ' + e.message, 'danger');
        }
    }

    async exportRecords(format) {
        try {
            const response = await fetch('/api/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ format }),
            });

            if (!response.ok) {
                this.showToast('Failed to export', 'danger');
                return;
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = format === 'csv' ? 'transcriptions_export.csv' : 'transcriptions_export.xlsx';
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            this.showToast(`Exported successfully as ${format.toUpperCase()}`, 'success');
        } catch (e) {
            this.showToast('Export failed: ' + e.message, 'danger');
        }
    }

    updateStats() {
        const tbody = document.querySelector('#transcriptionTable tbody');
        if (!tbody) return;

        const rows = tbody.querySelectorAll('tr');
        const totalRecords = rows.length;
        const lockedRecords = tbody.querySelectorAll('tr.locked-row').length;
        const correctedRecords = this.correctionTracker.getStats().corrected;

        document.getElementById('totalRecords').textContent = totalRecords;
        document.getElementById('lockedRecords').textContent = lockedRecords;
        document.getElementById('correctedRecords').textContent = correctedRecords;
    }

    buildSegmentUrl(fullPath) {
        return `/segments?path=${encodeURIComponent(fullPath)}`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showToast(message, type = 'info') {
        // Simple alert for now - can be enhanced with a toast library
        const alertClass = {
            success: 'alert-success',
            danger: 'alert-danger',
            warning: 'alert-warning',
            info: 'alert-info',
        }[type] || 'alert-info';

        console.log(`[${type.toUpperCase()}] ${message}`);
        
        // Could implement a proper toast notification system here
        if (type === 'danger' || type === 'warning') {
            alert(message);
        }
    }
}

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ASRApp();
});
