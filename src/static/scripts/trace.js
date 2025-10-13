
function toggleTracePanel() {
    let mobile = window.innerWidth < 768;
    const tracePanel = document.getElementById('trace-contents');
    const toggleButton = document.getElementById('toggle-trace-button');
    if (!tracePanel || !toggleButton) return;

    const isNowExpanded = tracePanel.classList.toggle('expanded');

    if (isNowExpanded) {
        tracePanel.hidden = false;
        toggleButton.textContent = mobile ? '🔎📜' : '📜 Click to hide';
        toggleButton.setAttribute('aria-expanded', 'true');
        tracePanel.style.height = 'auto';
        tracePanel.style.maxHeight = '40dvh';
        tracePanel.style.zIndex = '9999';
        tracePanel.style.overflow = 'auto';
        tracePanel.style.boxShadow = mobile ? '0vw 0vw 0vw 0.1vw rgba(155, 155, 155, 1)' : '';
        tracePanel.focus?.();
    } else {
        tracePanel.hidden = true;
        // Revert to original content
        toggleButton.setAttribute('aria-expanded', 'false');
        toggleButton.textContent = mobile ? '🔎📜' : '📜 Click to show';
        // Revert to original styles
        ['position','left','right','bottom','height','width','zIndex','overflow'].forEach(prop => {
            tracePanel.style[prop] = '';
        });
        ['boxShadow'].forEach(prop => {
            toggleButton.style[prop] = '';
        });
        if (typeof chatHistory !== 'undefined' && chatHistory) {
            chatHistory.style.marginTop = '';
        }
    }
}

export {toggleTracePanel};