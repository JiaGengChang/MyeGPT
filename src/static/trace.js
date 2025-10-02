function toggleTracePanel() {
    const tracePanel = document.getElementById('trace-contents');
    const toggleButton = document.getElementById('toggle-trace');
    if (!tracePanel || !toggleButton) return;

    const isNowExpanded = tracePanel.classList.toggle('expanded');

    if (isNowExpanded) {
        tracePanel.hidden = false;
        // Expand to half the viewport height (50vh) and full width, fixed to bottom
        // tracePanel.style.position = 'fixed';
        // tracePanel.style.left = '0';
        // tracePanel.style.right = '0';
        // tracePanel.style.bottom = '0';
        tracePanel.style.height = 'auto';
        tracePanel.style.maxHeight = '40dvh';
        // tracePanel.style.width = '100%';
        tracePanel.style.zIndex = '9999';
        tracePanel.style.overflow = 'auto';
        toggleButton.setAttribute('aria-expanded', 'true');
        toggleButton.textContent = '📜 Click to hide';
        toggleButton.style.marginBottom = '10px';
        // Keep chat history visible below panel if present
        // if (typeof chatHistory !== 'undefined' && chatHistory) {
        //     chatHistory.style.marginTop = `${tracePanel.offsetHeight}px`;
        // }
        tracePanel.focus?.();
    } else {
        // Revert to original styles
        ['position','left','right','bottom','height','width','zIndex','overflow'].forEach(prop => {
            tracePanel.style[prop] = '';
        });
        toggleButton.setAttribute('aria-expanded', 'false');
        toggleButton.textContent = '📜 Fine-grained';
        toggleButton.style['marginBottom'] = '';
        if (typeof chatHistory !== 'undefined' && chatHistory) {
            chatHistory.style.marginTop = '';
        }
        tracePanel.hidden = true;
    }
}