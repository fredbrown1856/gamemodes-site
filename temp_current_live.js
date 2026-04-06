/**
 * Wendy NPC Conversation Demo — Frontend Logic
 * Pure vanilla JavaScript, no frameworks.
 */

(function () {
    'use strict';

    // ============================================================================
    // State
    // ============================================================================

    const state = {
        currentConversationId: null,
        messages: [],
        affinity: 0,
        stage: 'Stranger',
        isActive: true,
        isLoading: false,
        conversations: [],
        // Demo mode state
        demoMode: false,
        demoSessionToken: null,
        demoQueueId: null,
        demoExpiresAt: null,
        demoTimerInterval: null,
        demoQueueInterval: null,
        demoMessagesCount: 0
    };

    // ============================================================================
    // DOM References
    // ============================================================================

    const DOM = {
        sidebar: document.getElementById('sidebar'),
        sidebarOverlay: document.getElementById('sidebar-overlay'),
        btnMenu: document.getElementById('btn-menu'),
        btnNewChat: document.getElementById('btn-new-chat'),
        conversationList: document.getElementById('conversation-list'),
        stageLabel: document.getElementById('stage-label'),
        affinityDisplay: document.getElementById('affinity-display'),
        affinityBar: document.getElementById('affinity-bar'),
        affinityMarker: document.getElementById('affinity-marker'),
        affinityValue: document.getElementById('affinity-value'),
        messagesContainer: document.getElementById('messages-container'),
        messagesList: document.getElementById('messages-list'),
        typingIndicator: document.getElementById('typing-indicator'),
        inputArea: document.getElementById('input-area'),
        messageInput: document.getElementById('message-input'),
        btnSend: document.getElementById('btn-send'),
        inputDisabledMessage: document.getElementById('input-disabled-message'),
        modalOverlay: document.getElementById('modal-overlay'),
        btnModalCancel: document.getElementById('btn-modal-cancel'),
        btnModalConfirm: document.getElementById('btn-modal-confirm')
    };

    // ============================================================================
    // API Helpers
    // ============================================================================

    const API_BASE = '';

    /**
     * Make an API request.
     */
    async function apiRequest(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...(options.headers || {})
            }
        };

        const response = await fetch(url, mergedOptions);
        const data = await response.json();

        if (!response.ok) {
            const error = new Error(data.error || `HTTP ${response.status}`);
            error.status = response.status;
            error.data = data;
            throw error;
        }

        return data;
    }

    // ============================================================================
    // API Calls
    // ============================================================================

    /**
     * Send a chat message.
     */
    async function sendMessage(conversationId, message) {
        return apiRequest('/api/chat', {
            method: 'POST',
            body: JSON.stringify({
                conversation_id: conversationId,
                message: message
            })
        });
    }

    /**
     * Create a new conversation.
     */
    async function createConversation() {
        return apiRequest('/api/conversations/new', {
            method: 'POST'
        });
    }

    /**
     * Get a conversation with its messages.
     */
    async function getConversation(conversationId) {
        return apiRequest(`/api/conversations/${conversationId}`);
    }

    /**
     * List conversations.
     */
    async function listConversations(limit = 50, offset = 0) {
        return apiRequest(`/api/conversations?limit=${limit}&offset=${offset}`);
    }

    /**
     * Delete a conversation.
     */
    async function deleteConversation(conversationId) {
        return apiRequest(`/api/conversations/${conversationId}`, {
            method: 'DELETE'
        });
    }

    // ============================================================================
    // Utility Functions
    // ============================================================================

    /**
     * Format a timestamp for display.
     */
    function formatTimestamp(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const isToday = date.toDateString() === now.toDateString();
        const isThisYear = date.getFullYear() === now.getFullYear();

        const hours = date.getHours();
        const minutes = date.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        const displayHours = hours % 12 || 12;
        const displayMinutes = minutes.toString().padStart(2, '0');
        const timeStr = `${displayHours}:${displayMinutes} ${ampm}`;

        if (isToday) {
            return timeStr;
        }

        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const month = months[date.getMonth()];
        const day = date.getDate();

        if (isThisYear) {
            return `${month} ${day}, ${timeStr}`;
        }

        return `${month} ${day}, ${date.getFullYear()}, ${timeStr}`;
    }

    /**
     * Format a date for conversation list.
     */
    function formatConversationDate(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const isToday = date.toDateString() === now.toDateString();

        if (isToday) {
            const hours = date.getHours();
            const minutes = date.getMinutes();
            const ampm = hours >= 12 ? 'PM' : 'AM';
            const displayHours = hours % 12 || 12;
            const displayMinutes = minutes.toString().padStart(2, '0');
            return `${displayHours}:${displayMinutes} ${ampm}`;
        }

        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${months[date.getMonth()]} ${date.getDate()}`;
    }

    /**
     * Get affinity color based on value.
     */
    function getAffinityColor(value) {
        if (value <= -50) return '#dc2626';
        if (value <= -20) return '#ea580c';
        if (value <= -10) return '#d97706';
        if (value < 10) return '#6b7280';
        if (value < 30) return '#65a30d';
        if (value < 50) return '#059669';
        if (value < 70) return '#0891b2';
        return '#7c3aed';
    }

    /**
     * Escape HTML to prevent XSS.
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show an error toast.
     */
    function showError(message) {
        let toast = document.querySelector('.error-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.className = 'error-toast';
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.classList.add('visible');

        setTimeout(() => {
            toast.classList.remove('visible');
        }, 4000);
    }

    // ============================================================================
    // Affinity Display
    // ============================================================================

    /**
     * Update the affinity bar and marker position.
     * Affinity ranges from -100 to +100.
     * Bar position: 0% at -100, 50% at 0, 100% at +100.
     */
    function updateAffinityDisplay(affinity, stage, animate = true) {
        state.affinity = affinity;
        state.stage = stage;

        // Calculate position (0-100%)
        const position = ((affinity + 100) / 200) * 100;

        // Update bar (mask from right — shows the "unfilled" portion)
        DOM.affinityBar.style.width = `${100 - position}%`;

        // Update marker position
        DOM.affinityMarker.style.left = `${position}%`;

        // Update color of marker
        const color = getAffinityColor(affinity);
        DOM.affinityMarker.style.backgroundColor = color;

        // Update value text
        DOM.affinityValue.textContent = affinity;
        DOM.affinityValue.style.color = color;

        // Update stage label
        DOM.stageLabel.textContent = stage;
        DOM.stageLabel.style.color = color;

        // Update title tooltip
        DOM.affinityDisplay.title = `Affinity: ${affinity} (${stage})`;
    }

    // ============================================================================
    // Message Rendering
    // ============================================================================

    /**
     * Create a message element.
     */
    function createMessageElement(message) {
        const wrapper = document.createElement('div');
        wrapper.className = `message-wrapper ${message.role}`;
        wrapper.dataset.messageId = message.id;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = message.role === 'assistant' ? 'W' : 'U';

        const content = document.createElement('div');
        content.className = 'message-content';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = message.content;

        const timestamp = document.createElement('div');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = formatTimestamp(message.timestamp);

        content.appendChild(bubble);
        content.appendChild(timestamp);

        wrapper.appendChild(avatar);
        wrapper.appendChild(content);

        return wrapper;
    }

    /**
     * Render all messages.
     */
    function renderMessages() {
        DOM.messagesList.innerHTML = '';

        if (state.messages.length === 0) {
            const emptyState = document.createElement('div');
            emptyState.className = 'empty-state';
            emptyState.innerHTML = `
                <div class="empty-state-icon">💬</div>
                <div class="empty-state-text">Start a conversation with Wendy!</div>
            `;
            DOM.messagesList.appendChild(emptyState);
            return;
        }

        state.messages.forEach(message => {
            const element = createMessageElement(message);
            DOM.messagesList.appendChild(element);
        });

        scrollToBottom();
    }

    /**
     * Append a single message and scroll to it.
     */
    function appendMessage(message) {
        // Remove empty state if present
        const emptyState = DOM.messagesList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        const element = createMessageElement(message);
        DOM.messagesList.appendChild(element);
        scrollToBottom();
    }

    /**
     * Scroll messages to the bottom.
     */
    function scrollToBottom() {
        requestAnimationFrame(() => {
            DOM.messagesContainer.scrollTop = DOM.messagesContainer.scrollHeight;
        });
    }

    // ============================================================================
    // Input State
    // ============================================================================

    /**
     * Enable or disable the input area.
     */
    function setInputEnabled(enabled) {
        DOM.messageInput.disabled = !enabled;
        DOM.btnSend.disabled = !enabled;

        if (!enabled) {
            DOM.inputDisabledMessage.classList.add('visible');
        } else {
            DOM.inputDisabledMessage.classList.remove('visible');
        }
    }

    /**
     * Set loading state.
     */
    function setLoading(loading) {
        state.isLoading = loading;

        if (loading) {
            DOM.typingIndicator.classList.add('visible');
            setInputEnabled(false);
            scrollToBottom();
        } else {
            DOM.typingIndicator.classList.remove('visible');
            if (state.isActive) {
                setInputEnabled(true);
            }
        }
    }

    /**
     * Auto-resize the textarea.
     */
    function autoResizeInput() {
        DOM.messageInput.style.height = 'auto';
        DOM.messageInput.style.height = Math.min(DOM.messageInput.scrollHeight, 120) + 'px';
    }

    // ============================================================================
    // Sidebar / Conversation List
    // ============================================================================

    /**
     * Render the conversation list.
     */
    function renderConversationList() {
        DOM.conversationList.innerHTML = '';

        if (state.conversations.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'empty-state';
            empty.innerHTML = `
                <div class="empty-state-icon">📋</div>
                <div class="empty-state-text">No conversations yet</div>
            `;
            DOM.conversationList.appendChild(empty);
            return;
        }

        state.conversations.forEach(conv => {
            const item = document.createElement('div');
            item.className = `conversation-item${conv.id === state.currentConversationId ? ' active' : ''}`;
            item.dataset.conversationId = conv.id;

            const preview = conv.last_message
                ? (conv.last_message.length > 40 ? conv.last_message.substring(0, 40) + '…' : conv.last_message)
                : 'No messages yet';

            item.innerHTML = `
                <div class="conversation-item-avatar">W</div>
                <div class="conversation-item-info">
                    <div class="conversation-item-header">
                        <span class="conversation-item-stage" style="color: ${getAffinityColor(conv.affinity)}">${escapeHtml(conv.stage || 'Stranger')}</span>
                        <span class="conversation-item-date">${formatConversationDate(conv.updated_at || conv.created_at)}</span>
                    </div>
                    <div class="conversation-item-preview">${escapeHtml(preview)}</div>
                </div>
                <button class="conversation-item-delete" title="Delete conversation" data-delete-id="${conv.id}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            `;

            DOM.conversationList.appendChild(item);
        });
    }

    /**
     * Refresh the conversation list from the server.
     */
    async function refreshConversationList() {
        try {
            const data = await listConversations();
            state.conversations = data.conversations || [];
            renderConversationList();
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
    }

    /**
     * Toggle sidebar open/closed (mobile).
     */
    function toggleSidebar(open) {
        if (open) {
            DOM.sidebar.classList.add('open');
            DOM.sidebarOverlay.classList.add('visible');
        } else {
            DOM.sidebar.classList.remove('open');
            DOM.sidebarOverlay.classList.remove('visible');
        }
    }

    // ============================================================================
    // Modal
    // ============================================================================

    let pendingNewChatCallback = null;

    /**
     * Show the confirmation modal.
     */
    function showConfirmModal(callback) {
        pendingNewChatCallback = callback;
        DOM.modalOverlay.classList.add('visible');
    }

    /**
     * Hide the confirmation modal.
     */
    function hideConfirmModal() {
        DOM.modalOverlay.classList.remove('visible');
        pendingNewChatCallback = null;
    }

    // ============================================================================
    // Core Actions
    // ============================================================================

    /**
     * Load a conversation by ID.
     */
    async function loadConversation(conversationId) {
        try {
            const data = await getConversation(conversationId);

            state.currentConversationId = data.conversation.id;
            state.affinity = data.conversation.affinity;
            state.isActive = data.conversation.is_active;
            state.messages = data.messages || [];

            updateAffinityDisplay(data.conversation.affinity, data.conversation.stage, false);
            renderMessages();

            if (!state.isActive) {
                setInputEnabled(false);
            } else {
                setInputEnabled(true);
            }

            // Update conversation list active state
            renderConversationList();

            // Close sidebar on mobile
            toggleSidebar(false);
        } catch (error) {
            console.error('Failed to load conversation:', error);
            showError('Failed to load conversation.');
        }
    }

    /**
     * Start a new conversation.
     */
    async function startNewConversation() {
        try {
            const data = await createConversation();

            state.currentConversationId = data.conversation.id;
            state.affinity = data.conversation.affinity;
            state.isActive = data.conversation.is_active;
            state.messages = [];

            updateAffinityDisplay(data.conversation.affinity, data.conversation.stage, false);
            renderMessages();
            setInputEnabled(true);

            // Refresh conversation list
            await refreshConversationList();

            // Focus input
            DOM.messageInput.focus();

            // Close sidebar on mobile
            toggleSidebar(false);
        } catch (error) {
            console.error('Failed to create conversation:', error);
            showError('Failed to start a new conversation.');
        }
    }

    /**
     * Handle the "New Chat" button click.
     */
    function handleNewChatClick() {
        if (state.messages.length > 0) {
            showConfirmModal(async () => {
                await startNewConversation();
            });
        } else {
            startNewConversation();
        }
    }

    /**
     * Send a message.
     */
    async function handleSendMessage() {
        const message = DOM.messageInput.value.trim();

        if (!message || state.isLoading || !state.isActive) {
            return;
        }

        if (!state.currentConversationId) {
            showError('No active conversation.');
            return;
        }

        // Clear input
        DOM.messageInput.value = '';
        autoResizeInput();

        // Add user message to UI immediately
        const userMessage = {
            id: Date.now(),
            role: 'user',
            content: message,
            timestamp: new Date().toISOString()
        };
        state.messages.push(userMessage);
        appendMessage(userMessage);

        // Show typing indicator
        setLoading(true);

        try {
            let data;

            if (state.demoMode) {
                // Demo mode: use the demo chat endpoint
                data = await apiRequest('/api/demo/chat', {
                    method: 'POST',
                    body: JSON.stringify({
                        session_token: state.demoSessionToken,
                        message: message
                    })
                });

                // Track demo message count
                state.demoMessagesCount++;

                // Check if time has run out
                if (data.time_remaining !== undefined && data.time_remaining <= 0) {
                    state.isActive = false;
                    setInputEnabled(false);
                    showSessionExpired();
                    return;
                }
            } else {
                // Normal mode: use the standard chat endpoint
                data = await sendMessage(state.currentConversationId, message);
            }

            // Add Wendy's response
            state.messages.push(data.message);
            appendMessage(data.message);

            // Update affinity
            state.isActive = data.conversation_active;
            updateAffinityDisplay(data.affinity.current, data.affinity.stage, true);

            // Check if conversation ended
            if (!data.conversation_active) {
                setInputEnabled(false);
            }

            // Refresh conversation list (non-demo only)
            if (!state.demoMode) {
                refreshConversationList();
            }
        } catch (error) {
            console.error('Failed to send message:', error);
            showError(error.message || 'Failed to send message. Please try again.');

            // Remove the optimistic user message
            state.messages.pop();
            renderMessages();
        } finally {
            setLoading(false);
            DOM.messageInput.focus();
        }
    }

    /**
     * Delete a conversation.
     */
    async function handleDeleteConversation(conversationId) {
        try {
            await deleteConversation(conversationId);

            // If we deleted the current conversation, start a new one
            if (conversationId === state.currentConversationId) {
                await startNewConversation();
            }

            // Refresh conversation list
            await refreshConversationList();
        } catch (error) {
            console.error('Failed to delete conversation:', error);
            showError('Failed to delete conversation.');
        }
    }

    // ============================================================================
    // Event Listeners
    // ============================================================================

    function initEventListeners() {
        // Menu toggle (mobile)
        DOM.btnMenu.addEventListener('click', () => {
            const isOpen = DOM.sidebar.classList.contains('open');
            toggleSidebar(!isOpen);
        });

        // Sidebar overlay click to close
        DOM.sidebarOverlay.addEventListener('click', () => {
            toggleSidebar(false);
        });

        // New chat button
        DOM.btnNewChat.addEventListener('click', handleNewChatClick);

        // Send button
        DOM.btnSend.addEventListener('click', handleSendMessage);

        // Input: Enter to send, Shift+Enter for newline
        DOM.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });

        // Auto-resize textarea
        DOM.messageInput.addEventListener('input', autoResizeInput);

        // Conversation list clicks (delegation)
        DOM.conversationList.addEventListener('click', (e) => {
            const deleteBtn = e.target.closest('.conversation-item-delete');
            if (deleteBtn) {
                e.stopPropagation();
                const convId = parseInt(deleteBtn.dataset.deleteId, 10);
                if (confirm('Delete this conversation?')) {
                    handleDeleteConversation(convId);
                }
                return;
            }

            const item = e.target.closest('.conversation-item');
            if (item) {
                const convId = parseInt(item.dataset.conversationId, 10);
                if (convId !== state.currentConversationId) {
                    loadConversation(convId);
                }
            }
        });

        // Modal buttons
        DOM.btnModalCancel.addEventListener('click', hideConfirmModal);

        DOM.btnModalConfirm.addEventListener('click', () => {
            if (pendingNewChatCallback) {
                const callback = pendingNewChatCallback;
                hideConfirmModal();
                callback();
            }
        });

        // Close modal on overlay click
        DOM.modalOverlay.addEventListener('click', (e) => {
            if (e.target === DOM.modalOverlay) {
                hideConfirmModal();
            }
        });

        // Keyboard: Escape to close sidebar/modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (DOM.modalOverlay.classList.contains('visible')) {
                    hideConfirmModal();
                } else if (DOM.sidebar.classList.contains('open')) {
                    toggleSidebar(false);
                }
            }
        });
    }

    // ============================================================================
    // Demo Mode
    // ============================================================================

    /**
     * Check if the app is in demo mode via URL parameter.
     */
    function isDemoMode() {
        return new URLSearchParams(window.location.search).has('demo');
    }

    /**
     * Initialize demo mode — hide normal UI, show welcome screen.
     */
    async function initDemoMode() {
        state.demoMode = true;

        // Hide sidebar and normal chat elements
        DOM.sidebar.style.display = 'none';
        DOM.sidebarOverlay.style.display = 'none';

        // Show the demo welcome screen
        document.getElementById('demo-welcome').style.display = 'flex';

        // Fetch and display queue stats
        try {
            const stats = await apiRequest('/api/demo/stats');
            const queueInfo = document.getElementById('demo-queue-info');
            if (stats.current_queue_size > 0) {
                queueInfo.textContent = `~${stats.current_queue_size} in line`;
            } else {
                queueInfo.textContent = 'No wait';
            }
        } catch (e) {
            // Stats are non-critical; leave default text
        }

        // Bind the demo start form
        document.getElementById('demo-start-form').addEventListener('submit', (e) => {
            e.preventDefault();
            startDemoSession();
        });
    }

    /**
     * Start a demo session — called when user clicks "Start Conversation".
     */
    async function startDemoSession() {
        const honeypot = document.getElementById('honeypot').value;

        try {
            const resp = await apiRequest('/api/demo/start', {
                method: 'POST',
                body: JSON.stringify({ honeypot: honeypot })
            });

            // Determine status: use explicit field, or infer from response shape
            const status = resp.status ||
                (resp.session_token ? 'active' : null) ||
                (resp.queue_id ? 'queued' : null);

            if (status === 'active') {
                // Got a slot — transition directly to chat
                state.demoSessionToken = resp.session_token;
                state.demoExpiresAt = resp.expires_at;
                transitionToChat(resp.conversation_id);
            } else if (status === 'queued') {
                // All slots full — show queue screen
                state.demoQueueId = resp.queue_id;
                document.getElementById('queue-position').textContent = `#${resp.position}`;
                document.getElementById('queue-eta').textContent = resp.estimated_wait;
                document.getElementById('demo-welcome').style.display = 'none';
                document.getElementById('demo-queue').style.display = 'flex';
                startQueuePolling();
            }
        } catch (error) {
            console.error('Demo start failed:', error);
            showError(error.message || 'Failed to start demo session.');
        }
    }

    /**
     * Poll the queue status endpoint until promoted to active.
     */
    function startQueuePolling() {
        state.demoQueueInterval = setInterval(async () => {
            try {
                const resp = await apiRequest(`/api/demo/status?queue_id=${state.demoQueueId}`);

                if (resp.status === 'active') {
                    clearInterval(state.demoQueueInterval);
                    state.demoQueueInterval = null;
                    state.demoSessionToken = resp.session_token;
                    state.demoExpiresAt = resp.expires_at;
                    transitionToChat(resp.conversation_id);
                } else if (resp.status === 'queued') {
                    document.getElementById('queue-position').textContent = `#${resp.position}`;
                    document.getElementById('queue-eta').textContent = resp.estimated_wait;
                } else if (resp.status === 'expired') {
                    clearInterval(state.demoQueueInterval);
                    state.demoQueueInterval = null;
                    showSessionExpired();
                }
            } catch (error) {
                console.error('Queue poll error:', error);
            }
        }, 10000);
    }

    /**
     * Start the session countdown timer.
     */
    function startSessionTimer() {
        const updateTimer = () => {
            const now = new Date();
            const expires = new Date(state.demoExpiresAt);
            const remaining = Math.max(0, Math.floor((expires - now) / 1000));

            const mins = Math.floor(remaining / 60);
            const secs = remaining % 60;
            document.getElementById('demo-timer-value').textContent =
                `${mins}:${secs.toString().padStart(2, '0')}`;

            const timerEl = document.getElementById('demo-timer');
            if (remaining <= 30) {
                timerEl.classList.add('timer-warning');
            } else {
                timerEl.classList.remove('timer-warning');
            }

            if (remaining <= 0) {
                clearInterval(state.demoTimerInterval);
                state.demoTimerInterval = null;
                state.isActive = false;
                showSessionExpired();
            }
        };

        updateTimer();
        state.demoTimerInterval = setInterval(updateTimer, 1000);
    }

    /**
     * Transition from a demo screen into the live chat UI.
     */
    function transitionToChat(conversationId) {
        // Hide all demo overlay screens
        document.querySelectorAll('.demo-screen').forEach(el => el.style.display = 'none');

        // Ensure sidebar stays hidden in demo mode
        DOM.sidebar.style.display = 'none';
        DOM.sidebarOverlay.style.display = 'none';

        // Show the timer in the header
        document.getElementById('demo-timer').style.display = 'flex';

        // Load the conversation using the existing function
        loadConversation(conversationId);

        // Start the countdown
        startSessionTimer();
    }

    /**
     * Show the session expired screen with conversation stats.
     */
    function showSessionExpired() {
        // Stop the timer
        if (state.demoTimerInterval) {
            clearInterval(state.demoTimerInterval);
            state.demoTimerInterval = null;
        }

        // Disable input
        setInputEnabled(false);

        // Populate stats
        document.getElementById('demo-messages-sent').textContent = state.demoMessagesCount;
        document.getElementById('demo-final-affinity').textContent = state.stage || 'Stranger';

        // Hide all demo overlay screens and the chat main area
        document.querySelectorAll('.demo-screen').forEach(el => el.style.display = 'none');
        document.querySelector('.chat-main').style.display = 'none';

        // Show the expired screen
        document.getElementById('demo-expired').style.display = 'flex';
    }

    // ============================================================================
    // Initialization
    // ============================================================================

    async function init() {
        initEventListeners();

        if (isDemoMode()) {
            // Demo mode: skip normal initialization
            await initDemoMode();
            return;
        }

        // Load conversation list
        await refreshConversationList();

        // Create a new conversation automatically
        await startNewConversation();
    }

    // Start the app when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

