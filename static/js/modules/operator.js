class OperatorDashboard {
    constructor() {
        this.currentJob = null;
        this.init();
    }

    init() {
        this.attachEventListeners();
        this.loadAllocatedJobs();
    }

    attachEventListeners() {
        const startJobBtn = document.getElementById('startJobBtn');
        const endJobBtn = document.getElementById('endJobBtn');
        const addManualJobBtn = document.getElementById('addManualJobBtn');
        const saveManualJobBtn = document.getElementById('saveManualJobBtn');

        if (startJobBtn) startJobBtn.addEventListener('click', () => this.confirmStartJob());
        if (endJobBtn) endJobBtn.addEventListener('click', () => this.confirmEndJob());
        if (addManualJobBtn) addManualJobBtn.addEventListener('click', () => this.showManualJobModal());
        if (saveManualJobBtn) saveManualJobBtn.addEventListener('click', () => this.addManualJob());
    }

    async loadAllocatedJobs() {
        try {
            const response = await API.operator.getAllocatedJobs();
            this.renderJobs(response.data);
        } catch (error) {
            showNotification('Failed to load jobs', 'error');
        }
    }

    renderJobs(jobs) {
        const container = document.getElementById('jobsContainer');
        if (!container) return;

        if (!jobs || jobs.length === 0) {
            container.innerHTML = '<div class="card"><p class="text-center">No jobs allocated to you at this time</p></div>';
            return;
        }

        container.innerHTML = jobs.map(job => `
            <div class="card job-card ${job.status === 'in_progress' ? 'job-active' : ''}" data-job-id="${job.id}">
                <div class="job-header">
                    <h3>Order: ${escapeHtml(job.order_number)}</h3>
                    <span class="status-badge status-${job.status}">${job.status}</span>
                </div>
                <div class="job-details">
                    <div class="detail-row">
                        <span class="detail-label">Product:</span>
                        <span class="detail-value">${escapeHtml(job.product_name || '-')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Quantity:</span>
                        <span class="detail-value">${job.scheduled_quantity}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Machine:</span>
                        <span class="detail-value">${escapeHtml(job.machine_name || '-')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Stage:</span>
                        <span class="detail-value">${escapeHtml(job.stage_name || '-')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Scheduled:</span>
                        <span class="detail-value">${formatDate(job.scheduled_date)}</span>
                    </div>
                    ${job.started_at ? `
                    <div class="detail-row">
                        <span class="detail-label">Started:</span>
                        <span class="detail-value">${formatDateTime(job.started_at)}</span>
                    </div>
                    ` : ''}
                </div>
                <div class="job-actions">
                    ${job.status === 'scheduled' ? `
                        <button class="btn btn-primary btn-block" data-action="start" data-job-id="${job.id}">Start Job</button>
                    ` : ''}
                    ${job.status === 'in_progress' ? `
                        <button class="btn btn-success btn-block" data-action="end" data-job-id="${job.id}">End Job</button>
                    ` : ''}
                </div>
            </div>
        `).join('');

        container.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const jobId = parseInt(e.target.dataset.jobId);
                this.handleJobAction(action, jobId);
            });
        });
    }

    handleJobAction(action, jobId) {
        const job = this.findJobById(jobId);
        if (!job) return;

        this.currentJob = job;

        if (action === 'start') {
            this.confirmStartJob();
        } else if (action === 'end') {
            this.confirmEndJob();
        }
    }

    findJobById(jobId) {
        const jobCard = document.querySelector(`[data-job-id="${jobId}"]`);
        if (!jobCard) return null;
        
        return {
            id: jobId,
            order_number: jobCard.querySelector('h3').textContent.replace('Order: ', '')
        };
    }

    confirmStartJob() {
        if (!this.currentJob) {
            const firstScheduledJob = document.querySelector('[data-action="start"]');
            if (firstScheduledJob) {
                const jobId = parseInt(firstScheduledJob.dataset.jobId);
                this.currentJob = this.findJobById(jobId);
            }
        }

        if (!this.currentJob) {
            showNotification('Please select a job to start', 'warning');
            return;
        }

        showModal('confirmStartModal');
    }

    async startJob() {
        if (!this.currentJob) return;

        try {
            await API.operator.startJob(this.currentJob.id);
            showNotification('Job started successfully', 'success');
            hideModal('confirmStartModal');
            this.loadAllocatedJobs();
            this.currentJob = null;
        } catch (error) {
            showNotification(error.message || 'Failed to start job', 'error');
        }
    }

    confirmEndJob() {
        if (!this.currentJob) {
            const firstActiveJob = document.querySelector('[data-action="end"]');
            if (firstActiveJob) {
                const jobId = parseInt(firstActiveJob.dataset.jobId);
                this.currentJob = this.findJobById(jobId);
            }
        }

        if (!this.currentJob) {
            showNotification('Please select a job to end', 'warning');
            return;
        }

        showModal('endJobModal');
    }

    async endJob() {
        if (!this.currentJob) return;

        const completedQty = document.getElementById('completedQuantity').value;
        if (!completedQty || completedQty <= 0) {
            showNotification('Please enter valid completed quantity', 'warning');
            return;
        }

        const notes = document.getElementById('jobNotes').value;

        try {
            await API.operator.endJob(this.currentJob.id, {
                actual_quantity: parseInt(completedQty),
                notes: notes || null
            });

            showNotification('Job completed successfully', 'success');
            hideModal('endJobModal');
            this.loadAllocatedJobs();
            this.currentJob = null;
            document.getElementById('endJobForm').reset();
        } catch (error) {
            showNotification(error.message || 'Failed to end job', 'error');
        }
    }

    showManualJobModal() {
        showModal('manualJobModal');
    }

    async addManualJob() {
        const orderNumber = document.getElementById('manualOrderNumber').value;
        if (!orderNumber) {
            showNotification('Please enter order number', 'warning');
            return;
        }

        try {
            await API.operator.addManualJob({ order_number: orderNumber });
            showNotification('Job added successfully', 'success');
            hideModal('manualJobModal');
            this.loadAllocatedJobs();
            document.getElementById('manualJobForm').reset();
        } catch (error) {
            showNotification(error.message || 'Failed to add manual job', 'error');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const confirmStartBtn = document.getElementById('confirmStartJobBtn');
    const confirmEndBtn = document.getElementById('confirmEndJobBtn');

    if (confirmStartBtn) {
        confirmStartBtn.addEventListener('click', () => {
            if (window.operatorDashboard) {
                window.operatorDashboard.startJob();
            }
        });
    }

    if (confirmEndBtn) {
        confirmEndBtn.addEventListener('click', () => {
            if (window.operatorDashboard) {
                window.operatorDashboard.endJob();
            }
        });
    }

    window.operatorDashboard = new OperatorDashboard();
});
