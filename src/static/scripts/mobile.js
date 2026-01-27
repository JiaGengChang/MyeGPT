/*
* adjust UI for mobile viewport
*/

const deleteAccBtn = document.getElementById('delete-account-button');
const eraseMemBtn = document.getElementById('erase-memory-button');
const fixHistoryBtn = document.getElementById('fix-history-button');
const logOutBtn = document.getElementById('logout-button');
const usageBtn = document.getElementById('check-usage');

const deleteAccBtnText = deleteAccBtn ? deleteAccBtn.textContent : '';
const eraseMemBtnText = eraseMemBtn ? eraseMemBtn.textContent : '';
const fixHistoryBtnText = fixHistoryBtn ? fixHistoryBtn.textContent : '';
const logOutBtnText = logOutBtn ? logOutBtn.textContent : '';
const usageBtnText = usageBtn ? usageBtn.textContent : '';

let mobile = window.innerWidth < 768;

function adjustForMobile() {
    if (mobile) {
        //remove text content in command buttons
        if (deleteAccBtn) deleteAccBtn.textContent = '🗑️🔐';
        if (eraseMemBtn) eraseMemBtn.textContent = '🗑️🧠';
        if (fixHistoryBtn) fixHistoryBtn.textContent = '🛠️🚧';
        if (logOutBtn) logOutBtn.textContent = '🚪👋';
        if (usageBtn) usageBtn.textContent = '💸🔥';
    } else {
        // restore original text command
        if (deleteAccBtn) deleteAccBtn.textContent = deleteAccBtnText;
        if (eraseMemBtn) eraseMemBtn.textContent = eraseMemBtnText;
        if (fixHistoryBtn) fixHistoryBtn.textContent = fixHistoryBtnText;
        if (logOutBtn) logOutBtn.textContent = logOutBtnText;
        if (usageBtn) usageBtn.textContent = usageBtnText;
    }
}

// Run on initial load
adjustForMobile();

// Listen for window resize events
window.addEventListener('resize', function() {
    const wasMobile = mobile;
    mobile = window.innerWidth < 768;
    
    // Only adjust if mobile state changed
    if (wasMobile !== mobile) {
        adjustForMobile();
    }
});
