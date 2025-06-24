// Chat UI Manager for WhatsApp JobBot
class ChatUI {
    constructor() {
        this.apiClient = new APIClient();
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        
        this.currentConversationState = null;
        this.bookingData = {};
        
        this.initializeEventListeners();
        this.showWelcomeMessage();
    }

    initializeEventListeners() {
        // Send message on button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter key
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Enable/disable send button based on input
        this.messageInput.addEventListener('input', () => {
            this.sendButton.disabled = !this.messageInput.value.trim();
        });

        // Initial button state
        this.sendButton.disabled = true;
    }

    showWelcomeMessage() {
        const welcomeMessage = {
            message: "👋 Hi! I'm JobBot, your AI booking assistant. I can help you book photography, videography, audio, or other freelance services. What's your name?",
            message_type: "text",
            conversation_state: "collecting_contact",
            suggested_actions: []
        };

        this.currentConversationState = "collecting_contact";
        this.displayBotMessage(welcomeMessage);
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        // Display user message
        this.displayUserMessage(message);
        this.messageInput.value = '';
        this.sendButton.disabled = true;

        // Show typing indicator
        this.showTypingIndicator();

        try {
            // Send message to API
            const response = await this.apiClient.sendMessage(message, this.currentConversationState);
            
            // Hide typing indicator
            this.hideTypingIndicator();

            // Update conversation state
            this.currentConversationState = response.conversation_state;
            this.bookingData = response.booking_data || {};

            // Display bot response
            this.displayBotMessage(response);

            // Handle completion
            if (response.conversation_state === 'completed') {
                this.handleBookingCompletion();
            }

        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            this.displayErrorMessage('Sorry, I encountered an error. Please try again.');
        }
    }

    displayUserMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message-bubble user';
        messageElement.innerHTML = `
            <div class="message-content">${this.escapeHtml(message)}</div>
            <div class="message-time">${this.getCurrentTime()}</div>
        `;
        
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }

    displayBotMessage(response) {
        const messageElement = document.createElement('div');
        messageElement.className = `message-bubble bot ${response.message_type}`;
        
        let content = response.message;
        
        // Handle timeslot selection specially
        if (response.message_type === 'timeslot_selection' && response.available_slots) {
            content += this.createTimeslotSelection(response.available_slots);
        }
        // Add regular suggested actions for other message types
        else if (response.suggested_actions && response.suggested_actions.length > 0) {
            content += this.createSuggestedActions(response.suggested_actions);
        }
        
        messageElement.innerHTML = `
            <div class="message-content">${this.formatMessage(content)}</div>
            <div class="message-time">${this.getCurrentTime()}</div>
        `;
        
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }

    displayErrorMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message-bubble bot error';
        messageElement.innerHTML = `
            <div class="message-content">${this.escapeHtml(message)}</div>
            <div class="message-time">${this.getCurrentTime()}</div>
        `;
        
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }

    createTimeslotSelection(availableSlots) {
        if (!availableSlots || availableSlots.length === 0) {
            return '<div class="no-slots">No available slots</div>';
        }

        const slotsHtml = availableSlots.map(slot => 
            `<button class="timeslot-btn" onclick="chatUI.handleTimeslotSelection('${this.escapeHtml(slot.display)}')" data-slot='${JSON.stringify(slot)}'>
                <div class="slot-time">${this.escapeHtml(slot.display)}</div>
                <div class="slot-duration">${slot.start_time} - ${slot.end_time}</div>
            </button>`
        ).join('');
        
        return `<div class="timeslot-selection">
            <div class="timeslot-header">Available Time Slots:</div>
            <div class="timeslot-grid">${slotsHtml}</div>
        </div>`;
    }

    createSuggestedActions(actions) {
        const actionsHtml = actions.map(action => 
            `<button class="action-btn" onclick="chatUI.handleSuggestedAction('${this.escapeHtml(action)}')">${this.escapeHtml(action)}</button>`
        ).join('');
        
        return `<div class="suggested-actions">${actionsHtml}</div>`;
    }

    handleTimeslotSelection(slotDisplay) {
        // Send the selected timeslot
        this.messageInput.value = slotDisplay;
        this.sendMessage();
    }

    handleSuggestedAction(action) {
        this.messageInput.value = action;
        this.sendMessage();
    }

    showTypingIndicator() {
        this.typingIndicator.style.display = 'flex';
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    getCurrentTime() {
        return new Date().toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true 
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatMessage(text) {
        // Convert markdown-style formatting to HTML
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    handleBookingCompletion() {
        // Show booking summary modal
        if (window.bookingFlow) {
            window.bookingFlow.showBookingSummary(this.bookingData);
        }
        
        // Show success message with calendar details
        if (this.bookingData.calendar_event) {
            const calendarEvent = this.bookingData.calendar_event;
            const successMessage = {
                message: `🎉 Booking confirmed! Your ${this.bookingData.job_type.toLowerCase()} session has been scheduled and added to your calendar.`,
                message_type: "confirmation",
                conversation_state: "completed",
                suggested_actions: ["View Calendar", "Start New Booking"]
            };
            
            setTimeout(() => {
                this.displayBotMessage(successMessage);
            }, 1000);
        }
    }

    resetChat() {
        this.chatMessages.innerHTML = '';
        this.currentConversationState = null;
        this.bookingData = {};
        this.showWelcomeMessage();
    }
}

// Initialize chat UI when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatUI = new ChatUI();
}); 