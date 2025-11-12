// schedule-card Web Component

class ScheduleCard extends HTMLElement {
    connectedCallback() {
        this.render();
        this.startCountdown();
    }
    
    disconnectedCallback() {
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
        }
    }
    
    render() {
        const jobId = this.getAttribute('job-id');
        const nextRun = this.getAttribute('next-run');
        const status = this.getAttribute('status');
        const trigger = this.getAttribute('trigger');
        
        this.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="job-id">${jobId}</h3>
                    <span class="status status-${status}">${status}</span>
                </div>
                <div class="card-body">
                    <div class="info-row">
                        <span class="label">Next Run:</span>
                        <span class="countdown"></span>
                    </div>
                    <div class="info-row">
                        <span class="label">Trigger:</span>
                        <span class="value">${trigger}</span>
                    </div>
                </div>
                <div class="card-actions">
                    <button class="btn-secondary"
                            hx-get="/schedules/edit/${jobId}"
                            hx-target="#content">
                        Edit
                    </button>
                    <button class="btn-danger"
                            hx-delete="/api/schedules/${jobId}"
                            hx-confirm="Delete schedule '${jobId}'?"
                            hx-target="closest schedule-card"
                            hx-swap="outerHTML">
                        Delete
                    </button>
                </div>
            </div>
        `;
        
        this.applyStyles();
    }
    
    startCountdown() {
        const nextRun = new Date(this.getAttribute('next-run'));
        const countdownEl = this.querySelector('.countdown');
        
        const updateCountdown = () => {
            const now = new Date();
            const diff = nextRun - now;
            
            if (diff < 0) {
                countdownEl.textContent = 'Running...';
                countdownEl.classList.add('running');
                return;
            }
            
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);
            
            countdownEl.textContent = `${hours}h ${minutes}m ${seconds}s`;
        };
        
        updateCountdown();
        this.countdownInterval = setInterval(updateCountdown, 1000);
    }
    
    applyStyles() {
        const style = document.createElement('style');
        style.textContent = `
            schedule-card {
                display: block;
            }
            
            schedule-card .card {
                background: var(--sz-surface);
                border: 1px solid var(--sz-border);
                border-radius: 0.5rem;
                padding: 1.5rem;
                transition: box-shadow 150ms;
            }
            
            schedule-card .card:hover {
                box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            }
            
            schedule-card .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
            }
            
            schedule-card .job-id {
                font-size: 1.125rem;
                font-weight: 600;
                color: var(--sz-text);
            }
            
            schedule-card .status {
                padding: 0.25rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }
            
            schedule-card .status-active {
                background: #dcfce7;
                color: #166534;
            }
            
            schedule-card .card-body {
                margin-bottom: 1rem;
            }
            
            schedule-card .info-row {
                display: flex;
                justify-content: space-between;
                padding: 0.5rem 0;
                border-bottom: 1px solid var(--sz-border);
            }
            
            schedule-card .info-row:last-child {
                border-bottom: none;
            }
            
            schedule-card .label {
                font-weight: 500;
                color: var(--sz-text-muted);
            }
            
            schedule-card .value,
            schedule-card .countdown {
                font-weight: 600;
                color: var(--sz-text);
            }
            
            schedule-card .countdown.running {
                color: var(--sz-primary);
            }
            
            schedule-card .card-actions {
                display: flex;
                gap: 0.5rem;
            }
            
            schedule-card button {
                flex: 1;
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 0.375rem;
                font-weight: 500;
                cursor: pointer;
                transition: all 150ms;
            }
            
            schedule-card .btn-secondary {
                background: var(--sz-background);
                color: var(--sz-text);
            }
            
            schedule-card .btn-secondary:hover {
                background: var(--sz-border);
            }
            
            schedule-card .btn-danger {
                background: #fecaca;
                color: #991b1b;
            }
            
            schedule-card .btn-danger:hover {
                background: #fca5a5;
            }
        `;
        this.appendChild(style);
    }
}

customElements.define('schedule-card', ScheduleCard);
