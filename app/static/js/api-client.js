// API Client for WhatsApp JobBot
class APIClient {
    constructor() {
        this.baseURL = '/api/v1';
        this.sessionId = this.generateSessionId();
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const requestOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers,
            },
        };

        try {
            const response = await fetch(url, requestOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    async sendMessage(content, conversationState = null) {
        const payload = {
            content: content,
            session_id: this.sessionId,
            conversation_state: conversationState,
            timestamp: new Date().toISOString()
        };

        return this.makeRequest('/chat/message', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    async resetConversation() {
        return this.makeRequest('/chat/reset', {
            method: 'POST',
            body: JSON.stringify({ session_id: this.sessionId })
        });
    }

    async getSessionData() {
        return this.makeRequest(`/chat/session/${this.sessionId}`, {
            method: 'GET'
        });
    }

    async confirmBooking(bookingData) {
        const payload = {
            session_id: this.sessionId,
            booking_data: bookingData
        };

        return this.makeRequest('/booking/confirm', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    async getBookingSummary(bookingId) {
        return this.makeRequest(`/booking/summary/${bookingId}`, {
            method: 'GET'
        });
    }

    async getBookingAnalytics() {
        return this.makeRequest('/booking/analytics', {
            method: 'GET'
        });
    }

    async formatBookingSummary(bookingData) {
        return this.makeRequest('/booking/format-summary', {
            method: 'POST',
            body: JSON.stringify(bookingData)
        });
    }

    // Health check
    async healthCheck() {
        try {
            const response = await fetch('/health');
            return await response.json();
        } catch (error) {
            console.error('Health check failed:', error);
            return { status: 'unhealthy', error: error.message };
        }
    }
}

// Export for use in other modules
window.APIClient = APIClient; 