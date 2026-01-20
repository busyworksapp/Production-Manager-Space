let currentWeekStart = null;
let departments = [];
let machines = [];
let calendarEvents = [];

async function init() {
    const user = getCurrentUser();
    if (user) {
        document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
    }
    
    setWeekToToday();
    attachEventListeners();
    await loadDepartments();
    await loadCalendar();
}

function attachEventListeners() {
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => logout());
    }

    const departmentFilter = document.getElementById('departmentFilter');
    if (departmentFilter) {
        departmentFilter.addEventListener('change', () => loadCalendar());
    }

    const startDateFilter = document.getElementById('startDateFilter');
    const endDateFilter = document.getElementById('endDateFilter');
    if (startDateFilter && endDateFilter) {
        startDateFilter.addEventListener('change', () => {
            updateWeekFromDates();
            loadCalendar();
        });
        endDateFilter.addEventListener('change', () => {
            updateWeekFromDates();
            loadCalendar();
        });
    }

    const prevWeek = document.getElementById('prevWeek');
    if (prevWeek) {
        prevWeek.addEventListener('click', () => {
            currentWeekStart.setDate(currentWeekStart.getDate() - 7);
            updateDateInputs();
            loadCalendar();
        });
    }

    const nextWeek = document.getElementById('nextWeek');
    if (nextWeek) {
        nextWeek.addEventListener('click', () => {
            currentWeekStart.setDate(currentWeekStart.getDate() + 7);
            updateDateInputs();
            loadCalendar();
        });
    }

    const todayBtn = document.getElementById('todayBtn');
    if (todayBtn) {
        todayBtn.addEventListener('click', () => {
            setWeekToToday();
            loadCalendar();
        });
    }
}

function setWeekToToday() {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
    currentWeekStart = new Date(today);
    currentWeekStart.setDate(today.getDate() + diff);
    currentWeekStart.setHours(0, 0, 0, 0);
    updateDateInputs();
}

function updateDateInputs() {
    const weekEnd = new Date(currentWeekStart);
    weekEnd.setDate(currentWeekStart.getDate() + 6);
    
    document.getElementById('startDateFilter').value = formatDateInput(currentWeekStart);
    document.getElementById('endDateFilter').value = formatDateInput(weekEnd);
    
    const weekDisplay = document.getElementById('weekDisplay');
    if (weekDisplay) {
        weekDisplay.textContent = `${formatDate(currentWeekStart)} - ${formatDate(weekEnd)}`;
    }
}

function updateWeekFromDates() {
    const startInput = document.getElementById('startDateFilter').value;
    if (startInput) {
        currentWeekStart = new Date(startInput + 'T00:00:00');
    }
}

async function loadDepartments() {
    try {
        const response = await API.departments.getAll();
        if (response.success) {
            departments = response.data;
            const select = document.getElementById('departmentFilter');
            if (select) {
                select.innerHTML = '<option value="">All Departments</option>' +
                    departments.map(dept => 
                        `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`
                    ).join('');
            }
        }
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

async function loadCalendar() {
    const departmentId = document.getElementById('departmentFilter').value;
    const startDate = document.getElementById('startDateFilter').value;
    const endDate = document.getElementById('endDateFilter').value;
    
    if (!startDate || !endDate) {
        return;
    }
    
    try {
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate
        });
        
        if (departmentId) {
            params.append('department_id', departmentId);
        }
        
        const response = await fetch(`/api/machines/calendar?${params}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        
        if (data.success) {
            machines = data.data.machines;
            calendarEvents = data.data.events;
            
            const jobSchedulesResponse = await fetch(`/api/orders/schedules?start_date=${startDate}&end_date=${endDate}${departmentId ? '&department_id=' + departmentId : ''}`, {
                headers: getAuthHeaders()
            });
            const jobSchedulesData = await jobSchedulesResponse.json();
            
            if (jobSchedulesData.success) {
                jobSchedulesData.data.forEach(job => {
                    if (job.machine_id) {
                        calendarEvents.push({
                            id: `job_${job.id}`,
                            type: 'job_schedule',
                            title: `${job.order_number} - ${job.product_name}`,
                            machine_id: job.machine_id,
                            machine_name: job.machine_name,
                            start: job.scheduled_date,
                            status: job.status,
                            customer: job.customer_name,
                            quantity: job.scheduled_quantity
                        });
                    }
                });
            }
            
            renderCalendar();
        }
    } catch (error) {
        console.error('Error loading calendar:', error);
        showNotification('Failed to load calendar data', 'error');
    }
}

function renderCalendar() {
    const grid = document.getElementById('calendarGrid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    grid.appendChild(createHeaderCell('Machine'));
    
    const days = [];
    for (let i = 0; i < 7; i++) {
        const day = new Date(currentWeekStart);
        day.setDate(currentWeekStart.getDate() + i);
        days.push(day);
        
        const dayHeader = createHeaderCell(formatDayOfWeek(day));
        grid.appendChild(dayHeader);
    }
    
    if (machines.length === 0) {
        const emptyCell = document.createElement('div');
        emptyCell.style.gridColumn = '1 / -1';
        emptyCell.style.textAlign = 'center';
        emptyCell.style.padding = '2rem';
        emptyCell.style.color = '#666';
        emptyCell.textContent = 'No machines found for the selected department.';
        grid.appendChild(emptyCell);
        return;
    }
    
    machines.forEach(machine => {
        const machineLabel = document.createElement('div');
        machineLabel.className = 'calendar-machine-label';
        machineLabel.innerHTML = `
            ${escapeHtml(machine.machine_name)}
            <span class="machine-status ${machine.status}">${machine.status}</span>
        `;
        grid.appendChild(machineLabel);
        
        days.forEach(day => {
            const cell = createMachineCell(machine, day);
            grid.appendChild(cell);
        });
    });
}

function createHeaderCell(text) {
    const header = document.createElement('div');
    header.className = 'calendar-day-header';
    header.textContent = text;
    return header;
}

function createMachineCell(machine, day) {
    const cell = document.createElement('div');
    cell.className = 'calendar-cell';
    
    if (machine.status === 'broken' || machine.status === 'retired') {
        cell.classList.add('unavailable');
    } else if (machine.status === 'maintenance') {
        cell.classList.add('maintenance');
    }
    
    const dayStart = formatDateInput(day);
    const dayEnd = formatDateInput(day);
    
    const machineEvents = calendarEvents.filter(event => {
        if (event.machine_id !== machine.id) return false;
        
        const eventDate = event.start.split('T')[0];
        return eventDate === dayStart;
    });
    
    machineEvents.forEach(event => {
        const eventEl = createEventElement(event);
        cell.appendChild(eventEl);
    });
    
    return cell;
}

function createEventElement(event) {
    const eventDiv = document.createElement('div');
    eventDiv.className = 'calendar-event';
    
    if (event.type === 'preventive_maintenance') {
        eventDiv.classList.add('pm');
        eventDiv.textContent = event.title.substring(0, 20);
        eventDiv.title = `${event.title} - ${event.maintenance_type}`;
    } else if (event.type === 'maintenance_ticket') {
        eventDiv.classList.add('mt');
        eventDiv.textContent = event.ticket_number;
        eventDiv.title = event.title;
    } else if (event.type === 'job_schedule') {
        eventDiv.classList.add('job');
        eventDiv.textContent = event.title.substring(0, 20);
        eventDiv.title = `${event.title} - ${event.customer}`;
    }
    
    eventDiv.addEventListener('click', () => showEventDetails(event));
    
    return eventDiv;
}

function showEventDetails(event) {
    const modal = document.getElementById('eventDetailsModal');
    const titleEl = document.getElementById('eventTitle');
    const bodyEl = document.getElementById('eventDetailsBody');
    
    let detailsHTML = '';
    
    if (event.type === 'preventive_maintenance') {
        titleEl.textContent = 'Preventive Maintenance';
        detailsHTML = `
            <div class="detail-row">
                <div class="detail-label">Schedule Name:</div>
                <div class="detail-value">${escapeHtml(event.title)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Machine:</div>
                <div class="detail-value">${escapeHtml(event.machine_name)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Maintenance Type:</div>
                <div class="detail-value">${escapeHtml(event.maintenance_type)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Scheduled Date:</div>
                <div class="detail-value">${formatDateTime(event.start)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Duration:</div>
                <div class="detail-value">${event.duration_minutes} minutes</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Priority:</div>
                <div class="detail-value"><span class="badge badge-${event.priority}">${event.priority}</span></div>
            </div>
            ${event.technician ? `
            <div class="detail-row">
                <div class="detail-label">Technician:</div>
                <div class="detail-value">${escapeHtml(event.technician)}</div>
            </div>` : ''}
            ${event.description ? `
            <div class="detail-row">
                <div class="detail-label">Description:</div>
                <div class="detail-value">${escapeHtml(event.description)}</div>
            </div>` : ''}
        `;
    } else if (event.type === 'maintenance_ticket') {
        titleEl.textContent = 'Maintenance Ticket';
        detailsHTML = `
            <div class="detail-row">
                <div class="detail-label">Ticket Number:</div>
                <div class="detail-value">${escapeHtml(event.ticket_number)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Machine:</div>
                <div class="detail-value">${escapeHtml(event.machine_name)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Status:</div>
                <div class="detail-value"><span class="badge badge-${event.status}">${event.status}</span></div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Severity:</div>
                <div class="detail-value"><span class="badge badge-${event.severity}">${event.severity}</span></div>
            </div>
            ${event.assigned_to ? `
            <div class="detail-row">
                <div class="detail-label">Assigned To:</div>
                <div class="detail-value">${escapeHtml(event.assigned_to)}</div>
            </div>` : ''}
            <div class="detail-row">
                <div class="detail-label">Description:</div>
                <div class="detail-value">${event.title.replace(event.ticket_number + ' - ', '')}</div>
            </div>
        `;
    } else if (event.type === 'job_schedule') {
        titleEl.textContent = 'Scheduled Job';
        detailsHTML = `
            <div class="detail-row">
                <div class="detail-label">Order:</div>
                <div class="detail-value">${event.title.split(' - ')[0]}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Customer:</div>
                <div class="detail-value">${escapeHtml(event.customer)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Product:</div>
                <div class="detail-value">${event.title.split(' - ')[1]}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Machine:</div>
                <div class="detail-value">${escapeHtml(event.machine_name)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Quantity:</div>
                <div class="detail-value">${event.quantity}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Status:</div>
                <div class="detail-value"><span class="badge badge-${event.status}">${event.status}</span></div>
            </div>
        `;
    }
    
    bodyEl.innerHTML = detailsHTML;
    showModal('eventDetailsModal');
}

function formatDayOfWeek(date) {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return `${days[date.getDay()]}<br><small>${formatDate(date)}</small>`;
}

function formatDateInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}
