/*
* adjust UI for mobile viewport
*/
let mobile = window.innerWidth < 768;

if (mobile) {
    //reduce h1 font size
    const headerH1 = document.querySelector('.header h1');
    if (headerH1) {
        headerH1.style.fontSize = '1.2em';
        headerH1.style.marginLeft = 'auto';
        headerH1.style.marginRight = 'auto';
    }
    //remove text content in command buttons
    const eraseMemBtn = document.getElementById('erase-memory-button');
    if (eraseMemBtn) eraseMemBtn.textContent = '🗑️🧠';
    const clearConvoBtn = document.getElementById('clear-convo-button');
    if (clearConvoBtn) clearConvoBtn.textContent = '🗑️💬';
    const logOutBtn = document.getElementById('logout-button');
    if (logOutBtn) logOutBtn.textContent = '🚪🔚';
    const notificationBtn = document.getElementById('notifications-button');
    if (notificationBtn) notificationBtn.textContent = '🔕 Off';
    const traceBtn = document.getElementById('toggle-trace-button');
    if (traceBtn) traceBtn.textContent = '🔎📜';
}
