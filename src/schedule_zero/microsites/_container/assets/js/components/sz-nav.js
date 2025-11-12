// sz-nav Web Component - Navigation with HTMX integration

class SzNav extends HTMLElement {
    connectedCallback() {
        this.render();
        this.attachEventListeners();
    }
    
    render() {
        const active = this.getAttribute('active') || '';
        
        // Logo/Title
        const header = document.createElement('div');
        header.className = 'nav-header';
        header.innerHTML = `
            <h1 class="nav-logo">⚡ ScheduleZero</h1>
        `;
        this.appendChild(header);
        
        // Nav Items Container
        const navItems = document.createElement('nav');
        navItems.className = 'nav-items';
        
        // Process nav-item children
        const items = Array.from(this.querySelectorAll('nav-item'));
        items.forEach(item => {
            const href = item.getAttribute('href');
            const icon = item.getAttribute('icon');
            const name = item.getAttribute('name');
            const target = item.getAttribute('target'); // External link support
            const label = item.textContent.trim();
            
            const link = document.createElement('a');
            link.href = href;
            link.className = `nav-item ${name === active ? 'active' : ''}`;
            
            // External links (target="_blank") don't use HTMX
            if (target === '_blank') {
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
            } else {
                // Internal links use HTMX for SPA-like navigation
                link.setAttribute('hx-get', href);
                link.setAttribute('hx-target', '#content');
                link.setAttribute('hx-push-url', 'true');
                link.setAttribute('hx-swap', 'innerHTML transition:true');
            }
            
            link.innerHTML = `
                <span class="nav-icon">${icon}</span>
                <span class="nav-label">${label}</span>
            `;
            
            navItems.appendChild(link);
        });
        
        // Clear original nav-items and add processed ones
        items.forEach(item => item.remove());
        this.appendChild(navItems);
        
        // Apply styles
        this.applyStyles();
    }
    
    attachEventListeners() {
        // Update active state after HTMX navigation
        document.body.addEventListener('htmx:afterSwap', (event) => {
            if (event.detail.target.id === 'content') {
                const url = new URL(window.location.href);
                const path = url.pathname;
                
                this.querySelectorAll('.nav-item').forEach(item => {
                    const href = item.getAttribute('hx-get');
                    item.classList.toggle('active', path === href);
                });
            }
        });
    }
    
    applyStyles() {
        const style = document.createElement('style');
        style.textContent = `
            sz-nav .nav-header {
                padding: 0 1.5rem 1.5rem;
                border-bottom: 1px solid var(--sz-border);
                margin-bottom: 1rem;
            }
            
            sz-nav .nav-logo {
                font-size: 1.25rem;
                font-weight: 600;
                color: var(--sz-primary);
            }
            
            sz-nav .nav-items {
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
                padding: 0 0.75rem;
            }
            
            sz-nav .nav-item {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.75rem 1rem;
                border-radius: 0.5rem;
                color: var(--sz-text);
                text-decoration: none;
                transition: all 150ms;
                cursor: pointer;
            }
            
            sz-nav .nav-item:hover {
                background: var(--sz-background);
                color: var(--sz-primary);
            }
            
            sz-nav .nav-item.active {
                background: var(--sz-primary);
                color: white;
            }
            
            sz-nav .nav-item[target="_blank"] {
                opacity: 0.8;
            }
            
            sz-nav .nav-item[target="_blank"]:hover {
                opacity: 1;
            }
            
            sz-nav .nav-icon {
                font-size: 1.25rem;
                width: 1.5rem;
                text-align: center;
            }
            
            sz-nav .nav-label {
                font-weight: 500;
            }
            
            @media (max-width: 768px) {
                sz-nav .nav-label {
                    display: none;
                }
                
                sz-nav .nav-header {
                    padding: 0 0.5rem 1rem;
                }
                
                sz-nav .nav-logo {
                    font-size: 1.5rem;
                    text-align: center;
                }
                
                sz-nav .nav-items {
                    align-items: center;
                    padding: 0 0.25rem;
                }
                
                sz-nav .nav-item {
                    justify-content: center;
                    padding: 0.75rem;
                }
            }
        `;
        this.appendChild(style);
    }
}

customElements.define('sz-nav', SzNav);
