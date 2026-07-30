/**
 * Complete Webcam System Fix
 * Production-ready webcam monitoring with proper error handling
 */

class WebcamSystem {
    constructor(options = {}) {
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        this.stream = null;
        this.isActive = false;
        this.errorCallback = options.onError || (() => {});
        this.successCallback = options.onSuccess || (() => {});
        this.statusCallback = options.onStatusChange || (() => {});
        
        console.log('WebcamSystem initialized');
    }
    
    /**
     * Check browser compatibility
     */
    static isSupported() {
        return !!(navigator.mediaDevices && 
                  navigator.mediaDevices.getUserMedia);
    }
    
    /**
     * Start webcam with comprehensive error handling
     */
    async start() {
        try {
            console.log('Starting webcam system...');
            this.statusCallback('initializing');
            
            // Check browser support
            if (!WebcamSystem.isSupported()) {
                throw new Error('Webcam not supported in this browser');
            }
            
            // Get video element
            this.video = document.getElementById('webcam');
            if (!this.video) {
                throw new Error('Webcam video element not found');
            }
            
            console.log('Video element found:', this.video);
            
            // Request camera access
            console.log('Requesting camera access...');
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640, max: 1280 },
                    height: { ideal: 480, max: 720 },
                    facingMode: 'user',
                    aspectRatio: { ideal: 4/3 }
                },
                audio: false
            });
            
            console.log('Camera access granted');
            
            // Connect stream to video element
            this.video.srcObject = this.stream;
            
            // Wait for video to be ready
            await new Promise((resolve, reject) => {
                this.video.onloadedmetadata = () => {
                    console.log('Video metadata loaded');
                    resolve();
                };
                
                this.video.onerror = (error) => {
                    console.error('Video error:', error);
                    reject(error);
                };
                
                // Timeout after 5 seconds
                setTimeout(() => {
                    reject(new Error('Video loading timeout'));
                }, 5000);
            });
            
            // Start playing video
            await this.video.play();
            console.log('Video started playing');
            
            // Setup canvas for processing
            this.canvas = document.getElementById('webcamCanvas');
            if (this.canvas) {
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
                this.ctx = this.canvas.getContext('2d');
                console.log('Canvas setup complete');
            }
            
            this.isActive = true;
            this.statusCallback('active');
            this.successCallback();
            
            console.log('Webcam system started successfully');
            return true;
            
        } catch (error) {
            console.error('Webcam start error:', error);
            this.handleError(error);
            return false;
        }
    }
    
    /**
     * Stop webcam
     */
    stop() {
        try {
            console.log('Stopping webcam...');
            
            // Stop video stream
            if (this.stream) {
                this.stream.getTracks().forEach(track => {
                    track.stop();
                });
                this.stream = null;
            }
            
            // Clear video element
            if (this.video) {
                this.video.srcObject = null;
            }
            
            this.isActive = false;
            this.statusCallback('stopped');
            
            console.log('Webcam stopped successfully');
            
        } catch (error) {
            console.error('Webcam stop error:', error);
            this.handleError(error);
        }
    }
    
    /**
     * Get current frame as image data
     */
    captureFrame() {
        if (!this.isActive || !this.video || !this.canvas || !this.ctx) {
            return null;
        }
        
        try {
            this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            return this.canvas.toDataURL('image/jpeg', 0.8);
        } catch (error) {
            console.error('Frame capture error:', error);
            return null;
        }
    }
    
    /**
     * Handle different types of errors
     */
    handleError(error) {
        console.error('Webcam error:', error);
        
        let errorMessage = 'Unknown error occurred';
        let errorType = 'unknown';
        
        if (error.name === 'NotAllowedError' || error.message.includes('denied')) {
            errorMessage = 'Camera access denied. Please allow camera access and refresh the page.';
            errorType = 'permission_denied';
        } else if (error.name === 'NotFoundError' || error.message.includes('not found')) {
            errorMessage = 'No webcam found. Please connect a camera and refresh the page.';
            errorType = 'device_not_found';
        } else if (error.name === 'NotReadableError' || error.message.includes('in use')) {
            errorMessage = 'Webcam is already in use by another application.';
            errorType = 'device_in_use';
        } else if (error.name === 'OverconstrainedError' || error.message.includes('constraints')) {
            errorMessage = 'Webcam does not support the required settings.';
            errorType = 'constraints_error';
        } else if (error.message.includes('not supported')) {
            errorMessage = 'Webcam not supported in this browser. Please use Chrome, Firefox, or Edge.';
            errorType = 'browser_not_supported';
        } else if (error.message.includes('Video element not found')) {
            errorMessage = 'Webcam video element not found. Please refresh the page.';
            errorType = 'element_not_found';
        } else if (error.message.includes('timeout')) {
            errorMessage = 'Webcam loading timeout. Please check your connection and refresh.';
            errorType = 'timeout';
        }
        
        this.statusCallback('error');
        this.errorCallback({
            message: errorMessage,
            type: errorType,
            originalError: error
        });
    }
    
    /**
     * Get webcam status
     */
    getStatus() {
        return {
            isActive: this.isActive,
            hasStream: !!this.stream,
            hasVideo: !!this.video,
            videoReady: this.video ? this.video.readyState >= 2 : false
        };
    }
}

// Global webcam instance
window.webcamSystem = null;

// Auto-start webcam when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, checking for webcam initialization...');
    
    // Only initialize on exam pages
    if (document.querySelector('.exam-container, #examForm, .adaptive-exam')) {
        console.log('Exam page detected, initializing webcam...');
        
        if (WebcamSystem.isSupported()) {
            console.log('Webcam is supported');
            
            window.webcamSystem = new WebcamSystem({
                onSuccess: () => {
                    console.log('Webcam started successfully');
                    updateWebcamStatus('active');
                },
                onError: (error) => {
                    console.error('Webcam error:', error);
                    updateWebcamStatus('error', error.message);
                    showWebcamError(error.message);
                },
                onStatusChange: (status) => {
                    console.log('Webcam status changed:', status);
                    updateWebcamStatus(status);
                }
            });
            
            // Auto-start after 1 second
            setTimeout(() => {
                if (window.webcamSystem) {
                    console.log('Auto-starting webcam...');
                    window.webcamSystem.start();
                }
            }, 1000);
            
        } else {
            console.warn('Webcam not supported');
            updateWebcamStatus('unsupported');
            showWebcamError('Webcam not supported in this browser. Please use Chrome, Firefox, or Edge.');
        }
    }
});

// UI update functions
function updateWebcamStatus(status, message = '') {
    const statusElement = document.getElementById('webcamStatus');
    const videoElement = document.getElementById('webcam');
    const placeholderElement = document.getElementById('webcamPlaceholder');
    
    console.log('Updating webcam status:', status, message);
    
    if (statusElement) {
        let statusText, statusClass, icon;
        
        switch (status) {
            case 'initializing':
                statusText = 'Initializing...';
                statusClass = 'text-warning';
                icon = 'bi-camera-video-off';
                break;
            case 'active':
                statusText = 'Camera Active';
                statusClass = 'text-success';
                icon = 'bi-camera-video-fill';
                break;
            case 'stopped':
                statusText = 'Camera Stopped';
                statusClass = 'text-muted';
                icon = 'bi-camera-video-off';
                break;
            case 'error':
                statusText = 'Camera Error';
                statusClass = 'text-danger';
                icon = 'bi-exclamation-triangle';
                break;
            case 'unsupported':
                statusText = 'Not Supported';
                statusClass = 'text-muted';
                icon = 'bi-camera-video-slash';
                break;
            default:
                statusText = 'Unknown';
                statusClass = 'text-muted';
                icon = 'bi-question-circle';
        }
        
        statusElement.className = `webcam-status ${statusClass}`;
        statusElement.innerHTML = `
            <i class="bi ${icon} me-1"></i>
            ${statusText}
        `;
    }
    
    // Show/hide video and placeholder
    if (videoElement && placeholderElement) {
        if (status === 'active') {
            videoElement.style.display = 'block';
            placeholderElement.style.display = 'none';
        } else {
            videoElement.style.display = 'none';
            placeholderElement.style.display = 'block';
            
            // Update placeholder message
            const placeholderText = placeholderElement.querySelector('.placeholder-text');
            if (placeholderText) {
                if (status === 'error') {
                    placeholderText.textContent = message || 'Camera error occurred';
                } else if (status === 'unsupported') {
                    placeholderText.textContent = 'Camera not supported';
                } else {
                    placeholderText.textContent = 'Initializing camera...';
                }
            }
        }
    }
}

function showWebcamError(message) {
    // Create error notification
    const notification = document.createElement('div');
    notification.className = 'alert alert-danger alert-dismissible fade show position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 1050; max-width: 400px;';
    notification.innerHTML = `
        <h6 class="alert-heading">
            <i class="bi bi-camera-video-off me-2"></i>
            Camera Error
        </h6>
        <p class="mb-2">${message}</p>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 10 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 10000);
}

// Export for use in other scripts
window.WebcamSystem = WebcamSystem;
