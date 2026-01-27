import { getCookie } from './utils.js';
import { createSystemMessage } from './messages.js';
import { loading_spinner_html } from './spinner.js';

const sendButton = document.querySelector('button#send-button');
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

async function eraseMemory() {
    if(confirm('Erase memory of previous conversations associated with this account?')) { 
        switchMode();
        try {
            const response = await fetch('/api/erase_memory', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getCookie('access_token')}`,
                },
            });
            
            if (!response.ok) throw new Error('Failed to erase memory');
            await response.json();
            switchMode();            
        } catch (error) {
            console.error('Error:', error);
        } finally {
            // insert a message into chat indicating memory has been erased
            createSystemMessage('🗑️ Memory of previous conversations has been erased.');
        }
    }
}

function clearChat() {
    if(confirm('Clear current conversation? This will not erase memory of these conversations.')){
        document.getElementById('chat-history').innerHTML = '';
    }
    createSystemMessage('🧹 Conversation has been cleared.');
}

function logOut() {
    if(confirm('Are you sure you want to log out?\nChat history will be cleared, although memory of the conversations will remain.')){
        // clear access token cookie
        document.cookie = 'access_token=; Max-Age=0; path=/;'; 
        // redirect to home page
        window.location.href = '/';
    }
}

async function deleteAccount() {
    if(confirm('Are you sure you want to delete your account?\nThis action is irreversible and will erase all your data, including chat history and memory.')) {
        const header = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getCookie('access_token')}`,
        };
        try {
            const response0 = await fetch('/api/erase_memory', {
                method: 'DELETE',
                headers: header,
            });
            if (!response0.ok) throw new Error('Failed to delete memory before account deletion');

            const response = await fetch('/api/delete_account', {
                method: 'DELETE',
                headers: header,
            });
            
            if (!response.ok) throw new Error('Failed to delete account');
            // clear access token cookie
            document.cookie = 'access_token=; Max-Age=0; path=/;'; 
            // redirect to home page
            window.location.href = '/';
            return await response.json();

        } catch (error) {
            console.error('Error:', error);
        } finally {
            //
        }
    }
}

async function fixHistory(){
    if(confirm('Fix history?')) {
        switchMode();
        const header = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getCookie('access_token')}`,
        };
        try {
            const response = await fetch('/api/fix_history', {
                method: 'POST',
                headers: header,
            });
            if (!response.ok) throw new Error('Failed to fix history');
            const data = await response.json();
            console.log(data);
            if (data.response == 0) {
                createSystemMessage('✅ Conversation history is empty. Start a new conversation.');
            } else if (data.response == 1) {
                createSystemMessage('✅ Conversation history seems fine. No changes were made.');
            } else if (data.response == 2) {
                createSystemMessage('🚧 Error-causing parts of the conversation history deleted. Try simplifying the question or asking it in another way.');
            } else {
                createSystemMessage('🚧 Unknown response code');
            }
        } catch (error) {
            console.error('Error:', error);
        } finally {
            switchMode();
        }
    }
}

export {isResponding, switchMode, eraseMemory, clearChat, logOut, deleteAccount, fixHistory};