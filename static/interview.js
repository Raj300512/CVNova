/**
 * CVNova — AI Mock Interview Simulator Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const setupCard = document.getElementById('setupCard');
    const chatCard = document.getElementById('chatCard');
    const btnStartTech = document.getElementById('btnStartTech');
    const btnStartBehav = document.getElementById('btnStartBehav');
    const btnEndInterview = document.getElementById('btnEndInterview');
    
    const targetRoleDisplay = document.getElementById('targetRoleDisplay');
    const resumeStatusDisplay = document.getElementById('resumeStatusDisplay');
    const chatRoleSubtitle = document.getElementById('chatRoleSubtitle');
    
    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const chatSend = document.getElementById('chatSend');
    
    let resumeText = '';
    let targetRole = '';
    let interviewType = ''; // 'technical' or 'behavioral'
    let chatHistory = [];
    let isWaitingForAI = false;
    let turnCount = 0;
    const MAX_TURNS = 4; // AI asks 4 questions then gives feedback
    
    // ─── Initialize from Session Storage ─────────────────────────────────
    try {
        const stored = sessionStorage.getItem('analysisResults');
        if (stored) {
            const data = JSON.parse(stored);
            if (data.resume_text && data.role) {
                resumeText = data.resume_text;
                targetRole = data.role;
                
                targetRoleDisplay.innerText = targetRole;
                resumeStatusDisplay.innerText = 'Resume data loaded successfully. Ready to begin.';
                resumeStatusDisplay.style.color = 'var(--green)';
                
                btnStartTech.disabled = false;
                btnStartBehav.disabled = false;
            } else {
                showNoResumeAlert('Incomplete data. Please run a new analysis first.');
            }
        } else {
            showNoResumeAlert('No resume data found. Upload your resume on the homepage first.');
        }
    } catch (e) {
        showNoResumeAlert('Error loading session data. Please run a new analysis.');
    }
    
    function showNoResumeAlert(msg) {
        targetRoleDisplay.innerText = 'Setup Required';
        resumeStatusDisplay.innerText = msg;
        resumeStatusDisplay.style.color = '#ffa726';
        // Show the no-resume CTA banner
        const alert = document.getElementById('noResumeAlert');
        if (alert) alert.style.display = 'block';
    }
    
    // ─── Start Interview ────────────────────────────────────────────────
    btnStartTech.addEventListener('click', () => startInterview('technical'));
    btnStartBehav.addEventListener('click', () => startInterview('behavioral'));
    
    function startInterview(type) {
        interviewType = type;
        chatRoleSubtitle.innerText = type === 'technical' ? 'Technical Interview' : 'Behavioral Interview';
        
        setupCard.style.display = 'none';
        chatCard.style.display = 'flex';
        
        // Initial system message to backend to kick off
        chatHistory = [];
        turnCount = 0;
        fetchNextQuestion();
    }
    
    // ─── Chat Logic ─────────────────────────────────────────────────────
    
    chatInput.addEventListener('input', () => {
        chatSend.disabled = chatInput.value.trim().length === 0 || isWaitingForAI;
        // Auto-resize
        chatInput.style.height = 'auto';
        chatInput.style.height = (chatInput.scrollHeight) + 'px';
    });
    
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });
    
    chatSend.addEventListener('click', handleSend);
    
    function handleSend() {
        const text = chatInput.value.trim();
        if (!text || isWaitingForAI) return;
        
        // Add user message to UI and history
        appendMessage('user', text);
        chatHistory.push({ role: 'user', content: text });
        
        chatInput.value = '';
        chatInput.style.height = 'auto';
        chatSend.disabled = true;
        
        turnCount++;
        fetchNextQuestion();
    }
    
    async function fetchNextQuestion() {
        isWaitingForAI = true;
        showTypingIndicator();
        
        try {
            const response = await fetch('/api/mock-interview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    history: chatHistory,
                    resume_text: resumeText,
                    role: targetRole,
                    interview_type: interviewType,
                    turn_count: turnCount,
                    max_turns: MAX_TURNS
                })
            });
            
            const data = await response.json();
            hideTypingIndicator();
            
            if (!response.ok || data.error) {
                throw new Error(data.error || 'Failed to connect to AI');
            }
            
            const reply = data.reply;
            chatHistory.push({ role: 'assistant', content: reply });
            appendMessage('ai', reply);
            
            if (data.is_finished) {
                chatInput.disabled = true;
                chatInput.placeholder = 'Interview concluded.';
            }
            
        } catch (err) {
            hideTypingIndicator();
            appendMessage('ai', `System Error: ${err.message}. Please try again.`);
            // Pop the last user message so they can retry? Or just let them continue.
        } finally {
            isWaitingForAI = false;
            if (!chatInput.disabled) chatInput.focus();
        }
    }
    
    // ─── UI Helpers ─────────────────────────────────────────────────────
    
    function appendMessage(sender, text) {
        const wrapper = document.createElement('div');
        wrapper.className = `msg-wrapper ${sender}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'msg-avatar';
        avatar.innerHTML = sender === 'ai' ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/></svg>` : 'U';
        
        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble';
        
        // Basic parsing for feedback blocks: if AI replies with "Feedback: ... \n Question: ..."
        if (sender === 'ai' && text.includes('**Feedback:**')) {
            let formattedText = text.replace('**Feedback:**', '<div class="feedback-box"><strong>Feedback:</strong>').replace('**Next Question:**', '</div><strong>Next Question:</strong>');
            // generic bold parsing
            formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            bubble.innerHTML = formattedText;
        } else {
            let formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            bubble.innerHTML = formattedText;
        }
        
        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        
        scrollToBottom();
    }
    
    function showTypingIndicator() {
        const id = 'typingIndicator';
        if (document.getElementById(id)) return;
        
        const wrapper = document.createElement('div');
        wrapper.className = 'typing-indicator';
        wrapper.id = id;
        
        const bubble = document.createElement('div');
        bubble.className = 'typing-bubble';
        
        for (let i=0; i<3; i++) {
            const dot = document.createElement('span');
            dot.className = 'typing-dot';
            bubble.appendChild(dot);
        }
        
        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        scrollToBottom();
    }
    
    function hideTypingIndicator() {
        const el = document.getElementById('typingIndicator');
        if (el) el.remove();
    }
    
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // ─── End Interview ──────────────────────────────────────────────────
    btnEndInterview.addEventListener('click', () => {
        if(confirm('Are you sure you want to end this mock interview session?')) {
            setupCard.style.display = 'block';
            chatCard.style.display = 'none';
            chatInput.disabled = false;
            chatInput.placeholder = 'Type your answer here... (Press Shift+Enter for new line)';
        }
    });
});
