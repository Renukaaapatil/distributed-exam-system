// Custom JavaScript for Distributed Exam System

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.remove();
            }, 500);
        }, 5000);
    });

    // Form validation enhancements
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Password strength indicator
    const passwordInputs = document.querySelectorAll('input[type="password"][id*="password"]');
    passwordInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            updatePasswordStrength(this.value);
        });
    });

    // Smooth scroll for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId !== '#') {
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Add loading states to buttons
    const buttons = document.querySelectorAll('.btn[type="submit"]');
    buttons.forEach(function(button) {
        const form = button.closest('form');
        if (form) {
            form.addEventListener('submit', function() {
                button.disabled = true;
                const originalText = button.innerHTML;
                button.innerHTML = '<span class="loading"></span> Loading...';
                
                // Re-enable after 10 seconds in case of errors
                setTimeout(function() {
                    button.disabled = false;
                    button.innerHTML = originalText;
                }, 10000);
            });
        }
    });

    // Confirm before destructive actions
    const destructiveButtons = document.querySelectorAll('[data-confirm]');
    destructiveButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });

    // Auto-resize textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(function(textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
        // Initial resize
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    });

    // Character counter for text inputs
    const charCountInputs = document.querySelectorAll('[data-max-length]');
    charCountInputs.forEach(function(input) {
        const maxLength = parseInt(input.getAttribute('data-max-length'));
        const counterId = input.id + '-counter';
        let counter = document.getElementById(counterId);
        
        if (!counter) {
            counter = document.createElement('small');
            counter.id = counterId;
            counter.className = 'text-muted';
            input.parentNode.appendChild(counter);
        }
        
        function updateCounter() {
            const remaining = maxLength - input.value.length;
            counter.textContent = `${input.value.length}/${maxLength} characters`;
            
            if (remaining < 10) {
                counter.className = 'text-danger';
            } else if (remaining < 20) {
                counter.className = 'text-warning';
            } else {
                counter.className = 'text-muted';
            }
        }
        
        input.addEventListener('input', updateCounter);
        updateCounter();
    });

    // Table sorting
    const sortableTables = document.querySelectorAll('.table-sortable');
    sortableTables.forEach(function(table) {
        const headers = table.querySelectorAll('th[data-sort]');
        headers.forEach(function(header) {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                const column = this.getAttribute('data-sort');
                sortTable(table, column);
            });
        });
    });

    // Search functionality
    const searchInputs = document.querySelectorAll('[data-search-target]');
    searchInputs.forEach(function(input) {
        const targetId = input.getAttribute('data-search-target');
        const target = document.getElementById(targetId);
        
        if (target) {
            input.addEventListener('input', function() {
                const searchTerm = this.value.toLowerCase();
                const items = target.querySelectorAll('[data-search-item]');
                
                items.forEach(function(item) {
                    const text = item.textContent.toLowerCase();
                    item.style.display = text.includes(searchTerm) ? '' : 'none';
                });
            });
        }
    });

    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('[data-copy]');
    copyButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const text = this.getAttribute('data-copy');
            navigator.clipboard.writeText(text).then(function() {
                showToast('Copied to clipboard!', 'success');
            }).catch(function() {
                showToast('Failed to copy', 'error');
            });
        });
    });

    // Initialize exam-specific features if on exam page
    if (document.querySelector('.exam-container')) {
        initializeExamFeatures();
    }
});

// Password strength checker
function updatePasswordStrength(password) {
    const strengthIndicator = document.getElementById('password-strength');
    if (!strengthIndicator) return;

    let strength = 0;
    
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;

    const strengthLevels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
    const strengthColors = ['#dc3545', '#fd7e14', '#ffc107', '#198754', '#0d6efd'];
    
    strengthIndicator.textContent = strengthLevels[strength] || 'Very Weak';
    strengthIndicator.style.color = strengthColors[strength] || '#dc3545';
}

// Table sorting function
function sortTable(table, column) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const columnIndex = Array.from(table.querySelectorAll('th')).findIndex(th => th.getAttribute('data-sort') === column);
    
    rows.sort(function(a, b) {
        const aText = a.children[columnIndex].textContent.trim();
        const bText = b.children[columnIndex].textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aText);
        const bNum = parseFloat(bText);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return aNum - bNum;
        }
        
        // Otherwise sort as text
        return aText.localeCompare(bText);
    });
    
    // Clear and re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
}

// Toast notification function
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

// Exam-specific initialization
function initializeExamFeatures() {
    // Auto-save answers to localStorage
    const examForm = document.getElementById('examForm');
    if (examForm) {
        // Load saved answers
        const savedAnswers = localStorage.getItem('examAnswers');
        if (savedAnswers) {
            const answers = JSON.parse(savedAnswers);
            Object.keys(answers).forEach(function(questionId) {
                const input = document.querySelector(`input[name="question_${questionId}"][value="${answers[questionId]}"]`);
                if (input) {
                    input.checked = true;
                    input.dispatchEvent(new Event('change'));
                }
            });
        }

        // Save answers on change
        const radioInputs = examForm.querySelectorAll('input[type="radio"]');
        radioInputs.forEach(function(input) {
            input.addEventListener('change', function() {
                const answers = JSON.parse(localStorage.getItem('examAnswers') || '{}');
                const questionId = this.name.replace('question_', '');
                answers[questionId] = this.value;
                localStorage.setItem('examAnswers', JSON.stringify(answers));
            });
        });

        // Clear saved answers on submit
        examForm.addEventListener('submit', function() {
            localStorage.removeItem('examAnswers');
        });
    }

    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) return; // Ignore modifier keys

        const questionCards = document.querySelectorAll('.question-card');
        const currentCard = document.querySelector('.question-card:focus-within');
        
        if (!currentCard && questionCards.length > 0) {
            questionCards[0].focus();
            return;
        }

        let currentIndex = Array.from(questionCards).indexOf(currentCard);
        
        if (e.key === 'ArrowDown' && currentIndex < questionCards.length - 1) {
            e.preventDefault();
            questionCards[currentIndex + 1].focus();
            questionCards[currentIndex + 1].scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else if (e.key === 'ArrowUp' && currentIndex > 0) {
            e.preventDefault();
            questionCards[currentIndex - 1].focus();
            questionCards[currentIndex - 1].scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });

    // Make question cards focusable
    document.querySelectorAll('.question-card').forEach(function(card) {
        card.setAttribute('tabindex', '0');
    });
}

// Utility functions
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = function() {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Global error handler
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    // In production, you might want to send this to an error tracking service
});

// Performance monitoring
window.addEventListener('load', function() {
    if (performance.timing) {
        const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
        console.log(`Page load time: ${loadTime}ms`);
    }
});
