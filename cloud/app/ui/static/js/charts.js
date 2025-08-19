/**
 * Charts JavaScript - Chart.js integration
 */

class ChartManager {
    constructor() {
        this.charts = {};
        this.colors = {
            primary: 'rgb(13, 110, 253)',
            success: 'rgb(25, 135, 84)',
            warning: 'rgb(255, 193, 7)',
            danger: 'rgb(220, 53, 69)',
            info: 'rgb(13, 202, 240)',
            temperature: 'rgb(255, 99, 132)',
            humidity: 'rgb(54, 162, 235)',
            wind: 'rgb(75, 192, 192)'
        };
        
        this.init();
    }
    
    init() {
        // Configure Chart.js defaults
        Chart.defaults.font.family = 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif';
        Chart.defaults.color = '#6c757d';
        Chart.defaults.scale.grid.color = 'rgba(0, 0, 0, 0.1)';
        
        this.initializeCharts();
    }
    
    initializeCharts() {
        this.initTelemetryChart();
        this.initAlertsChart();
    }
    
    initTelemetryChart() {
        const ctx = document.getElementById('telemetryChart');
        if (!ctx) return;
        
        this.charts.telemetry = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return new Date(context[0].parsed.x).toLocaleString();
                            },
                            label: function(context) {
                                const sensorType = context.dataset.sensorType || 'unknown';
                                const unit = context.dataset.unit || '';
                                return `${context.dataset.label}: ${context.parsed.y} ${unit}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour',
                            displayFormats: {
                                hour: 'HH:mm'
                            }
                        },
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Value'
                        },
                        beginAtZero: false
                    }
                }
            }
        });
    }
    
    initAlertsChart() {
        const ctx = document.getElementById('alertsChart');
        if (!ctx) return;
        
        this.charts.alerts = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        this.colors.danger,
                        '#fd7e14',
                        this.colors.warning,
                        this.colors.info
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? Math.round((context.raw / total) * 100) : 0;
                                return `${context.label}: ${context.raw} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    async updateTelemetryChart(hours = 24) {
        try {
            const response = await dashboard.apiCall(`/api/readings/chart-data?hours=${hours}`);
            const data = await response.json();
            
            const chart = this.charts.telemetry;
            if (!chart) return;
            
            // Clear existing datasets
            chart.data.datasets = [];
            
            // Add datasets for each sensor
            Object.entries(data.datasets).forEach(([sensorId, sensorData]) => {
                const color = this.getSensorColor(sensorId);
                
                chart.data.datasets.push({
                    label: sensorData.label,
                    data: sensorData.data,
                    borderColor: color,
                    backgroundColor: color + '20',
                    fill: false,
                    tension: 0.1,
                    pointRadius: 2,
                    pointHoverRadius: 4,
                    sensorType: this.getSensorType(sensorId),
                    unit: this.getSensorUnit(sensorId)
                });
            });
            
            // Update time scale based on hours
            if (hours <= 1) {
                chart.options.scales.x.time.unit = 'minute';
                chart.options.scales.x.time.displayFormats.minute = 'HH:mm';
            } else if (hours <= 24) {
                chart.options.scales.x.time.unit = 'hour';
                chart.options.scales.x.time.displayFormats.hour = 'HH:mm';
            } else {
                chart.options.scales.x.time.unit = 'day';
                chart.options.scales.x.time.displayFormats.day = 'MM/dd';
            }
            
            chart.update('none');
            
        } catch (error) {
            console.error('Error updating telemetry chart:', error);
        }
    }
    
    async updateAlertsChart() {
        try {
            const response = await dashboard.apiCall('/api/alerts/summary');
            const data = await response.json();
            
            const chart = this.charts.alerts;
            if (!chart) return;
            
            chart.data.datasets[0].data = [
                data.critical_alerts || 0,
                data.high_alerts || 0,
                data.medium_alerts || 0,
                data.low_alerts || 0
            ];
            
            chart.update('none');
            
        } catch (error) {
            console.error('Error updating alerts chart:', error);
        }
    }
    
    initSecurityDemoChart() {
        const ctx = document.getElementById('demoChart');
        if (!ctx) return;
        
        this.charts.demo = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Messages Sent',
                        data: [],
                        borderColor: this.colors.primary,
                        backgroundColor: this.colors.primary + '20',
                        fill: false
                    },
                    {
                        label: 'Messages Blocked',
                        data: [],
                        borderColor: this.colors.danger,
                        backgroundColor: this.colors.danger + '20',
                        fill: false
                    },
                    {
                        label: 'Valid Messages',
                        data: [],
                        borderColor: this.colors.success,
                        backgroundColor: this.colors.success + '20',
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Message Count'
                        },
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    updateSecurityDemoChart(demoData) {
        const chart = this.charts.demo;
        if (!chart || !demoData) return;
        
        const labels = demoData.timeline.map(point => 
            new Date(point.timestamp).toLocaleTimeString()
        );
        
        chart.data.labels = labels;
        chart.data.datasets[0].data = demoData.timeline.map(point => point.messages_sent || 0);
        chart.data.datasets[1].data = demoData.timeline.map(point => point.messages_blocked || 0);
        chart.data.datasets[2].data = demoData.timeline.map(point => point.valid_messages || 0);
        
        chart.update('none');
    }
    
    getSensorColor(sensorId) {
        if (sensorId.includes('temp')) return this.colors.temperature;
        if (sensorId.includes('humidity')) return this.colors.humidity;
        if (sensorId.includes('wind')) return this.colors.wind;
        return this.colors.primary;
    }
    
    getSensorType(sensorId) {
        if (sensorId.includes('temp')) return 'temperature';
        if (sensorId.includes('humidity')) return 'humidity';
        if (sensorId.includes('wind')) return 'wind';
        return 'unknown';
    }
    
    getSensorUnit(sensorId) {
        if (sensorId.includes('temp')) return '°C';
        if (sensorId.includes('humidity')) return '%';
        if (sensorId.includes('wind')) return 'm/s';
        return '';
    }
    
    destroyChart(chartName) {
        if (this.charts[chartName]) {
            this.charts[chartName].destroy();
            delete this.charts[chartName];
        }
    }
    
    destroyAllCharts() {
        Object.keys(this.charts).forEach(chartName => {
            this.destroyChart(chartName);
        });
    }
    
    resizeCharts() {
        Object.values(this.charts).forEach(chart => {
            chart.resize();
        });
    }
}

// Initialize chart manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chartManager = new ChartManager();
});

// Handle window resize
window.addEventListener('resize', () => {
    if (window.chartManager) {
        window.chartManager.resizeCharts();
    }
});