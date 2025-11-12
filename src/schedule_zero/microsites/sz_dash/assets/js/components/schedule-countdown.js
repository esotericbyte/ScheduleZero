// schedule-countdown Web Component - ISLAND
// Only this element is interactive, rest is static HTML

class ScheduleCountdown extends HTMLElement {
    connectedCallback() {
        this.startCountdown();
    }
    
    disconnectedCallback() {
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
        }
    }
    
    startCountdown() {
        const nextRun = new Date(this.getAttribute('next-run'));
        
        const updateCountdown = () => {
            const now = new Date();
            const diff = nextRun - now;
            
            if (diff < 0) {
                this.textContent = 'Running...';
                this.classList.add('running');
                return;
            }
            
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);
            
            this.textContent = `${hours}h ${minutes}m ${seconds}s`;
            this.classList.remove('running');
        };
        
        // Initial update
        updateCountdown();
        
        // Update every second
        this.countdownInterval = setInterval(updateCountdown, 1000);
        
        // Apply styles
        this.style.fontWeight = '600';
        this.style.color = 'var(--sz-text)';
    }
}

// Register the island
customElements.define('schedule-countdown', ScheduleCountdown);
