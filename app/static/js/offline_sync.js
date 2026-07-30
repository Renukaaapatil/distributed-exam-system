/**
 * Offline Mode + Sync System for Online Exam Platform
 * Handles offline detection, local storage, and automatic synchronization
 */

class OfflineSyncManager {
    constructor(options = {}) {
        this.isOnline = navigator.onLine;
        this.isSyncing = false;
        this.autoSaveInterval = options.autoSaveInterval || 5000; // 5 seconds
        this.syncRetryInterval = options.syncRetryInterval || 10000; // 10 seconds
        this.maxRetries = options.maxRetries || 3;
        
        // Storage keys
        this.storageKeys = {
            examAnswers: 'exam_answers',
            examMetadata: 'exam_metadata',
            syncQueue: 'sync_queue',
            lastSync: 'last_sync_timestamp',
            offlineMode: 'offline_mode_active'
        };
        
        // Event callbacks
        this.callbacks = {
            onOnline: options.onOnline || (() => {}),
            onOffline: options.onOffline || (() => {}),
            onSyncStart: options.onSyncStart || (() => {}),
            onSyncComplete: options.onSyncComplete || (() => {}),
            onSyncError: options.onSyncError || (() => {}),
            onAutoSave: options.onAutoSave || (() => {})
        };
        
        this.init();
    }
    
    init() {
        console.log('Initializing Offline Sync Manager...');
        
        // Set up online/offline event listeners
        this.setupConnectivityListeners();
        
        // Start auto-save interval
        this.startAutoSave();
        
        // Check for pending sync on load
        this.checkPendingSync();
        
        // Update initial status
        this.updateStatus();
        
        console.log('Offline Sync Manager initialized');
    }
    
    setupConnectivityListeners() {
        // Listen for online/offline events
        window.addEventListener('online', () => {
            this.handleOnlineEvent();
        });
        
        window.addEventListener('offline', () => {
            this.handleOfflineEvent();
        });
        
        // Listen for page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.isOnline) {
                this.checkPendingSync();
            }
        });
        
        // Listen for page unload to save current state
        window.addEventListener('beforeunload', () => {
            this.saveCurrentState();
        });
    }
    
    handleOnlineEvent() {
        console.log('Connection restored - Coming back online');
        this.isOnline = true;
        this.updateStatus();
        
        // Clear offline mode flag
        localStorage.removeItem(this.storageKeys.offlineMode);
        
        // Attempt to sync pending data
        this.checkPendingSync();
        
        // Trigger callback
        this.callbacks.onOnline();
    }
    
    handleOfflineEvent() {
        console.log('Connection lost - Entering offline mode');
        this.isOnline = false;
        this.updateStatus();
        
        // Set offline mode flag
        localStorage.setItem(this.storageKeys.offlineMode, 'true');
        
        // Trigger callback
        this.callbacks.onOffline();
    }
    
    // Local Storage Methods
    saveExamAnswers(examId, answers) {
        try {
            const data = {
                examId: examId,
                answers: answers,
                timestamp: new Date().toISOString(),
                version: '1.0'
            };
            
            localStorage.setItem(this.storageKeys.examAnswers, JSON.stringify(data));
            console.log('Exam answers saved locally');
            
            // Add to sync queue if offline
            if (!this.isOnline) {
                this.addToSyncQueue('exam_answers', data);
            }
            
            return true;
        } catch (error) {
            console.error('Failed to save exam answers:', error);
            return false;
        }
    }
    
    loadExamAnswers() {
        try {
            const saved = localStorage.getItem(this.storageKeys.examAnswers);
            if (saved) {
                const data = JSON.parse(saved);
                console.log('Loaded saved exam answers from', data.timestamp);
                return data;
            }
            return null;
        } catch (error) {
            console.error('Failed to load exam answers:', error);
            return null;
        }
    }
    
    saveExamMetadata(examId, metadata) {
        try {
            const data = {
                examId: examId,
                metadata: metadata,
                timestamp: new Date().toISOString()
            };
            
            localStorage.setItem(this.storageKeys.examMetadata, JSON.stringify(data));
            console.log('Exam metadata saved locally');
            
            return true;
        } catch (error) {
            console.error('Failed to save exam metadata:', error);
            return false;
        }
    }
    
    loadExamMetadata() {
        try {
            const saved = localStorage.getItem(this.storageKeys.examMetadata);
            if (saved) {
                return JSON.parse(saved);
            }
            return null;
        } catch (error) {
            console.error('Failed to load exam metadata:', error);
            return null;
        }
    }
    
    // Sync Queue Management
    addToSyncQueue(type, data) {
        try {
            const queue = this.getSyncQueue();
            const syncItem = {
                id: this.generateId(),
                type: type,
                data: data,
                timestamp: new Date().toISOString(),
                retries: 0
            };
            
            queue.push(syncItem);
            localStorage.setItem(this.storageKeys.syncQueue, JSON.stringify(queue));
            
            console.log('Added item to sync queue:', syncItem.id);
            return syncItem.id;
        } catch (error) {
            console.error('Failed to add to sync queue:', error);
            return null;
        }
    }
    
    getSyncQueue() {
        try {
            const queue = localStorage.getItem(this.storageKeys.syncQueue);
            return queue ? JSON.parse(queue) : [];
        } catch (error) {
            console.error('Failed to get sync queue:', error);
            return [];
        }
    }
    
    removeFromSyncQueue(itemId) {
        try {
            const queue = this.getSyncQueue();
            const updatedQueue = queue.filter(item => item.id !== itemId);
            localStorage.setItem(this.storageKeys.syncQueue, JSON.stringify(updatedQueue));
            return true;
        } catch (error) {
            console.error('Failed to remove from sync queue:', error);
            return false;
        }
    }
    
    // Auto-save functionality
    startAutoSave() {
        setInterval(() => {
            this.performAutoSave();
        }, this.autoSaveInterval);
        
        console.log(`Auto-save started: every ${this.autoSaveInterval}ms`);
    }
    
    performAutoSave() {
        try {
            // Get current form data
            const currentAnswers = this.getCurrentFormAnswers();
            
            if (currentAnswers && Object.keys(currentAnswers).length > 0) {
                const examId = this.getCurrentExamId();
                
                if (examId) {
                    this.saveExamAnswers(examId, currentAnswers);
                    this.callbacks.onAutoSave(currentAnswers);
                }
            }
        } catch (error) {
            console.error('Auto-save failed:', error);
        }
    }
    
    getCurrentFormAnswers() {
        const answers = {};
        
        // Get all radio button answers
        const radioInputs = document.querySelectorAll('input[type="radio"]:checked');
        radioInputs.forEach(input => {
            const questionId = this.extractQuestionId(input.name);
            if (questionId) {
                answers[questionId] = input.value;
            }
        });
        
        // Get all text input answers
        const textInputs = document.querySelectorAll('input[type="text"], textarea');
        textInputs.forEach(input => {
            const questionId = this.extractQuestionId(input.name);
            if (questionId && input.value) {
                answers[questionId] = input.value;
            }
        });
        
        return answers;
    }
    
    getCurrentExamId() {
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
    
    extractQuestionId(inputName) {
        // Handle patterns like "question_1", "q_1", etc.
        const match = inputName.match(/(?:question|q)[_\-](\d+)/);
        return match ? match[1] : inputName;
    }
    
    // Sync functionality
    async checkPendingSync() {
        if (!this.isOnline || this.isSyncing) {
            return;
        }
        
        const queue = this.getSyncQueue();
        if (queue.length === 0) {
            return;
        }
        
        console.log(`Found ${queue.length} items in sync queue`);
        await this.processSyncQueue();
    }
    
    async processSyncQueue() {
        if (this.isSyncing) {
            return;
        }
        
        this.isSyncing = true;
        this.updateStatus();
        this.callbacks.onSyncStart();
        
        const queue = this.getSyncQueue();
        const results = [];
        
        for (const item of queue) {
            try {
                const result = await this.syncItemToServer(item);
                results.push(result);
                
                if (result.success) {
                    this.removeFromSyncQueue(item.id);
                    console.log(`Successfully synced item: ${item.id}`);
                } else {
                    // Update retry count
                    item.retries++;
                    if (item.retries >= this.maxRetries) {
                        console.error(`Max retries exceeded for item: ${item.id}`);
                        this.removeFromSyncQueue(item.id);
                    }
                }
                
                // Small delay between syncs
                await this.delay(100);
                
            } catch (error) {
                console.error(`Error syncing item ${item.id}:`, error);
                results.push({ success: false, error: error.message });
            }
        }
        
        this.isSyncing = false;
        this.updateStatus();
        
        // Check if all items were synced successfully
        const successfulSyncs = results.filter(r => r.success).length;
        const totalItems = results.length;
        
        if (successfulSyncs === totalItems && totalItems > 0) {
            this.updateLastSyncTimestamp();
            console.log('All pending items synced successfully');
        }
        
        this.callbacks.onSyncComplete({
            total: totalItems,
            successful: successfulSyncs,
            failed: totalItems - successfulSyncs
        });
    }
    
    async syncItemToServer(item) {
        try {
            const response = await fetch('/sync_exam', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    type: item.type,
                    data: item.data,
                    timestamp: item.timestamp
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                return { success: true, data: result };
            } else {
                return { success: false, error: `HTTP ${response.status}` };
            }
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    // Manual sync trigger
    async manualSync() {
        if (!this.isOnline) {
            console.log('Cannot sync: offline');
            return false;
        }
        
        await this.checkPendingSync();
        return true;
    }
    
    // Status and UI updates
    updateStatus() {
        const statusElement = document.getElementById('connectionStatus');
        if (!statusElement) {
            return;
        }
        
        let status, className, icon;
        
        if (this.isSyncing) {
            status = 'Syncing...';
            className = 'syncing';
            icon = 'bi-arrow-repeat';
        } else if (this.isOnline) {
            status = 'Online';
            className = 'online';
            icon = 'bi-wifi';
        } else {
            status = 'Offline';
            className = 'offline';
            icon = 'bi-wifi-off';
        }
        
        statusElement.className = `connection-status ${className}`;
        statusElement.innerHTML = `
            <i class="bi ${icon} me-1"></i>
            ${status}
        `;
        
        // Update submit button state
        this.updateSubmitButtonState();
    }
    
    updateSubmitButtonState() {
        const submitBtn = document.getElementById('submitBtn');
        if (!submitBtn) {
            return;
        }
        
        if (!this.isOnline) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `
                <i class="bi bi-wifi-off me-2"></i>
                Offline - Answers Saved Locally
            `;
        } else {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `
                <i class="bi bi-check-circle me-2"></i>
                Submit Exam
            `;
        }
    }
    
    // Utility methods
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    getCSRFToken() {
        const token = document.querySelector('input[name="csrf_token"], meta[name="csrf-token"]');
        return token ? token.value || token.getAttribute('content') : '';
    }
    
    updateLastSyncTimestamp() {
        localStorage.setItem(this.storageKeys.lastSync, new Date().toISOString());
    }
    
    getLastSyncTimestamp() {
        return localStorage.getItem(this.storageKeys.lastSync);
    }
    
    saveCurrentState() {
        // Save current state before page unload
        this.performAutoSave();
    }
    
    // Public API methods
    isOfflineMode() {
        return !this.isOnline;
    }
    
    getPendingSyncCount() {
        return this.getSyncQueue().length;
    }
    
    clearLocalData() {
        // Clear all local storage data
        Object.values(this.storageKeys).forEach(key => {
            localStorage.removeItem(key);
        });
        console.log('Local data cleared');
    }
    
    getStorageStats() {
        const stats = {};
        
        Object.entries(this.storageKeys).forEach(([name, key]) => {
            const item = localStorage.getItem(key);
            stats[name] = {
                exists: !!item,
                size: item ? item.length : 0,
                lastModified: null
            };
        });
        
        return stats;
    }
}

// Initialize offline sync manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on exam pages
    if (document.querySelector('.exam-container, #examForm, .adaptive-exam')) {
        window.offlineSync = new OfflineSyncManager({
            onOnline: () => {
                console.log('Back online - checking for pending sync');
            },
            onOffline: () => {
                console.log('Gone offline - answers will be saved locally');
            },
            onSyncStart: () => {
                console.log('Sync started');
            },
            onSyncComplete: (result) => {
                console.log('Sync completed:', result);
            },
            onAutoSave: (answers) => {
                console.log('Auto-saved', Object.keys(answers).length, 'answers');
            }
        });
        
        console.log('Offline Sync Manager initialized for exam page');
    }
});

// Export for use in other scripts
window.OfflineSyncManager = OfflineSyncManager;
