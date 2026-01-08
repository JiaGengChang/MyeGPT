const loading_spinner_html = `<div class="lds-spinner"><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div></div>`;

var intervalId;
function create_spinner() {
    const chatHistory = document.querySelector('div#chat-history');
    const spinnerContainer = document.createElement('div');
    spinnerContainer.classList.add('init-spinner-container');
    const spinnerElement = document.createElement('div');
    spinnerElement.classList.add('init-spinner-element');
    spinnerContainer.appendChild(spinnerElement);
    const spinnerMessage = document.createElement('div');
    spinnerMessage.classList.add('init-spinner-message');    
    
    // Timer
    let seconds = 0;
    intervalId = setInterval(() => {
        seconds++;
        spinnerMessage.innerHTML = `<p>Resuming session... (${seconds}s)</p>`;
        if (seconds >= 15) {
            spinnerMessage.innerHTML = `<p>Resuming session... (${seconds}s)<br>Loading takes longer as chat history expands...</p>`;
        }
        if (seconds >= 45) {
            spinnerMessage.innerHTML = `<p>Resuming session... (${seconds}s)<br>Taking longer than usual.<br>It is possible the app previously crashed.<br>Recovery is being attempted...</p>`;
        }
        if (seconds >= 90) {
            clearInterval(intervalId);
            spinnerMessage.innerHTML = `<p>Resuming session... (${seconds}s)<br>Taking longer than usual<br>App is possibly unresponsive. Contact us or consider clearing chat history</p>`;
        }
    }, 1000);

    spinnerContainer.appendChild(spinnerMessage);
    chatHistory.appendChild(spinnerContainer);
    window.spinner = spinnerContainer; // enable global access
}

export { loading_spinner_html, create_spinner, intervalId };