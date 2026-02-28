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
            const message = await response.json();
            createSystemMessage(message.message);
        } catch (error) {
            console.error('Error:', error);
            createSystemMessage(error);
        } finally {
            switchMode();            
        }
    }
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
        // example usage_metadata for Claude 4.5 Opus
        // usage_metadata={'input_tokens': 65853, 'output_tokens': 121, 'total_tokens': 65974, 'input_token_details': {'cache_read': 0, 'cache_creation': 0, 'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}}        
        const inputT = usage_metadata.input_tokens || 0;
        const cacheHitsT = usage_metadata.input_token_details.cache_read || 0;
        const outputT = usage_metadata.output_tokens || 0;
        const totalT = usage_metadata.total_tokens || 0;
        
        // based on Claude 4.5 opus pricing
        const inputCost = inputT * 5e-6 + cacheHitsT * .5e-6;
        const outputCost = outputT * 2.5e-5;
        const cachedWrites5mCost = usage_metadata.input_token_details.ephemeral_5m_input_tokens * 6.25e-6;
        const cachedWrites1hCost = usage_metadata.input_token_details.ephemeral_1h_input_tokens * 1e-5;
        const totalCost = inputCost + outputCost + cachedWrites5mCost + cachedWrites1hCost;
        // Create two-column layout
        msg = `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <strong>💸💸 Running cost</strong><br>
                Input: $${inputCost.toFixed(3)}<br>
                Output: $${outputCost.toFixed(3)}<br>
                Cache writes (5m): $${cachedWrites5mCost.toFixed(3)}<br>
                Cache writes (1h): $${cachedWrites1hCost.toFixed(3)}<br>
                Total: $${totalCost.toFixed(3)} USD
            </div>
            <div>
                <strong>💬💬 Running token usage</strong><br>
                Input: ${inputT}&#9Cached: ${cacheHitsT}<br>
                Cache writes (5m): ${usage_metadata.input_token_details.ephemeral_5m_input_tokens}<br>
                Cache writes (1h): ${usage_metadata.input_token_details.ephemeral_1h_input_tokens}<br>
                Output: ${outputT}<br>
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

export {isResponding, switchMode, eraseMemory, logOut, deleteAccount, fixHistory, checkUsage};