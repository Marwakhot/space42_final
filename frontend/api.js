/**
 * API Client for Space42 HR Agent Backend
 * Handles all API communication with authentication
 */

const API_BASE_URL = 'http://localhost:8000'; // Change this to your backend URL

class APIClient {
    constructor() {
        this.baseURL = API_BASE_URL;
        this.token = localStorage.getItem('access_token');
        this.user = JSON.parse(localStorage.getItem('user') || 'null');
    }

    // Helper method to get auth headers
    getHeaders(includeAuth = true) {
        const headers = {
            'Content-Type': 'application/json',
        };
        if (includeAuth && this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        return headers;
    }

    // Helper method for making requests
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: {
                ...this.getHeaders(options.requireAuth !== false),
                ...options.headers,
            },
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // ============ Authentication ============

    async signup(email, password, firstName, lastName, location = null, yearsOfExperience = null) {
        const data = await this.request('/auth/signup', {
            method: 'POST',
            requireAuth: false,
            body: JSON.stringify({
                email,
                password,
                first_name: firstName,
                last_name: lastName,
                location,
                years_of_experience: yearsOfExperience,
            }),
        });

        // Store token and user info
        this.token = data.access_token;
        this.user = {
            user_id: data.user_id,
            user_type: data.user_type,
            email: data.email,
        };
        localStorage.setItem('access_token', this.token);
        localStorage.setItem('user', JSON.stringify(this.user));
        localStorage.setItem('isLoggedIn', 'true');

        return data;
    }

    async login(email, password) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            requireAuth: false,
            body: JSON.stringify({ email, password }),
        });

        // Store token and user info
        this.token = data.access_token;
        this.user = {
            user_id: data.user_id,
            user_type: data.user_type,
            email: data.email,
        };
        localStorage.setItem('access_token', this.token);
        localStorage.setItem('user', JSON.stringify(this.user));
        localStorage.setItem('isLoggedIn', 'true');

        return data;
    }

    async logout() {
        try {
            await this.request('/auth/logout', { method: 'POST' });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.token = null;
            this.user = null;
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            localStorage.removeItem('isLoggedIn');
            localStorage.removeItem('userRole');
        }
    }

    async getCurrentUser() {
        if (!this.token) {
            return null;
        }
        try {
            const data = await this.request('/auth/me');
            return data;
        } catch (error) {
            // Token might be invalid, clear it
            this.logout();
            return null;
        }
    }

    // ============ Jobs ============

    async getJobs(department = null, workType = null, activeOnly = true) {
        const params = new URLSearchParams();
        if (department) params.append('department', department);
        if (workType) params.append('work_type', workType);
        params.append('active_only', activeOnly);

        return await this.request(`/jobs?${params.toString()}`, {
            requireAuth: false,
        });
    }

    async getJob(jobId) {
        return await this.request(`/jobs/${jobId}`, {
            requireAuth: false,
        });
    }

    // ============ CVs ============

    async uploadCV(file, isPrimary = false) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('is_primary', isPrimary);

        const url = `${this.baseURL}/cvs/upload`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`,
            },
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    async getMyCVs() {
        return await this.request('/cvs');
    }

    async getCV(cvId) {
        return await this.request(`/cvs/${cvId}`);
    }

    async getMatchedRoles(cvId) {
        return await this.request(`/cvs/${cvId}/matched-roles`);
    }

    // ============ AI Chat ============

    async chat(message, conversationId = null) {
        return await this.request('/ai/chat', {
            method: 'POST',
            body: JSON.stringify({
                message,
                conversation_id: conversationId
            })
        });
    }

    async onboardingChat(message, conversationId = null) {
        return await this.request('/ai/onboarding', {
            method: 'POST',
            body: JSON.stringify({
                message,
                conversation_id: conversationId
            })
        });
    }

    async triggerCVParsing(cvId) {
        return await this.request(`/cvs/${cvId}/parse`, {
            method: 'POST',
        });
    }

    // ============ Applications ============

    async createApplication(jobRoleId, cvId = null, coverLetter = null) {
        return await this.request('/applications', {
            method: 'POST',
            body: JSON.stringify({
                job_role_id: jobRoleId,
                cv_id: cvId,
                cover_letter: coverLetter,
            }),
        });
    }

    async getMyApplications() {
        return await this.request('/applications/my');
    }

    async getApplication(applicationId) {
        return await this.request(`/applications/${applicationId}`);
    }

    async withdrawApplication(applicationId) {
        return await this.request(`/applications/${applicationId}`, {
            method: 'DELETE',
        });
    }

    // ============ AI Chat (RAG) ============

    async sendCandidateMessage(message, conversationId = null) {
        return await this.request('/ai/chat', {
            method: 'POST',
            body: JSON.stringify({
                message,
                conversation_id: conversationId,
            }),
        });
    }

    async sendOnboardingMessage(message, conversationId = null) {
        return await this.request('/ai/onboarding', {
            method: 'POST',
            body: JSON.stringify({
                message,
                conversation_id: conversationId,
            }),
        });
    }

    async getChatHistory(conversationId) {
        return await this.request(`/ai/chat/${conversationId}/history`);
    }

    // ============ HR Endpoints ============

    async getCandidate(candidateId) {
        return await this.request(`/candidates/${candidateId}`, {
            requireAuth: true,
        });
    }

    async listCandidates(location = null, minExperience = null) {
        const params = new URLSearchParams();
        if (location) params.append('location', location);
        if (minExperience) params.append('min_experience', minExperience);
        
        return await this.request(`/candidates?${params.toString()}`, {
            requireAuth: true,
        });
    }

    async updateApplicationStatus(applicationId, status, notes = null) {
        return await this.request(`/applications/${applicationId}/status`, {
            method: 'PUT',
            requireAuth: true,
            body: JSON.stringify({
                status,
                notes
            }),
        });
    }

    async scheduleInterview(applicationId, scheduledAt, interviewType, interviewer, meetingLink = null) {
        return await this.request(`/applications/${applicationId}/schedule-interview`, {
            method: 'POST',
            requireAuth: true,
            body: JSON.stringify({
                scheduled_at: scheduledAt,
                interview_type: interviewType,
                interviewer: interviewer,
                meeting_link: meetingLink
            }),
        });
    }

    async getJobRankings(jobId) {
        return await this.request(`/applications/job/${jobId}/rankings`, {
            requireAuth: true,
        });
    }

    // ============ HR Feedback / Notes ============

    async createFeedback(applicationId, feedbackData) {
        return await this.request('/feedback', {
            method: 'POST',
            requireAuth: true,
            body: JSON.stringify({
                application_id: applicationId,
                ...feedbackData
            }),
        });
    }

    async getApplicationFeedback(applicationId) {
        return await this.request(`/feedback/application/${applicationId}`, {
            requireAuth: true,
        });
    }

    async updateFeedback(feedbackId, feedbackData) {
        return await this.request(`/feedback/${feedbackId}`, {
            method: 'PUT',
            requireAuth: true,
            body: JSON.stringify(feedbackData),
        });
    }

    async deleteFeedback(feedbackId) {
        return await this.request(`/feedback/${feedbackId}`, {
            method: 'DELETE',
            requireAuth: true,
        });
    }

    async getFeedbackSummary(applicationId) {
        return await this.request(`/feedback/application/${applicationId}/summary`, {
            requireAuth: true,
        });
    }
}

// Create global instance
const api = new APIClient();

// Initialize user from localStorage on load
if (api.token && api.user) {
    // Verify token is still valid
    api.getCurrentUser().catch(() => {
        // Token invalid, will be cleared by getCurrentUser
    });
}
