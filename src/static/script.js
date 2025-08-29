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
    setInterval(() => {
        seconds++;
        spinnerMessage.innerHTML = `<p>Initializing... (${seconds}s)<br>Please refresh if it takes over 10 seconds</p>`;
    }, 1000);
    
    spinnerContainer.appendChild(spinnerMessage);
    chatHistory.appendChild(spinnerContainer);
    window.spinner = spinnerContainer; // enable global access
}

// Insert an AI message into chat history
function createBotMessage(message) {
    const botMessageElement = document.createElement('div');
    botMessageElement.classList.add('chat-message', 'ai-response');
    botMessageElement.innerHTML = message.replace(/\n/g, '<br>'); 
    const botMessageContainer = document.createElement('div');
    botMessageContainer.classList.add('chat-message-container');
    botMessageContainer.appendChild(botMessageElement);
    chatHistory.appendChild(botMessageContainer);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return botMessageContainer;
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
        window.spinner.remove();
        createBotMessage(`Session ID: ${response.thread_id}`);
        createBotMessage(response.message);
    } catch (error) {
        console.error('Error initializing chat:', error);
    }
}

// Call on page load
document.addEventListener('DOMContentLoaded', initializeChat);

async function sendMessage() {
    // Check if window width is below 768px, then remove logo
    if (window.innerWidth < 768) {
        //remove logo if exists
        const headerImg = document.querySelector('.header img');
        if (headerImg) {
            headerImg.remove();
        }
        //reduce h1 font size
        const headerH1 = document.querySelector('.header h1');
        if (headerH1) {
            headerH1.style.fontSize = '1.2em';
        }
    }
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
            },
            body: JSON.stringify({ user_input: message }),  
        });

        if (!response.ok) throw new Error('Failed to send message');
        
        // Read the streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        let lastThinkingContainer = null;
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            
            // Check if this is a thinking chunk
            const isThinking = chunk.startsWith('<thinking>') && chunk.endsWith('</thinking>');
            
            // Remove previous container if it was thinking
            if (lastThinkingContainer && !isThinking) {
            // Add fade-out animation before removing
            lastThinkingContainer.style.transition = 'opacity 0.3s ease-out';
            lastThinkingContainer.style.opacity = '0';
            setTimeout(() => lastThinkingContainer.parentElement.remove(), 300);
            lastThinkingContainer = null;
            }
            
            // // Create a new container for each chunk
            const botMessageContainer = createBotMessage(chunk);
            // const chunkMessageElement = document.createElement('div');
            // chunkMessageElement.classList.add('chat-message');
            // // In case we want to stylize it differently
            if (isThinking) {
                botMessageContainer.firstElementChild.classList.add('ai-thinking');
            } else {
                botMessageContainer.firstElementChild.classList.add('ai-response');
            };
            // chunkMessageElement.innerHTML = chunk.replace(/\n/g, '<br>');
            // const botMessageContainer = document.createElement('div');
            // botMessageContainer.classList.add('chat-message-container');
            // botMessageContainer.appendChild(chunkMessageElement);
            // chatHistory.appendChild(botMessageContainer);
            // chatHistory.scrollTop = chatHistory.scrollHeight;

            // Track thinking containers
            if (isThinking) {
            lastThinkingContainer = botMessageContainer;
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