// CVNova Content Script
// This runs on the actual job matching page (LinkedIn, Indeed, etc.)

let jobData = {
    title: '',
    company: '',
    description: ''
};

function extractJobInfo() {
    let url = window.location.href;
    
    if (url.includes('linkedin.com/jobs')) {
        // Basic LinkedIn Extraction
        const titleEl = document.querySelector('.job-details-jobs-unified-top-card__job-title');
        const compEl = document.querySelector('.job-details-jobs-unified-top-card__company-name');
        
        if (titleEl) jobData.title = titleEl.innerText;
        if (compEl) jobData.company = compEl.innerText;
        
    } else if (url.includes('indeed.com/viewjob')) {
        // Basic Indeed Extraction
        const titleEl = document.querySelector('.jobsearch-JobInfoHeader-title');
        const compEl = document.querySelector('[data-company-name="true"]');
        
        if (titleEl) jobData.title = titleEl.innerText;
        if (compEl) jobData.company = compEl.innerText;
    }
}

// Extract initially
setTimeout(extractJobInfo, 2000);

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getJobData") {
        extractJobInfo(); // Ensure fresh data
        sendResponse(jobData);
    }
});
