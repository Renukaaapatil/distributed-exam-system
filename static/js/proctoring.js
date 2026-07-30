/**
 * AI Proctoring Client for Distributed Exam System
 * Handles webcam capture, face detection monitoring, and tab switching detection
 */

class AIProctor {
    constructor(options = {}) {
        this.sessionId = null;
        this.examId = options.examId || null;
        this.responseId = options.responseId || null;
        
        // Configuration
        this.config = {
            frameInterval: options.frameInterval || 1000, // ms
            maxRetries: options.maxRetries || 3,
            apiBaseUrl: options.apiBaseUrl || '/api/proctoring',
            enableWebcam: options.enableWebcam !== false,
            enableTabDetection: options.enableTabDetection !== false
        };
        
        // State
        this.isActive = false;
        this.currentScore = 100;
        this.statusColor = 'green';
        this.violations = [];
        this.framesProcessed = 0;
        
        // Webcam
        this.video = null;
        this.canvas = null;
        this.stream = null;
        this.captureInterval = null;
        
        // Tab detection
        this.tabSwitchCount = 0;
        this.lastFocusTime = Date.now();
        this.isWindowFocused = true;
        
        // Callbacks
        this.onStatusUpdate = options.onStatusUpdate || (() => {});
        this.onViolation = options.onViolation || (() => {});
        this.onError = options.onError || (() => {});
        this.onSessionStart = options.onSessionStart || (() => {});
        this.onSessionEnd = options.onSessionEnd || (() => {});
        
        this.logger = this._createLogger();
    }
    
    async startSession() {
        try {
            this.logger.info('Starting AI proctoring session...');
            
            // Start proctoring session
            const response = await this._apiCall('/session/start', 'POST', {
                exam_id: this.examId,
                response_id: this.responseId
            });
            
            if (response.error) {
                throw new Error(response.error);
            }
            
            this.sessionId = response.session_id;
            this.isActive = true;
            this.currentScore = response.trust_score;
            this.statusColor = this._getStatusColor(this.currentScore);
            
            // Initialize webcam if enabled
            if (this.config.enableWebcam) {
                await this._initializeWebcam();
            }
            
            // Setup tab detection if enabled
            if (this.config.enableTabDetection) {
                this._setupTabDetection();
            }
            
            // Start frame capture
            if (this.config.enableWebcam) {
                this._startFrameCapture();
            }
            
            this.onSessionStart(response);
            this.logger.info('AI proctoring session started', {
                sessionId: this.sessionId,
                initialScore: this.currentScore
            });
            
            return response;
            
        } catch (error) {
            this.logger.error('Failed to start proctoring session', error);
            this.onError(error);
            throw error;
        }
    }
    
    async stopSession() {
        try {
            this.logger.info('Stopping AI proctoring session...');
            
            // Stop frame capture
            this._stopFrameCapture();
            
            // Stop webcam
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
                this.stream = null;
            }
            
            // Stop API session
            if (this.sessionId) {
                const response = await this._apiCall('/session/stop', 'POST', {
                    session_id: this.sessionId
                });
                
                this.isActive = false;
                this.onSessionEnd(response);
                
                this.logger.info('AI proctoring session stopped', response);
                return response;
            }
            
            return { message: 'No active session to stop' };
            
        } catch (error) {
            this.logger.error('Failed to stop proctoring session', error);
            this.onError(error);
            throw error;
        }
    }
    
    async getStatus() {
        try {
            if (!this.sessionId) {
                return { error: 'No active session' };
            }
            
            const response = await this._apiCall('/session/status', 'GET');
            
            if (response.error) {
                throw new Error(response.error);
            }
            
            this.currentScore = response.trust_score;
            this.statusColor = response.status_color;
            this.onStatusUpdate(response);
            
            return response;
            
        } catch (error) {
            this.logger.error('Failed to get proctoring status', error);
            this.onError(error);
            throw error;
        }
    }
    
    async _initializeWebcam() {
        try {
            this.logger.info('Initializing webcam...');
            
            // Create video element
            this.video = document.createElement('video');
            this.video.autoplay = true;
            this.video.muted = true;
            
            // Create canvas for frame capture
            this.canvas = document.createElement('canvas');
            this.canvas.width = 640;
            this.canvas.height = 480;
            
            // Get webcam stream
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                },
                audio: false
            });
            
            this.video.srcObject = this.stream;
            
            // Wait for video to be ready
            await new Promise((resolve) => {
                this.video.onloadedmetadata = resolve;
            });
            
            this.logger.info('Webcam initialized successfully');
            
        } catch (error) {
            this.logger.error('Failed to initialize webcam', error);
            
            // Create violation for no camera
            await this._reportViolation('no_camera', 'critical', 'Camera access denied or not available');
            
            throw error;
        }
    }
    
    _startFrameCapture() {
        if (!this.video || !this.canvas || !this.isActive) {
            return;
        }
        
        this.captureInterval = setInterval(async () => {
            if (!this.isActive) {
                return;
            }
            
            try {
                // Capture frame
                const context = this.canvas.getContext('2d');
                context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
                
                // Convert to base64
                const frameData = this.canvas.toDataURL('image/jpeg', 0.8);
                
                // Send to server for processing
                await this._processFrame(frameData);
                
                this.framesProcessed++;
                
            } catch (error) {
                this.logger.error('Frame capture error', error);
            }
        }, this.config.frameInterval);
        
        this.logger.info('Frame capture started');
    }
    
    _stopFrameCapture() {
        if (this.captureInterval) {
            clearInterval(this.captureInterval);
            this.captureInterval = null;
            this.logger.info('Frame capture stopped');
        }
    }
    
    async _processFrame(frameData) {
        try {
            // Remove data URL prefix
            const base64Data = frameData.replace(/^data:image\/jpeg;base64,/, '');
            
            const response = await this._apiCall('/frame/process', 'POST', {
                frame_data: base64Data
            });
            
            if (response.error) {
                throw new Error(response.error);
            }
            
            // Update trust score
            if (response.trust_score !== undefined && response.trust_score !== this.currentScore) {
                const oldScore = this.currentScore;
                this.currentScore = response.trust_score;
                this.statusColor = this._getStatusColor(this.currentScore);
                
                this.logger.info('Trust score updated', {
                    from: oldScore,
                    to: this.currentScore
                });
                
                this.onStatusUpdate(response);
            }
            
            // Handle violations
            if (response.violations && response.violations.length > 0) {
                for (const violation of response.violations) {
                    this._handleViolation(violation);
                }
            }
            
        } catch (error) {
            this.logger.error('Frame processing error', error);
            this.onError(error);
        }
    }
    
    _setupTabDetection() {
        this.logger.info('Setting up tab detection...');
        
        // Track page visibility
        document.addEventListener('visibilitychange', () => {
            this._handleVisibilityChange();
        });
        
        // Track window focus
        window.addEventListener('focus', () => {
            this._handleWindowFocus(true);
        });
        
        window.addEventListener('blur', () => {
            this._handleWindowFocus(false);
        });
        
        // Track mouse leave (potential tab switch)
        document.addEventListener('mouseleave', () => {
            this._handleMouseLeave();
        });
        
        // Track keyboard shortcuts (Alt+Tab, etc.)
        document.addEventListener('keydown', (e) => {
            this._handleKeyDown(e);
        });
        
        this.logger.info('Tab detection setup complete');
    }
    
    _handleVisibilityChange() {
        if (document.hidden) {
            this._reportTabSwitch('Page hidden (visibility change)');
        } else {
            this.isWindowFocused = true;
            this.lastFocusTime = Date.now();
        }
    }
    
    _handleWindowFocus(focused) {
        const wasFocused = this.isWindowFocused;
        this.isWindowFocused = focused;
        
        if (wasFocused && !focused) {
            this._reportTabSwitch('Window lost focus');
        } else if (!wasFocused && focused) {
            this.lastFocusTime = Date.now();
        }
    }
    
    _handleMouseLeave() {
        if (this.isWindowFocused) {
            // Small delay to avoid false positives
            setTimeout(() => {
                if (!this.isWindowFocused) {
                    this._reportTabSwitch('Mouse left window');
                }
            }, 1000);
        }
    }
    
    _handleKeyDown(event) {
        // Detect Alt+Tab, Ctrl+Tab, etc.
        if (event.altKey && event.key === 'Tab') {
            this._reportTabSwitch('Alt+Tab detected');
        } else if (event.ctrlKey && event.key === 'Tab') {
            this._reportTabSwitch('Ctrl+Tab detected');
        } else if (event.metaKey && event.key === 'Tab') {
            this._reportTabSwitch('Cmd+Tab detected');
        }
        
        // Detect F11 (fullscreen toggle)
        if (event.key === 'F11') {
            this._reportSuspiciousActivity('F11 key pressed (fullscreen toggle)');
        }
        
        // Detect Esc (potential attempt to exit fullscreen)
        if (event.key === 'Escape') {
            this._reportSuspiciousActivity('Escape key pressed');
        }
    }
    
    async _reportTabSwitch(reason) {
        try {
            this.tabSwitchCount++;
            
            const response = await this._apiCall('/tab/switch', 'POST');
            
            if (response.error) {
                throw new Error(response.error);
            }
            
            this.logger.warn('Tab switch detected', {
                reason: reason,
                count: this.tabSwitchCount
            });
            
            if (response.violation_type) {
                this._handleViolation(response);
            }
            
        } catch (error) {
            this.logger.error('Failed to report tab switch', error);
        }
    }
    
    async _reportSuspiciousActivity(activityType) {
        try {
            const response = await this._apiCall('/activity/suspicious', 'POST', {
                activity_type: activityType
            });
            
            if (response.error) {
                throw new Error(response.error);
            }
            
            this.logger.warn('Suspicious activity detected', {
                type: activityType
            });
            
            if (response.violation_type) {
                this._handleViolation(response);
            }
            
        } catch (error) {
            this.logger.error('Failed to report suspicious activity', error);
        }
    }
    
    async _reportViolation(violationType, severity, details) {
        try {
            this.logger.warn('Violation detected', {
                type: violationType,
                severity: severity,
                details: details
            });
            
            // Create local violation record
            const violation = {
                timestamp: Date.now(),
                violation_type: violationType,
                severity: severity,
                details: details
            };
            
            this.violations.push(violation);
            this.onViolation(violation);
            
        } catch (error) {
            this.logger.error('Failed to report violation', error);
        }
    }
    
    _handleViolation(violation) {
        this.logger.warn('Violation received from server', violation);
        
        // Update trust score
        if (violation.trust_score_after !== undefined) {
            this.currentScore = violation.trust_score_after;
            this.statusColor = this._getStatusColor(this.currentScore);
        }
        
        // Add to local violations
        this.violations.push(violation);
        this.onViolation(violation);
    }
    
    async _apiCall(endpoint, method = 'GET', data = null) {
        const url = this.config.apiBaseUrl + endpoint;
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this._getCSRFToken()
            }
        };
        
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }
        
        let retries = 0;
        while (retries < this.config.maxRetries) {
            try {
                const response = await fetch(url, options);
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.error || `HTTP ${response.status}`);
                }
                
                return result;
                
            } catch (error) {
                retries++;
                if (retries >= this.config.maxRetries) {
                    throw error;
                }
                
                // Wait before retry
                await new Promise(resolve => setTimeout(resolve, 1000 * retries));
            }
        }
    }
    
    _getCSRFToken() {
        // Get CSRF token from meta tag or cookie
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        
        // Try to get from cookie
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') {
                return value;
            }
        }
        
        return '';
    }
    
    _getStatusColor(score) {
        if (score >= 80) {
            return 'green';
        } else if (score >= 60) {
            return 'yellow';
        } else {
            return 'red';
        }
    }
    
    _createLogger() {
        return {
            info: (message, data = null) => {
                console.log(`[AIProctor] INFO: ${message}`, data || '');
            },
            warn: (message, data = null) => {
                console.warn(`[AIProctor] WARN: ${message}`, data || '');
            },
            error: (message, error = null) => {
                console.error(`[AIProctor] ERROR: ${message}`, error || '');
            }
        };
    }
    
    // Public methods for external access
    
    getViolationHistory() {
        return this.violations.slice();
    }
    
    getCurrentScore() {
        return this.currentScore;
    }
    
    getStatusColor() {
        return this.statusColor;
    }
    
    isActiveSession() {
        return this.isActive;
    }
    
    getStatistics() {
        return {
            sessionId: this.sessionId,
            currentScore: this.currentScore,
            statusColor: this.statusColor,
            violationsCount: this.violations.length,
            framesProcessed: this.framesProcessed,
            tabSwitchCount: this.tabSwitchCount,
            isActive: this.isActive
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AIProctor;
} else if (typeof window !== 'undefined') {
    window.AIProctor = AIProctor;
}
