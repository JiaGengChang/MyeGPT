const userDisplay = document.getElementById('username-display');
const emailDisplay = document.getElementById('email-display');
const modelIdDisplay = document.getElementById('model-id-display');
const embeddingsModelIdDisplay = document.getElementById('embeddings-model-id-display');

userDisplay.addEventListener('dblclick', () => {
    emailDisplay.hidden = !emailDisplay.hidden;
    modelIdDisplay.hidden = !modelIdDisplay.hidden;
    embeddingsModelIdDisplay.hidden = !embeddingsModelIdDisplay.hidden;
});