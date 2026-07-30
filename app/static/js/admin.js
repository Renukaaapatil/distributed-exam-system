/**
 * Live Exam Monitoring Dashboard JavaScript
 * Handles real-time updates and monitoring functionality
 */

class AdminDashboard {
    constructor() {
        this.refreshInterval = null;
        this.currentSessions = [];
        this.currentViolations = [];
        this.currentSnapshots = [];
        this.refreshRate = 3000; // 3 seconds
        
        this.init();
    }
    
    init() {
        console.log('Initializing Live Exam Monitoring Dashboard...');
        
        // Start auto-refresh
        this.startAutoRefresh();
        
        // Initial data load
        this.refreshDashboard();
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('Admin Dashboard initialized successfully');
    }
    
    startAutoRefresh() {
        // Clear existing interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        // Start new interval
        this.refreshInterval = setInterval(() => {
            this.refreshDashboard();
        }, this.refreshRate);
        
        console.log(`Auto-refresh started (${this.refreshRate}ms interval)`);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            console.log('Auto-refresh stopped');
        }
    }
    
    async refreshDashboard() {
        try {
            this.showRefreshIndicator();
            
            // Fetch all data in parallel
            const [sessions, violations, statistics] = await Promise.all([
                this.fetchSessions(),
                this.fetchViolations(),
                this.fetchStatistics()
            ]);
            
            // Update UI
            this.updateSessionsTable(sessions);
            this.updateViolationsFeed(violations);
            this.updateStatisticsCards(statistics);
            this.updateLastUpdated();
            
            // Update session filter for snapshots
            this.updateSessionFilter(sessions);
            
        } catch (error) {
            console.error('Dashboard refresh error:', error);
        } finally {
            this.hideRefreshIndicator();
        }
    }
    
    showRefreshIndicator() {
        const indicator = document.getElementById('refreshIndicator');
        if (indicator) {
            indicator.style.display = 'block';
        }
    }
    
    hideRefreshIndicator() {
        const indicator = document.getElementById('refreshIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
    
    updateLastUpdated() {
        const element = document.getElementById('lastUpdated');
        if (element) {
            const now = new Date();
            element.textContent = `Last updated: ${now.toLocaleTimeString()}`;
        }
    }
    
    async fetchSessions() {
        try {
            const response = await fetch('/admin/live_sessions');
            const data = await response.json();
            
            if (data.success) {
                this.currentSessions = data.sessions;
                return data.sessions;
            } else {
                console.error('Failed to fetch sessions:', data.error);
                return [];
            }
        } catch (error) {
            console.error('Failed to fetch sessions:', error);
            return [];
        }
    }
    
    async fetchViolations() {
        try {
            const response = await fetch('/admin/violations');
            const data = await response.json();
            
            if (data.success) {
                this.currentViolations = data.violations;
                return data.violations;
            } else {
                console.error('Failed to fetch violations:', data.error);
                return [];
            }
        } catch (error) {
            console.error('Failed to fetch violations:', error);
            return [];
        }
    }
    
    async fetchStatistics() {
        try {
            const response = await fetch('/admin/statistics');
            const data = await response.json();
            
            if (data.success) {
                return data.statistics;
            } else {
                console.error('Failed to fetch statistics:', data.error);
                return {};
            }
        } catch (error) {
            console.error('Failed to fetch statistics:', error);
            return {};
        }
    }
    
    updateSessionsTable(sessions) {
        const tbody = document.getElementById('sessionsTableBody');
        if (!tbody) return;
        
        if (sessions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        No active sessions found
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = sessions.map(session => {
            const trustScoreClass = this.getTrustScoreClass(session.trust_score);
            const rowClass = session.trust_score < 50 ? 'high-risk' : '';
            
            return `
                <tr class="${rowClass}">
                    <td>
                        <div class="d-flex align-items-center">
                            <div>
                                <strong>${this.escapeHtml(session.user_name)}</strong>
                                <br>
                                <small class="text-muted">${this.escapeHtml(session.user_email)}</small>
                            </div>
                        </div>
                    </td>
                    <td>
                        <div>
                            <strong>${this.escapeHtml(session.exam_title)}</strong>
                            <br>
                            <small class="text-muted">Q${session.current_question}/${session.answers_count + 1}</small>
                        </div>
                    </td>
                    <td class="trust-score-cell">
                        <span class="trust-score-badge ${trustScoreClass}">
                            ${session.trust_score}
                        </span>
                        ${session.trust_score < 50 ? '<br><small class="text-danger">High Risk</small>' : ''}
                    </td>
                    <td>
                        <span class="node-badge bg-info text-white">
                            Node ${session.node_id}
                        </span>
                    </td>
                    <td>
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar bg-${trustScoreClass}" 
                                 style="width: ${(session.answers_count / (session.answers_count + 1)) * 100}%">
                                ${session.answers_count} answered
                            </div>
                        </div>
                        <small class="text-muted">${this.formatTime(session.remaining_time)} left</small>
                    </td>
                    <td>
                        <span class="badge bg-${trustScoreClass}">
                            ${session.status_text}
                        </span>
                        ${session.recent_violations > 0 ? `<br><small class="text-warning">${session.recent_violations} violations</small>` : ''}
                    </td>
                </tr>
            `;
        }).join('');
    }
    
    updateViolationsFeed(violations) {
        const feed = document.getElementById('violationsFeed');
        const countBadge = document.getElementById('violationsCount');
        
        if (!feed) return;
        
        if (countBadge) {
            countBadge.textContent = violations.length;
        }
        
        if (violations.length === 0) {
            feed.innerHTML = `
                <div class="text-center text-muted py-4">
                    No recent violations
                </div>
            `;
            return;
        }
        
        feed.innerHTML = violations.map(violation => {
            const alertClass = this.getViolationAlertClass(violation.severity);
            
            return `
                <div class="alert-item ${alertClass}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong>${this.escapeHtml(violation.user_name)}</strong>
                            <span class="violation-type ms-2">${violation.violation_type}</span>
                            <br>
                            <small>${this.escapeHtml(violation.exam_title)}</small>
                            <br>
                            <small class="text-muted">${this.escapeHtml(violation.details)}</small>
                        </div>
                        <div class="text-end">
                            <small class="time-ago">${violation.time_ago}</small>
                            <br>
                            <small class="text-muted">
                                ${violation.trust_score_before} &rarr; ${violation.trust_score_after}
                            </small>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    updateStatisticsCards(stats) {
        const elements = {
            'activeSessionsCount': stats.active_sessions || 0,
            'recentViolationsCount': stats.recent_violations || 0,
            'safeStudentsCount': (stats.trust_score_distribution && stats.trust_score_distribution.safe) || 0,
            'riskStudentsCount': (stats.trust_score_distribution && stats.trust_score_distribution.risk) || 0
        };
        
        Object.keys(elements).forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = elements[id];
            }
        });
    }
    
    updateSessionFilter(sessions) {
        const filter = document.getElementById('snapshotSessionFilter');
        if (!filter) return;
        
        const currentValue = filter.value;
        
        filter.innerHTML = '<option value="">All Sessions</option>' +
            sessions.map(session => 
                `<option value="${session.session_id}">${this.escapeHtml(session.user_name)} - ${this.escapeHtml(session.exam_title)}</option>`
            ).join('');
        
        filter.value = currentValue;
    }
    
    getTrustScoreClass(score) {
        if (score >= 80) return 'trust-score-high';
        if (score >= 50) return 'trust-score-medium';
        return 'trust-score-low';
    }
    
    getViolationAlertClass(severity) {
        switch (severity) {
            case 'critical':
            case 'high':
                return 'critical';
            case 'medium':
                return 'warning';
            case 'low':
                return 'info';
            default:
                return 'info';
        }
    }
    
    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    setupEventListeners() {
        // Session filter change
        const sessionFilter = document.getElementById('snapshotSessionFilter');
        if (sessionFilter) {
            sessionFilter.addEventListener('change', () => {
                this.refreshSnapshots();
            });
        }
        
        // Refresh buttons
        const refreshSessionsBtn = document.querySelector('[onclick="refreshSessions()"]');
        if (refreshSessionsBtn) {
            refreshSessionsBtn.addEventListener('click', () => {
                this.refreshSessions();
            });
        }
        
        const refreshSnapshotsBtn = document.querySelector('[onclick="refreshSnapshots()"]');
        if (refreshSnapshotsBtn) {
            refreshSnapshotsBtn.addEventListener('click', () => {
                this.refreshSnapshots();
            });
        }
    }
    
    async refreshSessions() {
        const sessions = await this.fetchSessions();
        this.updateSessionsTable(sessions);
        this.updateSessionFilter(sessions);
    }
    
    async refreshSnapshots() {
        const sessionId = document.getElementById('snapshotSessionFilter')?.value;
        await this.loadSnapshots(sessionId);
    }
    
    async loadSnapshots(sessionId = null) {
        try {
            const url = sessionId ? `/admin/snapshots/${sessionId}` : '/admin/snapshots/all';
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                this.updateSnapshotsGrid(data.snapshots);
            } else {
                console.error('Failed to fetch snapshots:', data.error);
            }
        } catch (error) {
            console.error('Failed to fetch snapshots:', error);
        }
    }
    
    updateSnapshotsGrid(snapshots) {
        const grid = document.getElementById('snapshotsGrid');
        if (!grid) return;
        
        if (snapshots.length === 0) {
            grid.innerHTML = `
                <div class="text-center text-muted w-100 py-4">
                    No snapshots available
                </div>
            `;
            return;
        }
        
        grid.innerHTML = snapshots.map(snapshot => {
            const violationClass = snapshot.violation_detected ? 'snapshot-violation' : '';
            
            return `
                <div class="snapshot-item ${violationClass}">
                    <img src="${snapshot.image_url}" alt="Snapshot" 
                         onerror="this.src='/static/images/no-image.png'">
                    <div class="snapshot-overlay">
                        ${snapshot.violation_detected ? 'VIOLATION' : 'Normal'}
                        <br>
                        <small>${snapshot.time_ago}</small>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    setRefreshRate(rate) {
        this.refreshRate = Math.max(1000, rate); // Minimum 1 second
        this.startAutoRefresh();
        console.log(`Refresh rate set to ${this.refreshRate}ms`);
    }
    
    destroy() {
        this.stopAutoRefresh();
        console.log('Admin Dashboard destroyed');
    }
}

// Global functions for backward compatibility
window.refreshSessions = function() {
    if (window.adminDashboard) {
        window.adminDashboard.refreshSessions();
    }
};

window.refreshSnapshots = function() {
    if (window.adminDashboard) {
        window.adminDashboard.refreshSnapshots();
    }
};

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.adminDashboard = new AdminDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.adminDashboard) {
        window.adminDashboard.destroy();
    }
});

// Export for use in other scripts
window.AdminDashboard = AdminDashboard;
