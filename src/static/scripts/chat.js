import { getCookie } from './utils.js';
import { createAIMessage, createTraceMessage } from './messages.js';
import { create_spinner, loading_spinner_html, intervalId } from './spinner.js';

const sendButton = document.querySelector('button#send-button');
const chatInput = document.querySelector('textarea#chat-input');
const chatHistory = document.querySelector('div#chat-history');
const sendButtonIcon = sendButton.querySelector('span#send-icon');

let isResponding = false;

function switchMode() {
    if (isResponding) {
        sendButtonIcon.textContent = '↑';
        sendButton.disabled = false;
        isResponding = false;
    } 
    else {
        sendButtonIcon.innerHTML = loading_spinner_html;
        sendButton.disabled = true;
        isResponding = true;
    }
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
        const modelIdDisplay = document.getElementById('model-id-display');
        modelIdDisplay.textContent = `🤖 ${response.model_id}`;
        const embeddingsModelIdDisplay = document.getElementById('embeddings-model-id-display');
        embeddingsModelIdDisplay.textContent = `🤖𝐄 ${response.embeddings_model_id}`;
        createAIMessage(response.message);
        togglePageTitle(document.title, '🔔 New Message', 2000);
    } catch (error) {
        console.error('Error initializing chat:', error);
    }
}

function togglePageTitle(oldTitle, newTitle, timeOutMs=10000) {
    document.title = newTitle;
    if (document.hasFocus()) {
        setTimeout(() => {
            document.title = oldTitle;
        }, timeOutMs);
    } else {
        const focusHandler = () => {
            document.title = oldTitle;
            window.removeEventListener('focus', focusHandler);
        };
        window.addEventListener('focus', focusHandler);
    }
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

        let originalTitle = document.title;
        let loadingTitle = 'Working on it...';
        let alertTitle = '🔔 New Message'
        while (true) {
            document.title = loadingTitle;
            const { done, value } = await reader.read();
            if (done) {
                togglePageTitle(originalTitle, alertTitle);
                break;
            }
            var chunk = decoder.decode(value, { stream: false });
            console.log('Received chunk:', chunk);
            createAIMessage(chunk);
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

// Call on page load
document.addEventListener('DOMContentLoaded', initializeChat);