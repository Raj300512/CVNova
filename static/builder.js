// builder.js

document.addEventListener('DOMContentLoaded', () => {
    const editor = document.getElementById('resumeEditor');
    const roleSelect = document.getElementById('roleSelect');
    const customRoleInput = document.getElementById('customRoleInput');
    
    const syncStatus = document.getElementById('syncStatus');
    const syncDot = syncStatus.querySelector('.dot');
    
    const liveScoreFill = document.getElementById('liveScoreFill');
    const liveScoreVal = document.getElementById('liveScoreVal');
    const liveScoreDesc = document.getElementById('liveScoreDesc');
    
    const liveFoundSkills = document.getElementById('liveFoundSkills');
    const liveMissingSkills = document.getElementById('liveMissingSkills');
    const liveTips = document.getElementById('liveTips');
    
    const importBtn = document.getElementById('importLinkedinBtn');
    const linkedinUpload = document.getElementById('linkedinUpload');
    const builderOverlay = document.getElementById('builderOverlay');
    const overlayText = document.getElementById('overlayText');

    let debounceTimer;

    // Role handling
    roleSelect.addEventListener('change', () => {
        if (roleSelect.value === 'custom') {
            customRoleInput.style.display = 'block';
        } else {
            customRoleInput.style.display = 'none';
        }
        triggerSync();
    });

    customRoleInput.addEventListener('input', triggerSync);

    // Editor input handling
    editor.addEventListener('input', () => {
        setSyncStatus('yellow', 'Syncing...');
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(performSync, 1500);
    });

    function triggerSync() {
        if (editor.value.length < 50) return;
        setSyncStatus('yellow', 'Syncing...');
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(performSync, 500);
    }

    function setSyncStatus(color, text) {
        syncDot.className = `dot ${color}`;
        syncStatus.childNodes[1].textContent = ` ${text}`;
    }

    async function performSync() {
        const text = editor.value.trim();
        if (text.length < 50) {
            setSyncStatus('gray', 'Waiting for more text...');
            return;
        }

        try {
            const response = await fetch('/api/analyze-live', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    job_role: roleSelect.value,
                    custom_role: customRoleInput.value
                })
            });

            if (!response.ok) throw new Error('Analysis failed');

            const data = await response.json();
            updateUI(data);
            setSyncStatus('green', 'Synced');

        } catch (err) {
            console.error(err);
            setSyncStatus('gray', 'Sync failed');
        }
    }

    function updateUI(data) {
        // Update Score
        const score = data.ats_score ? data.ats_score.total : 0;
        const circumference = 2 * Math.PI * 45;
        const offset = circumference - (score / 100) * circumference;
        
        liveScoreFill.style.strokeDashoffset = offset;
        liveScoreVal.textContent = score;
        
        // Trigger bounce animation
        const circle = document.querySelector('.score-circle');
        if (circle) {
            circle.classList.remove('updating');
            void circle.offsetWidth; // trigger reflow
            circle.classList.add('updating');
        }

        if (score >= 80) {
            liveScoreFill.style.stroke = '#00e676';
            liveScoreDesc.textContent = 'Excellent! Ready to apply.';
        } else if (score >= 50) {
            liveScoreFill.style.stroke = '#ffea00';
            liveScoreDesc.textContent = 'Good, but could be better.';
        } else {
            liveScoreFill.style.stroke = '#ff5252';
            liveScoreDesc.textContent = 'Needs significant improvement.';
        }

        // Update Skills
        liveFoundSkills.innerHTML = '';
        if (data.found_skills && data.found_skills.length > 0) {
            data.found_skills.slice(0, 15).forEach(skill => {
                liveFoundSkills.innerHTML += `<span class="skill-tag found">${skill}</span>`;
            });
        } else {
            liveFoundSkills.innerHTML = '<p class="empty-state">No skills detected.</p>';
        }

        liveMissingSkills.innerHTML = '';
        if (data.missing_skills && data.missing_skills.length > 0) {
            data.missing_skills.slice(0, 15).forEach(skill => {
                liveMissingSkills.innerHTML += `<span class="skill-tag missing">${skill}</span>`;
            });
        } else {
            liveMissingSkills.innerHTML = '<p class="empty-state">No missing skills detected.</p>';
        }
        
        // Update Tips
        liveTips.innerHTML = '';
        if (data.weaknesses && data.weaknesses.length > 0) {
            liveTips.innerHTML = `<h3 style="margin-top:20px; color:#ff5252;">Critical Fixes</h3>`;
            data.weaknesses.slice(0, 3).forEach(w => {
                liveTips.innerHTML += `<div style="background:rgba(255,82,82,0.1); padding:10px; border-radius:8px; margin-top:8px; font-size:0.9rem;"><strong>${w.title}:</strong> ${w.detail}</div>`;
            });
        }
    }

    // LinkedIn Import
    importBtn.addEventListener('click', () => linkedinUpload.click());

    linkedinUpload.addEventListener('change', async (e) => {
        if (e.target.files.length === 0) return;
        const file = e.target.files[0];
        
        builderOverlay.style.display = 'flex';
        overlayText.textContent = 'Extracting and formatting LinkedIn profile... This may take up to 30 seconds.';

        const formData = new FormData();
        formData.append('pdf', file);

        try {
            const response = await fetch('/api/import-linkedin', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to import');

            editor.value = data.formatted_text;
            triggerSync();

        } catch (err) {
            alert('Error importing LinkedIn PDF: ' + err.message);
        } finally {
            builderOverlay.style.display = 'none';
            linkedinUpload.value = ''; // reset
        }
    });

    // Keyboard Shortcuts (Cmd/Ctrl + S to force sync)
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault(); // Prevent browser save dialog
            triggerSync();
        }
    });

});
