const conversationItemElements = document.querySelectorAll(".conversation-item");
const conversationContextMenuElement = document.getElementById("conversation-context-menu");
let selectedConversationElement = null;

function navigateToConversation(conversationElement) {
    window.location.href = conversationElement.dataset.chatUrl;
}

function hideConversationContextMenu() {
    if (conversationContextMenuElement) conversationContextMenuElement.hidden = true;
    selectedConversationElement = null;
}

conversationItemElements.forEach((conversationElement) => {
    conversationElement.addEventListener("click", () => {
        navigateToConversation(conversationElement);
    });

    conversationElement.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            navigateToConversation(conversationElement);
        }
    });

    // Replace the browser menu with chat-specific actions.
    conversationElement.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        if (!conversationContextMenuElement) return;

        selectedConversationElement = conversationElement;
        conversationContextMenuElement.hidden = false;
        conversationContextMenuElement.style.left = `${Math.min(
            event.clientX,
            window.innerWidth - 230
        )}px`;
        conversationContextMenuElement.style.top = `${Math.min(
            event.clientY,
            window.innerHeight - 120
        )}px`;
    });
});

conversationContextMenuElement?.addEventListener("click", (event) => {
    const selectedAction = event.target.dataset.action;
    if (!selectedConversationElement || !selectedAction) return;

    if (selectedAction === "open") {
        window.location.href = selectedConversationElement.dataset.chatUrl;
    } else if (selectedAction === "export") {
        window.location.href = selectedConversationElement.dataset.exportUrl;
    }
    hideConversationContextMenu();
});

document.addEventListener("click", (event) => {
    if (!conversationContextMenuElement?.contains(event.target)) {
        hideConversationContextMenu();
    }
});
window.addEventListener("resize", hideConversationContextMenu);
window.addEventListener("scroll", hideConversationContextMenu, true);
