// Frontend JavaScript for Sports Prediction Platform

// Initialize app
document.addEventListener('DOMContentLoaded', function () {
    console.log('Sports Prediction Platform loaded');
    initializeApp();
});

function initializeApp() {
    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card, .stat-card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('fade-in');
        }, index * 100);
    });

    // Initialize tooltips if needed
    initializeTooltips();
}

// Scraping Functions
function startScraping(sourceType, venueCode) {
    const button = event.target;
    button.disabled = true;
    button.textContent = 'Procesando...';

    fetch('/scraping/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            source_type: sourceType,
            venue_code: venueCode
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Scraping iniciado correctamente', 'success');
                // Poll for status
                pollScrapingStatus(data.log_id);
            } else {
                showNotification('Error: ' + data.message, 'error');
                button.disabled = false;
                button.textContent = 'Iniciar Scraping';
            }
        })
        .catch(error => {
            showNotification('Error de conexión', 'error');
            button.disabled = false;
            button.textContent = 'Iniciar Scraping';
        });
}

function pollScrapingStatus(logId) {
    const interval = setInterval(() => {
        fetch(`/scraping/status/${logId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' || data.status === 'error') {
                    clearInterval(interval);
                    if (data.status === 'success') {
                        showNotification('Scraping completado', 'success');
                    } else {
                        showNotification('Error en scraping: ' + data.error_message, 'error');
                    }
                    // Reload page to show updated data
                    setTimeout(() => location.reload(), 2000);
                }
            });
    }, 2000);
}

// Notification System
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? 'var(--success)' : type === 'error' ? 'var(--error)' : 'var(--primary)'};
        color: white;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-xl);
        z-index: 9999;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Tooltips
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(event) {
    const text = event.target.getAttribute('data-tooltip');
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    tooltip.style.cssText = `
        position: absolute;
        background: var(--bg-secondary);
        color: var(--text-primary);
        padding: 0.5rem 1rem;
        border-radius: var(--radius-md);
        font-size: 0.85rem;
        z-index: 10000;
        pointer-events: none;
        box-shadow: var(--shadow-lg);
    `;

    document.body.appendChild(tooltip);

    const rect = event.target.getBoundingClientRect();
    tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
    tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';

    event.target._tooltip = tooltip;
}

function hideTooltip(event) {
    if (event.target._tooltip) {
        event.target._tooltip.remove();
        delete event.target._tooltip;
    }
}

// API Helper Functions
async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`/api${endpoint}`);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return null;
    }
}

// Export functions for use in templates
window.startScraping = startScraping;
window.showNotification = showNotification;
window.fetchAPI = fetchAPI;
