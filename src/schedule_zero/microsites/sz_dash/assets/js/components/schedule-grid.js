// schedule-grid Web Component

class ScheduleGrid extends HTMLElement {
    connectedCallback() {
        this.applyStyles();
    }
    
    applyStyles() {
        const style = document.createElement('style');
        style.textContent = `
            schedule-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                gap: 1.5rem;
                margin-top: 2rem;
            }
            
            @media (max-width: 768px) {
                schedule-grid {
                    grid-template-columns: 1fr;
                }
            }
        `;
        this.appendChild(style);
    }
}

customElements.define('schedule-grid', ScheduleGrid);
