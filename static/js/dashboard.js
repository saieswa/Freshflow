// FreshFlow Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard
    initializeDashboard();
    initializeChart();
    initializeSidebar();
    initializeNotifications();
});

// Initialize dashboard components
function initializeDashboard() {
    // Add loading states to buttons
    const buttons = document.querySelectorAll('.btn-primary, .btn-secondary, .action-btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (this.href && !this.href.includes('#')) {
                this.style.opacity = '0.7';
                this.style.pointerEvents = 'none';
            }
        });
    });

    // Initialize tooltips for stat cards
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(-2px)';
        });
    });
}

// Initialize Chart.js for stock health
function initializeChart() {
    const ctx = document.getElementById('stockHealthChart');
    if (!ctx) return;

    // Fetch chart data from API
    fetch('/api/chart-data')
        .then(response => response.json())
        .then(data => {
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Fresh', 'Near Expiry', 'Expired'],
                    datasets: [{
                        data: [data.fresh, data.near, data.expired],
                        backgroundColor: [
                            '#27ae60',
                            '#e67e22',
                            '#e74c3c'
                        ],
                        borderWidth: 0,
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true,
                                font: {
                                    family: 'Inter',
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#fff',
                            bodyColor: '#fff',
                            borderColor: '#27ae60',
                            borderWidth: 1,
                            cornerRadius: 8,
                            displayColors: false,
                            callbacks: {
                                label: function(context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((context.parsed / total) * 100).toFixed(1);
                                    return `${context.label}: ${context.parsed} items (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '60%',
                    animation: {
                        animateRotate: true,
                        animateScale: true,
                        duration: 1000
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching chart data:', error);
            // Fallback chart with sample data
            createFallbackChart(ctx);
        });
}

// Create fallback chart with sample data
function createFallbackChart(ctx) {
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Fresh', 'Near Expiry', 'Expired'],
            datasets: [{
                data: [1200, 132, 12],
                backgroundColor: [
                    '#27ae60',
                    '#e67e22',
                    '#e74c3c'
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            family: 'Inter',
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#27ae60',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} items (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '60%',
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1000
            }
        }
    });
}

// Initialize sidebar functionality
function initializeSidebar() {
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 768) {
                if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                    sidebar.classList.remove('open');
                }
            }
        });

        // Handle window resize
        window.addEventListener('resize', function() {
            if (window.innerWidth > 768) {
                sidebar.classList.remove('open');
            }
        });
    }

    // Add active state to navigation links
    const navLinks = document.querySelectorAll('.nav-link');
    const currentPath = window.location.pathname;
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.closest('.nav-item').classList.add('active');
        }
    });
}

// Initialize notifications
function initializeNotifications() {
    const notificationBtn = document.querySelector('.notification-btn');
    
    if (notificationBtn) {
        notificationBtn.addEventListener('click', function() {
            // Toggle notification dropdown (placeholder)
            console.log('Notifications clicked');
            // In a real app, this would show a dropdown with notifications
        });
    }

    // Simulate real-time notifications
    simulateNotifications();
}

// Simulate real-time notifications
function simulateNotifications() {
    const notificationBadge = document.querySelector('.notification-badge');
    if (!notificationBadge) return;

    // Update notification count every 30 seconds
    setInterval(() => {
        const currentCount = parseInt(notificationBadge.textContent);
        const newCount = Math.max(0, currentCount + Math.floor(Math.random() * 3) - 1);
        notificationBadge.textContent = newCount;
        
        // Add animation for new notifications
        if (newCount > currentCount) {
            notificationBadge.style.animation = 'pulse 0.5s ease-in-out';
            setTimeout(() => {
                notificationBadge.style.animation = '';
            }, 500);
        }
    }, 30000);
}

// Search functionality
function initializeSearch() {
    const searchInput = document.querySelector('.search-box input');
    if (!searchInput) return;

    let searchTimeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length > 2) {
            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 300);
        }
    });
}

// Perform search (placeholder)
function performSearch(query) {
    console.log('Searching for:', query);
    // In a real app, this would make an API call to search inventory
}

// Utility functions
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .stat-card {
        animation: fadeIn 0.6s ease-out;
    }
    
    .stat-card:nth-child(1) { animation-delay: 0.1s; }
    .stat-card:nth-child(2) { animation-delay: 0.2s; }
    .stat-card:nth-child(3) { animation-delay: 0.3s; }
    .stat-card:nth-child(4) { animation-delay: 0.4s; }
`;
document.head.appendChild(style);

// Initialize search when DOM is ready
document.addEventListener('DOMContentLoaded', initializeSearch);
