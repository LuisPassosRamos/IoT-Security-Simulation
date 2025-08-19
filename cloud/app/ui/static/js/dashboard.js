/**
 * Dashboard JavaScript - Main application logic
 */

class Dashboard {
    constructor() {
        this.currentSection = 'dashboard';
        this.authToken = localStorage.getItem('authToken');
        this.refreshInterval = null;
        this.charts = {};
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupNavigation();
        this.loadInitialData();
        this.startAutoRefresh();
    }
    
    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = e.target.getAttribute('href').substring(1);
                this.showSection(section);
            });
        });
        
        // Time range controls
        document.querySelectorAll('input[name="timeRange"]').forEach(radio => {
            radio.addEventListener('change', () => {
                this.updateCharts();
            });
        });
        
        // Filter controls
        const alertFilter = document.getElementById('alert-filter');
        if (alertFilter) {
            alertFilter.addEventListener('change', () => {
                this.loadAlerts();
            });
        }
        
        const eventFilter = document.getElementById('event-filter');
        if (eventFilter) {
            eventFilter.addEventListener('change', () => {
                this.loadEvents();
            });
        }
        
        // Refresh button
        window.refreshData = () => {
            this.loadCurrentSectionData();
        };
        
        // Logout
        window.logout = () => {
            this.logout();
        };
    }
    
    setupNavigation() {
        // Set initial active nav
        this.updateActiveNav('dashboard');
    }
    
    showSection(section) {
        // Hide all sections
        document.querySelectorAll('.content-section').forEach(sec => {
            sec.classList.add('d-none');
        });
        
        // Show target section
        const targetSection = document.getElementById(`${section}-section`);
        if (targetSection) {
            targetSection.classList.remove('d-none');
            this.currentSection = section;
            this.updateActiveNav(section);
            this.loadCurrentSectionData();
        }
    }
    
    updateActiveNav(section) {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        const activeLink = document.getElementById(`nav-${section}`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
    }
    
    loadCurrentSectionData() {
        switch (this.currentSection) {
            case 'dashboard':
                this.loadDashboardData();
                break;
            case 'sensors':
                this.loadSensors();
                break;
            case 'alerts':
                this.loadAlerts();
                break;
            case 'events':
                this.loadEvents();
                break;
            case 'security':
                // Security demo is handled separately
                break;
        }
    }
    
    async loadDashboardData() {
        try {
            await Promise.all([
                this.loadStats(),
                this.loadRecentAlerts(),
                this.loadRecentEvents()
            ]);
            
            this.updateCharts();
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showError('Failed to load dashboard data');
        }
    }
    
    async loadStats() {
        try {
            const response = await this.apiCall('/api/readings/summary');
            const data = await response.json();
            
            document.getElementById('stat-sensors').textContent = data.active_sensors || 0;
            document.getElementById('stat-readings').textContent = data.total_readings || 0;
            document.getElementById('stat-alerts').textContent = data.total_alerts || 0;
            
            // Get security events count
            const securityResponse = await this.apiCall('/api/events/count?severity=error&hours=24');
            const securityData = await securityResponse.json();
            document.getElementById('stat-security').textContent = securityData.count || 0;
            
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    async loadRecentAlerts() {
        try {
            const response = await this.apiCall('/api/alerts?limit=5&acknowledged=false');
            const alerts = await response.json();
            
            const container = document.getElementById('recent-alerts');
            if (alerts.length === 0) {
                container.innerHTML = '<div class="text-muted p-3">No recent alerts</div>';
                return;
            }
            
            container.innerHTML = alerts.map(alert => this.renderAlertItem(alert)).join('');
            
        } catch (error) {
            console.error('Error loading recent alerts:', error);
        }
    }
    
    async loadRecentEvents() {
        try {
            const response = await this.apiCall('/api/events?limit=5');
            const events = await response.json();
            
            const container = document.getElementById('recent-events');
            if (events.length === 0) {
                container.innerHTML = '<div class="text-muted p-3">No recent events</div>';
                return;
            }
            
            container.innerHTML = events.map(event => this.renderEventItem(event)).join('');
            
        } catch (error) {
            console.error('Error loading recent events:', error);
        }
    }
    
    async loadSensors() {
        try {
            const response = await this.apiCall('/api/readings/summary');
            const data = await response.json();
            
            const container = document.getElementById('sensors-grid');
            if (!data.sensors || data.sensors.length === 0) {
                container.innerHTML = '<div class="col-12"><div class="text-muted p-3">No sensors found</div></div>';
                return;
            }
            
            container.innerHTML = data.sensors.map(sensor => this.renderSensorCard(sensor)).join('');
            
        } catch (error) {
            console.error('Error loading sensors:', error);
            this.showError('Failed to load sensors');
        }
    }
    
    async loadAlerts() {
        try {
            const filter = document.getElementById('alert-filter')?.value || '';
            const url = filter ? `/api/alerts?severity=${filter}&limit=50` : '/api/alerts?limit=50';
            
            const response = await this.apiCall(url);
            const alerts = await response.json();
            
            const container = document.getElementById('alerts-table-container');
            if (alerts.length === 0) {
                container.innerHTML = '<div class="text-muted p-3">No alerts found</div>';
                return;
            }
            
            container.innerHTML = this.renderAlertsTable(alerts);
            
        } catch (error) {
            console.error('Error loading alerts:', error);
            this.showError('Failed to load alerts');
        }
    }
    
    async loadEvents() {
        try {
            const filter = document.getElementById('event-filter')?.value || '';
            const url = filter ? `/api/events?event_type=${filter}&limit=50` : '/api/events?limit=50';
            
            const response = await this.apiCall(url);
            const events = await response.json();
            
            const container = document.getElementById('events-table-container');
            if (events.length === 0) {
                container.innerHTML = '<div class="text-muted p-3">No events found</div>';
                return;
            }
            
            container.innerHTML = this.renderEventsTable(events);
            
        } catch (error) {
            console.error('Error loading events:', error);
            this.showError('Failed to load events');
        }
    }
    
    renderAlertItem(alert) {
        const timeAgo = this.timeAgo(new Date(alert.created_at));
        const severityClass = `severity-${alert.severity}`;
        
        return `
            <div class="list-group-item alert-item ${alert.severity} p-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${alert.title}</h6>
                        <p class="mb-1 text-muted small">${alert.message}</p>
                        <small class="text-muted">
                            <i class="fas fa-microchip me-1"></i>${alert.sensor_id} • ${timeAgo}
                        </small>
                    </div>
                    <span class="badge ${severityClass}">${alert.severity.toUpperCase()}</span>
                </div>
            </div>
        `;
    }
    
    renderEventItem(event) {
        const timeAgo = this.timeAgo(new Date(event.created_at));
        
        return `
            <div class="list-group-item event-item ${event.severity} p-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${event.title}</h6>
                        <p class="mb-1 text-muted small">${event.message}</p>
                        <small class="text-muted">
                            ${event.sensor_id ? `<i class="fas fa-microchip me-1"></i>${event.sensor_id} • ` : ''}
                            ${timeAgo}
                        </small>
                    </div>
                    <span class="badge bg-secondary">${event.event_type}</span>
                </div>
            </div>
        `;
    }
    
    renderSensorCard(sensor) {
        const isOnline = sensor.last_reading_time && 
            (new Date() - new Date(sensor.last_reading_time)) < 300000; // 5 minutes
        
        const statusClass = isOnline ? 'online' : 'offline';
        const statusText = isOnline ? 'Online' : 'Offline';
        const lastReading = sensor.last_reading_value !== null ? 
            `${sensor.last_reading_value} ${this.getSensorUnit(sensor.sensor_type)}` : 'No data';
        
        return `
            <div class="col-md-4 mb-3">
                <div class="card sensor-card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="card-title mb-0">${sensor.name}</h6>
                            <span class="status-indicator ${isOnline ? 'secure' : 'insecure'}">
                                <span class="sensor-status ${statusClass}"></span>
                                ${statusText}
                            </span>
                        </div>
                        <p class="card-text text-muted">${sensor.sensor_type}</p>
                        <div class="row text-center">
                            <div class="col-6">
                                <strong>${lastReading}</strong>
                                <div class="small text-muted">Last Reading</div>
                            </div>
                            <div class="col-6">
                                <strong>${sensor.reading_count_24h}</strong>
                                <div class="small text-muted">24h Readings</div>
                            </div>
                        </div>
                        ${sensor.alert_count_24h > 0 ? 
                            `<div class="mt-2">
                                <span class="badge bg-warning">${sensor.alert_count_24h} alerts today</span>
                            </div>` : ''
                        }
                    </div>
                </div>
            </div>
        `;
    }
    
    renderAlertsTable(alerts) {
        const rows = alerts.map(alert => {
            const timeAgo = this.timeAgo(new Date(alert.created_at));
            const severityBadge = `<span class="badge severity-${alert.severity}">${alert.severity.toUpperCase()}</span>`;
            const statusBadge = alert.is_acknowledged ? 
                '<span class="badge bg-success">Acknowledged</span>' : 
                '<span class="badge bg-warning">Pending</span>';
            
            return `
                <tr>
                    <td>${alert.sensor_id}</td>
                    <td>${alert.title}</td>
                    <td>${severityBadge}</td>
                    <td>${statusBadge}</td>
                    <td>${timeAgo}</td>
                    <td>
                        ${!alert.is_acknowledged ? 
                            `<button class="btn btn-sm btn-outline-primary" onclick="dashboard.acknowledgeAlert(${alert.id})">
                                Acknowledge
                            </button>` : ''
                        }
                    </td>
                </tr>
            `;
        }).join('');
        
        return `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Sensor</th>
                            <th>Alert</th>
                            <th>Severity</th>
                            <th>Status</th>
                            <th>Time</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    renderEventsTable(events) {
        const rows = events.map(event => {
            const timeAgo = this.timeAgo(new Date(event.created_at));
            const severityBadge = this.getSeverityBadge(event.severity);
            
            return `
                <tr>
                    <td>${event.sensor_id || 'System'}</td>
                    <td>${event.title}</td>
                    <td><span class="badge bg-info">${event.event_type}</span></td>
                    <td>${severityBadge}</td>
                    <td>${timeAgo}</td>
                </tr>
            `;
        }).join('');
        
        return `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Source</th>
                            <th>Event</th>
                            <th>Type</th>
                            <th>Severity</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    async acknowledgeAlert(alertId) {
        try {
            const response = await this.apiCall(`/api/alerts/${alertId}/acknowledge`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    acknowledged_by: 'admin'
                })
            });
            
            if (response.ok) {
                this.loadAlerts(); // Refresh the alerts
                this.showSuccess('Alert acknowledged successfully');
            } else {
                this.showError('Failed to acknowledge alert');
            }
        } catch (error) {
            console.error('Error acknowledging alert:', error);
            this.showError('Failed to acknowledge alert');
        }
    }
    
    async updateCharts() {
        if (this.currentSection === 'dashboard') {
            const timeRange = document.querySelector('input[name="timeRange"]:checked')?.value || 24;
            
            try {
                // Update telemetry chart
                if (window.chartManager) {
                    await window.chartManager.updateTelemetryChart(timeRange);
                    await window.chartManager.updateAlertsChart();
                }
            } catch (error) {
                console.error('Error updating charts:', error);
            }
        }
    }
    
    startAutoRefresh() {
        // Refresh data every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadCurrentSectionData();
        }, 30000);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    async apiCall(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Authorization': `Bearer ${this.authToken}`,
                'Content-Type': 'application/json'
            }
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        if (options.headers) {
            mergedOptions.headers = { ...defaultOptions.headers, ...options.headers };
        }
        
        const response = await fetch(url, mergedOptions);
        
        if (response.status === 401) {
            this.logout();
            throw new Error('Unauthorized');
        }
        
        return response;
    }
    
    logout() {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
    }
    
    getSensorUnit(sensorType) {
        const units = {
            'temperature': '°C',
            'humidity': '%',
            'wind': 'm/s'
        };
        return units[sensorType] || '';
    }
    
    getSeverityBadge(severity) {
        const badges = {
            'critical': '<span class="badge bg-danger">Critical</span>',
            'error': '<span class="badge bg-danger">Error</span>',
            'warning': '<span class="badge bg-warning">Warning</span>',
            'info': '<span class="badge bg-info">Info</span>',
            'debug': '<span class="badge bg-secondary">Debug</span>'
        };
        return badges[severity] || `<span class="badge bg-secondary">${severity}</span>`;
    }
    
    timeAgo(date) {
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    }
    
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    showError(message) {
        this.showToast(message, 'error');
    }
    
    showToast(message, type) {
        // Simple toast implementation
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'success' ? 'success' : 'danger'} position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }
    
    loadInitialData() {
        this.loadDashboardData();
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});