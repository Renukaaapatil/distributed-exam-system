/**
 * Production-Ready Voice Detection System
 * Detects talking during exams with real-time UI updates
 */

class VoiceDetectionSystem {
    constructor(options = {}) {
        this.isListening = false;
        this.audioContext = null;
        this.microphone = null;
        this.analyser = null;
        this.dataArray = null;
        this.examId = options.examId || null;
        this.userId = options.userId || null;
        
        // Detection settings
        this.volumeThreshold = options.volumeThreshold || 0.1;  // Volume threshold (0-1)
        this.talkingDuration = options.talkingDuration || 2000;  // 2 seconds of talking
        this.checkInterval = options.checkInterval || 100;     // Check every 100ms
        
        // State tracking
        this.currentVolume = 0;
        this.talkingStartTime = null;
        this.violationCount = 0;
        this.lastViolationTime = null;
        this.currentTrustScore = 100;
        
        // Callbacks
        this.callbacks = {
            onTalkingDetected: options.onTalkingDetected || (() => {}),
            onViolation: options.onViolation || (() => {}),
            onTrustScoreUpdate: options.onTrustScoreUpdate || (() => {}),
            onStatusChange: options.onStatusChange || (() => {}),
            onError: options.onError || (() => {})
        };
        
        this.checkTimer = null;
        this.status = 'idle';  // idle, listening, talking, violation
    }
    
    async startListening() {
        try {
            console.log('Starting voice detection...');
            
            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: true,
                video: false 
            });
            
            // Setup audio context
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.microphone = this.audioContext.createMediaStreamSource(stream);
            this.analyser = this.audioContext.createAnalyser();
            
            // Configure analyser
            this.analyser.fftSize = 256;
            this.analyser.smoothingTimeConstant = 0.8;
            
            // Connect microphone to analyser
            this.microphone.connect(this.analyser);
            
            // Setup data array
            const bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(bufferLength);
            
            // Start monitoring
            this.isListening = true;
            this.status = 'listening';
            this.startVolumeMonitoring();
            
            this.callbacks.onStatusChange('listening');
            console.log('Voice detection started successfully');
            
            return true;
            
        } catch (error) {
            console.error('Failed to start voice detection:', error);
            this.callbacks.onError(error);
            return false;
        }
    }
    
    stopListening() {
        try {
            console.log('Stopping voice detection...');
            
            // Clear monitoring timer
            if (this.checkTimer) {
                clearInterval(this.checkTimer);
                this.checkTimer = null;
            }
            
            // Stop audio context
            if (this.audioContext) {
                this.audioContext.close();
                this.audioContext = null;
            }
            
            // Stop microphone stream
            if (this.microphone) {
                this.microphone.disconnect();
                this.microphone = null;
            }
            
            this.isListening = false;
            this.status = 'idle';
            this.callbacks.onStatusChange('idle');
            
            console.log('Voice detection stopped');
            
        } catch (error) {
            console.error('Error stopping voice detection:', error);
            this.callbacks.onError(error);
        }
    }
    
    startVolumeMonitoring() {
        this.checkTimer = setInterval(() => {
            if (!this.isListening) return;
            
            this.checkVolumeLevel();
        }, this.checkInterval);
    }
    
    checkVolumeLevel() {
        if (!this.analyser || !this.dataArray) return;
        
        // Get frequency data
        this.analyser.getByteFrequencyData(this.dataArray);
        
        // Calculate RMS (Root Mean Square) volume
        let sum = 0;
        for (let i = 0; i < this.dataArray.length; i++) {
            const normalized = this.dataArray[i] / 255;  // Normalize to 0-1
            sum += normalized * normalized;
        }
        
        this.currentVolume = Math.sqrt(sum / this.dataArray.length);
        
        // Check if talking is detected
        if (this.currentVolume > this.volumeThreshold) {
            this.handleTalkingDetected();
        } else {
            this.handleSilenceDetected();
        }
    }
    
    handleTalkingDetected() {
        const now = Date.now();
        
        if (!this.talkingStartTime) {
            // Start of talking
            this.talkingStartTime = now;
            this.status = 'talking';
            this.callbacks.onStatusChange('talking');
            console.log('Talking detected - starting timer...');
        }
        
        // Check if talking duration exceeds threshold
        const talkingDuration = now - this.talkingStartTime;
        if (talkingDuration >= this.talkingDuration) {
            this.triggerViolation();
            this.talkingStartTime = null;  // Reset timer
        }
        
        this.callbacks.onTalkingDetected(this.currentVolume);
    }
    
    handleSilenceDetected() {
        if (this.talkingStartTime) {
            // Talking stopped before violation threshold
            const talkingDuration = Date.now() - this.talkingStartTime;
            console.log(`Talking stopped after ${talkingDuration}ms (below threshold)`);
            this.talkingStartTime = null;
        }
        
        if (this.status === 'talking') {
            this.status = 'listening';
            this.callbacks.onStatusChange('listening');
        }
    }
    
    async triggerViolation() {
        try {
            this.violationCount++;
            this.lastViolationTime = Date.now();
            this.status = 'violation';
            
            console.log(`Voice violation #${this.violationCount} triggered!`);
            
            // Send violation to backend
            const violationData = {
                violation: 'talking_detected',
                volume: this.currentVolume,
                duration: this.talkingDuration,
                violation_count: this.violationCount,
                timestamp: new Date().toISOString()
            };
            
            await this.reportViolation(violationData);
            
            // Check for auto-submit condition
            if (this.violationCount >= this.autoSubmitThreshold) {
                console.log('Auto-submit threshold reached!');
                await this.handleAutoSubmit();
            }
            
            this.callbacks.onViolation(violationData);
            
            // Reset status after a delay
            setTimeout(() => {
                if (this.status === 'violation') {
                    this.status = 'listening';
                    this.callbacks.onStatusChange('listening');
                }
            }, 3000);
            
        } catch (error) {
            console.error('Error handling violation:', error);
            this.callbacks.onError(error);
        }
    }
    
    async reportViolation(violationData) {
        try {
            const response = await fetch('/detect_voice_violation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    exam_id: this.examId,
                    volume_level: this.currentVolume,
                    timestamp: new Date().toISOString()
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Violation reported successfully:', result);
                
                // Update trust score in real-time
                if (result.success) {
                    this.currentTrustScore = result.new_trust_score;
                    this.callbacks.onTrustScoreUpdate({
                        oldScore: result.old_trust_score,
                        newScore: result.new_trust_score,
                        isHighRisk: result.is_high_risk
                    });
                }
                
                return result;
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
        } catch (error) {
            console.error('Failed to report violation:', error);
            throw error;
        }
    }
    
    async handleAutoSubmit() {
        try {
            console.log('Auto-submitting exam due to repeated voice violations...');
            
            // Find and click submit button
            const submitBtn = document.getElementById('submitBtn') || 
                             document.querySelector('button[type="submit"]') ||
                             document.querySelector('input[type="submit"]');
            
            if (submitBtn) {
                // Show warning first
                this.showAutoSubmitWarning();
                
                // Submit after 3 seconds
                setTimeout(() => {
                    submitBtn.click();
                }, 3000);
                
                this.callbacks.onAutoSubmit();
            } else {
                console.error('Submit button not found for auto-submit');
            }
            
        } catch (error) {
            console.error('Error during auto-submit:', error);
            this.callbacks.onError(error);
        }
    }
    
    showAutoSubmitWarning() {
        // Create warning modal
        const warning = document.createElement('div');
        warning.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        warning.style.cssText = 'top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 9999; max-width: 500px;';
        warning.innerHTML = `
            <h5 class="alert-heading">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Exam Auto-Submit
            </h5>
            <p class="mb-2">
                <strong>Multiple voice violations detected!</strong><br>
                Your exam will be automatically submitted in 3 seconds.
            </p>
            <hr>
            <p class="mb-0">
                <small>This action is taken due to repeated talking during the exam.</small>
            </p>
        `;
        
        document.body.appendChild(warning);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (warning.parentNode) {
                warning.parentNode.removeChild(warning);
            }
        }, 5000);
    }
    
    // Utility methods
    getCSRFToken() {
        const token = document.querySelector('input[name="csrf_token"], meta[name="csrf-token"]');
        return token ? token.value || token.getAttribute('content') : '';
    }
    
    getExamId() {
        // Try to get exam ID from various sources
        const examIdInput = document.getElementById('examId');
        if (examIdInput) {
            return examIdInput.value;
        }
        
        const examContainer = document.querySelector('[data-exam-id]');
        if (examContainer) {
            return examContainer.dataset.examId;
        }
        
        // Try to get from URL
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('exam_id');
    }
    
    // Public API methods
    getStatus() {
        return {
            status: this.status,
            isListening: this.isListening,
            currentVolume: this.currentVolume,
            violationCount: this.violationCount,
            lastViolationTime: this.lastViolationTime
        };
    }
    
    setThreshold(threshold) {
        if (threshold >= 0 && threshold <= 1) {
            this.volumeThreshold = threshold;
            console.log(`Volume threshold set to: ${threshold}`);
        }
    }
    
    setTalkingDuration(duration) {
        if (duration > 0) {
            this.talkingDuration = duration;
            console.log(`Talking duration set to: ${duration}ms`);
        }
    }
    
    resetViolations() {
        this.violationCount = 0;
        this.lastViolationTime = null;
        console.log('Violation count reset');
    }
    
    // Static method to check browser support
    static isSupported() {
        return !!(navigator.mediaDevices && 
                  navigator.mediaDevices.getUserMedia && 
                  (window.AudioContext || window.webkitAudioContext));
    }
}

// Global voice detection instance
window.voiceDetection = null;

// Initialize voice detection when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on exam pages
    if (document.querySelector('.exam-container, #examForm, .adaptive-exam')) {
        if (VoiceDetectionSystem.isSupported()) {
            console.log('Voice detection is supported');
            
            // Get exam ID from page
            const examId = document.querySelector('input[name="exam_id"]')?.value || 
                           document.querySelector('[data-exam-id]')?.dataset.examId;
            
            // Auto-start voice detection
            window.voiceDetection = new VoiceDetectionSystem({
                examId: examId,
                volumeThreshold: 0.1,
                talkingDuration: 2000,
                onTalkingDetected: (volume) => {
                    console.log(`Talking detected - Volume: ${volume.toFixed(3)}`);
                    updateVoiceStatus('talking', volume);
                    updateVolumeBar(volume);
                },
                onViolation: (data) => {
                    console.log('Voice violation triggered:', data);
                    updateVoiceStatus('violation');
                    showViolationNotification('Voice talking detected! Trust score reduced.');
                },
                onTrustScoreUpdate: (scoreData) => {
                    console.log('Trust score updated:', scoreData);
                    updateTrustScoreDisplay(scoreData.newScore, scoreData.isHighRisk);
                    
                    if (scoreData.isHighRisk) {
                        showHighRiskWarning();
                    }
                },
                onStatusChange: (status) => {
                    console.log('Voice status changed:', status);
                    updateVoiceStatus(status);
                },
                onError: (error) => {
                    console.error('Voice detection error:', error);
                    updateVoiceStatus('error');
                }
            });
            
            // Auto-start after 2 seconds
            setTimeout(() => {
                if (window.voiceDetection) {
                    window.voiceDetection.startListening();
                }
            }, 2000);
            
        } else {
            console.warn('Voice detection is not supported in this browser');
            updateVoiceStatus('unsupported');
        }
    }
});

// UI update functions
function updateVoiceStatus(status, volume = null) {
    const statusElement = document.getElementById('voiceStatus');
    const volumeElement = document.getElementById('voiceVolume');
    
    if (!statusElement) return;
    
    let statusText, statusClass, icon;
    
    switch (status) {
        case 'idle':
            statusText = 'Idle';
            statusClass = 'text-muted';
            icon = 'bi-mic-mute';
            break;
        case 'listening':
            statusText = 'Listening...';
            statusClass = 'text-success';
            icon = 'bi-mic';
            break;
        case 'talking':
            statusText = 'Talking detected!';
            statusClass = 'text-warning';
            icon = 'bi-mic-fill';
            break;
        case 'violation':
            statusText = 'Violation recorded!';
            statusClass = 'text-danger';
            icon = 'bi-exclamation-triangle';
            break;
        case 'auto-submit':
            statusText = 'Auto-submitting...';
            statusClass = 'text-danger';
            icon = 'bi-x-circle';
            break;
        case 'error':
            statusText = 'Error';
            statusClass = 'text-danger';
            icon = 'bi-exclamation-circle';
            break;
        case 'unsupported':
            statusText = 'Not supported';
            statusClass = 'text-muted';
            icon = 'bi-mic-slash';
            break;
        default:
            statusText = 'Unknown';
            statusClass = 'text-muted';
            icon = 'bi-question-circle';
    }
    
    statusElement.className = `voice-status ${statusClass}`;
    statusElement.innerHTML = `
        <i class="bi ${icon} me-1"></i>
        ${statusText}
    `;
    
    if (volumeElement && volume !== null) {
        volumeElement.textContent = `Volume: ${(volume * 100).toFixed(1)}%`;
    }
}

function updateVolumeBar(volume) {
    const volumeBar = document.getElementById('voiceLevelIndicator');
    if (volumeBar) {
        const percentage = Math.min(100, Math.round(volume * 100));
        volumeBar.style.width = percentage + '%';
        
        // Change color based on volume level
        if (volume > 0.1) {
            volumeBar.className = 'voice-level-bar voice-active';
        } else {
            volumeBar.className = 'voice-level-bar voice-inactive';
        }
    }
}

function updateTrustScoreDisplay(newScore, isHighRisk) {
    // Update trust score display if it exists
    const trustScoreElement = document.getElementById('trustScoreDisplay');
    if (trustScoreElement) {
        trustScoreElement.textContent = newScore;
        
        // Update color based on score
        if (isHighRisk) {
            trustScoreElement.className = 'trust-score-badge trust-critical';
        } else if (newScore >= 80) {
            trustScoreElement.className = 'trust-score-badge trust-excellent';
        } else if (newScore >= 60) {
            trustScoreElement.className = 'trust-score-badge trust-good';
        } else if (newScore >= 40) {
            trustScoreElement.className = 'trust-score-badge trust-average';
        } else {
            trustScoreElement.className = 'trust-score-badge trust-poor';
        }
    }
}

function showHighRiskWarning() {
    const warning = document.createElement('div');
    warning.className = 'alert alert-danger alert-dismissible fade show position-fixed';
    warning.style.cssText = 'top: 80px; right: 20px; z-index: 1050; max-width: 400px;';
    warning.innerHTML = `
        <h6 class="alert-heading">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>
            High Risk Status
        </h6>
        <p class="mb-2">
            <strong>Your trust score has fallen below 40!</strong><br>
            Continued violations may result in exam termination.
        </p>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(warning);
    
    // Auto-remove after 8 seconds
    setTimeout(() => {
        if (warning.parentNode) {
            warning.parentNode.removeChild(warning);
        }
    }, 8000);
}

function showViolationNotification(message) {
    // Create notification
    const notification = document.createElement('div');
    notification.className = 'alert alert-warning alert-dismissible fade show position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 1050; max-width: 350px;';
    notification.innerHTML = `
        <i class="bi bi-exclamation-triangle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Export for use in other scripts
window.VoiceDetectionSystem = VoiceDetectionSystem;
