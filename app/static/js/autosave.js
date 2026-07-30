/**
 * Auto-Save System for Fault-Tolerant Distributed Exam System
 * Automatically saves exam progress and handles failover recovery
 */

class AutoSaveSystem {
    constructor(options = {}) {
        this.sessionId = options.sessionId || null;
        this.examId = options.examId || null;
        this.saveInterval = options.saveInterval || 5000; // 5 seconds
        this.maxRetries = options.maxRetries || 3;
        this.retryDelay = options.retryDelay || 1000;
        
        // State tracking
        this.currentAnswers = {};
        this.currentQuestionIndex = 0;
        this.remainingTime = 1800; // 30 minutes default
        this.lastSaveTime = null;
        this.saveTimer = null;
        this.isSaving = false;
        this.saveQueue = [];
        
        // Failover detection
        this.failoverDetected = false;
        this.nodeDownRetries = 0;
        
        // Configuration
        this.endpoints = {
            saveProgress: '/api/fault_tolerance/save_progress',
            resumeExam: '/api/fault_tolerance/resume_exam',
            health: '/api/fault_tolerance/health'
        };
        
        // Callbacks
        this.callbacks = {
            onSaveSuccess: options.onSaveSuccess || (() => {}),
            onSaveError: options.onSaveError || (() => {}),
            onFailover: options.onFailover || (() => {}),
            onSessionRestored: options.onSessionRestored || (() => {}),
            onStatusUpdate: options.onStatusUpdate || (() => {})
        };
        
        this.init();
    }
    
    /**
     * Initialize the auto-save system
     */
    init() {
        console.log('Initializing Auto-Save System...');
        
        // Get session info from page
        this.extractSessionInfo();
        
        if (!this.sessionId) {
            console.warn('No session ID found, auto-save disabled');
            return;
        }
        
        // Start auto-save timer
        this.startAutoSave();
        
        // Setup failover detection
        this.setupFailoverDetection();
        
        // Load saved progress
        this.loadSavedProgress();
        
        console.log('Auto-Save System initialized');
    }
    
    /**
     * Extract session information from the page
     */
    extractSessionInfo() {
        // Try to get session ID from hidden input
        const sessionIdInput = document.getElementById('sessionId');
        if (sessionIdInput) {
            this.sessionId = sessionIdInput.value;
        }
        
        // Try to get exam ID from hidden input or data attribute
        const examIdInput = document.getElementById('examId');
        if (examIdInput) {
            this.examId = examIdInput.value;
        } else {
            const examContainer = document.querySelector('[data-exam-id]');
            if (examContainer) {
                this.examId = examContainer.dataset.examId;
            }
        }
        
        console.log(`Session ID: ${this.sessionId}, Exam ID: ${this.examId}`);
    }
    
    /**
     * Start the auto-save timer
     */
    startAutoSave() {
        if (this.saveTimer) {
            clearInterval(this.saveTimer);
        }
        
        this.saveTimer = setInterval(() => {
            this.saveProgress();
        }, this.saveInterval);
        
        console.log(`Auto-save started: every ${this.saveInterval}ms`);
    }
    
    /**
     * Stop the auto-save timer
     */
    stopAutoSave() {
        if (this.saveTimer) {
            clearInterval(this.saveTimer);
            this.saveTimer = null;
        }
        
        console.log('Auto-save stopped');
    }
    
    /**
     * Save current progress
     */
    async saveProgress() {
        if (this.isSaving || !this.sessionId) {
            return;
        }
        
        this.isSaving = true;
        
        try {
            // Collect current answers
            this.collectCurrentAnswers();
            
            // Get current question index
            this.getCurrentQuestionIndex();
            
            // Get remaining time
            this.getRemainingTime();
            
            // Prepare save data
            const saveData = {
                session_id: this.sessionId,
                current_question_index: this.currentQuestionIndex,
                answers: this.currentAnswers,
                remaining_time: this.remainingTime
            };
            
            // Send save request
            const response = await fetch(this.endpoints.saveProgress, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(saveData)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.lastSaveTime = new Date();
                this.nodeDownRetries = 0; // Reset failover counter
                
                console.log('Progress saved successfully');
                this.callbacks.onSaveSuccess(result);
                this.updateStatus('saved');
                
            } else {
                throw new Error(`Save failed: ${response.status}`);
            }
            
        } catch (error) {
            console.error('Failed to save progress:', error);
            this.nodeDownRetries++;
            
            // Check if this might be a node failure
            if (this.nodeDownRetries >= this.maxRetries) {
                this.handleFailover(error);
            } else {
                // Retry after delay
                setTimeout(() => this.saveProgress(), this.retryDelay);
            }
            
            this.callbacks.onSaveError(error);
            this.updateStatus('error');
            
        } finally {
            this.isSaving = false;
        }
    }
    
    /**
     * Collect current answers from the form
     */
    collectCurrentAnswers() {
        this.currentAnswers = {};
        
        // Get all radio button answers
        const radioInputs = document.querySelectorAll('input[type="radio"]:checked');
        radioInputs.forEach(input => {
            const questionId = this.extractQuestionId(input.name);
            if (questionId) {
                this.currentAnswers[questionId] = input.value;
            }
        });
        
        // Get all text input answers
        const textInputs = document.querySelectorAll('input[type="text"], textarea');
        textInputs.forEach(input => {
            const questionId = this.extractQuestionId(input.name);
            if (questionId && input.value) {
                this.currentAnswers[questionId] = input.value;
            }
        });
        
        console.log(`Collected ${Object.keys(this.currentAnswers).length} answers`);
    }
    
    /**
     * Extract question ID from input name
     */
    extractQuestionId(inputName) {
        // Handle patterns like "question_1", "q_1", etc.
        const match = inputName.match(/(?:question|q)[_\-](\d+)/);
        return match ? match[1] : inputName;
    }
    
    /**
     * Get current question index
     */
    getCurrentQuestionIndex() {
        // Try to get from current question indicator
        const currentQuestionElement = document.querySelector('.current-question, [data-current-question]');
        if (currentQuestionElement) {
            this.currentQuestionIndex = parseInt(currentQuestionElement.textContent || currentQuestionElement.dataset.currentQuestion) - 1;
        }
        
        // Fallback: check which question is visible
        const questions = document.querySelectorAll('.question-card, .question');
        questions.forEach((question, index) => {
            if (question.style.display !== 'none' && !question.classList.contains('d-none')) {
                this.currentQuestionIndex = index;
            }
        });
    }
    
    /**
     * Get remaining time from timer
     */
    getRemainingTime() {
        // Try to get from timer element
        const timerElement = document.getElementById('timer, .timer');
        if (timerElement) {
            const timerText = timerElement.textContent;
            const match = timerText.match(/(\d+):(\d+)/);
            if (match) {
                const minutes = parseInt(match[1]);
                const seconds = parseInt(match[2]);
                this.remainingTime = minutes * 60 + seconds;
            }
        }
    }
    
    /**
     * Load saved progress
     */
    async loadSavedProgress() {
        if (!this.sessionId) {
            return;
        }
        
        try {
            const response = await fetch(`${this.endpoints.resumeExam}/${this.sessionId}`);
            
            if (response.ok) {
                const result = await response.json();
                
                if (result.success) {
                    this.restoreSession(result.session);
                    console.log('Session restored successfully');
                    this.callbacks.onSessionRestored(result.session);
                }
            }
            
        } catch (error) {
            console.error('Failed to load saved progress:', error);
        }
    }
    
    /**
     * Restore session from saved data
     */
    restoreSession(sessionData) {
        // Restore answers
        if (sessionData.answers) {
            this.restoreAnswers(sessionData.answers);
        }
        
        // Restore current question
        if (sessionData.current_question_index !== undefined) {
            this.goToQuestion(sessionData.current_question_index);
        }
        
        // Restore timer
        if (sessionData.remaining_time) {
            this.restoreTimer(sessionData.remaining_time);
        }
        
        console.log('Session restored:', sessionData);
    }
    
    /**
     * Restore saved answers
     */
    restoreAnswers(answers) {
        Object.keys(answers).forEach(questionId => {
            const answer = answers[questionId];
            
            // Try to find and check radio button
            const radioButton = document.querySelector(`input[name="question_${questionId}"][value="${answer}"]`);
            if (radioButton) {
                radioButton.checked = true;
                this.updateAnswerUI(radioButton);
            }
            
            // Try to find and fill text input
            const textInput = document.querySelector(`input[name="question_${questionId}"], textarea[name="question_${questionId}"]`);
            if (textInput) {
                textInput.value = answer;
            }
        });
    }
    
    /**
     * Go to specific question
     */
    goToQuestion(questionIndex) {
        // Hide all questions
        const questions = document.querySelectorAll('.question-card, .question');
        questions.forEach(q => q.style.display = 'none');
        
        // Show target question
        if (questions[questionIndex]) {
            questions[questionIndex].style.display = 'block';
        }
        
        // Update question navigation
        this.updateQuestionNavigation(questionIndex);
    }
    
    /**
     * Restore timer
     */
    restoreTimer(remainingSeconds) {
        // This would need to be implemented based on your timer system
        const timerElement = document.getElementById('timer');
        if (timerElement && window.updateTimer) {
            // Update global timer variable if it exists
            if (typeof window.timeLeft !== 'undefined') {
                window.timeLeft = remainingSeconds;
            }
        }
    }
    
    /**
     * Setup failover detection
     */
    setupFailoverDetection() {
        // Monitor fetch failures
        const originalFetch = window.fetch;
        
        window.fetch = async (...args) => {
            try {
                const response = await originalFetch(...args);
                
                // Check for server errors
                if (!response.ok && response.status >= 500) {
                    this.handlePotentialFailover();
                }
                
                return response;
                
            } catch (error) {
                // Network errors might indicate node failure
                this.handlePotentialFailover();
                throw error;
            }
        };
    }
    
    /**
     * Handle potential failover
     */
    handlePotentialFailover(error = null) {
        if (this.failoverDetected) {
            return; // Already handling failover
        }
        
        console.warn('Potential node failure detected:', error);
        
        // Check if we can reach the health endpoint
        this.checkNodeHealth();
    }
    
    /**
     * Check node health
     */
    async checkNodeHealth() {
        try {
            const response = await fetch(this.endpoints.health, { timeout: 3000 });
            
            if (!response.ok) {
                this.handleFailover(new Error('Health check failed'));
            }
            
        } catch (error) {
            this.handleFailover(error);
        }
    }
    
    /**
     * Handle failover
     */
    handleFailover(error) {
        if (this.failoverDetected) {
            return;
        }
        
        this.failoverDetected = true;
        console.error('Node failure detected, initiating failover:', error);
        
        // Show failover message
        this.showFailoverMessage();
        
        // Try to redirect to resume exam
        this.redirectToResume();
        
        // Notify callback
        this.callbacks.onFailover(error);
    }
    
    /**
     * Show failover message to user
     */
    showFailoverMessage() {
        const message = document.createElement('div');
        message.className = 'alert alert-warning alert-dismissible fade show position-fixed';
        message.style.cssText = 'top: 20px; right: 20px; z-index: 1050; max-width: 400px;';
        message.innerHTML = `
            <strong>System Alert</strong><br>
            The current node is experiencing issues. Your exam progress is being saved and you will be redirected to a backup node.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(message);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (message.parentNode) {
                message.parentNode.removeChild(message);
            }
        }, 10000);
    }
    
    /**
     * Redirect to resume exam
     */
    redirectToResume() {
        if (this.sessionId) {
            console.log(`Redirecting to resume exam: ${this.endpoints.resumeExam}/${this.sessionId}`);
            window.location.href = `${this.endpoints.resumeExam}/${this.sessionId}`;
        } else {
            // Fallback to exam list
            console.log('No session ID, redirecting to exam list');
            window.location.href = '/exams';
        }
    }
    
    /**
     * Update answer UI when answer is restored
     */
    updateAnswerUI(input) {
        // Add visual feedback for restored answers
        const formGroup = input.closest('.form-check, .form-group');
        if (formGroup) {
            formGroup.classList.add('answer-restored');
            
            // Remove the class after a short time
            setTimeout(() => {
                formGroup.classList.remove('answer-restored');
            }, 2000);
        }
    }
    
    /**
     * Update question navigation
     */
    updateQuestionNavigation(questionIndex) {
        // Update navigation buttons
        const navButtons = document.querySelectorAll('.question-nav button, .pagination button');
        navButtons.forEach((button, index) => {
            if (index === questionIndex) {
                button.classList.add('active', 'current');
            } else {
                button.classList.remove('active', 'current');
            }
        });
    }
    
    /**
     * Update status display
     */
    updateStatus(status) {
        const statusElement = document.getElementById('autosaveStatus');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `autosave-status status-${status}`;
        }
    }
    
    /**
     * Get CSRF token
     */
    getCSRFToken() {
        const csrfToken = document.querySelector('input[name="csrf_token"], meta[name="csrf-token"]');
        return csrfToken ? csrfToken.value || csrfToken.getAttribute('content') : '';
    }
    
    /**
     * Manual save trigger
     */
    manualSave() {
        console.log('Manual save triggered');
        return this.saveProgress();
    }
    
    /**
     * Get system status
     */
    getStatus() {
        return {
            sessionId: this.sessionId,
            examId: this.examId,
            lastSaveTime: this.lastSaveTime,
            currentAnswers: this.currentAnswers,
            currentQuestionIndex: this.currentQuestionIndex,
            remainingTime: this.remainingTime,
            isSaving: this.isSaving,
            failoverDetected: this.failoverDetected,
            nodeDownRetries: this.nodeDownRetries
        };
    }
    
    /**
     * Destroy the auto-save system
     */
    destroy() {
        this.stopAutoSave();
        
        // Save one last time
        this.saveProgress();
        
        console.log('Auto-Save System destroyed');
    }
}

// Export for use in templates
window.AutoSaveSystem = AutoSaveSystem;
