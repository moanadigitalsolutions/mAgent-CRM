// Analytics Dashboard JavaScript

let trendsChart = null;
let citiesChart = null;
let leadScoreChart = null;
let engagementChart = null;

function initializeAnalyticsDashboard() {
    // Initialize all charts
    initializeTrendsChart();
    initializeCitiesChart();
    initializeLeadScoreChart();
    initializeEngagementChart();
}

function initializeTrendsChart() {
    const ctx = document.getElementById('trendsChart');
    if (!ctx) return;
    
    // Get data from API
    fetchAnalyticsData('customer_trends', 30).then(data => {
        const labels = data.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('en-NZ', { month: 'short', day: 'numeric' });
        });
        const values = data.map(item => item.count);
        
        trendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'New Customers',
                    data: values,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    });
}

function initializeCitiesChart() {
    const ctx = document.getElementById('citiesChart');
    if (!ctx) return;
    
    fetchAnalyticsData('geographic_distribution').then(data => {
        const labels = data.slice(0, 5).map(item => item.city || 'Unknown');
        const values = data.slice(0, 5).map(item => item.count);
        const colors = [
            '#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1'
        ];
        
        citiesChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    }
                }
            }
        });
    });
}

function initializeLeadScoreChart() {
    const ctx = document.getElementById('leadScoreChart');
    if (!ctx) return;
    
    fetchAnalyticsData('lead_scores').then(data => {
        const labels = data.map(item => item.label);
        const values = data.map(item => item.count);
        
        leadScoreChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Customers',
                    data: values,
                    backgroundColor: [
                        '#dc3545', '#fd7e14', '#ffc107', '#28a745', '#007bff'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    });
}

function initializeEngagementChart() {
    const ctx = document.getElementById('engagementChart');
    if (!ctx) return;
    
    fetchAnalyticsData('engagement_scores').then(data => {
        const labels = data.map(item => item.label);
        const values = data.map(item => item.count);
        
        engagementChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        '#dc3545', '#fd7e14', '#ffc107', '#28a745', '#007bff'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 15
                        }
                    }
                }
            }
        });
    });
}

function updateTrendsChart() {
    const period = document.getElementById('trendsPeriod').value;
    showChartLoading('trendsChart');
    
    fetchAnalyticsData('customer_trends', period).then(data => {
        const labels = data.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('en-NZ', { month: 'short', day: 'numeric' });
        });
        const values = data.map(item => item.count);
        
        trendsChart.data.labels = labels;
        trendsChart.data.datasets[0].data = values;
        trendsChart.update();
        
        hideChartLoading('trendsChart');
    });
}

function refreshDashboard() {
    // Show loading state
    const refreshBtn = document.querySelector('button[onclick="refreshDashboard()"]');
    if (refreshBtn) {
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
        refreshBtn.disabled = true;
    }
    
    // Reload the page to get fresh data
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

function fetchAnalyticsData(chartType, days = null) {
    let url = '/analytics/api/data/?chart=' + chartType;
    if (days) {
        url += '&days=' + days;
    }
    
    return fetch(url)
        .then(response => response.json())
        .then(data => data.data)
        .catch(error => {
            console.error('Error fetching analytics data:', error);
            return [];
        });
}

function showChartLoading(chartId) {
    const chartContainer = document.getElementById(chartId).parentElement;
    if (chartContainer.querySelector('.loading-overlay')) return;
    
    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay';
    loadingOverlay.innerHTML = '<div class="loading-spinner"></div>';
    chartContainer.style.position = 'relative';
    chartContainer.appendChild(loadingOverlay);
}

function hideChartLoading(chartId) {
    const chartContainer = document.getElementById(chartId).parentElement;
    const loadingOverlay = chartContainer.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

// Utility functions for number formatting
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function formatPercentage(num) {
    return num.toFixed(1) + '%';
}

// Export functions for use in other modules
window.analyticsUtils = {
    formatNumber,
    formatPercentage,
    fetchAnalyticsData,
    showChartLoading,
    hideChartLoading
};