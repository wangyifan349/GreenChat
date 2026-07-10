const chatConfiguration = window.CHAT_CONFIG;
const messageListElement = document.getElementById("message-list");
const loadingStateElement = document.getElementById("loading-state");
const messageFormElement = document.getElementById("message-form");
const messageInputElement = document.getElementById("message-input");
const fileInputElement = document.getElementById("file-input");
const filePreviewElement = document.getElementById("file-preview");
const fileNameElement = document.getElementById("file-name");
const removeFileButtonElement = document.getElementById("remove-file");
const sendButtonElement = document.getElementById("send-button");
const errorBoxElement = document.getElementById("error-box");
let latestMessageId = 0;
let isInitialLoad = true;
let isLoadingMessages = false;

// Convert a byte count into a compact human-readable file size.
function formatFileSize(fileSizeBytes) {
    if (fileSizeBytes === null || fileSizeBytes === undefined) return "";
    const fileSizeUnits = ["B", "KB", "MB", "GB"];
    let displayValue = Number(fileSizeBytes);
    let unitIndex = 0;
    while (displayValue >= 1024 && unitIndex < fileSizeUnits.length - 1) {
        displayValue /= 1024;
        unitIndex += 1;
    }
    const decimalPlaces = unitIndex === 0 ? 0 : 1;
    return `${displayValue.toFixed(decimalPlaces)} ${fileSizeUnits[unitIndex]}`;
}

function showErrorMessage(errorMessage) {
    errorBoxElement.textContent = errorMessage;
    errorBoxElement.classList.remove("d-none");
}

function clearErrorMessage() {
    errorBoxElement.textContent = "";
    errorBoxElement.classList.add("d-none");
}

// Build one message row without injecting untrusted HTML.
function appendMessage(messageData) {
    const messageRowElement = document.createElement("div");
    messageRowElement.className = `message-row${messageData.is_mine ? " mine" : ""}`;

    const avatarElement = document.createElement("div");
    avatarElement.className = "message-avatar";
    avatarElement.textContent = messageData.sender_username.charAt(0).toUpperCase();

    const messageBubbleElement = document.createElement("div");
    messageBubbleElement.className = "message-bubble";

    if (messageData.message_text) {
        const messageTextElement = document.createElement("div");
        messageTextElement.className = "message-text";
        messageTextElement.textContent = messageData.message_text;
        messageBubbleElement.appendChild(messageTextElement);
    }

    if (messageData.original_file_name) {
        const fileLinkElement = document.createElement("a");
        fileLinkElement.className = "file-card";
        fileLinkElement.href = messageData.download_url;

        const fileIconElement = document.createElement("div");
        fileIconElement.className = "file-icon";
        fileIconElement.textContent = "FILE";

        const fileDetailsElement = document.createElement("div");
        fileDetailsElement.className = "file-details";

        const fileTitleElement = document.createElement("div");
        fileTitleElement.className = "file-title";
        fileTitleElement.textContent = messageData.original_file_name;

        const fileSizeElement = document.createElement("div");
        fileSizeElement.className = "file-size";
        fileSizeElement.textContent = formatFileSize(messageData.file_size);

        fileDetailsElement.append(fileTitleElement, fileSizeElement);
        fileLinkElement.append(fileIconElement, fileDetailsElement);
        messageBubbleElement.appendChild(fileLinkElement);
    }

    const messageMetadataElement = document.createElement("div");
    messageMetadataElement.className = "message-meta";
    const messageDate = new Date(messageData.created_at);
    messageMetadataElement.textContent = Number.isNaN(messageDate.getTime())
        ? ""
        : messageDate.toLocaleString();

    messageBubbleElement.appendChild(messageMetadataElement);
    messageRowElement.append(avatarElement, messageBubbleElement);
    messageListElement.appendChild(messageRowElement);
}

// Poll only for messages newer than the latest message already displayed.
async function loadNewMessages() {
    if (isLoadingMessages) return;
    isLoadingMessages = true;
    try {
        const response = await fetch(
            `/api/chat/${encodeURIComponent(chatConfiguration.username)}/messages?after_id=${latestMessageId}`
        );
        const responseData = await response.json();
        if (!response.ok || !responseData.ok) {
            throw new Error(responseData.error || "Unable to load messages.");
        }

        loadingStateElement?.remove();
        const distanceFromBottom =
            messageListElement.scrollHeight
            - messageListElement.scrollTop
            - messageListElement.clientHeight;
        const shouldKeepScrolledToBottom = distanceFromBottom < 180;

        responseData.messages.forEach((messageData) => {
            appendMessage(messageData);
            latestMessageId = Math.max(latestMessageId, messageData.id);
        });

        if (isInitialLoad || shouldKeepScrolledToBottom) {
            messageListElement.scrollTop = messageListElement.scrollHeight;
        }
        isInitialLoad = false;
    } catch (error) {
        showErrorMessage(error.message);
    } finally {
        isLoadingMessages = false;
    }
}

messageFormElement.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrorMessage();

    // Keep the original value so code indentation and line breaks are preserved.
    const originalMessageText = messageInputElement.value;
    const containsVisibleText = originalMessageText.trim().length > 0;
    const selectedFile = fileInputElement.files[0];
    if (!containsVisibleText && !selectedFile) {
        showErrorMessage("Enter a message or select a file.");
        return;
    }

    const requestBody = new FormData();
    requestBody.append("message", originalMessageText);
    if (selectedFile) requestBody.append("file", selectedFile);

    sendButtonElement.disabled = true;
    try {
        const response = await fetch(
            `/api/chat/${encodeURIComponent(chatConfiguration.username)}/send`,
            {
                method: "POST",
                headers: { "X-CSRF-Token": chatConfiguration.csrfToken },
                body: requestBody,
            }
        );
        const responseData = await response.json();
        if (!response.ok || !responseData.ok) {
            throw new Error(responseData.error || "Unable to send message.");
        }

        messageInputElement.value = "";
        messageInputElement.style.height = "auto";
        fileInputElement.value = "";
        filePreviewElement.classList.add("d-none");
        await loadNewMessages();
        messageInputElement.focus();
    } catch (error) {
        showErrorMessage(error.message);
    } finally {
        sendButtonElement.disabled = false;
    }
});

fileInputElement.addEventListener("change", () => {
    clearErrorMessage();
    const selectedFile = fileInputElement.files[0];
    if (selectedFile && selectedFile.size > chatConfiguration.maxUploadBytes) {
        fileInputElement.value = "";
        filePreviewElement.classList.add("d-none");
        showErrorMessage("The selected file exceeds the 4 GiB upload limit.");
        return;
    }

    if (selectedFile) {
        fileNameElement.textContent = `${selectedFile.name} | ${formatFileSize(selectedFile.size)}`;
        filePreviewElement.classList.remove("d-none");
    } else {
        filePreviewElement.classList.add("d-none");
    }
});

removeFileButtonElement.addEventListener("click", () => {
    fileInputElement.value = "";
    filePreviewElement.classList.add("d-none");
});

messageInputElement.addEventListener("input", () => {
    messageInputElement.style.height = "auto";
    messageInputElement.style.height = `${Math.min(messageInputElement.scrollHeight, 150)}px`;
});

// Enter inserts a new line. Ctrl+Enter sends the current message.
messageInputElement.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.ctrlKey) {
        event.preventDefault();
        messageFormElement.requestSubmit();
    }
});

loadNewMessages();
window.setInterval(loadNewMessages, 1800);
