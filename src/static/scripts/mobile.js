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
const commandTray = document.querySelector('.command-buttons');
const commandTrayStyle = commandTray ? commandTray.style : null;

function adjustForMobile() {
    // Create hamburger menu if it doesn't exist
    if (mobile) {
        
        if (commandTray && !document.getElementById('mobile-hamburger')) {
            const hamburger = document.createElement('button');
            hamburger.id = 'mobile-hamburger';
            hamburger.innerHTML = '☰';
            
            commandTray.style.display = 'none';
            commandTray.parentNode.insertBefore(hamburger, commandTray);
            
            hamburger.addEventListener('click', function() {
                if (commandTray.style.display === 'none') {
                    commandTray.style.cssText = `
                        display: block;
                        position: absolute;
                        max-height: 300px;
                        overflow-y: auto;
                        background: white;
                        border: 1px solid #ccc;
                        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                        z-index: 1000;
                        transform: translate(8%, 80%);
                    `;
                } else {
                    commandTray.style.cssText = 'display: none;';
                };
            });
        }
    } else {
        // restore original text command
        const hamburger = document.getElementById('mobile-hamburger');
        if (hamburger) {
            hamburger.remove();
            if (commandTray && commandTrayStyle) {
                // revert to original css
                commandTray.style = commandTrayStyle;
            }
        }
        // restore button texts
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
