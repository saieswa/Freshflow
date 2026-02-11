// ...existing code...

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.donate-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const itemId = this.getAttribute('data-item-id');
            fetch(`/donate/${itemId}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Optionally remove the item from the DOM or show a success message
                        location.reload();
                    }
                });
        });
    });

    document.querySelectorAll('.remove-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const itemId = this.getAttribute('data-item-id');
            fetch(`/remove/${itemId}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Optionally remove the item from the DOM or show a success message
                        location.reload();
                    }
                });
        });
    });
});

// ...existing code...