/**
 * AI Proctoring System - Real-time Cheating Detection
 * Uses MediaPipe Face Mesh for facial analysis and cheating detection
 */

class AIProctor {
    constructor(examId, options = {}) {
        this.examId = examId;
        this.userId = null;
        this.sessionId = null;
        this.isRunning = false;
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        this.faceMesh = null;
        this.camera = null;
        
        // Voice detection variables
        this.audioContext = null;
        this.microphone = null;
        this.analyser = null;
        this.audioDataArray = null;
        this.voiceThreshold = 0.1; // Voice detection threshold
        this.voiceDetectedTime = null;
        this.maxVoiceDuration = 5000; // Max 5 seconds continuous talking
        this.voiceViolationCount = 0;
        
        // Configuration
        this.config = {
            detectionInterval: options.detectionInterval || 2000, // 2 seconds
            enableWebcam: options.enableWebcam !== false,
            enableVoiceDetection: options.enableVoiceDetection !== false,
            enableTabDetection: options.enableTabDetection !== false,
            onStatusUpdate: options.onStatusUpdate || (() => {}),
            onViolation: options.onViolation || (() => {}),
            onError: options.onError || (() => {}),
            onSessionStart: options.onSessionStart || (() => {}),
            onSessionEnd: options.onSessionEnd || (() => {})
        };
        
        // Detection thresholds
        this.thresholds = {
            headYawThreshold: 0.3,  // Head turned left/right
            headPitchThreshold: 0.4, // Head looking down
            eyeGazeThreshold: 0.5,   // Eyes not looking at screen
            multipleFacesThreshold: 1, // More than 1 face
            phoneConfidenceThreshold: 0.7 // Phone detection confidence
        };
        
        // Statistics
        this.stats = {
            framesProcessed: 0,
            violationsCount: 0,
            tabSwitchCount: 0,
            lastViolation: null,
            startTime: null
        };
        
        // Violation tracking
        this.violationHistory = [];
        this.lastViolationTime = {};
        
        this.init();
    }
    
    /**
     * Initialize the proctoring system
     */
    async init() {
        try {
            console.log('Initializing AI Proctoring System...');
            
            // Start tab detection if enabled
            if (this.config.enableTabDetection) {
                this.initTabDetection();
            }
            
            // Initialize webcam if enabled
            if (this.config.enableWebcam) {
                // Wait for webcam system to be ready
                await this.waitForWebcamReady();
                await this.initWebcam();
                await this.initFaceMesh();
            }
            
            // Initialize voice detection if enabled
            if (this.config.enableVoiceDetection) {
                await this.initVoiceDetection();
            }
            
            this.stats.startTime = Date.now();
            console.log('AI Proctoring System initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize AI Proctoring:', error);
            this.config.onError(error);
        }
    }
    
    /**
     * Initialize voice detection using Web Audio API
     */
    async initVoiceDetection() {
        try {
            console.log('Initializing voice detection...');
            
            // Create audio context
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Get microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            this.microphone = this.audioContext.createMediaStreamSource(stream);
            
            // Create analyser for voice detection
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            this.analyser.smoothingTimeConstant = 0.8;
            
            // Connect microphone to analyser
            this.microphone.connect(this.analyser);
            
            // Create data array for audio analysis
            this.audioDataArray = new Uint8Array(this.analyser.frequencyBinCount);
            
            console.log('Voice detection initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize voice detection:', error);
            throw new Error('Microphone access denied or not available');
        }
    }
    
    /**
     * Monitor voice levels and detect violations
     */
    monitorVoiceLevels() {
        if (!this.analyser || !this.audioDataArray) return;
        
        this.analyser.getByteFrequencyData(this.audioDataArray);
        
        // Calculate average volume
        let sum = 0;
        for (let i = 0; i < this.audioDataArray.length; i++) {
            sum += this.audioDataArray[i];
        }
        const average = sum / this.audioDataArray.length;
        const normalizedVolume = average / 255; // Normalize to 0-1
        
        // Check if voice is detected
        if (normalizedVolume > this.voiceThreshold) {
            if (!this.voiceDetectedTime) {
                this.voiceDetectedTime = Date.now();
            } else {
                const voiceDuration = Date.now() - this.voiceDetectedTime;
                
                // Check if talking for too long
                if (voiceDuration > this.maxVoiceDuration) {
                    this.reportViolation('voice_detected', 'high', 
                        `Student talking continuously for ${Math.round(voiceDuration/1000)} seconds`);
                    this.voiceDetectedTime = null; // Reset to avoid multiple reports
                    this.voiceViolationCount++;
                }
            }
        } else {
            // Reset voice detection when silence
            this.voiceDetectedTime = null;
        }
        
        // Update voice level indicator (for UI)
        this.updateVoiceIndicator(normalizedVolume);
    }
    
    /**
     * Update voice level indicator in UI
     */
    updateVoiceIndicator(level) {
        const indicator = document.getElementById('voiceLevelIndicator');
        if (indicator) {
            const percentage = Math.round(level * 100);
            indicator.style.width = percentage + '%';
            indicator.className = 'voice-level-bar ' + 
                (level > this.voiceThreshold ? 'voice-active' : 'voice-inactive');
        }
    }
    
    /**
     * Wait for webcam system to be ready
     */
    async waitForWebcamReady() {
        console.log('Waiting for webcam system to be ready...');
        
        const maxWaitTime = 10000; // 10 seconds max wait
        const checkInterval = 100; // Check every 100ms
        let waitTime = 0;
        
        while (waitTime < maxWaitTime) {
            if (window.webcamSystem && window.webcamSystem.isActive) {
                console.log('Webcam system is ready');
                return true;
            }
            
            await new Promise(resolve => setTimeout(resolve, checkInterval));
            waitTime += checkInterval;
        }
        
        throw new Error('Webcam system failed to initialize within timeout period');
    }
    
    /**
     * Initialize webcam access
     */
    async initWebcam() {
        try {
            console.log('Initializing webcam for proctoring...');
            
            // Use existing video element from webcam system
            this.video = document.getElementById('webcam');
            if (!this.video) {
                throw new Error('Webcam video element not found. Make sure webcam system is initialized first.');
            }
            
            // Use existing canvas from webcam system
            this.canvas = document.getElementById('webcamCanvas');
            if (!this.canvas) {
                throw new Error('Webcam canvas element not found.');
            }
            
            this.ctx = this.canvas.getContext('2d');
            
            // Wait for webcam to be ready
            if (!this.video.srcObject) {
                throw new Error('Webcam stream not available. Please wait for webcam to initialize.');
            }
            
            // Set canvas dimensions
            this.canvas.width = this.video.videoWidth || 640;
            this.canvas.height = this.video.videoHeight || 480;
            
            console.log('Proctoring webcam initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize proctoring webcam:', error);
            throw new Error('Proctoring webcam initialization failed: ' + error.message);
        }
    }
    
    /**
     * Initialize MediaPipe Face Mesh
     */
    async initFaceMesh() {
        try {
            console.log('Initializing MediaPipe Face Mesh...');
            
            // Load MediaPipe Face Mesh
            const faceMesh = new FaceMesh({
                locateFile: (file) => {
                    return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
                }
            });
            
            faceMesh.setOptions({
                maxNumFaces: 3, // Detect up to 3 faces
                refineLandmarks: true,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });
            
            faceMesh.onResults((results) => {
                this.processFaceDetectionResults(results);
            });
            
            this.faceMesh = faceMesh;
            console.log('MediaPipe Face Mesh initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize Face Mesh:', error);
            throw new Error('Failed to load face detection models');
        }
    }
    
    /**
     * Start proctoring session
     */
    async startSession() {
        try {
            console.log('Starting proctoring session...');
            
            if (!this.faceMesh && this.config.enableWebcam) {
                throw new Error('Face detection not initialized');
            }
            
            // Start detection loop
            this.isRunning = true;
            this.detectionLoop();
            
            console.log('Proctoring session started');
            
        } catch (error) {
            console.error('Failed to start proctoring session:', error);
            this.config.onError(error);
        }
    }
    
    /**
     * Main detection loop
     */
    async detectionLoop() {
        if (!this.isRunning) return;
        
        try {
            if (this.config.enableWebcam && this.faceMesh && this.video) {
                // Send frame to MediaPipe
                await this.faceMesh.send({ image: this.video });
                this.stats.framesProcessed++;
            }
            
            // Monitor voice levels
            if (this.config.enableVoiceDetection) {
                this.monitorVoiceLevels();
            }
            
            // Check for tab switching
            if (this.config.enableTabDetection) {
                this.checkTabSwitching();
            }
            
        } catch (error) {
            console.error('Error in detection loop:', error);
        }
    }
    
    /**
     * Process face detection results
     */
    processFaceDetectionResults(results) {
        try {
            const faces = results.multiFaceLandmarks || [];
            
            // Check for multiple faces
            if (faces.length > this.thresholds.multipleFacesThreshold) {
                this.reportViolation('multiple_faces', {
                    faceCount: faces.length,
                    timestamp: Date.now()
                });
            }
            
            // Process each detected face
            faces.forEach((landmarks, index) => {
                if (index === 0) { // Process primary face
                    this.analyzePrimaryFace(landmarks);
                }
            });
            
            // Update status
            this.updateProctoringStatus();
            
        } catch (error) {
            console.error('Error processing face detection results:', error);
        }
    }
    
    /**
     * Analyze primary face for violations
     */
    analyzePrimaryFace(landmarks) {
        try {
            // Head pose estimation
            const headPose = this.estimateHeadPose(landmarks);
            
            // Check head turning (left/right)
            if (Math.abs(headPose.yaw) > this.thresholds.headYawThreshold) {
                this.reportViolation('head_turned', {
                    direction: headPose.yaw > 0 ? 'right' : 'left',
                    angle: headPose.yaw,
                    timestamp: Date.now()
                });
            }
            
            // Check head looking down
            if (headPose.pitch > this.thresholds.headPitchThreshold) {
                this.reportViolation('looking_away', {
                    type: 'looking_down',
                    angle: headPose.pitch,
                    timestamp: Date.now()
                });
            }
            
            // Eye gaze estimation (simplified)
            const eyeGaze = this.estimateEyeGaze(landmarks);
            if (eyeGaze.deviation > this.thresholds.eyeGazeThreshold) {
                this.reportViolation('looking_away', {
                    type: 'eye_gaze',
                    deviation: eyeGaze.deviation,
                    timestamp: Date.now()
                });
            }
            
        } catch (error) {
            console.error('Error analyzing primary face:', error);
        }
    }
    
    /**
     * Estimate head pose from facial landmarks
     */
    estimateHeadPose(landmarks) {
        // Simplified head pose estimation using key facial points
        const noseTip = landmarks[1];
        const chin = landmarks[175];
        const leftEye = landmarks[33];
        const rightEye = landmarks[263];
        
        // Calculate yaw (left/right rotation)
        const eyeCenter = {
            x: (leftEye.x + rightEye.x) / 2,
            y: (leftEye.y + rightEye.y) / 2
        };
        
        const yaw = (noseTip.x - eyeCenter.x) / eyeCenter.x;
        
        // Calculate pitch (up/down rotation)
        const pitch = (chin.y - eyeCenter.y) / eyeCenter.y;
        
        return { yaw, pitch };
    }
    
    /**
     * Estimate eye gaze direction
     */
    estimateEyeGaze(landmarks) {
        // Simplified eye gaze estimation
        const leftEyeInner = landmarks[133];
        const leftEyeOuter = landmarks[33];
        const rightEyeInner = landmarks[362];
        const rightEyeOuter = landmarks[263];
        
        // Calculate eye centers
        const leftEyeCenter = {
            x: (leftEyeInner.x + leftEyeOuter.x) / 2,
            y: (leftEyeInner.y + leftEyeOuter.y) / 2
        };
        
        const rightEyeCenter = {
            x: (rightEyeInner.x + rightEyeOuter.x) / 2,
            y: (rightEyeInner.y + rightEyeOuter.y) / 2
        };
        
        // Calculate deviation from center
        const faceCenter = {
            x: (leftEyeCenter.x + rightEyeCenter.x) / 2,
            y: (leftEyeCenter.y + rightEyeCenter.y) / 2
        };
        
        const deviation = Math.sqrt(
            Math.pow(faceCenter.x - 0.5, 2) + 
            Math.pow(faceCenter.y - 0.5, 2)
        );
        
        return { deviation, leftEye: leftEyeCenter, rightEye: rightEyeCenter };
    }
    
    /**
     * Initialize tab switching detection
     */
    initTabDetection() {
        console.log('Initializing tab switching detection...');
        
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.reportViolation('tab_switch', {
                    timestamp: Date.now(),
                    pageHidden: true
                });
                this.stats.tabSwitchCount++;
            }
        });
        
        // Detect window focus/blur
        window.addEventListener('blur', () => {
            this.reportViolation('tab_switch', {
                timestamp: Date.now(),
                windowBlurred: true
            });
            this.stats.tabSwitchCount++;
        });
        
        console.log('Tab switching detection initialized');
    }
    
    /**
     * Report a violation
     */
    async reportViolation(violationType, details) {
        try {
            // Prevent spamming the same violation
            const now = Date.now();
            const lastTime = this.lastViolationTime[violationType] || 0;
            
            if (now - lastTime < 5000) { // 5 second cooldown
                return;
            }
            
            this.lastViolationTime[violationType] = now;
            
            // Update statistics
            this.stats.violationsCount++;
            this.stats.lastViolation = {
                type: violationType,
                details,
                timestamp: now
            };
            
            // Add to violation history
            this.violationHistory.push({
                type: violationType,
                details,
                timestamp: now
            });
            
            // Keep only last 50 violations
            if (this.violationHistory.length > 50) {
                this.violationHistory = this.violationHistory.slice(-50);
            }
            
            console.log(`Violation detected: ${violationType}`, details);
            
            // Send to backend
            await this.sendViolationToBackend(violationType, details);
            
            // Trigger callback
            this.config.onViolation({
                type: violationType,
                details,
                timestamp: now,
                totalViolations: this.stats.violationsCount
            });
            
        } catch (error) {
            console.error('Error reporting violation:', error);
        }
    }
    
    /**
     * Send violation to backend API
     */
    async sendViolationToBackend(violationType, details) {
        try {
            const response = await fetch('/api/proctoring/update_trust_score', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    violation_type: violationType,
                    exam_id: this.examId,
                    details: details
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log(`Trust score updated: ${result.trust_score}`);
                
                // Check for auto-submit
                if (result.auto_submitted) {
                    this.handleAutoSubmit(result);
                }
                
                // Update status
                this.updateProctoringStatus();
            } else {
                console.error('Failed to update trust score:', result.error);
            }
            
        } catch (error) {
            console.error('Error sending violation to backend:', error);
        }
    }
    
    /**
     * Handle auto-submit scenario
     */
    handleAutoSubmit(result) {
        console.log('Exam auto-submitted due to trust score violation');
        
        // Stop proctoring
        this.stopSession();
        
        // Show alert
        alert('Your exam has been auto-submitted due to multiple trust score violations.');
        
        // Redirect to results page
        window.location.href = '/dashboard';
    }
    
    /**
     * Update proctoring status
     */
    async updateProctoringStatus() {
        try {
            const response = await fetch(`/api/proctoring/get_trust_score?exam_id=${this.examId}`);
            const result = await response.json();
            
            if (result.success) {
                this.config.onStatusUpdate({
                    trustScore: result.trust_score,
                    statusColor: result.status_color,
                    statusText: result.status_text,
                    violationsCount: result.violations_count,
                    lastUpdated: result.last_updated
                });
            }
            
        } catch (error) {
            console.error('Error updating proctoring status:', error);
        }
    }
    
    /**
     * Get CSRF token from form
     */
    getCSRFToken() {
        const csrfToken = document.querySelector('input[name="csrf_token"]');
        return csrfToken ? csrfToken.value : '';
    }
    
    /**
     * Get current statistics
     */
    getStatistics() {
        return {
            ...this.stats,
            violations: this.violationHistory,
            isRunning: this.isRunning,
            sessionDuration: this.isRunning ? Date.now() - this.stats.startTime : 0
        };
    }
    
    /**
     * Stop proctoring session
     */
    stopSession() {
        console.log('Stopping proctoring session...');
        
        this.isRunning = false;
        
        // Stop webcam
        if (this.camera) {
            this.camera.stop();
        }
        
        // Stop voice detection
        if (this.microphone) {
            this.microphone.disconnect();
        }
        if (this.audioContext) {
            this.audioContext.close();
        }
        
        // Clean up DOM elements
        if (this.video) {
            this.video.remove();
        }
        if (this.canvas) {
            this.canvas.remove();
        }
        
        console.log('Proctoring session stopped');
        this.config.onSessionEnd();
    }
    
    /**
     * Check if session is active
     */
    isActiveSession() {
        return this.isRunning;
    }
}

// Export for use in templates
window.AIProctor = AIProctor;
