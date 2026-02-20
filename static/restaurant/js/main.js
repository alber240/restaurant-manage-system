
import { authFetch, setTokens } from './api.js';
// Base JavaScript for the entire site
document.addEventListener('DOMContentLoaded', function() {
    // Initialize cart counter
    updateCartCounter();
    
    // Set up event listeners for all add-to-cart forms
    document.querySelectorAll('.add-to-cart-form').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            try {
                const response = await fetch(this.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                    },
                });
                
                if (response.ok) {
                    const data = await response.json();
                    updateCartCounter(data.cart_count);
                    showAlert('Item added to cart!', 'success');
                } else {
                    throw new Error('Failed to add item to cart');
                }
            } catch (error) {
                console.error('Error:', error);
                showAlert('Failed to add item to cart', 'error');
            }
        });
    });
    
    // Mobile menu toggle (if needed)
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            document.querySelector('.main-nav').classList.toggle('active');
        });
    }
});

// Update cart counter in navigation
function updateCartCounter(count) {
    const counterElements = document.querySelectorAll('.cart-counter, .cart-badge');
    
    if (typeof count === 'undefined') {
        // Fetch current count via AJAX if not provided
        fetch('/cart-count/')
            .then(response => response.json())
            .then(data => {
                counterElements.forEach(el => {
                    el.textContent = data.count;
                    el.style.display = data.count > 0 ? 'inline-block' : 'none';
                });
            });
    } else {
        counterElements.forEach(el => {
            el.textContent = count;
            el.style.display = count > 0 ? 'inline-block' : 'none';
        });
    }
}

// Show alert message
function showAlert(message, type = 'success') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    
    const messagesContainer = document.querySelector('.messages') || document.body;
    messagesContainer.prepend(alert);
    
    setTimeout(() => {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 300);
    }, 3000);
}

document.addEventListener('DOMContentLoaded', function() {
    // Add loading state to add-to-cart buttons
    document.querySelectorAll('.add-to-cart-form').forEach(form => {
        form.addEventListener('submit', function() {
            const btn = this.querySelector('button');
            btn.classList.add('btn-loading');
            btn.innerHTML = '<span class="spinner-border spinner-border-sm loading-spinner" role="status" aria-hidden="true"></span> Adding...';
        });
    });



    
    // Login form handling
    const loginForm = document.querySelector('.login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            try {
                const response = await authFetch('/api/token/', {
                    method: 'POST',
                    body: JSON.stringify({
                        username: formData.get('username'),
                        password: formData.get('password')
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    setTokens(data.access, data.refresh);
                    window.location.href = '/'; // Redirect after login
                } else {
                    showAlert('Login failed', 'error');
                }
            } catch (error) {
                console.error('Login error:', error);
                showAlert('Login failed', 'error');
            }
        });
    }
});