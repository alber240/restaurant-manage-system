
import { authFetch } from './api.js';
// Cart page specific JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Quantity controls
    document.querySelectorAll('.qty-btn').forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentElement.querySelector('.qty-input');
            let value = parseInt(input.value);
            
            if (this.classList.contains('minus') && value > 1) {
                input.value = value - 1;
            } else if (this.classList.contains('plus')) {
                input.value = value + 1;
            }
        });
    });
    
    // Update quantity forms
     document.querySelectorAll('.quantity-form').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            try {
                const response = await authFetch(this.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                    },
                });
                
                if (response.ok) {
                    const data = await response.json();
                    // Update the item total if needed
                    const totalCell = itemRow.querySelector('td:nth-child(4)');
                    if (totalCell) {
                        totalCell.textContent = `$${data.item_total}`;
                    }
                    // Update cart summary
                    document.querySelector('.order-total span:last-child').textContent = `$${data.cart_total}`;
                    showAlert('Cart updated', 'success');
                } else {
                    throw new Error('Failed to update cart');
                }
            } catch (error) {
                console.error('Error:', error);
                showAlert('Failed to update cart', 'error');
            }
        });
    });
    
    // Remove item forms
    document.querySelectorAll('.remove-form').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (confirm('Are you sure you want to remove this item?')) {
                const formData = new FormData(this);
                const itemRow = this.closest('.cart-item');
                
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
                        itemRow.remove();
                        // Update cart summary
                        document.querySelector('.order-total span:last-child').textContent = `$${data.cart_total}`;
                        updateCartCounter(data.cart_count);
                        showAlert('Item removed from cart', 'success');
                        
                        // If cart is now empty, show empty message
                        if (data.cart_count === 0) {
                            document.querySelector('.cart-items table').style.display = 'none';
                            document.querySelector('.cart-actions').style.display = 'none';
                            document.querySelector('.empty-cart').style.display = 'block';
                        }
                    } else {
                        throw new Error('Failed to remove item');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showAlert('Failed to remove item', 'error');
                }
            }
        });
    });
});

// Shared showAlert function (in case cart.js is loaded separately)
if (typeof showAlert !== 'function') {
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
});