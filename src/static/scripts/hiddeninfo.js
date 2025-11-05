const userDisplay = document.getElementById('username-display');
const emailDisplay = document.getElementById('email-display');
const modelIdDisplay = document.getElementById('model-id-display');
const embeddingsProviderDisplay = document.getElementById('embeddings-provider-display');

userDisplay.addEventListener('dblclick', () => {
    emailDisplay.hidden = !emailDisplay.hidden;
    modelIdDisplay.hidden = !modelIdDisplay.hidden;
    embeddingsProviderDisplay.hidden = !embeddingsProviderDisplay.hidden;
});