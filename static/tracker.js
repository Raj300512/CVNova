// ═══════════════════════════════════════════════════════════════════════════
// ─── Job Tracker — Premium Kanban Board Logic ───────────────────────────
// ═══════════════════════════════════════════════════════════════════════════

// Global State
let allJobs = [];

// DOM Elements
const kanbanCards = {
    'Applied': document.getElementById('cards-applied'),
    'Interviewing': document.getElementById('cards-interviewing'),
    'Offered': document.getElementById('cards-offered'),
    'Rejected': document.getElementById('cards-rejected')
};

const countBadges = {
    'Applied': document.getElementById('count-applied'),
    'Interviewing': document.getElementById('count-interviewing'),
    'Offered': document.getElementById('count-offered'),
    'Rejected': document.getElementById('count-rejected')
};

// Empty state templates
const emptyStates = {
    'Applied': `<div class="empty-column" id="empty-applied">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.3">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
        </svg>
        <span>No applications yet</span>
    </div>`,
    'Interviewing': `<div class="empty-column" id="empty-interviewing">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.3">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
        <span>No interviews scheduled</span>
    </div>`,
    'Offered': `<div class="empty-column" id="empty-offered">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.3">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        <span>No offers yet</span>
    </div>`,
    'Rejected': `<div class="empty-column" id="empty-rejected">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.3">
            <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
        <span>None rejected</span>
    </div>`
};

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    fetchJobs();
    
    // Modal form submit
    document.getElementById('jobForm').addEventListener('submit', handleFormSubmit);
    
    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
});

async function fetchJobs() {
    try {
        const response = await fetch('/api/applications');

        // Login session expire ho gayi ho toh redirect karo
        if (response.redirected || response.status === 401 || response.url.includes('/login')) {
            window.location.href = '/login';
            return;
        }

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();

        // Agar array nahi aaya toh empty treat karo
        allJobs = Array.isArray(data) ? data : [];
        renderBoard();
    } catch (error) {
        console.error('Error fetching jobs:', error);
        showToast('Failed to load applications', 'error');
        // Board ko empty state mein render karo — blank screen nahi dikhega
        allJobs = [];
        renderBoard();
    }
}

function renderBoard() {
    // Clear columns
    Object.values(kanbanCards).forEach(el => el.innerHTML = '');
    
    // Reset counts
    const counts = { 'Applied': 0, 'Interviewing': 0, 'Offered': 0, 'Rejected': 0 };
    
    allJobs.forEach(job => {
        const card = createJobCard(job);
        if (kanbanCards[job.status]) {
            kanbanCards[job.status].appendChild(card);
            counts[job.status]++;
        }
    });
    
    // Show empty states for empty columns
    Object.keys(kanbanCards).forEach(status => {
        if (counts[status] === 0) {
            kanbanCards[status].innerHTML = emptyStates[status];
        }
    });
    
    // Update count badges
    Object.keys(countBadges).forEach(status => {
        countBadges[status].innerText = counts[status];
    });
    
    // Update stats bar
    updateStats(counts);
}

function updateStats(counts) {
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    
    const statTotal = document.getElementById('stat-total');
    const statApplied = document.getElementById('stat-applied');
    const statInterviewing = document.getElementById('stat-interviewing');
    const statOffered = document.getElementById('stat-offered');
    const statRejected = document.getElementById('stat-rejected');
    
    if (statTotal) animateNumber(statTotal, total);
    if (statApplied) animateNumber(statApplied, counts['Applied']);
    if (statInterviewing) animateNumber(statInterviewing, counts['Interviewing']);
    if (statOffered) animateNumber(statOffered, counts['Offered']);
    if (statRejected) animateNumber(statRejected, counts['Rejected']);
}

function animateNumber(el, target) {
    const current = parseInt(el.innerText) || 0;
    if (current === target) return;
    
    const duration = 400;
    const start = performance.now();
    
    function tick(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
        const value = Math.round(current + (target - current) * eased);
        el.innerText = value;
        if (progress < 1) requestAnimationFrame(tick);
    }
    
    requestAnimationFrame(tick);
}

function createJobCard(job) {
    const card = document.createElement('div');
    card.className = 'job-card';
    card.draggable = true;
    card.id = `job-${job.id}`;
    card.dataset.id = job.id;
    
    card.ondragstart = (e) => {
        e.dataTransfer.setData('text/plain', job.id);
        card.classList.add('dragging');
        // Small delay for visual smoothness
        setTimeout(() => card.style.opacity = '0.4', 0);
    };
    card.ondragend = () => {
        card.classList.remove('dragging');
        card.style.opacity = '1';
        // Remove drag-over from all columns
        document.querySelectorAll('.kanban-column').forEach(col => col.classList.remove('drag-over'));
    };

    const dateStr = new Date(job.applied_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

    // Build meta info
    let metaHTML = '';
    if (job.location || job.salary) {
        metaHTML = '<div class="job-card-meta">';
        if (job.location) {
            metaHTML += `<span>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                ${escapeHtml(job.location)}
            </span>`;
        }
        if (job.salary) {
            metaHTML += `<span>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                ${escapeHtml(job.salary)}
            </span>`;
        }
        metaHTML += '</div>';
    }

    // Build link button
    let linkBtn = '';
    if (job.job_url) {
        linkBtn = `<a href="${escapeHtml(job.job_url)}" target="_blank" class="action-btn link" title="Open Posting" onclick="event.stopPropagation()">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        </a>`;
    }

    card.innerHTML = `
        <div class="job-card-role">${escapeHtml(job.role)}</div>
        <div class="job-card-company">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" opacity="0.4"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            ${escapeHtml(job.company)}
        </div>
        ${metaHTML}
        <div class="job-card-footer">
            <span class="job-card-date">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                ${dateStr}
            </span>
            <div class="job-card-actions">
                ${linkBtn}
                <button class="action-btn" onclick="openEmailModal(${job.id})" title="Draft Follow-up Email">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
                </button>
                <button class="action-btn" onclick="editJob(${job.id})" title="Edit">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button class="action-btn delete" onclick="deleteJob(${job.id})" title="Delete">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
            </div>
        </div>
    `;
    return card;
}

// Helper: Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ─── Drag & Drop ─────────────────────────────────────────────────────────

function allowDrop(ev) {
    ev.preventDefault();
}

function dragEnter(ev) {
    ev.preventDefault();
    const column = ev.currentTarget;
    column.classList.add('drag-over');
}

function dragLeave(ev) {
    const column = ev.currentTarget;
    // Only remove if we're actually leaving the column (not entering a child)
    const rect = column.getBoundingClientRect();
    const x = ev.clientX;
    const y = ev.clientY;
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
        column.classList.remove('drag-over');
    }
}

async function drop(ev, newStatus) {
    ev.preventDefault();
    const column = ev.currentTarget;
    column.classList.remove('drag-over');
    
    const jobId = ev.dataTransfer.getData('text/plain');
    
    // Update locally for instant feedback
    const job = allJobs.find(j => j.id == jobId);
    if (job && job.status !== newStatus) {
        const oldStatus = job.status;
        job.status = newStatus;
        renderBoard();
        showToast(`Moved "${job.role}" to ${newStatus}`, 'success');
        
        if (newStatus === 'Offered' && typeof confetti === 'function') {
            confetti({
                particleCount: 150,
                spread: 80,
                origin: { y: 0.6 },
                colors: ['#81c784', '#7c4dff', '#ffb74d']
            });
        }
        
        // Update on server
        try {
            const resp = await fetch(`/api/applications/${jobId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });
            if (!resp.ok) throw new Error('Server error');
        } catch (error) {
            console.error('Error updating status:', error);
            job.status = oldStatus; // Rollback
            renderBoard();
            showToast('Failed to update status', 'error');
        }
    }
}

// ─── Modal Actions ───────────────────────────────────────────────────────

function openModal(jobId = null) {
    const modal = document.getElementById('jobModal');
    const form = document.getElementById('jobForm');
    form.reset();
    document.getElementById('jobId').value = '';
    document.getElementById('modalTitle').innerText = 'Track New Job';
    
    if (jobId) {
        const job = allJobs.find(j => j.id == jobId);
        if (job) {
            document.getElementById('jobId').value = job.id;
            document.getElementById('company').value = job.company;
            document.getElementById('role').value = job.role;
            document.getElementById('location').value = job.location || '';
            document.getElementById('salary').value = job.salary || '';
            document.getElementById('jobUrl').value = job.job_url || '';
            document.getElementById('notes').value = job.notes || '';
            document.getElementById('modalTitle').innerText = 'Edit Job Details';
        }
    }
    
    modal.classList.add('active');
    // Focus first input after animation
    setTimeout(() => document.getElementById('company').focus(), 300);
}

function closeModal() {
    const modal = document.getElementById('jobModal');
    modal.classList.remove('active');
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const saveBtn = document.getElementById('saveBtn');
    const jobId = document.getElementById('jobId').value;
    
    const data = {
        company: document.getElementById('company').value,
        role: document.getElementById('role').value,
        location: document.getElementById('location').value,
        salary: document.getElementById('salary').value,
        job_url: document.getElementById('jobUrl').value,
        notes: document.getElementById('notes').value
    };

    // Show loading state
    saveBtn.disabled = true;
    saveBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation: spin 0.8s linear infinite;"><circle cx="12" cy="12" r="10" stroke-dasharray="60" stroke-dashoffset="20"/></svg>
        Saving...
    `;

    try {
        let response;
        if (jobId) {
            response = await fetch(`/api/applications/${jobId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } else {
            response = await fetch('/api/applications', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }
        
        if (response.ok) {
            closeModal();
            fetchJobs();
            showToast(jobId ? 'Job updated successfully!' : `Added "${data.role}" at ${data.company}`, 'success');
        } else {
            showToast('Error saving job application', 'error');
        }
    } catch (error) {
        console.error('Error saving job:', error);
        showToast('Network error — please try again', 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            Save Job
        `;
        saveBtn.className = 'tracker-btn-save';
    }
}

async function deleteJob(id) {
    if (!confirm('Remove this job from your tracker?')) return;
    
    try {
        const response = await fetch(`/api/applications/${id}`, { method: 'DELETE' });
        if (response.ok) {
            const job = allJobs.find(j => j.id === id);
            allJobs = allJobs.filter(j => j.id !== id);
            renderBoard();
            showToast(`Removed "${job?.role || 'job'}" from tracker`, 'success');
        }
    } catch (error) {
        console.error('Error deleting job:', error);
        showToast('Failed to delete', 'error');
    }
}

function editJob(id) {
    openModal(id);
}

// ─── Feature 6: Email Draft Modal ────────────────────────────────────────

function openEmailModal(jobId) {
    const job = allJobs.find(j => j.id == jobId);
    if (!job) return;

    // Create modal if not exists
    let modal = document.getElementById('emailModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'emailModal';
        modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);backdrop-filter:blur(8px);z-index:2000;display:flex;align-items:center;justify-content:center;padding:20px;';
        modal.innerHTML = `
            <div style="background:var(--card-bg,#1e1e2e);border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:28px;max-width:600px;width:100%;max-height:90vh;overflow-y:auto;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
                    <h3 style="margin:0;">✉️ Draft Email</h3>
                    <button onclick="document.getElementById('emailModal').remove()" style="background:none;border:none;color:rgba(255,255,255,0.5);cursor:pointer;font-size:1.4rem;line-height:1;">×</button>
                </div>
                <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;" id="emailTypeBtns">
                    <button onclick="generateEmail('followup')" class="email-type-btn active" style="padding:8px 16px;border-radius:8px;border:1px solid rgba(187,134,252,0.4);background:rgba(124,77,255,0.15);color:#bb86fc;cursor:pointer;font-size:0.85rem;font-weight:600;">Follow-up</button>
                    <button onclick="generateEmail('thank_you')" class="email-type-btn" style="padding:8px 16px;border-radius:8px;border:1px solid var(--border,rgba(255,255,255,0.1));background:transparent;color:rgba(255,255,255,0.6);cursor:pointer;font-size:0.85rem;font-weight:600;">Thank You</button>
                    <button onclick="generateEmail('withdraw')" class="email-type-btn" style="padding:8px 16px;border-radius:8px;border:1px solid var(--border,rgba(255,255,255,0.1));background:transparent;color:rgba(255,255,255,0.6);cursor:pointer;font-size:0.85rem;font-weight:600;">Withdraw</button>
                </div>
                <div id="emailLoading" style="display:none;text-align:center;padding:30px;color:rgba(255,255,255,0.5);">
                    <div style="width:24px;height:24px;border:3px solid rgba(255,255,255,0.2);border-top-color:#bb86fc;border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 12px;"></div>
                    Generating email...
                </div>
                <textarea id="emailOutput" style="width:100%;min-height:200px;background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:14px;color:#fff;font-family:inherit;font-size:0.9rem;line-height:1.6;resize:vertical;outline:none;box-sizing:border-box;display:none;" placeholder="Email will appear here..."></textarea>
                <div style="display:flex;gap:10px;margin-top:16px;justify-content:flex-end;" id="emailActions" style="display:none;">
                    <button onclick="copyEmail()" style="padding:10px 20px;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.1);border-radius:8px;color:#fff;cursor:pointer;font-size:0.9rem;">Copy</button>
                    <button onclick="document.getElementById('emailModal').remove()" style="padding:10px 20px;background:linear-gradient(135deg,#7c4dff,#bb86fc);border:none;border-radius:8px;color:#fff;cursor:pointer;font-size:0.9rem;font-weight:600;">Done</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
    }

    modal.style.display = 'flex';
    modal._job = job;
    generateEmail('followup');
}

async function generateEmail(type) {
    const modal = document.getElementById('emailModal');
    if (!modal || !modal._job) return;
    const job = modal._job;

    // Update active button
    modal.querySelectorAll('.email-type-btn').forEach(b => {
        const isActive = b.textContent.toLowerCase().includes(type.replace('_', ' ').replace('thank you', 'thank'));
        b.style.background = isActive ? 'rgba(124,77,255,0.15)' : 'transparent';
        b.style.borderColor = isActive ? 'rgba(187,134,252,0.4)' : 'rgba(255,255,255,0.1)';
        b.style.color = isActive ? '#bb86fc' : 'rgba(255,255,255,0.6)';
    });

    document.getElementById('emailLoading').style.display = 'block';
    document.getElementById('emailOutput').style.display = 'none';
    document.getElementById('emailActions').style.display = 'none';

    const appliedDate = new Date(job.applied_at);
    const daysSince = Math.floor((Date.now() - appliedDate.getTime()) / 86400000);

    try {
        const resp = await fetch('/api/generate-followup-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ company: job.company, role: job.role, days_since: daysSince, email_type: type })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error);
        document.getElementById('emailOutput').value = data.email;
        document.getElementById('emailOutput').style.display = 'block';
        document.getElementById('emailActions').style.display = 'flex';
    } catch (e) {
        document.getElementById('emailOutput').value = `Error: ${e.message}`;
        document.getElementById('emailOutput').style.display = 'block';
    } finally {
        document.getElementById('emailLoading').style.display = 'none';
    }
}

function copyEmail() {
    const text = document.getElementById('emailOutput').value;
    navigator.clipboard.writeText(text);
    showToast('Email copied to clipboard!', 'success');
}

// ─── Toast Notifications ─────────────────────────────────────────────────

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success'
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#81c784" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e57373" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
    
    toast.innerHTML = `
        <div style="display:flex; align-items:center; gap:10px;">
            ${icon}<span>${message}</span>
        </div>
        <div class="toast-progress"></div>
    `;
    container.appendChild(toast);
    
    // Auto remove after 3s
    setTimeout(() => {
        toast.style.transition = 'all 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(30px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
