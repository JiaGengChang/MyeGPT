const userDisplay = document.getElementById('username-display');
const emailDisplay = document.getElementById('email-display');
const modelIdDisplay = document.getElementById('model-id-display');
const embedModelIdDisplay = document.getElementById('embed-model-provider-display');

userDisplay.addEventListener('dblclick', () => {
    emailDisplay.hidden = !emailDisplay.hidden;
    modelIdDisplay.hidden = !modelIdDisplay.hidden;
    embedModelIdDisplay.hidden = !embedModelIdDisplay.hidden;
});