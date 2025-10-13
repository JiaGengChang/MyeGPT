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
        try {
            const response = await fetch('/api/delete_account', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getCookie('access_token')}`,
                },
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

function toggleNotificationBtn () {
    const notificationBtn = document.getElementById("notifications-button");
    Notification.requestPermission().then((permission) => {
        if (permission === "granted") {
            if (window.innerWidth < 768) {
            notificationBtn.textContent = "🔔 On";
            } else {
            notificationBtn.textContent = "🔔 Enabled";
            }
            new Notification("Example Notification from MyeGPT");
        } else {
            if (window.innerWidth < 768) {
            notificationBtn.textContent = "🔕 Off";
            } else {
            notificationBtn.textContent = "🔕 Disabled";
            }
        }
    })
}


export {eraseMemory, clearChat, logOut, deleteAccount, toggleNotificationBtn};