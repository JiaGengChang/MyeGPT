const sendButton = document.querySelector('.send-button');
const chatInput = document.querySelector('.chat-input');
const chatHistory = document.querySelector('.chat-history');
const sendButtonIcon = sendButton.querySelector('.icon'); 

let isResponding = false;

const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 30000);
const loading_spinner_html = `<div class="lds-spinner"><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div></div>`;

function switchMode() {
    if (isResponding) {
        sendButtonIcon.textContent = '↑';
        sendButton.disabled = false;
        isResponding = false;
    } 
    else {
        sendButtonIcon.innerHTML = loading_spinner_html;
        sendButton.disabled = false;
        isResponding = true;
    }
}


var intervalId;
function create_spinner() {
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
        if (seconds >= 30) {
            spinnerMessage.innerHTML = `<p>Resuming session... (${seconds}s)<br>It is possible the app previously crashed.<br>Please wait as recovery is attempted...</p>`;
        }
        if (seconds >= 100) {
            clearInterval(intervalId);
            spinnerMessage.innerHTML = `<p>Resuming session... (${seconds}s)<br>Time limit exceeded<br>Consider clearing chat history</p>`;
        }
    }, 1000);

    spinnerContainer.appendChild(spinnerMessage);
    chatHistory.appendChild(spinnerContainer);
    window.spinner = spinnerContainer; // enable global access
}

// Insert an AI message into chat history
function createBotMessage(message) {
    const botMessageElement = document.createElement('div');
    botMessageElement.classList.add('chat-message', 'ai');
    botMessageElement.innerHTML = message.replace(/\n/g, '<br>'); 
    const botMessageContainer = document.createElement('div');
    botMessageContainer.classList.add('chat-message-container');
    botMessageContainer.appendChild(botMessageElement);
    chatHistory.appendChild(botMessageContainer);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return botMessageContainer;
}

// insert a message into trace
function createTraceMessage(message) {
    // first reveal the trace button if its hidden
    const traceButton = document.getElementById('toggle-trace-button');
    if (traceButton && traceButton.hidden) {
        traceButton.hidden = false;
    }
    const tracePanel = document.getElementById('trace-contents');
    if (!tracePanel) return;

    const traceMessageElement = document.createElement('div');
    traceMessageElement.classList.add('trace-message');
    traceMessageElement.innerHTML = message.replace(/\n/g, '<br>'); 
    tracePanel.appendChild(traceMessageElement);
    tracePanel.scrollTop = tracePanel.scrollHeight;
    return traceMessageElement;
}

async function initializeChat() {    
    try {
        create_spinner()
        const initResponse = await fetch('/api/init', {
            method: 'POST',
            headers: {
            'Content-Type': 'application/json',
            },
        });
        if (!initResponse.ok) throw new Error('Failed to initialize chat');
        const response = await initResponse.json();
        clearInterval(intervalId); // remove the countdown till refresh
        window.spinner.remove(); // remove the loading icon
        const usernameDisplay = document.getElementById('username-display');
        usernameDisplay.textContent = `👤 ${response.username}`;
        const emailDisplay = document.getElementById('email-display');
        emailDisplay.textContent = `📤 ${response.email}`;
        const ipaddressDisplay = document.getElementById('ipaddress-display');
        ipaddressDisplay.textContent = `🌐 ${response.client_ip}`;
        createBotMessage(response.message);
        new Notification("New message from MyeGPT");
    } catch (error) {
        console.error('Error initializing chat:', error);
    }
}

// Call on page load
document.addEventListener('DOMContentLoaded', initializeChat);

function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    switchMode();

    // Add user message to chat history
    const userMessageContainer = document.createElement('div');
    userMessageContainer.classList.add('chat-message-container');
    const userMessageElement = document.createElement('div');
    userMessageElement.classList.add('chat-message', 'user');

    // Replace newline characters with <br> for HTML rendering
    userMessageElement.innerHTML = message.replace(/\n/g, '<br>'); 

    userMessageContainer.appendChild(userMessageElement);
    chatHistory.appendChild(userMessageContainer);

    chatHistory.scrollTop = chatHistory.scrollHeight;
    chatInput.value = '';
    resizeInput();

    // Send user message to backend
    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getCookie('access_token')}`,
            },
            body: JSON.stringify({ user_input: message }),  
        });


        if (!response.ok) throw new Error('Failed to send message');
        
        // Read the streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            var chunk = decoder.decode(value);
            console.log('Received chunk: ' + chunk);
            if (chunk.includes('💬')) {
                const lastIdx = chunk.lastIndexOf('💬');
                if (lastIdx !== -1) {
                    chunk = chunk.slice(start=lastIdx);
                }
                const botMessageContainer = createBotMessage(chunk);
                botMessageContainer.firstElementChild.classList.add('ai');
                // send an alert to desktop 
                new Notification("New message from MyeGPT");
            } else {
                createTraceMessage(chunk);
            }
        }

        } catch (error) {
        console.error('Error:', error);
    } finally {
        switchMode();
    }
}

sendButton.addEventListener('click', () => {
    if (!isResponding) {
        sendMessage();
    }
});

chatInput.addEventListener('keydown', function (event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendButton.click();
  }
});

const resizeInput = () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = `${chatInput.scrollHeight}px`;
};

chatInput.addEventListener('input', resizeInput);