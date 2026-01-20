/*
* adjust UI for mobile viewport
*/
const headerH1 = document.querySelector('.header h1');

const deleteAccBtn = document.getElementById('delete-account-button');
const eraseMemBtn = document.getElementById('erase-memory-button');
const clearConvoBtn = document.getElementById('clear-convo-button');
const logOutBtn = document.getElementById('logout-button');
const notificationBtn = document.getElementById('notifications-button');
const exportBtn = document.getElementById('export-chat-button');

const headerH1Style = headerH1 ? window.getComputedStyle(headerH1) : null;
const deleteAccBtnText = deleteAccBtn ? deleteAccBtn.textContent : '';
const eraseMemBtnText = eraseMemBtn ? eraseMemBtn.textContent : '';
const clearConvoBtnText = clearConvoBtn ? clearConvoBtn.textContent : '';
const logOutBtnText = logOutBtn ? logOutBtn.textContent : '';
const notificationBtnText = notificationBtn ? notificationBtn.textContent : '';
const exportBtnText = exportBtn ? exportBtn.textContent : '';

let mobile = window.innerWidth < 768;

function adjustForMobile() {
    if (mobile) {
        //reduce h1 font size
        if (headerH1) {
            headerH1.style.fontSize = '1.2em';
            headerH1.style.marginLeft = 'auto';
            headerH1.style.marginRight = 'auto';
        }
        //remove text content in command buttons
        if (deleteAccBtn) deleteAccBtn.textContent = '🗑️🔐';
        if (eraseMemBtn) eraseMemBtn.textContent = '🗑️🧠';
        if (clearConvoBtn) clearConvoBtn.textContent = '🗑️💬';
        if (logOutBtn) logOutBtn.textContent = '🚪🔚';
        if (notificationBtn) notificationBtn.textContent = '🔕 Off';
        if (exportBtn) exportBtn.textContent = '🖨️💬';
    } else {
        if (headerH1 && headerH1Style) {
            headerH1.style.fontSize = headerH1Style.fontSize;
            headerH1.style.marginLeft = headerH1Style.marginLeft;
            headerH1.style.marginRight = headerH1Style.marginRight;
        }
        if (deleteAccBtn) deleteAccBtn.textContent = deleteAccBtnText;
        if (eraseMemBtn) eraseMemBtn.textContent = eraseMemBtnText;
        if (clearConvoBtn) clearConvoBtn.textContent = clearConvoBtnText;
        if (logOutBtn) logOutBtn.textContent = logOutBtnText;
        if (notificationBtn) notificationBtn.textContent = notificationBtnText;
        if (exportBtn) exportBtn.textContent = exportBtnText;
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
