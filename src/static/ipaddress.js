const userDisplay = document.getElementById('username-display');
const emailDisplay = document.getElementById('email-display');
const ipAddressDisplay = document.getElementById('ipaddress-display');

userDisplay.addEventListener('dblclick', () => {
    emailDisplay.hidden = !emailDisplay.hidden;
    ipAddressDisplay.hidden = !ipAddressDisplay.hidden;
});