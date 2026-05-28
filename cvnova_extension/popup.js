document.addEventListener('DOMContentLoaded', () => {
    // Determine active tab
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
        let activeTab = tabs[0];
        
        // Ask content script for data
        chrome.tabs.sendMessage(activeTab.id, {action: "getJobData"}, (response) => {
            if (response && response.title) {
                document.getElementById('loadingState').style.display = 'none';
                document.getElementById('resultsState').style.display = 'block';
                
                document.getElementById('jobTitle').innerText = response.title;
                
                // Demo score (In a real app, we'd hit CVNova's backend API)
                let score = Math.floor(Math.random() * 40) + 50; 
                document.getElementById('scoreValue').innerText = score + '%';
                document.getElementById('scoreCircle').style.background = `conic-gradient(#bb86fc ${score}%, rgba(255,255,255,0.1) 0%)`;
                
                document.getElementById('trackJobBtn').onclick = () => {
                    alert("Added to VitaForge Tracker!");
                };
            }
        });
    });
});
