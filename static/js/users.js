(() => {
    const searchInputElement = document.getElementById("live-user-search-input");
    const searchMenuElement = document.getElementById("live-user-search-menu");
    if (!searchInputElement || !searchMenuElement) return;

    let searchDelayTimer = null;
    let activeResultIndex = -1;
    let resultLinkElements = [];

    function closeSearchMenu() {
        searchMenuElement.hidden = true;
        searchInputElement.setAttribute("aria-expanded", "false");
        activeResultIndex = -1;
        resultLinkElements = [];
    }

    function selectResultByIndex(resultIndex) {
        resultLinkElements.forEach((resultLinkElement) => {
            resultLinkElement.classList.remove("active");
        });
        if (!resultLinkElements.length) {
            activeResultIndex = -1;
            return;
        }

        activeResultIndex = Math.max(0, Math.min(resultIndex, resultLinkElements.length - 1));
        const activeResultElement = resultLinkElements[activeResultIndex];
        activeResultElement.classList.add("active");
        activeResultElement.scrollIntoView({ block: "nearest" });
    }

    function renderSearchResults(usernames) {
        searchMenuElement.replaceChildren();
        activeResultIndex = -1;
        resultLinkElements = [];

        if (!usernames.length) {
            const emptyMessageElement = document.createElement("div");
            emptyMessageElement.className = "live-user-search-empty";
            emptyMessageElement.textContent = "No matching users.";
            searchMenuElement.appendChild(emptyMessageElement);
        } else {
            usernames.forEach((username) => {
                const resultLinkElement = document.createElement("a");
                resultLinkElement.className = "live-user-search-item";
                resultLinkElement.href = `/chat/${encodeURIComponent(username)}`;
                resultLinkElement.setAttribute("role", "option");

                const avatarElement = document.createElement("span");
                avatarElement.className = "live-user-search-avatar";
                avatarElement.textContent = username.charAt(0).toUpperCase();

                const usernameElement = document.createElement("strong");
                usernameElement.textContent = username;

                resultLinkElement.append(avatarElement, usernameElement);
                searchMenuElement.appendChild(resultLinkElement);
            });
            resultLinkElements = Array.from(
                searchMenuElement.querySelectorAll(".live-user-search-item")
            );
        }

        searchMenuElement.hidden = false;
        searchInputElement.setAttribute("aria-expanded", "true");
    }

    // Request ranked usernames after a short debounce interval.
    async function refreshSearchResults() {
        try {
            const response = await fetch(
                `/api/users/search?q=${encodeURIComponent(searchInputElement.value)}`,
                { headers: { Accept: "application/json" } }
            );
            const responseData = await response.json();
            if (!response.ok || !responseData.ok) {
                throw new Error(responseData.error || "Search failed.");
            }
            renderSearchResults(responseData.users);
        } catch (error) {
            closeSearchMenu();
        }
    }

    searchInputElement.addEventListener("input", () => {
        window.clearTimeout(searchDelayTimer);
        searchDelayTimer = window.setTimeout(refreshSearchResults, 120);
    });
    searchInputElement.addEventListener("focus", refreshSearchResults);

    searchInputElement.addEventListener("keydown", (event) => {
        if (event.key === "ArrowDown") {
            event.preventDefault();
            if (searchMenuElement.hidden) refreshSearchResults();
            else selectResultByIndex(activeResultIndex + 1);
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            selectResultByIndex(
                activeResultIndex <= 0
                    ? resultLinkElements.length - 1
                    : activeResultIndex - 1
            );
        } else if (
            event.key === "Enter"
            && activeResultIndex >= 0
            && resultLinkElements[activeResultIndex]
        ) {
            event.preventDefault();
            window.location.href = resultLinkElements[activeResultIndex].href;
        } else if (event.key === "Escape") {
            closeSearchMenu();
        }
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".live-user-search-wrapper")) closeSearchMenu();
    });
})();
