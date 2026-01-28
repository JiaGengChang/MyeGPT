import { getCookie } from './utils.js';
import { createAIMessage, createSystemMessage } from './messages.js';
import { create_spinner, intervalId } from './spinner.js';
import { isResponding, switchMode } from './controls.js';

const sendButton = document.querySelector('button#send-button');
const chatInput = document.querySelector('textarea#chat-input');
const chatHistory = document.querySelector('div#chat-history');

const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getCookie('access_token')}`,
}

async function initializeChat() {    
    switchMode();
    try {
        create_spinner();
        const initResponse = await fetch('/api/init', {
            method: 'POST',
            headers: headers,
        });
        if (!initResponse.ok) {
            throw new Error(`Failed to initialize chat. ${initResponse.status} ${initResponse.statusText}`);
        }
        const response = await initResponse.json();
        clearInterval(intervalId); // remove the countdown till refresh
        window.spinner.remove(); // remove the loading icon
        const usernameDisplay = document.getElementById('username-display');
        usernameDisplay.innerHTML = `<img id="user-icon" src="/static/favicon-32x32.png"><span>${response.username}</span>`;
        const emailDisplay = document.getElementById('email-display');
        emailDisplay.innerHTML = `<span>📧 ${response.email}</span>`;
        const modelIdDisplay = document.getElementById('model-id-display');
        modelIdDisplay.innerHTML = `<img id="llm-icon" src="/static/llm-icon.png"><span>${response.model_id}</span>`;
        const embeddingsModelIdDisplay = document.getElementById('embeddings-model-id-display');
        embeddingsModelIdDisplay.innerHTML = `<span>💬 ${response.embeddings_model_id}</span>`;
        createAIMessage(response.message);
        togglePageTitle(document.title, '🔔 New Message', 1000);
    } catch (error) {
        console.error('Error initializing chat:', error);
    } finally {
        switchMode();
    }
}

function togglePageTitle(oldTitle, newTitle, timeOutMs=5000) {
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
            headers: headers,
            body: JSON.stringify({ user_input: message }),  
        });

        if (!response.ok) {
            createSystemMessage(`Session expired. Please log in again. Error ${response.status}: ${response.statusText}`);
            throw new Error(`Failed to send message. ${response.status} ${response.statusText}`);
        }
        
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