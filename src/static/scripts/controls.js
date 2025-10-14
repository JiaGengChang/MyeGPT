import { getCookie } from './utils.js';

async function eraseMemory() {
    if(confirm('Erase memory of previous conversations associated with this account?')) { 
        try {
            const response = await fetch('/api/erase_memory', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getCookie('access_token')}`,
                },
            });
            
            if (!response.ok) throw new Error('Failed to erase memory');
            return await response.json();

        } catch (error) {
            console.error('Error:', error);
        } finally {
            //
        }
    }
}

function clearChat() {
    if(confirm('Clear current conversation? This will not erase memory of these conversations.')){
        document.getElementById('chat-history').innerHTML = '';
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

function toggleNotificationBtn() {
    const notificationBtn = document.getElementById("notifications-button");
    Notification.requestPermission().then((permission) => {
        if (permission === "granted") {
            if (window.innerWidth < 768) {
                notificationBtn.textContent = "🔔 On";
            } else {
                notificationBtn.textContent = "🔔 Enabled";
            }
            return new Notification("Example Notification from MyeGPT");
        } else {
            if (window.innerWidth < 768) {
                notificationBtn.textContent = "🔕 Off";
            } else {
                notificationBtn.textContent = "🔕 Disabled";
            }
        }
    });
}

function toggleTracePanel() {
    let mobile = window.innerWidth < 768;
    const tracePanel = document.getElementById('trace-contents');
    const toggleButton = document.getElementById('toggle-trace-button');
    if (!tracePanel || !toggleButton) return;

    const isNowExpanded = tracePanel.classList.toggle('expanded');

    if (isNowExpanded) {
        tracePanel.hidden = false;
        toggleButton.textContent = mobile ? '🔎📜' : '📜 Click to hide';
        toggleButton.setAttribute('aria-expanded', 'true');
        tracePanel.style.height = 'auto';
        tracePanel.style.maxHeight = '40dvh';
        tracePanel.style.zIndex = '9999';
        tracePanel.style.overflow = 'auto';
        tracePanel.style.boxShadow = mobile ? '0vw 0vw 0vw 0.1vw rgba(155, 155, 155, 1)' : '';
        tracePanel.focus?.();
    } else {
        tracePanel.hidden = true;
        // Revert to original content
        toggleButton.setAttribute('aria-expanded', 'false');
        toggleButton.textContent = mobile ? '🔎📜' : '📜 Click to show';
        // Revert to original styles
        ['position','left','right','bottom','height','width','zIndex','overflow'].forEach(prop => {
            tracePanel.style[prop] = '';
        });
        ['boxShadow'].forEach(prop => {
            toggleButton.style[prop] = '';
        });
        if (typeof chatHistory !== 'undefined' && chatHistory) {
            chatHistory.style.marginTop = '';
        }
    }
}

export {eraseMemory, clearChat, logOut, deleteAccount, toggleNotificationBtn, toggleTracePanel};