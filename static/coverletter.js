/**
 * CVNova — Cover Letter Generator Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateBtn');
    const copyBtn = document.getElementById('copyBtn');
    const pdfBtn = document.getElementById('pdfBtn');
    const regenBtn = document.getElementById('regenBtn');
    const outputCard = document.getElementById('outputCard');
    const editor = document.getElementById('coverLetterEditor');
    const resumeTextarea = document.getElementById('resumeText');
    const resumeHint = document.getElementById('resumeHint');
    const jdTextarea = document.getElementById('jobDescription');

    // ─── Auto-populate resume from sessionStorage ────────────────────────
    try {
        const stored = sessionStorage.getItem('analysisResults');
        if (stored) {
            const data = JSON.parse(stored);
            if (data.resume_text && data.resume_text.length > 50) {
                resumeTextarea.value = data.resume_text;
                resumeHint.classList.add('visible');
            }
            // Also pre-fill role if available
            const roleTitle = document.getElementById('roleTitle');
            if (data.role && roleTitle) {
                roleTitle.value = data.role;
            }
        }
    } catch (e) {
        console.log('No previous analysis data found.');
    }

    // ─── Generate Cover Letter ───────────────────────────────────────────
    generateBtn.addEventListener('click', () => generateCoverLetter());
    regenBtn.addEventListener('click', () => generateCoverLetter());

    async function generateCoverLetter() {
        const jobDescription = jdTextarea.value.trim();
        const resumeText = resumeTextarea.value.trim();
        const companyName = document.getElementById('companyName').value.trim();
        const roleTitle = document.getElementById('roleTitle').value.trim();

        if (!jobDescription) {
            showToast('Please paste a job description first.', 'error');
            jdTextarea.focus();
            return;
        }

        if (!resumeText) {
            showToast('Please provide your resume text.', 'error');
            resumeTextarea.focus();
            return;
        }

        // Set loading state
        generateBtn.classList.add('loading');
        generateBtn.disabled = true;

        try {
            const response = await fetch('/api/generate-cover-letter', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_description: jobDescription,
                    resume_text: resumeText,
                    company_name: companyName || 'the company',
                    role_title: roleTitle || 'the position'
                })
            });

            const result = await response.json();

            if (!response.ok || result.error) {
                throw new Error(result.error || 'Failed to generate cover letter');
            }

            // Show output card and render with typewriter
            outputCard.style.display = 'block';
            outputCard.scrollIntoView({ behavior: 'smooth', block: 'start' });

            typewriterEffect(editor, result.cover_letter);

        } catch (err) {
            console.error('Cover letter generation error:', err);
            showToast(err.message || 'Something went wrong. Please try again.', 'error');
        } finally {
            generateBtn.classList.remove('loading');
            generateBtn.disabled = false;
        }
    }

    // ─── Typewriter Effect ───────────────────────────────────────────────
    function typewriterEffect(element, text) {
        element.innerHTML = '';
        let index = 0;
        const cursor = document.createElement('span');
        cursor.className = 'cl-cursor';

        // Split text into paragraphs for proper formatting
        const paragraphs = text.split('\n\n');
        let currentParagraph = 0;
        let currentParagraphEl = null;
        let charIndex = 0;

        function createNewParagraph() {
            if (cursor.parentNode) cursor.parentNode.removeChild(cursor);
            currentParagraphEl = document.createElement('p');
            currentParagraphEl.style.marginBottom = '16px';
            currentParagraphEl.style.lineHeight = '1.8';
            element.appendChild(currentParagraphEl);
            charIndex = 0;
        }

        createNewParagraph();

        const speed = 8; // ms per character
        function type() {
            if (currentParagraph >= paragraphs.length) {
                // Done typing — remove cursor
                if (cursor.parentNode) cursor.parentNode.removeChild(cursor);
                return;
            }

            const currentText = paragraphs[currentParagraph];

            if (charIndex < currentText.length) {
                // Handle single newlines within a paragraph
                if (currentText[charIndex] === '\n') {
                    currentParagraphEl.appendChild(document.createElement('br'));
                } else {
                    currentParagraphEl.appendChild(document.createTextNode(currentText[charIndex]));
                }
                // Keep cursor at end
                if (cursor.parentNode) cursor.parentNode.removeChild(cursor);
                currentParagraphEl.appendChild(cursor);

                charIndex++;
                setTimeout(type, speed);
            } else {
                // Move to next paragraph
                currentParagraph++;
                if (currentParagraph < paragraphs.length) {
                    createNewParagraph();
                    setTimeout(type, speed * 10); // Slight pause between paragraphs
                } else {
                    // All done
                    if (cursor.parentNode) cursor.parentNode.removeChild(cursor);
                }
            }
        }

        type();
    }

    // ─── Copy to Clipboard ───────────────────────────────────────────────
    copyBtn.addEventListener('click', async () => {
        const text = editor.innerText;
        if (!text) return;

        try {
            await navigator.clipboard.writeText(text);
            copyBtn.classList.add('copied');
            const originalHTML = copyBtn.innerHTML;
            copyBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12" />
                </svg>
                Copied!
            `;
            showToast('Cover letter copied to clipboard!', 'success');

            setTimeout(() => {
                copyBtn.classList.remove('copied');
                copyBtn.innerHTML = originalHTML;
            }, 2000);
        } catch (err) {
            showToast('Failed to copy. Please select and copy manually.', 'error');
        }
    });

    // ─── Download as PDF ─────────────────────────────────────────────────
    pdfBtn.addEventListener('click', async () => {
        const text = editor.innerText;
        if (!text) return;

        const companyName = document.getElementById('companyName').value.trim() || 'Company';
        const roleTitle = document.getElementById('roleTitle').value.trim() || 'Position';

        try {
            pdfBtn.disabled = true;
            pdfBtn.innerHTML = `
                <div class="cl-spinner" style="width:14px;height:14px;border-width:2px;"></div>
                Generating...
            `;

            const response = await fetch('/api/download-cover-letter-pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cover_letter: text,
                    company_name: companyName,
                    role_title: roleTitle
                })
            });

            if (!response.ok) throw new Error('PDF generation failed');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Cover_Letter_${companyName.replace(/\s+/g, '_')}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showToast('PDF downloaded successfully!', 'success');
        } catch (err) {
            showToast('Failed to download PDF. ' + err.message, 'error');
        } finally {
            pdfBtn.disabled = false;
            pdfBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Download PDF
            `;
        }
    });

    // ─── Toast Notification ──────────────────────────────────────────────
    function showToast(message, type = 'success') {
        // Remove existing toasts
        document.querySelectorAll('.cl-toast').forEach(t => t.remove());

        const toast = document.createElement('div');
        toast.className = `cl-toast ${type}`;
        toast.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                ${type === 'success'
                ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>'
                : '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>'}
            </svg>
            ${message}
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            if (toast.parentNode) toast.remove();
        }, 3000);
    }
});
