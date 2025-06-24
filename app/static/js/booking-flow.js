// Booking Flow Manager for WhatsApp JobBot
class BookingFlow {
    constructor() {
        this.apiClient = new APIClient();
        this.bookingModal = document.getElementById('bookingModal');
        this.successModal = document.getElementById('successModal');
        this.bookingSummary = document.getElementById('bookingSummary');
        this.successMessage = document.getElementById('successMessage');
        
        this.currentBookingData = null;
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Modal close buttons
        document.querySelectorAll('.close-modal').forEach(button => {
            button.addEventListener('click', () => this.closeModals());
        });

        // Modal backdrop clicks
        this.bookingModal.addEventListener('click', (e) => {
            if (e.target === this.bookingModal) {
                this.closeModals();
            }
        });

        this.successModal.addEventListener('click', (e) => {
            if (e.target === this.successModal) {
                this.closeModals();
            }
        });

        // Booking confirmation button
        document.getElementById('confirmBooking').addEventListener('click', () => {
            this.confirmBooking();
        });

        // Edit booking button
        document.getElementById('editBooking').addEventListener('click', () => {
            this.editBooking();
        });

        // New booking button
        document.getElementById('newBooking').addEventListener('click', () => {
            this.startNewBooking();
        });

        // Escape key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModals();
            }
        });
    }

    showBookingSummary(bookingData) {
        this.currentBookingData = bookingData;
        
        // Format the booking summary
        const summary = this.formatBookingSummary(bookingData);
        this.bookingSummary.innerHTML = summary;
        
        // Show the modal
        this.bookingModal.style.display = 'flex';
        
        // Focus on the modal for accessibility
        setTimeout(() => {
            document.getElementById('confirmBooking').focus();
        }, 100);
    }

    formatBookingSummary(bookingData) {
        const fields = [
            { key: 'job_type', label: 'Job Type', icon: '🎯' },
            { key: 'date', label: 'Date', icon: '📅' },
            { key: 'duration', label: 'Duration', icon: '⏱️' },
            { key: 'location', label: 'Location', icon: '📍' },
            { key: 'budget', label: 'Budget', icon: '💰' },
            { key: 'contact_name', label: 'Contact Name', icon: '👤' },
            { key: 'phone', label: 'Phone', icon: '📞' },
            { key: 'email', label: 'Email', icon: '📧' }
        ];

        let summaryHtml = '<div class="booking-summary-content">';
        
        fields.forEach(field => {
            const value = bookingData[field.key] || 'Not specified';
            summaryHtml += `
                <div class="booking-field">
                    <div class="field-icon">${field.icon}</div>
                    <div class="field-content">
                        <div class="field-label">${field.label}</div>
                        <div class="field-value">${this.escapeHtml(value)}</div>
                    </div>
                </div>
            `;
        });

        if (bookingData.details) {
            summaryHtml += `
                <div class="booking-field">
                    <div class="field-icon">📝</div>
                    <div class="field-content">
                        <div class="field-label">Additional Notes</div>
                        <div class="field-value">${this.escapeHtml(bookingData.details)}</div>
                    </div>
                </div>
            `;
        }

        summaryHtml += '</div>';
        return summaryHtml;
    }

    async confirmBooking() {
        if (!this.currentBookingData) {
            console.error('No booking data available');
            return;
        }

        // Show loading state
        const confirmButton = document.getElementById('confirmBooking');
        const originalText = confirmButton.textContent;
        confirmButton.textContent = 'Processing...';
        confirmButton.disabled = true;

        try {
            // Send booking confirmation to API
            const response = await this.apiClient.confirmBooking(this.currentBookingData);
            
            // Hide booking modal
            this.bookingModal.style.display = 'none';
            
            // Show success modal
            this.showSuccessMessage(response);
            
        } catch (error) {
            console.error('Booking confirmation failed:', error);
            
            // Reset button state
            confirmButton.textContent = originalText;
            confirmButton.disabled = false;
            
            // Show error message
            this.showErrorMessage('Failed to confirm booking. Please try again.');
        }
    }

    showSuccessMessage(confirmation) {
        let successHtml = '';
        
        if (confirmation.status === 'CONFIRMED') {
            successHtml = `
                <div class="success-content">
                    <div class="success-icon">✅</div>
                    <div class="success-title">Booking Confirmed!</div>
                    <div class="success-message">${this.formatMessage(confirmation.confirmation_message)}</div>
                    ${confirmation.job_dossier ? `
                        <div class="job-dossier">
                            <h4>Job Dossier</h4>
                            <pre>${this.escapeHtml(confirmation.job_dossier)}</pre>
                        </div>
                    ` : ''}
                </div>
            `;
        } else {
            successHtml = `
                <div class="success-content">
                    <div class="success-icon">⚠️</div>
                    <div class="success-title">Booking Received</div>
                    <div class="success-message">${this.escapeHtml(confirmation.confirmation_message)}</div>
                </div>
            `;
        }
        
        this.successMessage.innerHTML = successHtml;
        this.successModal.style.display = 'flex';
        
        // Focus on new booking button
        setTimeout(() => {
            document.getElementById('newBooking').focus();
        }, 100);
    }

    showErrorMessage(message) {
        // Create a temporary error message in the chat
        if (window.chatUI) {
            window.chatUI.displayErrorMessage(message);
        }
    }

    editBooking() {
        // Close the modal and allow user to continue chatting
        this.closeModals();
        
        // Send a message to continue editing
        if (window.chatUI) {
            window.chatUI.messageInput.value = 'I want to edit my booking details';
            window.chatUI.sendMessage();
        }
    }

    startNewBooking() {
        // Close modals
        this.closeModals();
        
        // Reset chat and start fresh
        if (window.chatUI) {
            window.chatUI.resetChat();
        }
        
        // Reset booking data
        this.currentBookingData = null;
    }

    closeModals() {
        this.bookingModal.style.display = 'none';
        this.successModal.style.display = 'none';
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
}

// Initialize booking flow when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.bookingFlow = new BookingFlow();
}); 