// delete-button Web Component - ISLAND
// Interactive delete button with HTMX integration

class DeleteButton extends HTMLElement {
    connectedCallback() {
        this.render();
    }
    
    render() {
        const jobId = this.getAttribute('job-id');
        const endpoint = this.getAttribute('endpoint');
        
        const button = document.createElement('button');
        button.className = 'btn-danger';
        button.textContent = 'Delete';
        button.setAttribute('hx-delete', endpoint);
        button.setAttribute('hx-confirm', `Delete schedule '${jobId}'?`);
        button.setAttribute('hx-target', 'closest .schedule-card');
        button.setAttribute('hx-swap', 'outerHTML swap:200ms');
        
        this.appendChild(button);
        
        // Tell HTMX to process this new element
        if (window.htmx) {
            htmx.process(button);
        }
    }
}

customElements.define('delete-button', DeleteButton);
