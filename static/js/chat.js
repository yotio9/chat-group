document.addEventListener("DOMContentLoaded", () => {
    const appShell = document.getElementById("appShell");
    const sidebar = document.getElementById("sidebar");
    const conversationList = document.getElementById("conversationList");
    const conversationCount = document.getElementById("conversationCount");
    const searchInput = document.getElementById("searchInput");
    const messagesContainer = document.getElementById("messagesContainer");
    const messageForm = document.getElementById("messageForm");
    const messageInput = document.getElementById("messageInput");
    const fileInput = document.getElementById("fileInput");
    const attachmentPreview = document.getElementById("attachmentPreview");
    const attachmentName = document.getElementById("attachmentName");
    const removeAttachmentBtn = document.getElementById("removeAttachmentBtn");
    const chatAvatar = document.getElementById("chatAvatar");
    const chatName = document.getElementById("chatName");
    const chatStatus = document.getElementById("chatStatus");

    if (
        !appShell || !sidebar || !conversationList || !conversationCount ||
        !searchInput || !messagesContainer || !messageForm || !messageInput ||
        !fileInput || !attachmentPreview || !attachmentName ||
        !removeAttachmentBtn || !chatAvatar || !chatName || !chatStatus
    ) {
        console.error("La page de messagerie ne contient pas les éléments requis.");
        return;
    }

    const conversations = new Map();
    let activeFilter = "all";
    let activeConversationId = null;
    let activeMessages = [];
    let attachedFile = null;
    let isSendingMessage = false;
    let isCreatingConversation = false;
    let activeRequestId = 0;
    let activeRequestController = null;
    let directoryRequestController = null;
    let groupRequestController = null;
    let directoryRequestId = 0;
    let groupRequestId = 0;
    let directoryNextOffset = null;
    let groupNextOffset = null;
    const selectedGroupMemberIds = new Set();

    const initialConversationItems = Array.from(
        conversationList.querySelectorAll(".conversation-item")
    );

    initialConversationItems.forEach((item) => {
        const id = item.dataset.id;
        conversations.set(id, item);
    });

    const dateDivider = messagesContainer.querySelector(".date-divider");
    const notice = document.createElement("p");
    notice.className = "chat-notice";
    notice.id = "chatNotice";
    notice.setAttribute("aria-live", "polite");
    notice.hidden = true;
    document.querySelector(".chat-header").after(notice);

    function updateConversationCount() {
        const visibleCount = Array.from(conversations.values())
            .filter((item) => !item.hidden).length;
        conversationCount.textContent =
            `${visibleCount} conversation${visibleCount === 1 ? "" : "s"}`;
    }

    function filterConversations() {
        const query = searchInput.value.trim().toLocaleLowerCase();

        conversations.forEach((item) => {
            const matchesQuery = item.dataset.name.toLocaleLowerCase().includes(query);
            const matchesFilter =
                activeFilter === "all" ||
                (activeFilter === "unread" && Number(item.dataset.unread) > 0) ||
                (activeFilter === "groups" && item.dataset.type === "group");
            item.hidden = !(matchesQuery && matchesFilter);
        });

        let emptyState = document.getElementById("conversationEmptyState");
        if (!emptyState) {
            emptyState = document.createElement("p");
            emptyState.className = "sidebar-empty";
            emptyState.id = "conversationEmptyState";
            emptyState.textContent = "Aucune conversation correspondante.";
            conversationList.append(emptyState);
        }
        emptyState.hidden = Array.from(conversations.values())
            .some((item) => !item.hidden);
        updateConversationCount();
    }

    function showNotice(message) {
        notice.textContent = message;
        notice.hidden = false;
    }

    function showMessageState(message) {
        messagesContainer.replaceChildren();
        if (dateDivider) {
            messagesContainer.append(dateDivider);
        }

        const state = document.createElement("p");
        state.className = "empty-state";
        state.setAttribute("role", "status");
        state.textContent = message;
        messagesContainer.append(state);
    }

    function renderMessages(messages) {
        activeMessages = messages;
        messagesContainer.replaceChildren();
        if (dateDivider) {
            dateDivider.querySelector("span").textContent =
                new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" }).format(new Date());
            messagesContainer.append(dateDivider);
        }

        messages.forEach((message) => {
            const row = document.createElement("div");
            row.className = `message-row ${message.is_mine ? "sent" : "received"}`;
            const bubble = document.createElement("div");
            bubble.className = "message-bubble";
            const text = document.createElement("p");
            text.textContent = message.content;
            const meta = document.createElement("span");
            meta.className = "message-meta";
            meta.textContent = message.created_at;
            bubble.append(text, meta);
            row.append(bubble);
            messagesContainer.append(row);
        });

        if (messages.length === 0) {
            const emptyState = document.createElement("p");
            emptyState.className = "empty-state";
            emptyState.setAttribute("role", "status");
            emptyState.textContent = "Aucun message dans cette conversation.";
            messagesContainer.append(emptyState);
        }

        applyMessageSearch();
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async function loadConversationMessages(conversationId) {
        const requestId = ++activeRequestId;
        activeRequestController?.abort();
        activeRequestController = new AbortController();
        const { signal } = activeRequestController;

        activeMessages = [];
        messagesContainer.setAttribute("aria-busy", "true");
        showMessageState("Chargement des messages...");

        try {
            const response = await fetch(
                `/conversation/${encodeURIComponent(conversationId)}/`,
                {
                    headers: { Accept: "application/json" },
                    credentials: "same-origin",
                    signal
                }
            );

            if (!response.ok) {
                throw new Error(`Le serveur a répondu avec le statut ${response.status}.`);
            }

            if (!response.headers.get("content-type")?.includes("application/json")) {
                throw new Error("La réponse du serveur n'est pas au format JSON.");
            }

            const data = await response.json();
            if (!Array.isArray(data.messages)) {
                throw new Error("La réponse JSON ne contient pas de liste de messages.");
            }

            if (requestId !== activeRequestId || activeConversationId !== conversationId) {
                return;
            }

            messagesContainer.setAttribute("aria-busy", "false");
            renderMessages(data.messages);
        } catch (error) {
            if (error.name === "AbortError" || requestId !== activeRequestId) {
                return;
            }

            messagesContainer.setAttribute("aria-busy", "false");
            console.error("Erreur lors du chargement des messages :", error);
            showMessageState(
                "Impossible de charger les messages. Vérifiez votre connexion et réessayez."
            );
        }
    }

    function applyMessageSearch() {
        const input = document.getElementById("messageSearchInput");
        if (!input) {
            return;
        }

        const query = input.value.trim().toLocaleLowerCase();
        let visibleCount = 0;
        messagesContainer.querySelectorAll(".message-row").forEach((row) => {
            row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
            if (!row.hidden) {
                visibleCount += 1;
            }
        });

        let emptyState = messagesContainer.querySelector(".empty-state");
        if (!emptyState) {
            emptyState = document.createElement("p");
            emptyState.className = "empty-state";
            messagesContainer.append(emptyState);
        }
        emptyState.hidden = visibleCount > 0;
        if (query && visibleCount === 0) {
            emptyState.textContent = "Aucun message trouvé.";
        } else if (visibleCount === 0) {
            emptyState.textContent = "Aucun message pour le moment. Écrivez le premier !";
        }
    }

    function selectConversation(item) {
        activeConversationId = item.dataset.id;
        messageInput.disabled = false;
        messageForm.querySelector('button[type="submit"]').disabled = false;
        conversations.forEach((conversation) => {
            conversation.classList.toggle("active", conversation === item);
            conversation.setAttribute(
                "aria-current",
                conversation === item ? "true" : "false"
            );
        });

        chatName.textContent = item.dataset.name;
        chatStatus.textContent = item.dataset.status;
        chatStatus.classList.remove("is-online");
        chatAvatar.replaceChildren();
        chatAvatar.className = `conversation-avatar avatar-${item.dataset.color}`;
        if (item.dataset.avatar) {
            const image = document.createElement("img");
            image.className = "avatar-photo";
            image.src = item.dataset.avatar;
            image.alt = "";
            chatAvatar.append(image);
        } else {
            chatAvatar.textContent = item.dataset.initial;
        }

        item.dataset.unread = "0";
        item.querySelector(".unread-count")?.remove();
        notice.hidden = true;
        const messageSearch = document.getElementById("messageSearchInput");
        if (messageSearch) {
            messageSearch.value = "";
        }

        loadConversationMessages(activeConversationId);
        appShell.classList.add("mobile-chat-open");
        filterConversations();
    }

    function renderDirectoryUsers(users, list, mode, append = false) {
        if (!append) {
            list.replaceChildren();
        } else {
            list.querySelector(".directory-empty")?.remove();
        }

        users.forEach((user) => {
            const row = document.createElement("div");
            row.className = "directory-user";
            row.dataset.userId = String(user.id);

            const avatar = document.createElement("div");
            avatar.className = "conversation-avatar avatar-violet";
            if (user.avatar) {
                const image = document.createElement("img");
                image.className = "avatar-photo";
                image.src = user.avatar;
                image.alt = "";
                avatar.append(image);
            } else {
                avatar.textContent = user.name.charAt(0).toLocaleUpperCase();
            }

            const info = document.createElement("div");
            info.className = "directory-user-info";
            const name = document.createElement("strong");
            name.textContent = user.name;
            const details = document.createElement("span");
            details.textContent = user.bio || `@${user.username}`;
            info.append(name, details);
            row.append(avatar, info);

            if (mode === "group") {
                const checkbox = document.createElement("input");
                checkbox.type = "checkbox";
                checkbox.className = "group-member-checkbox";
                checkbox.value = String(user.id);
                checkbox.checked = selectedGroupMemberIds.has(String(user.id));
                checkbox.setAttribute("aria-label", `Ajouter ${user.name} au groupe`);
                row.append(checkbox);
            } else {
                const action = document.createElement("button");
                action.type = "button";
                action.className = "directory-user-action";
                action.dataset.userId = String(user.id);
                action.textContent = "Écrire";
                row.append(action);
            }

            list.append(row);
        });

        if (list.childElementCount === 0) {
            const empty = document.createElement("p");
            empty.className = "directory-empty";
            empty.textContent = "Aucun utilisateur trouvé.";
            list.append(empty);
        }
    }

    async function loadDirectoryUsers(query, offset, mode, append = false) {
        const isGroup = mode === "group";
        const currentRequestId = isGroup ? ++groupRequestId : ++directoryRequestId;
        const previousController = isGroup ? groupRequestController : directoryRequestController;
        previousController?.abort();
        const controller = new AbortController();
        if (isGroup) {
            groupRequestController = controller;
        } else {
            directoryRequestController = controller;
        }

        const list = document.getElementById(isGroup ? "groupUserList" : "directoryUserList");
        const status = document.getElementById(isGroup ? "groupStatus" : "directoryStatus");
        const loadMore = document.getElementById(
        isGroup ? "groupLoadMoreBtn" : "directoryLoadMoreBtn"
        );
        status.textContent = "Chargement des utilisateurs...";
        if (!append) {
            list.replaceChildren();
        }

        try {
            const params = new URLSearchParams({ q: query, offset: String(offset) });
            const response = await fetch(`/users/?${params}`, {
                headers: { Accept: "application/json" },
                credentials: "same-origin",
                signal: controller.signal
            });
            const data = await response.json();
            if (!response.ok || !Array.isArray(data.users)) {
                throw new Error(data.error || `Erreur HTTP ${response.status}.`);
            }
            if ((isGroup ? groupRequestId : directoryRequestId) !== currentRequestId) {
                return;
            }

            renderDirectoryUsers(data.users, list, mode, append);
                status.textContent = data.users.length
                ? `${data.users.length} utilisateur${data.users.length === 1 ? "" : "s"} affiché${data.users.length === 1 ? "" : "s"}.`
                : "Aucun utilisateur correspondant.";
            if (!isGroup) {
                directoryNextOffset = data.next_offset;
                loadMore.hidden = directoryNextOffset === null;
            } else {
                groupNextOffset = data.next_offset;
                loadMore.hidden = groupNextOffset === null;
            }
        } catch (error) {
            if (error.name === "AbortError" ||
                (isGroup ? groupRequestId : directoryRequestId) !== currentRequestId) {
                return;
            }
            console.error("Erreur lors du chargement de l'annuaire :", error);
            status.textContent = error.message || "Impossible de charger l'annuaire.";
        }
    }

    function upsertConversation(conversation) {
        const id = String(conversation.id);
        let item = conversations.get(id);
        if (!item) {
            item = document.createElement("button");
            item.type = "button";
            item.className = "conversation-item";

            const avatar = document.createElement("div");
            avatar.className = "conversation-avatar avatar-violet";
            const content = document.createElement("div");
            content.className = "conversation-content";
            const top = document.createElement("div");
            top.className = "conversation-top";
            const name = document.createElement("strong");
            top.append(name);
            const bottom = document.createElement("div");
            bottom.className = "conversation-bottom";
            const preview = document.createElement("span");
            preview.className = "conversation-preview";
            preview.textContent = "Aucun message pour le moment";
            bottom.append(preview);
            content.append(top, bottom);
            item.append(avatar, content);
            conversationList.prepend(item);
            conversations.set(id, item);
        }

        item.dataset.id = id;
        item.dataset.type = conversation.type;
        item.dataset.name = conversation.name;
        item.dataset.initial = conversation.name.charAt(0).toLocaleUpperCase();
        item.dataset.avatar = conversation.avatar || "";
        item.dataset.color = "violet";
        item.dataset.status = conversation.status;
        item.dataset.unread = "0";
        item.querySelector(".conversation-content strong").textContent = conversation.name;
        const avatar = item.querySelector(".conversation-avatar");
        avatar.replaceChildren();
        if (conversation.avatar) {
            const image = document.createElement("img");
            image.className = "avatar-photo";
            image.src = conversation.avatar;
            image.alt = "";
            avatar.append(image);
        } else {
            avatar.textContent = item.dataset.initial;
        }
        filterConversations();
        return item;
    }

    async function createPrivateConversation(userId) {
        const csrfToken = messageForm.querySelector(
            '[name="csrfmiddlewaretoken"]'
        )?.value;
        if (!csrfToken) {
            showNotice("Le jeton de sécurité est absent. Rechargez la page.");
            return;
        }

        try {
            const response = await fetch("/conversation/private/", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify({ user_id: userId })
            });
            const data = await response.json();
            if (!response.ok || !data.success || !data.conversation) {
                throw new Error(data.error || `Erreur HTTP ${response.status}.`);
            }

            const item = upsertConversation(data.conversation);
            document.getElementById("userDirectoryDialog").close();
            selectConversation(item);
        } catch (error) {
            console.error("Erreur lors de la création de la conversation :", error);
            document.getElementById("directoryStatus").textContent =
                error.message || "Impossible de démarrer la conversation.";
        }
    }

    conversationList.addEventListener("click", (event) => {
        const item = event.target.closest(".conversation-item");
        if (item && conversationList.contains(item)) {
            selectConversation(item);
        }
    });

    searchInput.addEventListener("input", filterConversations);
    let directorySearchTimeout;
    let groupSearchTimeout;

    document.getElementById("directoryBtn").addEventListener("click", () => {
        const dialog = document.getElementById("userDirectoryDialog");
        document.getElementById("directorySearchInput").value = "";
        document.getElementById("directoryLoadMoreBtn").hidden = true;
        dialog.showModal();
        loadDirectoryUsers("", 0, "private");
    });

    document.getElementById("closeDirectoryBtn").addEventListener("click", () => {
        directoryRequestController?.abort();
        document.getElementById("userDirectoryDialog").close();
    });

    document.getElementById("directorySearchInput").addEventListener("input", (event) => {
        window.clearTimeout(directorySearchTimeout);
        directorySearchTimeout = window.setTimeout(() => {
            document.getElementById("directoryLoadMoreBtn").hidden = true;
            loadDirectoryUsers(event.target.value.trim(), 0, "private");
        }, 200);
    });

    document.getElementById("directoryLoadMoreBtn").addEventListener("click", () => {
        if (directoryNextOffset !== null) {
            loadDirectoryUsers(
                document.getElementById("directorySearchInput").value.trim(),
                directoryNextOffset,
                "private",
                true
            );
        }
    });

    document.getElementById("directoryUserList").addEventListener("click", (event) => {
        const action = event.target.closest(".directory-user-action");
        if (action) {
            createPrivateConversation(action.dataset.userId);
        }
    });

    document.getElementById("newGroupBtn").addEventListener("click", () => {
        selectedGroupMemberIds.clear();
        document.getElementById("groupNameInput").value = "";
        document.getElementById("groupSearchInput").value = "";
        document.getElementById("groupLoadMoreBtn").hidden = true;
        document.getElementById("groupDialog").showModal();
        loadDirectoryUsers("", 0, "group");
    });

    document.getElementById("closeGroupBtn").addEventListener("click", () => {
        groupRequestController?.abort();
        document.getElementById("groupDialog").close();
    });

    document.getElementById("cancelGroupBtn").addEventListener("click", () => {
        groupRequestController?.abort();
        document.getElementById("groupDialog").close();
    });

    document.getElementById("groupSearchInput").addEventListener("input", (event) => {
        window.clearTimeout(groupSearchTimeout);
        groupSearchTimeout = window.setTimeout(() => {
            document.getElementById("groupLoadMoreBtn").hidden = true;
            loadDirectoryUsers(event.target.value.trim(), 0, "group");
        }, 200);
    });

    document.getElementById("groupLoadMoreBtn").addEventListener("click", () => {
        if (groupNextOffset !== null) {
            loadDirectoryUsers(
                document.getElementById("groupSearchInput").value.trim(),
                groupNextOffset,
                "group",
                true
            );
        }
    });

    document.getElementById("groupUserList").addEventListener("change", (event) => {
        const checkbox = event.target.closest(".group-member-checkbox");
        if (!checkbox) {
            return;
        }
        if (checkbox.checked) {
            selectedGroupMemberIds.add(checkbox.value);
        } else {
            selectedGroupMemberIds.delete(checkbox.value);
        }
    });

    document.getElementById("groupForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        if (isCreatingConversation) {
            return;
        }
        const name = document.getElementById("groupNameInput").value.trim();
        if (!name || selectedGroupMemberIds.size === 0) {
            document.getElementById("groupStatus").textContent =
                "Saisissez un nom et sélectionnez au moins un membre.";
            return;
        }

        const csrfToken = messageForm.querySelector(
            '[name="csrfmiddlewaretoken"]'
        )?.value;
        if (!csrfToken) {
            document.getElementById("groupStatus").textContent =
                "Le jeton de sécurité est absent. Rechargez la page.";
            return;
        }

        const submitButton = document.getElementById("createGroupBtn");
        isCreatingConversation = true;
        submitButton.disabled = true;
        document.getElementById("groupStatus").textContent = "Création du groupe...";
        try {
            const response = await fetch("/conversation/group/create/", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify({
                    name,
                    member_ids: Array.from(selectedGroupMemberIds)
                })
            });
            const data = await response.json();
            if (!response.ok || !data.success || !data.conversation) {
                throw new Error(data.error || `Erreur HTTP ${response.status}.`);
            }

            const item = upsertConversation(data.conversation);
            selectedGroupMemberIds.clear();
            document.getElementById("groupDialog").close();
            selectConversation(item);
        } catch (error) {
            console.error("Erreur lors de la création du groupe :", error);
            document.getElementById("groupStatus").textContent =
                error.message || "Impossible de créer le groupe.";
        } finally {
            isCreatingConversation = false;
            submitButton.disabled = false;
        }
    });

    document.querySelectorAll(".filter-btn").forEach((button) => {
        button.addEventListener("click", () => {
            activeFilter = button.dataset.filter;
            document.querySelectorAll(".filter-btn").forEach((filterButton) => {
                const isActive = filterButton === button;
                filterButton.classList.toggle("active", isActive);
                filterButton.setAttribute("aria-pressed", String(isActive));
            });
            filterConversations();
        });
    });

    document.getElementById("mobileBackBtn")?.addEventListener("click", () => {
        appShell.classList.remove("mobile-chat-open");
        searchInput.focus({ preventScroll: true });
    });

    document.getElementById("searchMessagesBtn")?.addEventListener("click", () => {
        let search = document.getElementById("messageSearchInput");
        if (search) {
            search.parentElement.remove();
            renderMessages(activeMessages);
            return;
        }

        search = document.createElement("input");
        search.type = "search";
        search.id = "messageSearchInput";
        search.className = "message-search-input";
        search.placeholder = "Rechercher dans les messages...";
        search.setAttribute("aria-label", "Rechercher dans les messages");
        const wrapper = document.createElement("div");
        wrapper.className = "message-search";
        wrapper.append(search);
        document.querySelector(".header-actions").before(wrapper);
        search.addEventListener("input", applyMessageSearch);
        search.focus();
    });

    document.getElementById("chatInfoBtn")?.addEventListener("click", () => {
        showNotice(`${chatName.textContent} · ${chatStatus.textContent}`);
    });

    document.getElementById("chatMoreBtn")?.addEventListener("click", () => {
        showNotice("Aucune autre option n'est disponible pour cette conversation.");
    });

    document.getElementById("emojiBtn")?.addEventListener("click", () => {
        const start = messageInput.selectionStart;
        const end = messageInput.selectionEnd;
        messageInput.setRangeText("😊", start, end, "end");
        messageInput.dispatchEvent(new Event("input", { bubbles: true }));
        messageInput.focus();
    });

    document.getElementById("attachBtn")?.addEventListener("click", () => {
        fileInput.click();
    });

    fileInput.addEventListener("change", () => {
        attachedFile = fileInput.files?.[0] ?? null;
        attachmentName.textContent = attachedFile?.name ?? "";
        attachmentPreview.hidden = !attachedFile;
    });

    removeAttachmentBtn.addEventListener("click", () => {
        attachedFile = null;
        fileInput.value = "";
        attachmentName.textContent = "";
        attachmentPreview.hidden = true;
    });

    messageInput.addEventListener("input", () => {
        messageInput.style.height = "auto";
        messageInput.style.height = `${Math.min(messageInput.scrollHeight, 160)}px`;
    });

    messageInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            messageForm.requestSubmit();
        }
    });

    messageForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const text = messageInput.value.trim();
        if (isSendingMessage || !activeConversationId) {
            return;
        }

        if (!text) {
            if (attachedFile) {
                showNotice("L'envoi des pièces jointes n'est pas encore pris en charge.");
            }
            return;
        }

        if (attachedFile) {
            showNotice("Retirez la pièce jointe pour envoyer le message texte.");
            return;
        }

        const csrfToken = messageForm.querySelector(
            '[name="csrfmiddlewaretoken"]'
        )?.value;
        if (!csrfToken) {
            showNotice("Le jeton de sécurité est absent. Rechargez la page et réessayez.");
            return;
        }

        const conversationId = activeConversationId;
        const sendButton = messageForm.querySelector('button[type="submit"]');
        isSendingMessage = true;
        if (sendButton) {
            sendButton.disabled = true;
        }

        fetch(`/conversation/${encodeURIComponent(conversationId)}/send/`, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                Accept: "application/json",
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            },
            body: JSON.stringify({ content: text })
        })
            .then(async (response) => {
                let data;
                try {
                    data = await response.json();
                } catch {
                    throw new Error(
                        `Le serveur a répondu avec le statut ${response.status}.`
                    );
                }

                if (!response.ok || !data.success || !data.message) {
                    throw new Error(
                        data.error || data.message || `Erreur HTTP ${response.status}.`
                    );
                }

                if (activeConversationId === conversationId) {
                    activeMessages = [...activeMessages, data.message];
                    renderMessages(activeMessages);
                    const conversationItem = conversations.get(conversationId);
                    const preview = conversationItem?.querySelector(".conversation-preview");
                    const timestamp = conversationItem?.querySelector(".conversation-time");
                    if (preview) {
                        preview.textContent = data.message.content;
                    }
                    if (timestamp) {
                        timestamp.textContent = data.message.created_at;
                    }

                    if (messageInput.value.trim() === text) {
                        messageInput.value = "";
                        messageInput.style.height = "auto";
                    }
                    notice.hidden = true;
                }
            })
            .catch((error) => {
                console.error("Erreur lors de l'envoi du message :", error);
                showNotice(error.message || "Impossible d'envoyer le message.");
            })
            .finally(() => {
                isSendingMessage = false;
                if (sendButton) {
                    sendButton.disabled = false;
                }
            });
    });

    document.addEventListener("keydown", (event) => {
        const target = event.target;
        const isTyping = target instanceof HTMLElement &&
            (target.isContentEditable || ["INPUT", "TEXTAREA"].includes(target.tagName));
        if (event.key === "/" && !isTyping) {
            event.preventDefault();
            searchInput.focus();
        } else if (event.key === "Escape" && appShell.classList.contains("mobile-chat-open")) {
            appShell.classList.remove("mobile-chat-open");
        }
    });

    const selectedConversation =
        initialConversationItems.find((item) => item.classList.contains("active")) ??
        initialConversationItems[0];
    if (selectedConversation) {
        selectConversation(selectedConversation);
    } else {
        messageInput.disabled = true;
        messageForm.querySelector('button[type="submit"]').disabled = true;
        showMessageState("Aucune conversation. Commencez un échange avec l'annuaire.");
    }
    filterConversations();
});
