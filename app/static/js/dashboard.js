/**
 * Real-time Admin Dashboard JavaScript
 * Handles live updates, alerts, and interactive features
 */

class LiveDashboard {
    constructor() {
        this.refreshInterval = 5000; // 5 seconds
        this.currentData = null;
        this.violationSound = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT');
        this.isDarkMode = false;
        this.filters = {
            node: 'all',
            status: 'all',
            trustScore: 'all'
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.startRealTimeUpdates();
        this.initializeFilters();
        this.loadInitialData();
    }
    
    setupEventListeners() {
        // Dark mode toggle
        document.getElementById('darkModeToggle')?.addEventListener('click', () => {
            this.toggleDarkMode();
        });
        
        // Filter controls
        document.getElementById('nodeFilter')?.addEventListener('change', (e) => {
            this.filters.node = e.target.value;
            this.applyFilters();
        });
        
        document.getElementById('statusFilter')?.addEventListener('change', (e) => {
            this.filters.status = e.target.value;
            this.applyFilters();
        });
        
        document.getElementById('trustScoreFilter')?.addEventListener('change', (e) => {
            this.filters.trustScore = e.target.value;
            this.applyFilters();
        });
        
        // Force action buttons
        document.getElementById('terminateExamBtn')?.addEventListener('click', () => {
            this.terminateExam();
        });
        
        document.getElementById('markSuspiciousBtn')?.addEventListener('click', () => {
            this.markSuspicious();
        });
        
        document.getElementById('reassignNodeBtn')?.addEventListener('click', () => {
            this.reassignNode();
        });
    }
    
    async loadInitialData() {
        try {
            const response = await fetch('/api/live_dashboard_data');
            const data = await response.json();
            this.currentData = data;
            this.updateDashboard(data);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load dashboard data');
        }
    }
    
    startRealTimeUpdates() {
        setInterval(async () => {
            try {
                const response = await fetch('/api/live_dashboard_data');
                const data = await response.json();
                
                // Check for new violations
                this.checkForNewViolations(data);
                
                // Update dashboard
                this.currentData = data;
                this.updateDashboard(data);
                
            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }, this.refreshInterval);
    }
    
    checkForNewViolations(newData) {
        if (!this.currentData) return;
        
        const oldViolations = this.currentData.violations || [];
        const newViolations = newData.violations || [];
        
        if (newViolations.length > oldViolations.length) {
            // New violation detected
            const latestViolation = newViolations[newViolations.length - 1];
            this.showViolationAlert(latestViolation);
            this.playAlertSound();
        }
    }
    
    updateDashboard(data) {
        // Update statistics
        this.updateStatistics(data);
        
        // Update student grid
        this.updateStudentGrid(data.students || []);
        
        // Update node distribution
        this.updateNodeDistribution(data.node_distribution || {});
        
        // Update webcam snapshots
        this.updateWebcamSnapshots(data.webcam_snapshots || []);
        
        // Update progress bars
        this.updateProgressBars(data.students || []);
    }
    
    updateStatistics(data) {
        // Update active sessions
        const activeSessionsEl = document.getElementById('activeSessions');
        if (activeSessionsEl) {
            activeSessionsEl.textContent = data.active_sessions || 0;
        }
        
        // Update violations count
        const violationsEl = document.getElementById('violationsCount');
        if (violationsEl) {
            violationsEl.textContent = data.violations?.length || 0;
        }
        
        // Update average trust score
        const avgTrustEl = document.getElementById('avgTrustScore');
        if (avgTrustEl && data.students) {
            const avgScore = data.students.reduce((sum, s) => sum + s.trust_score, 0) / data.students.length;
            avgTrustEl.textContent = avgScore.toFixed(1);
            avgTrustEl.className = this.getTrustScoreClass(avgScore);
        }
    }
    
    updateStudentGrid(students) {
        const gridEl = document.getElementById('studentGrid');
        if (!gridEl) return;
        
        gridEl.innerHTML = '';
        
        students.forEach(student => {
            const card = this.createStudentCard(student);
            gridEl.appendChild(card);
        });
    }
    
    createStudentCard(student) {
        const card = document.createElement('div');
        card.className = 'student-card';
        card.dataset.node = student.node;
        card.dataset.status = student.status;
        card.dataset.trustScore = student.trust_score;
        
        card.innerHTML = `
            <div class="card-header">
                <div class="student-info">
                    <h6 class="mb-0">${student.name}</h6>
                    <small class="text-muted">Node ${student.node}</small>
                </div>
                <div class="student-status">
                    ${this.getStatusBadge(student.status)}
                </div>
            </div>
            <div class="card-body">
                <div class="trust-score-container mb-3">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span>Trust Score</span>
                        <span class="${this.getTrustScoreClass(student.trust_score)}">${student.trust_score}</span>
                    </div>
                    <div class="progress" style="height: 8px;">
                        <div class="progress-bar ${this.getTrustScoreProgressBarClass(student.trust_score)}" 
                             style="width: ${student.trust_score}%"></div>
                    </div>
                </div>
                
                <div class="progress-container mb-3">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span>Progress</span>
                        <span>${student.progress}%</span>
                    </div>
                    <div class="progress" style="height: 6px;">
                        <div class="progress-bar bg-info" style="width: ${student.progress}%"></div>
                    </div>
                </div>
                
                <div class="action-buttons">
                    <button class="btn btn-sm btn-outline-warning" onclick="dashboard.markSuspicious('${student.id}')">
                        <i class="bi bi-exclamation-triangle"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="dashboard.terminateStudent('${student.id}')">
                        <i class="bi bi-x-circle"></i>
                    </button>
                </div>
            </div>
        `;
        
        return card;
    }
    
    getStatusBadge(status) {
        const badges = {
            'active': '<span class="badge bg-success">Active</span>',
            'suspicious': '<span class="badge bg-warning">Suspicious</span>',
            'cheating': '<span class="badge bg-danger">Cheating Detected</span>'
        };
        return badges[status] || '<span class="badge bg-secondary">Unknown</span>';
    }
    
    getTrustScoreClass(score) {
        if (score >= 80) return 'text-success';
        if (score >= 50) return 'text-warning';
        return 'text-danger';
    }
    
    getTrustScoreProgressBarClass(score) {
        if (score >= 80) return 'bg-success';
        if (score >= 50) return 'bg-warning';
        return 'bg-danger';
    }
    
    updateNodeDistribution(distribution) {
        const container = document.getElementById('nodeDistribution');
        if (!container) return;
        
        container.innerHTML = '';
        
        Object.entries(distribution).forEach(([node, count]) => {
            const nodeCard = document.createElement('div');
            nodeCard.className = 'node-card';
            nodeCard.innerHTML = `
                <div class="node-header">
                    <h6 class="mb-0">Node ${node}</h6>
                </div>
                <div class="node-body">
                    <div class="student-count">
                        <span class="count">${count}</span>
                        <span class="label">Students</span>
                    </div>
                    <div class="progress">
                        <div class="progress-bar bg-primary" style="width: ${(count / Math.max(...Object.values(distribution))) * 100}%"></div>
                    </div>
                </div>
            `;
            container.appendChild(nodeCard);
        });
    }
    
    updateWebcamSnapshots(snapshots) {
        const gridEl = document.getElementById('webcamGrid');
        if (!gridEl) return;
        
        gridEl.innerHTML = '';
        
        snapshots.forEach(snapshot => {
            const snapshotCard = document.createElement('div');
            snapshotCard.className = 'webcam-snapshot';
            snapshotCard.innerHTML = `
                <div class="snapshot-header">
                    <span class="student-name">${snapshot.student_name}</span>
                    <span class="timestamp">${new Date(snapshot.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="snapshot-image">
                    <img src="${snapshot.image_url}" alt="${snapshot.student_name}" class="img-fluid">
                </div>
                <div class="snapshot-status">
                    ${this.getStatusBadge(snapshot.status)}
                </div>
            `;
            gridEl.appendChild(snapshotCard);
        });
    }
    
    updateProgressBars(students) {
        students.forEach(student => {
            const progressEl = document.getElementById(`progress-${student.id}`);
            if (progressEl) {
                progressEl.style.width = `${student.progress}%`;
                progressEl.setAttribute('aria-valuenow', student.progress);
            }
        });
    }
    
    showViolationAlert(violation) {
        const toast = document.createElement('div');
        toast.className = 'toast violation-toast show';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="toast-header bg-danger text-white">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong class="me-auto">Violation Detected</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                <strong>${violation.student_name}</strong> - ${violation.violation_type}
                <div class="mt-1">
                    <small class="text-muted">${new Date(violation.timestamp).toLocaleString()}</small>
                </div>
            </div>
        `;
        
        const container = document.getElementById('toastContainer');
        if (container) {
            container.appendChild(toast);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 5000);
        }
    }
    
    playAlertSound() {
        try {
            this.violationSound.play().catch(e => console.log('Could not play alert sound:', e));
        } catch (error) {
            console.log('Alert sound not available:', error);
        }
    }
    
    applyFilters() {
        const cards = document.querySelectorAll('.student-card');
        
        cards.forEach(card => {
            const node = card.dataset.node;
            const status = card.dataset.status;
            const trustScore = parseInt(card.dataset.trustScore);
            
            let show = true;
            
            // Node filter
            if (this.filters.node !== 'all' && node !== this.filters.node) {
                show = false;
            }
            
            // Status filter
            if (this.filters.status !== 'all' && status !== this.filters.status) {
                show = false;
            }
            
            // Trust score filter
            if (this.filters.trustScore !== 'all') {
                if (this.filters.trustScore === 'high' && trustScore < 80) show = false;
                if (this.filters.trustScore === 'medium' && (trustScore < 50 || trustScore >= 80)) show = false;
                if (this.filters.trustScore === 'low' && trustScore >= 50) show = false;
            }
            
            card.style.display = show ? 'block' : 'none';
        });
    }
    
    initializeFilters() {
        // Set up filter event listeners
        const filterSelects = document.querySelectorAll('.filter-select');
        filterSelects.forEach(select => {
            select.addEventListener('change', () => this.applyFilters());
        });
    }
    
    toggleDarkMode() {
        this.isDarkMode = !this.isDarkMode;
        document.body.classList.toggle('dark-mode', this.isDarkMode);
        
        const toggle = document.getElementById('darkModeToggle');
        if (toggle) {
            toggle.innerHTML = this.isDarkMode ? 
                '<i class="bi bi-moon-fill"></i>' : 
                '<i class="bi bi-sun-fill"></i>';
        }
    }
    
    async terminateExam() {
        if (confirm('Are you sure you want to terminate all active exams?')) {
            try {
                const response = await fetch('/api/terminate_all_exams', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    }
                });
                
                if (response.ok) {
                    this.showSuccess('All exams terminated successfully');
                } else {
                    this.showError('Failed to terminate exams');
                }
            } catch (error) {
                this.showError('Error terminating exams');
            }
        }
    }
    
    async markSuspicious(studentId = null) {
        try {
            const response = await fetch('/api/mark_suspicious', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ student_id: studentId })
            });
            
            if (response.ok) {
                this.showSuccess('Student marked as suspicious');
            } else {
                this.showError('Failed to mark student as suspicious');
            }
        } catch (error) {
            this.showError('Error marking student as suspicious');
        }
    }
    
    async reassignNode() {
        const studentId = prompt('Enter student ID to reassign:');
        const newNode = prompt('Enter new node (A, B, C):');
        
        if (studentId && newNode) {
            try {
                const response = await fetch('/api/reassign_node', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({ 
                        student_id: studentId, 
                        new_node: newNode.toUpperCase() 
                    })
                });
                
                if (response.ok) {
                    this.showSuccess('Student reassigned successfully');
                } else {
                    this.showError('Failed to reassign student');
                }
            } catch (error) {
                this.showError('Error reassigning student');
            }
        }
    }
    
    async terminateStudent(studentId) {
        if (confirm(`Are you sure you want to terminate this student's exam?`)) {
            try {
                const response = await fetch('/api/terminate_student', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({ student_id: studentId })
                });
                
                if (response.ok) {
                    this.showSuccess('Student exam terminated');
                } else {
                    this.showError('Failed to terminate student exam');
                }
            } catch (error) {
                this.showError('Error terminating student exam');
            }
        }
    }
    
    getCSRFToken() {
        const token = document.querySelector('input[name="csrf_token"], meta[name="csrf-token"]');
        return token ? token.value || token.getAttribute('content') : '';
    }
    
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    showError(message) {
        this.showToast(message, 'danger');
    }
    
    showToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast show ${type}`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="toast-header bg-${type} text-white">
                <strong class="me-auto">${type === 'success' ? 'Success' : 'Error'}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        const container = document.getElementById('toastContainer');
        if (container) {
            container.appendChild(toast);
            
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 3000);
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.dashboard = new LiveDashboard();
});

// Export for use in other scripts
window.LiveDashboard = LiveDashboard;
