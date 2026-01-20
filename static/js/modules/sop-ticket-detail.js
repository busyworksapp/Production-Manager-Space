let currentTicket = null;
let currentUser = null;
let ticketId = null;

async function init() {
    currentUser = getCurrentUser();
    if (currentUser) {
        document.getElementById('username').textContent = `${currentUser.first_name} ${currentUser.last_name}`;
    }
    
    ticketId = window.location.pathname.split('/').pop();
    
    attachEventListeners();
    await loadDepartments();
    await loadTicketDetails();
}

function attachEventListeners() {
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => logout());
    }

    const reassignForm = document.getElementById('reassignForm');
    if (reassignForm) {
        reassignForm.addEventListener('submit', (e) => handleReassign(e));
    }

    const rejectForm = document.getElementById('rejectForm');
    if (rejectForm) {
        rejectForm.addEventListener('submit', (e) => handleReject(e));
    }

    const ncrForm = document.getElementById('ncrForm');
    if (ncrForm) {
        ncrForm.addEventListener('submit', (e) => handleNcrSubmit(e));
    }

    const hodDecisionForm = document.getElementById('hodDecisionForm');
    if (hodDecisionForm) {
        hodDecisionForm.addEventListener('submit', (e) => handleHodDecision(e));
    }

    const hodDecisionSelect = document.getElementById('hodDecision');
    if (hodDecisionSelect) {
        hodDecisionSelect.addEventListener('change', () => {
            const finalDeptGroup = document.getElementById('finalDeptGroup');
            if (hodDecisionSelect.value === 'assign') {
                finalDeptGroup.style.display = 'block';
                document.getElementById('finalDepartmentId').required = true;
            } else {
                finalDeptGroup.style.display = 'none';
                document.getElementById('finalDepartmentId').required = false;
            }
        });
    }
}

async function loadDepartments() {
    try {
        const response = await API.departments.getAll();
        if (response.success) {
            const selects = ['newDepartmentId', 'finalDepartmentId'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (select) {
                    select.innerHTML = '<option value="">Select Department...</option>' +
                        response.data.map(dept => 
                            `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`
                        ).join('');
                }
            });
        }
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

async function loadTicketDetails() {
    try {
        const response = await API.sop.getTicket(ticketId);
        
        if (response.success) {
            currentTicket = response.data;
            renderTicketDetails(currentTicket);
            renderWorkflowTimeline(currentTicket);
            renderActionButtons(currentTicket);
            
            if (currentTicket.ncr) {
                renderNCR(currentTicket.ncr);
            }
        } else {
            showNotification(response.error || 'Failed to load ticket', 'error');
        }
    } catch (error) {
        console.error('Error loading ticket:', error);
        showNotification('Failed to load ticket details', 'error');
    }
}

function renderTicketDetails(ticket) {
    document.getElementById('ticketTitle').textContent = `SOP Ticket: ${ticket.ticket_number}`;
    document.getElementById('ticketNumber').textContent = ticket.ticket_number;
    document.getElementById('sopReference').textContent = ticket.sop_reference || '-';
    document.getElementById('ticketStatus').innerHTML = createStatusBadge(ticket.status);
    document.getElementById('chargingDept').textContent = ticket.charging_department_name || '-';
    document.getElementById('chargedDept').textContent = ticket.charged_department_name || '-';
    document.getElementById('createdBy').textContent = ticket.created_by_name || '-';
    document.getElementById('createdAt').textContent = formatDateTime(ticket.created_at);
    document.getElementById('failureDesc').textContent = ticket.failure_description || '-';
    document.getElementById('impactDesc').textContent = ticket.impact_description || '-';
    
    const isReadOnly = ticket.status === 'ncr_completed' || ticket.status === 'closed';
    if (isReadOnly) {
        document.getElementById('readonlyNotice').style.display = 'block';
    }
    
    if (ticket.escalated_to_hod && !ticket.hod_decision_date) {
        document.getElementById('escalationNotice').style.display = 'block';
    }
    
    if (ticket.reassignment_reason) {
        document.getElementById('reassignmentInfo').style.display = 'block';
        document.getElementById('reassignmentReason').textContent = ticket.reassignment_reason;
    }
    
    if (ticket.rejection_reason) {
        document.getElementById('rejectionInfo').style.display = 'block';
        document.getElementById('rejectionReason').textContent = ticket.rejection_reason;
    }
}

function renderWorkflowTimeline(ticket) {
    const timeline = document.getElementById('workflowTimeline');
    const steps = [];
    
    steps.push({
        title: 'Ticket Created',
        date: ticket.created_at,
        description: `By ${ticket.created_by_name}`,
        status: 'completed'
    });
    
    if (ticket.charged_department_id !== ticket.original_charged_department_id) {
        steps.push({
            title: 'Reassigned',
            date: ticket.updated_at,
            description: `Reassigned to ${ticket.charged_department_name}`,
            status: 'completed'
        });
    }
    
    if (ticket.status === 'rejected') {
        steps.push({
            title: 'Rejected & Escalated',
            date: ticket.updated_at,
            description: 'Escalated to HOD for decision',
            status: 'completed'
        });
    }
    
    if (ticket.hod_decision_date) {
        steps.push({
            title: 'HOD Decision',
            date: ticket.hod_decision_date,
            description: ticket.hod_decision || 'Decision made',
            status: 'completed'
        });
    } else if (ticket.escalated_to_hod) {
        steps.push({
            title: 'Awaiting HOD Decision',
            date: null,
            description: 'Pending HOD review',
            status: 'current'
        });
    }
    
    if (ticket.ncr_completed_at) {
        steps.push({
            title: 'NCR Completed',
            date: ticket.ncr_completed_at,
            description: 'Non-Conformance Report completed',
            status: 'completed'
        });
    } else if (ticket.status === 'open' || ticket.status === 'reassigned') {
        steps.push({
            title: 'Pending NCR',
            date: null,
            description: 'Awaiting NCR completion',
            status: 'current'
        });
    }
    
    if (ticket.closed_at) {
        steps.push({
            title: 'Ticket Closed',
            date: ticket.closed_at,
            description: 'Ticket successfully closed',
            status: 'completed'
        });
    }
    
    timeline.innerHTML = steps.map((step, index) => `
        <div class="timeline-item">
            ${index < steps.length - 1 ? '<div class="timeline-line"></div>' : ''}
            <div class="timeline-marker ${step.status}">
                ${step.status === 'completed' ? '✓' : (index + 1)}
            </div>
            <div class="timeline-content ${step.status}">
                <strong>${escapeHtml(step.title)}</strong>
                ${step.date ? `<p style="margin: 0.25rem 0; color: #666; font-size: 0.9rem;">${formatDateTime(step.date)}</p>` : ''}
                <p style="margin: 0.5rem 0 0 0;">${escapeHtml(step.description)}</p>
            </div>
        </div>
    `).join('');
}

function renderActionButtons(ticket) {
    const container = document.getElementById('actionButtons');
    const buttons = [];
    
    const isReadOnly = ticket.status === 'ncr_completed' || ticket.status === 'closed';
    const canReassign = ticket.charged_department_id === ticket.original_charged_department_id && 
                        (ticket.status === 'open' || ticket.status === 'reassigned') &&
                        !isReadOnly;
    const canReject = (ticket.status === 'open' || ticket.status === 'reassigned') && !isReadOnly;
    const canCompleteNCR = (ticket.status === 'open' || ticket.status === 'reassigned') && !isReadOnly && !ticket.ncr;
    const isHODEscalated = ticket.escalated_to_hod && !ticket.hod_decision_date;
    
    buttons.push('<a href="/sop/tickets" class="btn btn-secondary">← Back to List</a>');
    
    if (!isReadOnly) {
        if (canReassign) {
            buttons.push('<button class="btn btn-warning" onclick="openReassignModal()">Reassign</button>');
        }
        
        if (canReject) {
            buttons.push('<button class="btn btn-danger" onclick="openRejectModal()">Reject & Escalate</button>');
        }
        
        if (canCompleteNCR) {
            buttons.push('<button class="btn btn-success" onclick="openNcrModal()">Complete NCR</button>');
        }
    }
    
    container.innerHTML = buttons.join('');
    
    const hodCard = document.getElementById('hodDecisionCard');
    if (isHODEscalated && currentUser.role_name === 'HOD') {
        hodCard.style.display = 'block';
    } else {
        hodCard.style.display = 'none';
    }
}

function renderNCR(ncr) {
    const ncrCard = document.getElementById('ncrCard');
    ncrCard.style.display = 'block';
    
    document.getElementById('ncrCompletedBy').textContent = ncr.completed_by_name || '-';
    document.getElementById('ncrCompletionDate').textContent = formatDateTime(ncr.created_at);
    document.getElementById('ncrRootCause').textContent = ncr.root_cause_analysis || '-';
    document.getElementById('ncrCorrectiveActions').textContent = ncr.corrective_actions || '-';
    document.getElementById('ncrPreventiveMeasures').textContent = ncr.preventive_measures || '-';
}

function openReassignModal() {
    showModal('reassignModal');
}

function closeReassignModal() {
    hideModal('reassignModal');
    document.getElementById('reassignForm').reset();
}

async function handleReassign(e) {
    e.preventDefault();
    
    const newDepartmentId = document.getElementById('newDepartmentId').value;
    const reason = document.getElementById('reassignReason').value;
    
    if (!confirm('Are you sure you want to reassign this ticket? This action can only be done once.')) {
        return;
    }
    
    try {
        const response = await API.sop.reassignTicket(ticketId, {
            new_department_id: parseInt(newDepartmentId),
            reason: reason
        });
        
        if (response.success) {
            showNotification('Ticket reassigned successfully', 'success');
            closeReassignModal();
            await loadTicketDetails();
        } else {
            showNotification(response.error || 'Failed to reassign ticket', 'error');
        }
    } catch (error) {
        console.error('Error reassigning ticket:', error);
        showNotification(error.message || 'Failed to reassign ticket', 'error');
    }
}

function openRejectModal() {
    showModal('rejectModal');
}

function closeRejectModal() {
    hideModal('rejectModal');
    document.getElementById('rejectForm').reset();
}

async function handleReject(e) {
    e.preventDefault();
    
    const reason = document.getElementById('rejectReason').value;
    
    if (!confirm('Are you sure you want to reject this ticket? It will be escalated to the HOD.')) {
        return;
    }
    
    try {
        const response = await API.sop.rejectTicket(ticketId, reason);
        
        if (response.success) {
            showNotification('Ticket rejected and escalated to HOD', 'success');
            closeRejectModal();
            await loadTicketDetails();
        } else {
            showNotification(response.error || 'Failed to reject ticket', 'error');
        }
    } catch (error) {
        console.error('Error rejecting ticket:', error);
        showNotification('Failed to reject ticket', 'error');
    }
}

function openNcrModal() {
    showModal('ncrModal');
}

function closeNcrModal() {
    hideModal('ncrModal');
    document.getElementById('ncrForm').reset();
}

async function handleNcrSubmit(e) {
    e.preventDefault();
    
    const data = {
        root_cause_analysis: document.getElementById('rootCauseAnalysis').value,
        corrective_actions: document.getElementById('correctiveActions').value,
        preventive_measures: document.getElementById('preventiveMeasures').value
    };
    
    if (!confirm('Completing the NCR will close this ticket. Continue?')) {
        return;
    }
    
    try {
        const response = await API.sop.createNCR(ticketId, data);
        
        if (response.success) {
            showNotification('NCR completed successfully. Ticket closed.', 'success');
            closeNcrModal();
            await loadTicketDetails();
        } else {
            showNotification(response.error || 'Failed to complete NCR', 'error');
        }
    } catch (error) {
        console.error('Error completing NCR:', error);
        showNotification('Failed to complete NCR', 'error');
    }
}

async function handleHodDecision(e) {
    e.preventDefault();
    
    const decision = document.getElementById('hodDecision').value;
    const finalDepartmentId = document.getElementById('finalDepartmentId').value;
    const decisionNotes = document.getElementById('hodDecisionNotes').value;
    
    const data = {
        decision: decision,
        decision_notes: decisionNotes
    };
    
    if (decision === 'assign' && finalDepartmentId) {
        data.final_department_id = parseInt(finalDepartmentId);
    }
    
    if (!confirm(`Confirm HOD decision: ${decision}?`)) {
        return;
    }
    
    try {
        const response = await API.sop.hodDecision(ticketId, data);
        
        if (response.success) {
            showNotification('HOD decision recorded successfully', 'success');
            await loadTicketDetails();
        } else {
            showNotification(response.error || 'Failed to record decision', 'error');
        }
    } catch (error) {
        console.error('Error recording HOD decision:', error);
        showNotification('Failed to record HOD decision', 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    init();
});
