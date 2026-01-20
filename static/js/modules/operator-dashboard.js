class OperatorDashboardPage {
    constructor() {
        this.currentJob = null;
        this.init();
    }

    init() {
        this.loadEmployeeInfo();
        this.attachEventListeners();
        this.loadJobs();
        this.setupOfflineMonitoring();
    }

    loadEmployeeInfo() {
        const user = getCurrentUser();
        if (user) {
            const nameEl = document.getElementById('employeeName');
            const typeEl = document.getElementById('employeeType');
            const deptEl = document.getElementById('departmentName');
            
            if (nameEl) nameEl.textContent = user.name || user.username;
            if (typeEl) typeEl.textContent = (user.employee_type || 'Operator').replace('_', ' ').toUpperCase();
            if (deptEl) deptEl.textContent = user.department_name || 'Department';
        }
    }

    attachEventListeners() {
        const logoutBtn = document.querySelector('.operator-logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                logout();
            });
        }

        const completeJobBtn = document.querySelector('.complete-btn');
        if (completeJobBtn) {
            completeJobBtn.addEventListener('click', () => this.showCurrentJobActions());
        }

        const defectBtn = document.querySelector('.defect-btn');
        if (defectBtn) {
            defectBtn.addEventListener('click', () => this.reportDefect());
        }

        const pauseBtn = document.querySelector('.pause-btn');
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => this.showBreakOptions());
        }

        const addJobBtn = document.querySelector('.add-job-btn');
        if (addJobBtn) {
            addJobBtn.addEventListener('click', () => showModal('manualJobModal'));
        }

        const completeJobForm = document.getElementById('completeJobForm');
        if (completeJobForm) {
            completeJobForm.addEventListener('submit', (e) => this.handleCompleteJob(e));
        }

        const manualJobForm = document.getElementById('manualJobForm');
        if (manualJobForm) {
            manualJobForm.addEventListener('submit', (e) => this.handleManualJob(e));
        }

        const closeModalBtns = document.querySelectorAll('.close-modal-btn');
        closeModalBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modalId = e.target.getAttribute('data-modal');
                if (modalId) hideModal(modalId);
            });
        });

        const incrementBtn = document.querySelector('.increment-qty-btn');
        if (incrementBtn) {
            incrementBtn.addEventListener('click', () => this.incrementQuantity());
        }

        const decrementBtn = document.querySelector('.decrement-qty-btn');
        if (decrementBtn) {
            decrementBtn.addEventListener('click', () => this.decrementQuantity());
        }
    }

    incrementQuantity() {
        const input = document.getElementById('actualQuantity');
        if (input) {
            input.value = parseInt(input.value || 0) + 1;
        }
    }

    decrementQuantity() {
        const input = document.getElementById('actualQuantity');
        if (input) {
            const currentValue = parseInt(input.value || 0);
            if (currentValue > 0) {
                input.value = currentValue - 1;
            }
        }
    }

    showCurrentJobActions() {
        if (this.currentJob) {
            this.completeJobPrompt(this.currentJob.id, this.currentJob.scheduled_quantity);
        } else {
            showAlert('No job currently in progress', 'warning');
        }
    }

    reportDefect() {
        if (this.currentJob) {
            window.location.href = `/defects/replacement-tickets?job_id=${this.currentJob.id}`;
        } else {
            showAlert('Please start a job first', 'warning');
        }
    }

    showBreakOptions() {
        showAlert('Break tracking coming soon', 'info');
    }

    async loadJobs() {
        try {
            const response = await API.operator.getMyJobs();
            
            if (response.success) {
                const jobs = response.data;
                const inProgressJob = jobs.find(j => j.status === 'in_progress');
                const scheduledJobs = jobs.filter(j => j.status === 'scheduled');
                
                if (inProgressJob) {
                    this.currentJob = inProgressJob;
                    this.showCurrentJob(inProgressJob);
                } else {
                    this.currentJob = null;
                    const currentJobSection = document.getElementById('currentJobSection');
                    if (currentJobSection) {
                        currentJobSection.style.display = 'none';
                    }
                }
                
                this.renderJobsList(scheduledJobs);
            }
        } catch (error) {
            console.error('Error loading jobs:', error);
            showAlert('Failed to load jobs', 'danger');
        }
    }

    showCurrentJob(job) {
        const currentJobSection = document.getElementById('currentJobSection');
        if (currentJobSection) {
            currentJobSection.style.display = 'block';
        }

        const elements = {
            currentJobNumber: job.order_number,
            currentCustomer: job.customer_name || '-',
            currentProduct: job.product_name || '-',
            currentScheduledQty: job.scheduled_quantity || '-',
            currentStage: job.stage_name || 'N/A',
            currentMachine: job.machine_name || 'No Machine'
        };

        Object.keys(elements).forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = elements[id];
        });

        const produced = job.actual_quantity || 0;
        const remaining = (job.scheduled_quantity || 0) - produced;
        
        const producedEl = document.getElementById('producedQty');
        const remainingEl = document.getElementById('remainingQty');
        
        if (producedEl) producedEl.textContent = produced;
        if (remainingEl) remainingEl.textContent = remaining > 0 ? remaining : 0;
    }

    renderJobsList(jobs) {
        const jobsList = document.getElementById('jobsList');
        if (!jobsList) return;

        if (jobs.length === 0) {
            jobsList.innerHTML = '<p class="no-jobs-message">No upcoming jobs</p>';
            return;
        }

        jobsList.innerHTML = jobs.map(job => `
            <div class="card job-card" data-job-id="${job.id}">
                <div class="job-card-header">
                    <div>
                        <div class="job-order-number">${escapeHtml(job.order_number)}</div>
                        <div class="job-customer-name">${escapeHtml(job.customer_name)}</div>
                    </div>
                    <span class="badge badge-info">Scheduled</span>
                </div>
                <div class="job-details-grid">
                    <div><strong>Product:</strong> ${escapeHtml(job.product_name || 'N/A')}</div>
                    <div><strong>Quantity:</strong> ${job.scheduled_quantity}</div>
                    <div><strong>Stage:</strong> ${escapeHtml(job.stage_name || 'N/A')}</div>
                    <div><strong>Machine:</strong> ${escapeHtml(job.machine_name || 'N/A')}</div>
                </div>
                <button class="btn btn-success start-job-btn" data-job-id="${job.id}">
                    Start Job
                </button>
            </div>
        `).join('');

        const startButtons = jobsList.querySelectorAll('.start-job-btn');
        startButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const jobId = parseInt(e.target.getAttribute('data-job-id'));
                this.startJob(jobId);
            });
        });

        const jobCards = jobsList.querySelectorAll('.job-card');
        jobCards.forEach(card => {
            card.addEventListener('click', (e) => {
                if (!e.target.classList.contains('start-job-btn')) {
                    const jobId = parseInt(card.getAttribute('data-job-id'));
                    this.selectJob(jobId);
                }
            });
        });
    }

    selectJob(jobId) {
        console.log('Selected job:', jobId);
    }

    async startJob(jobId) {
        try {
            const response = await API.operator.startJob(jobId, {});
            
            if (response.success) {
                showAlert('Job started successfully', 'success');
                this.loadJobs();
            }
        } catch (error) {
            showAlert(error.message || 'Failed to start job', 'danger');
        }
    }

    completeJobPrompt(jobId, scheduledQty) {
        const jobIdInput = document.getElementById('completingJobId');
        const qtyInput = document.getElementById('actualQuantity');
        
        if (jobIdInput) jobIdInput.value = jobId;
        if (qtyInput) qtyInput.value = scheduledQty;
        
        showModal('completeJobModal');
    }

    async handleCompleteJob(e) {
        e.preventDefault();
        
        const jobId = document.getElementById('completingJobId').value;
        const data = {
            actual_quantity: parseInt(document.getElementById('actualQuantity').value),
            notes: document.getElementById('jobNotes').value
        };
        
        try {
            const response = await API.operator.completeJob(jobId, data);
            
            if (response.success) {
                showAlert('Job completed successfully', 'success');
                hideModal('completeJobModal');
                resetForm('completeJobForm');
                this.loadJobs();
            }
        } catch (error) {
            showAlert(error.message || 'Failed to complete job', 'danger');
        }
    }

    async handleManualJob(e) {
        e.preventDefault();
        
        const data = {
            order_number: document.getElementById('orderNumber').value
        };
        
        try {
            const response = await API.operator.addManualJob(data);
            
            if (response.success) {
                showAlert('Job added successfully', 'success');
                hideModal('manualJobModal');
                resetForm('manualJobForm');
                this.loadJobs();
            }
        } catch (error) {
            showAlert(error.message || 'Failed to add job', 'danger');
        }
    }

    setupOfflineMonitoring() {
        window.addEventListener('online', () => {
            const indicator = document.getElementById('offlineIndicator');
            if (indicator) indicator.style.display = 'none';
            
            const statusIndicator = document.querySelector('.status-indicator');
            if (statusIndicator) {
                statusIndicator.className = 'status-indicator online';
            }
            this.loadJobs();
        });
        
        window.addEventListener('offline', () => {
            const indicator = document.getElementById('offlineIndicator');
            if (indicator) indicator.style.display = 'block';
            
            const statusIndicator = document.querySelector('.status-indicator');
            if (statusIndicator) {
                statusIndicator.className = 'status-indicator offline';
            }
        });
        
        if (!navigator.onLine) {
            const indicator = document.getElementById('offlineIndicator');
            if (indicator) indicator.style.display = 'block';
            
            const statusIndicator = document.querySelector('.status-indicator');
            if (statusIndicator) {
                statusIndicator.className = 'status-indicator offline';
            }
        }
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new OperatorDashboardPage());
} else {
    new OperatorDashboardPage();
}
