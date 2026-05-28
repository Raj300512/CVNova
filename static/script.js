/**
 * CVNova — Frontend Logic
 * Handles file upload, API communication, and dashboard rendering.
 */

document.addEventListener('DOMContentLoaded', () => {
    // ─── Hero Dynamic Text Logic ────────────────────────────────────────
    const dynamicTexts = document.querySelectorAll('.dynamic-text');
    if (dynamicTexts.length > 0) {
        let currentIndex = 0;
        setInterval(() => {
            const current = dynamicTexts[currentIndex];
            current.classList.remove('active');
            current.classList.add('out');
            
            setTimeout(() => {
                current.classList.remove('out');
            }, 600); // wait for transition to finish

            currentIndex = (currentIndex + 1) % dynamicTexts.length;
            dynamicTexts[currentIndex].classList.add('active');
        }, 2500); // Change text every 2.5 seconds
    }

    // ─── Upload Page Logic ──────────────────────────────────────────────
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        initUploadPage();
    }

    // ─── Dashboard Page Logic ───────────────────────────────────────────
    const resultsContainer = document.getElementById('resultsContainer');
    if (resultsContainer) {
        initDashboard();
        initChatWidget();
    }
});


/* ═══════════════════════════════════════════════════════════════════════════ */
/* ─── UPLOAD PAGE ─────────────────────────────────────────────────────────── */
/* ═══════════════════════════════════════════════════════════════════════════ */

function initUploadPage() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const fileRemove = document.getElementById('fileRemove');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const uploadForm = document.getElementById('uploadForm');
    const errorToast = document.getElementById('errorToast');
    const errorMessage = document.getElementById('errorMessage');
    const jobRole = document.getElementById('jobRole');
    const customRoleRow = document.getElementById('customRoleRow');
    const customRoleInput = document.getElementById('customRole');

    let selectedFile = null;

    // Drop zone click
    dropZone.addEventListener('click', () => fileInput.click());

    // Drag & drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFile(files[0]);
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleFile(e.target.files[0]);
    });

    // Custom role toggle
    jobRole.addEventListener('change', () => {
        if (jobRole.value === 'custom') {
            customRoleRow.style.display = 'grid';
            customRoleInput.required = true;
            customRoleInput.focus();
        } else {
            customRoleRow.style.display = 'none';
            customRoleInput.required = false;
        }
    });

    // Remove file
    fileRemove.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        filePreview.style.display = 'none';
        dropZone.style.display = 'flex';
        analyzeBtn.disabled = true;
        hideError();
    });

    function handleFile(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['pdf', 'docx'].includes(ext)) {
            showError('Invalid file type. Please upload a PDF or DOCX file.');
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            showError('File too large. Maximum size is 10MB.');
            return;
        }

        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        filePreview.style.display = 'flex';
        dropZone.style.display = 'none';
        analyzeBtn.disabled = false;
        hideError();
    }

    // Submit form
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!selectedFile) return;

        const btnText = analyzeBtn.querySelector('.btn-text');
        const btnLoading = analyzeBtn.querySelector('.btn-loading');

        // Show loading
        btnText.style.display = 'none';
        btnLoading.style.display = 'flex';
        analyzeBtn.disabled = true;
        hideError();

        const formData = new FormData();
        formData.append('resume', selectedFile);
        formData.append('job_role', jobRole.value);
        formData.append('job_description', document.getElementById('jobDescription').value);

        if (jobRole.value === 'custom') {
            formData.append('custom_role', customRoleInput.value);
        }

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Something went wrong');
            }

            // Store results and redirect to dashboard
            sessionStorage.setItem('analysisResults', JSON.stringify(data));
            window.location.href = '/dashboard';

        } catch (err) {
            showError(err.message);
            btnText.style.display = 'flex';
            btnLoading.style.display = 'none';
            analyzeBtn.disabled = false;
        }
    });

    function showError(msg) {
        errorMessage.textContent = msg;
        errorToast.style.display = 'flex';
    }

    function hideError() {
        errorToast.style.display = 'none';
    }
}


/* ═══════════════════════════════════════════════════════════════════════════ */
/* ─── DASHBOARD ───────────────────────────────────────────────────────────── */
/* ═══════════════════════════════════════════════════════════════════════════ */

function initDashboard() {
    const data = sessionStorage.getItem('analysisResults');
    if (!data) {
        window.location.href = '/';
        return;
    }

    const results = JSON.parse(data);
    const loadingState = document.getElementById('loadingState');
    const dashboardMain = document.getElementById('dashboardMain');

    // Show loading briefly for effect
    loadingState.style.display = 'flex';

    setTimeout(() => {
        loadingState.style.display = 'none';
        if (dashboardMain) {
            dashboardMain.style.display = ''; // Clear inline display:none
        }
        renderResults(results);
    }, 1200);

    // Download Report Button
    const downloadBtn = document.getElementById('downloadReportBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => downloadReport(results));
    }

    // Share Analysis Button
    const shareBtn = document.getElementById('shareAnalysisBtn');
    if (shareBtn) {
        shareBtn.addEventListener('click', () => shareAnalysis(results));
    }

    // Save for Comparison Button
    const saveCompareBtn = document.getElementById('saveForCompareBtn');
    if (saveCompareBtn) {
        saveCompareBtn.addEventListener('click', () => saveForCompare(results));
    }
}


function renderResults(data) {
    // Header & Sidebar Info
    document.getElementById('dashSubtitle').textContent = `${data.filename} • ${data.role} • ${data.word_count} words`;

    if (data.identity && data.identity.name !== "Not Detected") {
        document.getElementById('navCandidateName').textContent = data.identity.name;
    } else {
        document.getElementById('navCandidateName').textContent = "Candidate";
    }
    document.getElementById('navCandidateRole').textContent = data.role;

    // Core Init
    initTabs(data);

    // Render Individual Tabs
    renderOverviewTab(data);
    renderExtractedDataTab(data.identity, data.sections);
    renderAtsAnalysisTab(data);
    renderJobMatchTab(data);
    renderImprovementsTab(data);
    renderInsightsTab(data);
    renderAiRewriteTab(data);
    renderCareersTab(data);
    renderAnalyticsTab();
}

function initTabs(data) {
    const tabs = document.querySelectorAll('.nav-item');
    const panes = document.querySelectorAll('.tab-pane');

    if (data.jd_match) {
        document.getElementById('navJobMatch').style.display = 'flex';
    }

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            panes.forEach(p => p.classList.remove('active'));

            tab.classList.add('active');
            const target = document.getElementById(tab.dataset.target);
            if (target) {
                target.classList.add('active');
                // Small animation reset
                target.classList.remove('fade-in');
                void target.offsetWidth;
                target.classList.add('fade-in');
            }
        });
    });
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* ─── TAB RENDERERS ───────────────────────────────────────────────────────── */
/* ═══════════════════════════════════════════════════════════════════════════ */

async function renderAnalyticsTab() {
    try {
        const response = await fetch('/api/analytics');
        if (!response.ok) throw new Error('Failed to fetch analytics');
        const history = await response.json();

        const empty = document.getElementById('analyticsEmpty');
        const chartWrapper = document.getElementById('chartWrapper');

        if (history.error || history.length === 0) {
            if (empty) empty.style.display = 'block';
            if (chartWrapper) chartWrapper.style.display = 'none';
            return;
        }

        if (empty) empty.style.display = 'none';
        if (chartWrapper) chartWrapper.style.display = 'block';

        // ── Summary Stats ──────────────────────────────────────────────
        const scores = history.map(h => h.ats_score);
        const best = Math.max(...scores);
        const avg = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
        const improvement = scores.length > 1 ? scores[scores.length - 1] - scores[0] : 0;

        const el = id => document.getElementById(id);
        if (el('statTotalUploads')) el('statTotalUploads').textContent = history.length;
        if (el('statBestScore'))    el('statBestScore').textContent = best + '%';
        if (el('statAvgScore'))     el('statAvgScore').textContent = avg + '%';
        if (el('statImprovement'))  {
            el('statImprovement').textContent = (improvement >= 0 ? '+' : '') + improvement + '%';
            el('statImprovement').style.color = improvement >= 0 ? '#00e676' : '#ff5252';
        }

        // ── History Table ──────────────────────────────────────────────
        const tbody = document.getElementById('analyticsHistoryTable');
        if (tbody) {
            tbody.innerHTML = history.slice().reverse().map(h => {
                const date = new Date(h.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                const scoreColor = h.ats_score >= 80 ? '#00e676' : h.ats_score >= 60 ? '#ffa726' : '#ff5252';
                const badge = h.ats_score >= 80 ? '🟢' : h.ats_score >= 60 ? '🟡' : '🔴';
                return `
                    <tr style="border-bottom:1px solid var(--border);transition:background 0.2s;"
                        onmouseover="this.style.background='rgba(255,255,255,0.03)'"
                        onmouseout="this.style.background=''">
                        <td style="padding:12px 16px;color:var(--text-secondary);font-size:0.85rem;">${date}</td>
                        <td style="padding:12px 16px;font-size:0.85rem;">${h.filename}</td>
                        <td style="padding:12px 16px;font-size:0.85rem;color:var(--text-secondary);">${h.role.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</td>
                        <td style="padding:12px 16px;">
                            <span style="font-weight:700;color:${scoreColor};">${badge} ${h.ats_score}%</span>
                        </td>
                        <td style="padding:12px 16px;color:var(--text-muted);font-size:0.85rem;">${h.word_count || '—'}</td>
                    </tr>`;
            }).join('');
        }

        // ── Chart ──────────────────────────────────────────────────────
        const ctx = document.getElementById('analyticsChart');
        if (ctx) {
            // Destroy existing chart if any
            if (window._analyticsChartInstance) {
                window._analyticsChartInstance.destroy();
            }
            const labels = history.map(h => new Date(h.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
            const dataPoints = history.map(h => h.ats_score);

            window._analyticsChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'ATS Score',
                        data: dataPoints,
                        borderColor: '#bb86fc',
                        backgroundColor: (context) => {
                            const chart = context.chart;
                            const { ctx: c, chartArea } = chart;
                            if (!chartArea) return 'transparent';
                            const gradient = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                            gradient.addColorStop(0, 'rgba(187,134,252,0.3)');
                            gradient.addColorStop(1, 'rgba(187,134,252,0.0)');
                            return gradient;
                        },
                        borderWidth: 2.5,
                        pointBackgroundColor: '#bb86fc',
                        pointBorderColor: '#0a0a0f',
                        pointBorderWidth: 2,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            min: Math.max(0, Math.min(...dataPoints) - 10),
                            max: 100,
                            grid: { color: 'rgba(255,255,255,0.04)' },
                            ticks: { color: '#8e8ea0', font: { size: 11 }, callback: v => v + '%' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#8e8ea0', font: { size: 11 } }
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(18,18,30,0.95)',
                            titleColor: '#fff',
                            bodyColor: '#e8e8ef',
                            borderColor: 'rgba(187,134,252,0.3)',
                            borderWidth: 1,
                            padding: 12,
                            callbacks: {
                                label: ctx => ` ATS Score: ${ctx.parsed.y}%`
                            }
                        }
                    }
                }
            });
        }
    } catch (err) {
        console.error("Error rendering analytics:", err);
    }
}

function renderOverviewTab(data) {
    if (!data) return;

    // Progress Bars
    const resumeScore = (data.ats_score && data.ats_score.total) || 0;
    const jdMatchScore = data.jd_match ? (data.jd_match.match_percentage || 0) : 0;

    const found_skills = data.found_skills || [];
    const missing_skills = data.missing_skills || [];
    const totalPossibleSkills = found_skills.length + missing_skills.length;
    const skillGapProgress = totalPossibleSkills > 0 ? Math.round((found_skills.length / totalPossibleSkills) * 100) : 0;

    setTimeout(() => {
        const resumeBar = document.getElementById('resumeScoreBar');
        const jobBar = document.getElementById('jobMatchBar');
        const skillBar = document.getElementById('skillGapBar');

        if (resumeBar) resumeBar.style.width = resumeScore + '%';
        if (jobBar) jobBar.style.width = jdMatchScore + '%';
        if (skillBar) skillBar.style.width = skillGapProgress + '%';

        animateNumber(document.getElementById('resumeScoreVal'), 0, resumeScore, 1000, '%');
        animateNumber(document.getElementById('jobMatchVal'), 0, jdMatchScore, 1000, '%');
        animateNumber(document.getElementById('skillGapVal'), 0, skillGapProgress, 1000, '%');
    }, 400);

    // Strengths & Weaknesses
    renderList('strengthsList', data.strengths || [], 'sw-item');
    renderList('weaknessesList', data.weaknesses || [], 'sw-item');
}


function renderExtractedDataTab(identity, sections) {
    if (!identity) return;

    // Contact Info
    const contactHtml = `
        <div class="contact-grid">
            <div class="contact-item">
                <span class="contact-label">Full Name</span>
                <span class="contact-value">${identity.name || 'Not Detected'}</span>
            </div>
            <div class="contact-item">
                <span class="contact-label">Detected Role</span>
                <span class="contact-value">${identity.possible_role || 'Not Detected'}</span>
            </div>
            <div class="contact-item">
                <span class="contact-label">Email</span>
                <span class="contact-value">${identity.email || 'Not Detected'}</span>
            </div>
            <div class="contact-item">
                <span class="contact-label">Phone</span>
                <span class="contact-value">${identity.phone || 'Not Detected'}</span>
            </div>
            <div class="contact-item">
                <span class="contact-label">LinkedIn</span>
                <span class="contact-value">${identity.linkedin || 'Not Detected'}</span>
            </div>
            <div class="contact-item">
                <span class="contact-label">GitHub</span>
                <span class="contact-value">${identity.github || 'Not Detected'}</span>
            </div>
        </div>
    `;
    const contactContainer = document.getElementById('extractedContact');
    if (contactContainer) contactContainer.innerHTML = contactHtml;

    // Sections
    const sectionsContainer = document.getElementById('extractedSections');
    if (sectionsContainer) {
        sectionsContainer.innerHTML = '';
        if (sections) {
            Object.entries(sections).forEach(([secName, secText]) => {
                if (secText.trim()) {
                    const el = document.createElement('div');
                    el.className = 'extracted-section-card';
                    // Trim to ~150 chars for preview
                    let preview = secText.substring(0, 150);
                    if (secText.length > 150) preview += "...";

                    el.innerHTML = `
                        <div class="sec-header">
                            <h3>${secName}</h3>
                            <span class="badge status-success">Detected</span>
                        </div>
                        <p class="sec-preview">${preview}</p>
                    `;
                    sectionsContainer.appendChild(el);
                }
            });
        }
    }
}


function renderAtsAnalysisTab(data) {
    if (!data) return;

    // Circle Score
    const ats_score = data.ats_score || { total: 0, grade: { letter: 'N/A', label: 'Processing', color: '#666' } };
    const score = ats_score.total || 0;
    const grade = ats_score.grade;
    const scoreFill = document.getElementById('scoreFill');
    const scoreNumber = document.getElementById('scoreNumber');
    const scoreGrade = document.getElementById('scoreGrade');

    const circumference = 2 * Math.PI * 85;
    const offset = circumference - (score / 100) * circumference;
    setTimeout(() => {
        if (scoreFill) {
            scoreFill.style.strokeDashoffset = offset;
            scoreFill.style.stroke = grade.color;
        }
    }, 200);

    animateNumber(scoreNumber, 0, score, 1500);
    if (scoreGrade) {
        scoreGrade.textContent = `${grade.letter} — ${grade.label}`;
        scoreGrade.style.background = grade.color + '22';
        scoreGrade.style.color = grade.color;
    }

    // Section Strengths (Unified)
    const strengthBars = document.getElementById('sectionStrengthBars');
    if (strengthBars) {
        strengthBars.innerHTML = '';
        if (data.section_strength) {
            Object.entries(data.section_strength).forEach(([secName, secScore], index) => {
                const pct = Math.max(0, secScore);
                let color = pct >= 80 ? 'var(--status-success)' : pct >= 50 ? 'var(--status-warning)' : 'var(--status-danger)';

                const el = document.createElement('div');
                el.className = 'breakdown-item fade-in';
                el.style.animationDelay = `${index * 0.1}s`;
                el.innerHTML = `
                    <div class="breakdown-label">
                        <span>${secName}</span>
                        <span>${pct}%</span>
                    </div>
                    <div class="breakdown-bar">
                        <div class="breakdown-bar-fill" style="background: ${color}; width: 0;" data-width="${pct}%"></div>
                    </div>
                `;
                strengthBars.appendChild(el);
            });

            setTimeout(() => {
                document.querySelectorAll('#sectionStrengthBars .breakdown-bar-fill').forEach(bar => {
                    bar.style.width = bar.dataset.width;
                });
            }, 400);
        }
    }

    // Formatting List
    const fmtList = document.getElementById('formattingList');
    if (fmtList) {
        fmtList.innerHTML = '';
        if (data.formatting) {
            // Deduplicate to be completely safe and limit to 5
            const uniqueFmt = [];
            const seenFmt = new Set();
            data.formatting.forEach(issue => {
                if (!seenFmt.has(issue.title)) {
                    uniqueFmt.push(issue);
                    seenFmt.add(issue.title);
                }
            });

            uniqueFmt.slice(0, 5).forEach(issue => {
                const li = document.createElement('li');
                li.className = 'formatting-item fade-in';
                li.innerHTML = `
                    <span class="formatting-icon">${issue.icon || '📝'}</span>
                    <div class="formatting-body">
                        <strong>${issue.title}</strong>
                        <p>${issue.detail}</p>
                    </div>
                `;
                fmtList.appendChild(li);
            });
        }
    }
}


function renderJobMatchTab(data) {
    if (!data.jd_match) return;

    const jdCard = document.getElementById('jdCard');
    jdCard.style.display = 'flex';

    // Match percentage UI
    const jdPct = data.jd_match.match_percentage;
    const jdFill = document.getElementById('jdFill');
    const jdNumber = document.getElementById('jdNumber');
    const jdDetail = document.getElementById('jdDetail');

    const jdCircumference = 2 * Math.PI * 65;
    const jdOffset = jdCircumference - (jdPct / 100) * jdCircumference;
    setTimeout(() => {
        jdFill.style.strokeDashoffset = jdOffset;
    }, 400);

    animateNumber(jdNumber, 0, jdPct, 1500);
    jdDetail.textContent = `${data.jd_match.matched_count} of ${data.jd_match.total_jd_keywords} keywords matched`;

    // 1. Matched Keywords (Skills found in both)
    if (data.jd_match.matched_keywords && data.jd_match.matched_keywords.length > 0) {
        document.getElementById('jdMatchedKeywordsRow').style.display = 'block';
        renderSkillTags('jdMatchedKeywords', data.jd_match.matched_keywords, 'found');
    }

    // 2. Missing Keywords
    if (data.jd_match.missing_keywords && data.jd_match.missing_keywords.length > 0) {
        document.getElementById('jdKeywordsRow').style.display = 'block';
        renderSkillTags('jdMissingKeywords', data.jd_match.missing_keywords, 'jd-missing');
    }

    // 3. Missing Technical Skills
    if (data.jd_match.missing_tech_skills && data.jd_match.missing_tech_skills.length > 0) {
        document.getElementById('jdTechKeywordsRow').style.display = 'block';
        renderSkillTags('jdMissingTech', data.jd_match.missing_tech_skills, 'jd-missing');
    }

    // 4. Suggestions to improve match score
    const suggestionsList = document.getElementById('jdSuggestionsList');
    if (suggestionsList) {
        suggestionsList.innerHTML = '';
        const suggestions = [];

        if (jdPct < 50) {
            suggestions.push({
                title: "Significant Keyword Gap",
                detail: "Your resume is missing a large portion of the job requirements. Try naturally integrating more of the 'Missing Keywords' listed above.",
                icon: "⚠️"
            });
        }

        if (data.jd_match.missing_tech_skills && data.jd_match.missing_tech_skills.length > 0) {
            suggestions.push({
                title: "Add Technical Proficiencies",
                detail: `The job expects you to know ${data.jd_match.missing_tech_skills.slice(0, 3).join(", ")}. If you have these skills, list them explicitly in your 'Skills' section.`,
                icon: "💻"
            });
        }

        if (data.jd_match.matched_count < 10) {
            suggestions.push({
                title: "Strengthen Your Core Messaging",
                detail: "You only matched a few words. Ensure you are using the EXACT phrasing from the job description (e.g., 'Project Management' instead of 'Managed Projects').",
                icon: "📝"
            });
        }

        if (suggestions.length === 0) {
            suggestions.push({
                title: "Excellent Match!",
                detail: "Your profile aligns very closely with the job description. Keep your formatting clean to ensure the ATS parses the keywords correctly.",
                icon: "🌟"
            });
        }

        suggestions.forEach(s => {
            const li = document.createElement('div');
            li.className = 'sw-item fade-in';
            li.innerHTML = `
                <span class="sw-icon" style="font-size: 1.5rem;">${s.icon}</span>
                <div class="sw-content">
                    <h4>${s.title}</h4>
                    <p>${s.detail}</p>
                </div>
            `;
            suggestionsList.appendChild(li);
        });
        document.getElementById('jdSuggestionsCard').style.display = 'block';
    }
}


function renderImprovementsTab(data) {
    // Bullet Rewrites
    const rewritesContainer = document.getElementById('bulletRewritesList');
    rewritesContainer.innerHTML = '';

    if (data.bullet_rewrites && data.bullet_rewrites.length > 0) {
        data.bullet_rewrites.forEach(bw => {
            const el = document.createElement('div');
            el.className = 'rewrite-card';
            el.innerHTML = `
                <div class="rewrite-original">
                    <span class="badge status-danger">Original</span>
                    <p>"${bw.original}"</p>
                </div>
                <div class="rewrite-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><polyline points="19 12 12 19 5 12"></polyline></svg>
                </div>
                <div class="rewrite-improved">
                    <span class="badge status-success">AI Improved</span>
                    <p>"${bw.improved}"</p>
                </div>
            `;
            rewritesContainer.appendChild(el);
        });
    } else {
        rewritesContainer.innerHTML = '<p class="empty-state">No major weak bullet points detected. Great job!</p>';
    }

    // Keyword Examples
    const kexContainer = document.getElementById('keywordExamplesList');
    kexContainer.innerHTML = '';
    if (data.keyword_examples && data.keyword_examples.length > 0) {
        data.keyword_examples.forEach(kex => {
            const el = document.createElement('div');
            el.className = 'keyword-example-card';
            el.innerHTML = `
                <div class="kw-header">
                    <span class="skill-tag jd-missing">${kex.keyword}</span>
                </div>
                <div class="kw-body">
                    <strong>Suggestion:</strong> <em>"${kex.example}"</em>
                </div>
            `;
            kexContainer.appendChild(el);
        });
    } else {
        kexContainer.innerHTML = '<p class="empty-state">No critical missing keywords to optimize.</p>';
    }
}


function renderInsightsTab(data) {
    // Roadmap
    const rContainer = document.getElementById('roadmapContainer');
    if (rContainer && data.roadmap && data.roadmap.steps) {
        rContainer.innerHTML = '';
        data.roadmap.steps.forEach((step, index) => {
            const stepEl = document.createElement('div');
            stepEl.className = 'roadmap-step fade-in';
            stepEl.style.animationDelay = `${(index + 2) * 0.1}s`;

            let techHtml = '';
            if (step.tech && step.tech.length > 0) {
                techHtml = `<div class="step-tech">${step.tech.map(t => `<span class="tech-tag">${t}</span>`).join('')}</div>`;
            }

            let projectHtml = '';
            if (step.projects && step.projects.length > 0) {
                projectHtml = `<div class="step-project"><strong>Project:</strong> ${step.projects[0]}</div>`;
            }

            stepEl.innerHTML = `
                <div class="step-title">${step.title}</div>
                <div class="step-detail">${step.detail}</div>
                ${techHtml}
                ${projectHtml}
            `;
            rContainer.appendChild(stepEl);
        });
    }

    // Interview Prep
    const content = document.getElementById('interviewContent');
    const tabs = document.querySelectorAll('.tab-btn');

    if (!content || !data.interview_questions) return;

    const renderQuestions = (type) => {
        content.innerHTML = '';
        const list = data.interview_questions[type] || [];
        const badgeClass = type === 'technical' ? 'tech-q' : (type === 'projects' || type === 'project') ? 'proj-q' : 'behave-q';
        const badgeLabel = type === 'technical' ? 'Tech' : (type === 'projects' || type === 'project') ? 'Project' : 'Behavioral';

        list.forEach((q, i) => {
            const card = document.createElement('div');
            card.className = 'question-card fade-in';
            card.style.animationDelay = `${i * 0.1}s`;
            card.innerHTML = `
                <div class="q-text">${q}</div>
                <span class="q-badge ${badgeClass}">${badgeLabel}</span>
            `;
            content.appendChild(card);
        });
    };

    renderQuestions('technical');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            renderQuestions(tab.dataset.tab);
        });
    });
}


/* ═══════════════════════════════════════════════════════════════════════════ */
/* ─── AI RESUME REWRITE ──────────────────────────────────────────────────── */
/* ═══════════════════════════════════════════════════════════════════════════ */

function renderAiRewriteTab(data) {
    const container = document.getElementById('aiRewritesList');
    if (!container) return;
    container.innerHTML = '';

    const rewrites = data.ai_rewrites || [];

    if (rewrites.length === 0) {
        container.innerHTML = `
            <div style="text-align:center;padding:40px;">
                <h3 style="margin-bottom:12px;color:var(--text-primary);">✨ Your Resume Language is Strong</h3>
                <p style="color:var(--text-secondary);max-width:500px;margin:0 auto;">
                    We analyzed your resume bullet points and didn't detect common weak phrases like "worked on", "helped", or "responsible for".
                    Your resume already uses professional, action-oriented language. Great work!
                </p>
            </div>`;
        return;
    }

    rewrites.forEach((rw, index) => {
        const card = document.createElement('div');
        card.className = 'ai-rewrite-card fade-in';
        card.style.animationDelay = `${index * 0.15}s`;
        card.innerHTML = `
            <div class="rewrite-before">
                <span class="rewrite-label danger-label">✗ Before</span>
                <p>"${rw.original}"</p>
            </div>
            <div class="rewrite-arrow">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7c4dff" stroke-width="2">
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                    <polyline points="12 5 19 12 12 19"></polyline>
                </svg>
            </div>
            <div class="rewrite-after">
                <span class="rewrite-label success-label">✓ After (AI Improved)</span>
                <p>"${rw.improved}"</p>
            </div>
        `;
        container.appendChild(card);
    });
}





/* ═══════════════════════════════════════════════════════════════════════════ */
/* ─── CAREER OPPORTUNITIES ───────────────────────────────────────────────── */
/* ═══════════════════════════════════════════════════════════════════════════ */

function renderCareersTab(data) {
    const container = document.getElementById('jobRecommendations');
    if (!container) return;
    container.innerHTML = '';

    const recommendations = data.job_recommendations || [];

    if (recommendations.length === 0) {
        const skills = (data.found_skills || []).join(', ') || 'your detected skills';
        container.innerHTML = `
            <div class="glass-card" style="text-align:center;padding:40px;">
                <h3 style="margin-bottom:12px;">Building Your Career Map</h3>
                <p style="color:var(--text-secondary);max-width:500px;margin:0 auto;">
                    Based on <strong>${skills}</strong>, we are analyzing the best career pathways for you.
                    Upload a more detailed resume with projects and experience for personalized recommendations.
                </p>
            </div>`;
        return;
    }

    recommendations.forEach((rec, index) => {
        const matchColor = rec.match_percentage >= 70 ? '#00e676' : rec.match_percentage >= 40 ? '#ffa726' : '#ef5350';

        const matchedHtml = (rec.matched_skills || []).map(s => `<span class="skill-tag found">${s}</span>`).join('');
        const missingHtml = (rec.missing_skills || []).map(s => `<span class="skill-tag jd-missing">${s}</span>`).join('');

        const roadmapHtml = (rec.learning_roadmap || []).map(step => `
            <div class="roadmap-step">
                <strong>${step.step}</strong>
                <p>${step.detail}</p>
            </div>
        `).join('');

        const card = document.createElement('div');
        card.className = 'job-rec-card fade-in';
        card.style.animationDelay = `${index * 0.1}s`;
        card.innerHTML = `
            <div class="job-rec-header">
                <div>
                    <h3 class="job-rec-title">${rec.role}</h3>
                    <p class="job-rec-desc">${rec.description}</p>
                </div>
                <div class="job-rec-match" style="border-color: ${matchColor}; color: ${matchColor}">
                    ${rec.match_percentage}%
                </div>
            </div>
            ${rec.why_fits ? `<div class="job-rec-why-fits"><span class="job-rec-why-label">Why This Fits You</span><p>${rec.why_fits}</p></div>` : ''}
            <div class="job-rec-skills">
                <div class="job-rec-skill-group">
                    <span class="job-rec-skill-label">Your Skills Match</span>
                    <div class="skills-grid compact">${matchedHtml || '<span class="text-muted">None detected</span>'}</div>
                </div>
                <div class="job-rec-skill-group">
                    <span class="job-rec-skill-label">Skills to Learn</span>
                    <div class="skills-grid compact">${missingHtml || '<span class="text-muted">None</span>'}</div>
                </div>
            </div>
            ${roadmapHtml ? `<div class="job-rec-roadmap"><span class="job-rec-skill-label">Learning Roadmap</span>${roadmapHtml}</div>` : ''}
            <div class="job-rec-suggestion">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ffa726" stroke-width="2">
                    <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                ${rec.suggestion}
            </div>
        `;
        container.appendChild(card);
    });
}


/* ═══════════════════════════════════════════════════════════════════════════ */
/* ─── DOWNLOAD REPORT ─────────────────────────────────────────────────────── */
/* ═══════════════════════════════════════════════════════════════════════════ */

async function downloadReport(data) {
    const btn = document.getElementById('downloadReportBtn');
    if (!btn) return;

    const originalText = btn.innerHTML;
    btn.innerHTML = `<div class="spinner" style="width:16px;height:16px;border-width:2px;"></div> Generating...`;
    btn.disabled = true;

    try {
        const payload = {
            ats_score: data.ats_score,
            role: data.role,
            word_count: data.word_count,
            found_skills: data.found_skills,
            missing_skills: data.missing_skills,
            strengths: data.strengths,
            weaknesses: data.weaknesses,
            suggestions: data.suggestions,
            jd_match: data.jd_match,
            roadmap: data.roadmap,
            interview_questions: data.interview_questions,
            identity: data.identity,
            section_strength: data.section_strength,
            formatting: data.formatting,
            bullet_rewrites: data.bullet_rewrites,
            keyword_examples: data.keyword_examples,
            filename: data.identity?.name ? `${data.identity.name.replace(/\s+/g, '_')}_Resume_Report.pdf` : 'Resume_Analysis_Report.pdf'
        };

        const response = await fetch('/api/download-pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || 'Failed to generate PDF');
        }

        // Create a blob from the response and trigger download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = payload.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

    } catch (err) {
        alert('Error downloading report: ' + err.message);
    }

    btn.innerHTML = originalText;
    btn.disabled = false;
}


/* ═══════════════════════════════════════════════════════════════════════════ */
/* ─── UTILITIES ───────────────────────────────────────────────────────────── */
/* ═══════════════════════════════════════════════════════════════════════════ */

function renderList(containerId, items, defaultClass = 'sw-item') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    const rawItems = Array.isArray(items) ? items : [];

    // Deduplicate by title to ensure clean UI
    const listItems = [];
    const seenTitles = new Set();

    rawItems.forEach(item => {
        if (!item) return;
        const title = item.title || item.msg || (typeof item === 'string' ? item : 'Information');
        if (!seenTitles.has(title)) {
            listItems.push(item);
            seenTitles.add(title);
        }
    });

    if (listItems.length === 0) {
        container.innerHTML = '<p class="empty-list">No items found for this section.</p>';
        return;
    }

    listItems.slice(0, 5).forEach(item => {
        // Some items might be strings or objects
        const title = item.title || item.msg || (typeof item === 'string' ? item : 'Information');
        const detail = item.detail || '';
        const icon = item.icon || 'ℹ️';

        const el = document.createElement('div');
        el.className = defaultClass;
        el.innerHTML = `
            <span class="sw-icon" style="font-size: 1.5rem;">${icon}</span>
            <div class="sw-content">
                <h4>${title}</h4>
                ${detail ? `<p>${detail}</p>` : ''}
            </div>
        `;
        container.appendChild(el);
    });
}

function renderSkillTags(containerId, skills, className) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    const skillList = Array.isArray(skills) ? skills : [];

    skillList.forEach(skill => {
        if (!skill) return;
        const tag = document.createElement('span');
        tag.className = `skill-tag ${className}`;
        tag.textContent = skill;
        container.appendChild(tag);
    });
}


/* ─── Utilities ────────────────────────────────────────────────────────────── */

function animateNumber(element, start, end, duration, suffix = '') {
    const startTime = performance.now();
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // ease-out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + (end - start) * eased);
        element.textContent = current + suffix;
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* ─── FEATURE 9: Share Analysis ──────────────────────────────────────────── */
/* ═══════════════════════════════════════════════════════════════════════════ */

async function shareAnalysis(data) {
    try {
        const resp = await fetch('/api/share-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                role: data.role,
                ats_score: data.ats_score,
                found_skills: data.found_skills,
                missing_skills: data.missing_skills,
                strengths: data.strengths,
                weaknesses: data.weaknesses
            })
        });
        const result = await resp.json();
        const fullUrl = window.location.origin + result.url;
        await navigator.clipboard.writeText(fullUrl);

        // Show toast
        const toast = document.createElement('div');
        toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1e1e2e;border:1px solid rgba(0,230,118,0.4);color:#00e676;padding:12px 24px;border-radius:10px;font-size:0.9rem;font-weight:600;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,0.4);';
        toast.textContent = '🔗 Share link copied to clipboard!';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    } catch (e) {
        alert('Could not generate share link: ' + e.message);
    }
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* ─── FEATURE 3: Save for Comparison ─────────────────────────────────────── */
/* ═══════════════════════════════════════════════════════════════════════════ */

async function saveForCompare(data) {
    const name = prompt('Name this version (e.g. "Updated Resume v2"):', `Version ${new Date().toLocaleDateString()}`);
    if (!name) return;

    // We need the resume text — get from sessionStorage if available
    const stored = JSON.parse(sessionStorage.getItem('analysisResults') || '{}');
    const resumeText = stored.resume_text || '';

    try {
        const resp = await fetch('/api/resume-versions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resume_text: resumeText || `Score: ${data.ats_score?.total} | Role: ${data.role}`,
                job_role: data.role,
                name: name
            })
        });
        if (resp.ok) {
            const toast = document.createElement('div');
            toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1e1e2e;border:1px solid rgba(187,134,252,0.4);color:#bb86fc;padding:12px 24px;border-radius:10px;font-size:0.9rem;font-weight:600;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,0.4);';
            toast.innerHTML = '✅ Saved! <a href="/compare" style="color:#00e676;margin-left:8px;">View in Compare →</a>';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
        }
    } catch (e) {
        alert('Error saving: ' + e.message);
    }
}



function initChatWidget() {
    const launcher = document.getElementById('bunnyLauncher');
    const panel = document.getElementById('bunnyPanel');
    const closeBtn = document.getElementById('bunnyClose');
    const input = document.getElementById('bunnyInput');
    const sendBtn = document.getElementById('bunnySend');
    const messages = document.getElementById('bunnyMessages');
    const typingEl = document.getElementById('bunnyTyping');
    const chipsWrap = document.getElementById('bunnyChips');
    const avatarWrap = document.getElementById('bunnyAvatarWrap');
    const clearBtn = document.getElementById('bunnyClear');

    if (!launcher || !panel) return;

    let isOpen = false;

    // ── Open / Close ─────────────────────────────────────────────────────
    launcher.addEventListener('click', () => openBunny());
    closeBtn.addEventListener('click', () => closeBunny());
    if (clearBtn) clearBtn.addEventListener('click', () => clearChat());

    function openBunny() {
        isOpen = true;
        launcher.classList.add('hidden');
        panel.classList.remove('closing');
        panel.classList.add('open');
        setTimeout(() => input.focus(), 350);
    }

    function closeBunny() {
        isOpen = false;
        panel.classList.add('closing');
        setTimeout(() => {
            panel.classList.remove('open', 'closing');
            launcher.classList.remove('hidden');
        }, 250);
    }

    // ── Keyboard Navigation ──────────────────────────────────────────────
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
        if (e.key === 'Escape') closeBunny();
    });

    sendBtn.addEventListener('click', sendMessage);

    // ── Suggestion Chips ─────────────────────────────────────────────────
    chipsWrap.querySelectorAll('.bunny-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            input.value = chip.dataset.prompt;
            sendMessage();
        });
    });

    // ── Avatar Animations ────────────────────────────────────────────────
    function triggerHop() {
        avatarWrap.classList.remove('hop', 'blink');
        void avatarWrap.offsetWidth; // reflow
        avatarWrap.classList.add('hop');
        setTimeout(() => avatarWrap.classList.remove('hop'), 500);
    }

    function triggerBlink() {
        avatarWrap.classList.remove('hop', 'blink');
        void avatarWrap.offsetWidth;
        avatarWrap.classList.add('blink');
        setTimeout(() => avatarWrap.classList.remove('blink'), 2000);
    }

    // ── Emotional Reactions ──────────────────────────────────────────────
    function getEmotionalPrefix() {
        try {
            const ctx = JSON.parse(sessionStorage.getItem('analysisResults') || '{}');
            const atsScore = ctx.ats_score?.total;
            const missingSkills = ctx.missing_skills || [];

            if (atsScore !== undefined) {
                if (atsScore >= 75) return "Nice! Your resume looks strong 🐰 ";
                if (atsScore < 40) return "Don't worry! We can improve this together 🐰 ";
            }
            if (missingSkills.length > 15) return "I noticed quite a few missing skills for your target role. ";
        } catch (e) { /* ignore */ }
        return "";
    }

    // ── Conversation Memory ──────────────────────────────────────────────
    let conversationHistory = [
        { role: 'assistant', content: "Hi! I'm Bunny 🐰\nYour AI Resume Companion.\nI can help you understand and improve your resume!" }
    ];

    // ── Send Message ─────────────────────────────────────────────────────
    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        // Show user message
        appendMessage('user', text);

        // Add user message to history
        conversationHistory.push({ role: 'user', content: text });

        input.value = '';
        input.disabled = true;
        sendBtn.disabled = true;

        // Trigger hop on user message
        triggerHop();

        // Hide chips after first message
        chipsWrap.style.display = 'none';

        // Show typing indicator
        typingEl.style.display = 'flex';
        scrollToBottom();

        try {
            const contextData = JSON.parse(sessionStorage.getItem('analysisResults') || '{}');

            // Send standard history + current message
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    context: contextData,
                    history: conversationHistory
                })
            });

            const data = await response.json();

            // Hide typing indicator
            typingEl.style.display = 'none';

            if (data.error) {
                // If it failed, we remove the user message from history so it's not a duplicate later
                conversationHistory.pop();
                appendMessage('ai', "Oops! Something went wrong 🐰 " + data.error);
            } else {
                let reply = data.response || "I'm not sure how to answer that. Try asking about your resume!";

                // Add AI response to memory
                conversationHistory.push({ role: 'assistant', content: reply });

                // Bunny personality logic
                const prefix = getEmotionalPrefix();
                if (conversationHistory.length === 2 && prefix && !reply.startsWith("Nice") && !reply.startsWith("Don't")) {
                    reply = prefix + "\n\n" + reply;
                }

                // Format UI
                reply = reply.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                reply = reply.replace(/\n/g, '<br>');
                reply = reply.replace(/<br>- /g, '<br>• ');

                appendMessage('ai', reply);
            }

            // Trigger blink
            triggerBlink();

        } catch (err) {
            typingEl.style.display = 'none';
            // Remove user message from history on network error too
            conversationHistory.pop();
            appendMessage('ai', "I'm having trouble connecting right now 🐰 Please check your connection and try again.");
        }

        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
    }

    // ── Append Message ───────────────────────────────────────────────────
    function appendMessage(sender, html) {
        const wrapper = document.createElement('div');
        wrapper.className = `bunny-msg bunny-msg-${sender} bunny-msg-enter`;

        const avatar = document.createElement('div');
        avatar.className = 'bunny-msg-avatar-mini';
        avatar.textContent = sender === 'ai' ? '🐰' : '👤';

        const bubble = document.createElement('div');
        bubble.className = 'bunny-msg-bubble';
        bubble.innerHTML = html;

        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);
        messages.appendChild(wrapper);

        scrollToBottom();
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            messages.scrollTop = messages.scrollHeight;
        });
    }

    // ── Clear Chat ───────────────────────────────────────────────────────
    function clearChat() {
        if (!confirm("Are you sure you want to clear the conversation?")) return;

        // Reset history
        conversationHistory = [
            { role: 'assistant', content: "Hi! I'm Bunny 🐰\nYour AI Resume Companion.\nI can help you understand and improve your resume!" }
        ];

        // Clear UI
        messages.innerHTML = `
            <div class="bunny-msg bunny-msg-ai bunny-msg-enter">
                <div class="bunny-msg-avatar-mini">🐰</div>
                <div class="bunny-msg-bubble">
                    <strong>Hi! I'm Bunny</strong> 🐰<br>
                    Your AI Resume Companion.<br>
                    I can help you understand and improve your resume!
                </div>
            </div>
        `;

        // Show chips again
        chipsWrap.style.display = 'flex';
        
        // Focus input
        input.focus();
    }
}

