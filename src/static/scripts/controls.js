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
    if(confirm('This will delete tool calls that do not have corresponding results. The conversation history will be truncated up to the deleted tool call. Proceed?')) {
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

function parse_usage_metadata(usage_metadata) {
    let msg;
    if (!usage_metadata) {
        msg = 'No usage metadata available.';
    } else {
        // example usage_metadata
        // {"input_tokens":21188,"output_tokens":341,"total_tokens":21529,"input_token_details":{"audio":0,"cache_read":18048},"output_token_details":{"audio":0,"reasoning":128}}
        const cachedT = usage_metadata.input_token_details.cache_read || -1;
        const inputT = usage_metadata.input_tokens - cachedT || -1;
        const reasonT = usage_metadata.output_token_details.reasoning || -1;
        const outputT = usage_metadata.output_tokens - reasonT || -1;
        const totalT = usage_metadata.total_tokens || -1;
        // based on GPT-5-mini pricing
        const inputCost = inputT * 2.5e-7 + cachedT * 2.5e-8;
        const outputCost = outputT * 2e-6;
        const totalCost = inputCost + outputCost;
        // Create two-column layout
        msg = `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <strong>💸💸 Running cost</strong><br>
                Input: $${inputCost.toFixed(3)}<br>
                Output: $${outputCost.toFixed(3)}<br>
                Total: $${totalCost.toFixed(3)} USD
            </div>
            <div>
                <strong>💬💬 Running token usage</strong><br>
                Input: ${inputT}&#9Cached: ${cachedT}<br>
                Output: ${outputT}&#9Reasoning: ${reasonT}<br>
                Total: ${totalT}
            </div>
        </div>`
    }
    return msg;
}

async function checkUsage(){
    switchMode();
    const header = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getCookie('access_token')}`,
    };
    try {
        const response = await fetch('/api/usage_metadata', {
            method: 'GET',
            headers: header
        });
        if (!response.ok) throw new Error('Failed to fetch usage metadata');
        const data = await response.json();
        const usage_metadata_msg = parse_usage_metadata(data.usage_metadata)
        createSystemMessage(usage_metadata_msg);
    } catch (error) {
        createSystemMessage('Error fetching usage metadata. See console for details.');
        console.error('Error:', error);
    } finally {
        switchMode();
    };
};

export {isResponding, switchMode, eraseMemory, clearChat, logOut, deleteAccount, fixHistory, checkUsage};