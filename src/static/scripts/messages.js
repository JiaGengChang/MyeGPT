const chatHistory = document.querySelector('div#chat-history');


// Insert an AI message into chat history
function createAIMessage(message) {
    const botMessageElement = document.createElement('div');
    botMessageElement.classList.add('chat-message', 'ai');
    botMessageElement.innerHTML = message//.replace(/\n/g, '<br>'); 
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
        // add extra column to accommodate trace button
        const commandButtons = document.querySelector('.command-buttons');
        if (commandButtons) {
            commandButtons.style.gridTemplateColumns = 'repeat(5, 1fr)';
        }
        traceButton.hidden = false;
    }
    const tracePanel = document.getElementById('trace-contents');
    if (!tracePanel) return;

    const traceMessageElement = document.createElement('div');
    traceMessageElement.classList.add('trace-message');
    traceMessageElement.innerHTML = message//.replace(/\n/g, '<br>'); 
    tracePanel.appendChild(traceMessageElement);
    tracePanel.scrollTop = tracePanel.scrollHeight;
    return traceMessageElement;
}

function createSystemMessage(message) {
    const memoryErasedMessageContainer = document.createElement('div');
    memoryErasedMessageContainer.classList.add('chat-message-container');
    const memoryErasedMessageElement = document.createElement('div');
    memoryErasedMessageElement.classList.add('chat-message', 'system');
    memoryErasedMessageElement.innerHTML = message;
    memoryErasedMessageContainer.appendChild(memoryErasedMessageElement);
    chatHistory.appendChild(memoryErasedMessageContainer);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

export { createAIMessage, createSystemMessage, createTraceMessage };
