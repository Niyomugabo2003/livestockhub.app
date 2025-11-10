// Main JavaScript for LivestockHub

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Add loading states to buttons on form submission
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="loading-spinner me-2"></span>Processing...';
            }
        });
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add hover effects to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('shadow-lg');
        });
        
        card.addEventListener('mouseleave', function() {
            this.classList.remove('shadow-lg');
        });
    });

    // Status update confirmation
    const statusSelects = document.querySelectorAll('.status-select');
    statusSelects.forEach(select => {
        select.addEventListener('change', function(e) {
            const newStatus = this.value;
            const orderNumber = this.closest('tr').querySelector('.order-number')?.textContent || 'this order';
            
            if (newStatus === 'cancelled') {
                if (!confirm(`Are you sure you want to cancel ${orderNumber}? This will notify the customer.`)) {
                    this.form.reset();
                    return;
                }
            }
            
            if (newStatus === 'delivered') {
                if (!confirm(`Mark ${orderNumber} as delivered? This action cannot be undone.`)) {
                    this.form.reset();
                    return;
                }
            }
            
            // Show loading state
            const originalText = this.options[this.selectedIndex].text;
            this.disabled = true;
            this.options[this.selectedIndex].text = 'Updating...';
        });
    });

    // Cart quantity updates
    const quantityInputs = document.querySelectorAll('.quantity-input');
    quantityInputs.forEach(input => {
        input.addEventListener('change', function() {
            if (this.value < 1) {
                this.value = 1;
            }
            if (this.value > 100) {
                this.value = 100;
            }
        });
    });

    // Search functionality enhancement
    const searchInputs = document.querySelectorAll('.search-input');
    searchInputs.forEach(input => {
        input.addEventListener('input', debounce(function(e) {
            const searchTerm = e.target.value.toLowerCase();
            // You can add live search functionality here
            console.log('Searching for:', searchTerm);
        }, 300));
    });

    // Price range filter
    const priceRange = document.getElementById('priceRange');
    if (priceRange) {
        const priceOutput = document.getElementById('priceOutput');
        priceRange.addEventListener('input', function() {
            if (priceOutput) {
                priceOutput.textContent = `RWF ${this.value}`;
            }
        });
    }
});

// Utility function for debouncing
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-RW', {
        style: 'currency',
        currency: 'RWF'
    }).format(amount);
}

// Show notification
function showNotification(message, type = 'info') {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';

    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show`;
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
            ${message}
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.querySelector('.container').insertBefore(notification, document.querySelector('.container').firstChild);

    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}