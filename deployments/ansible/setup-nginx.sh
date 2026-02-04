#!/bin/bash
# ScheduleZero Nginx Setup Script
#
# This script helps automate the nginx reverse proxy setup for ScheduleZero.
# It can be run in interactive or non-interactive mode.
#
# Usage:
#   ./setup-nginx.sh                    # Interactive mode
#   ./setup-nginx.sh subdomain auto     # Non-interactive subdomain setup
#   ./setup-nginx.sh path manual        # Non-interactive path setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIMPLE_CONFIG="${SCRIPT_DIR}/nginx-schedulezero-simple.conf"
FULL_CONFIG="${SCRIPT_DIR}/nginx-schedulezero.conf"

# Functions
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  ScheduleZero Nginx Setup${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_nginx() {
    if ! command -v nginx &> /dev/null; then
        print_error "Nginx is not installed"
        echo
        print_info "Install nginx with:"
        echo "  Ubuntu/Debian: sudo apt-get install nginx"
        echo "  CentOS/RHEL:   sudo yum install nginx"
        exit 1
    fi
    print_success "Nginx is installed"
}

check_certbot() {
    if ! command -v certbot &> /dev/null; then
        print_warning "Certbot is not installed (needed for SSL)"
        echo
        print_info "Install certbot with:"
        echo "  sudo apt-get install certbot python3-certbot-nginx"
        return 1
    fi
    print_success "Certbot is installed"
    return 0
}

get_domain() {
    local default="${1:-sz.example.com}"
    local domain
    
    if [ -n "$NON_INTERACTIVE" ]; then
        domain="$default"
    else
        read -p "Enter your domain (e.g., sz.yourdomain.com) [$default]: " domain
        domain="${domain:-$default}"
    fi
    
    echo "$domain"
}

get_port() {
    local default="${1:-8888}"
    local port
    
    if [ -n "$NON_INTERACTIVE" ]; then
        port="$default"
    else
        read -p "Enter ScheduleZero port [$default]: " port
        port="${port:-$default}"
    fi
    
    echo "$port"
}

test_schedulezero() {
    local port="$1"
    
    print_info "Testing ScheduleZero connection on port $port..."
    
    if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${port}/api/health" | grep -q "200"; then
        print_success "ScheduleZero is running and responding"
        return 0
    else
        print_warning "Cannot connect to ScheduleZero on port $port"
        print_info "Make sure ScheduleZero is running before continuing"
        return 1
    fi
}

setup_subdomain() {
    local domain="$1"
    local port="$2"
    local ssl_mode="$3"
    
    print_header
    echo "Setting up subdomain-based routing"
    echo "Domain: $domain"
    echo "Port: $port"
    echo "SSL: $ssl_mode"
    echo
    
    # Create config from template
    local config_file="/etc/nginx/sites-available/schedulezero"
    
    print_info "Creating nginx configuration..."
    
    # Copy simple config and customize
    cp "$SIMPLE_CONFIG" "$config_file"
    
    # Replace domain and port
    sed -i "s/schedulezero\.yourdomain\.com/${domain}/g" "$config_file"
    sed -i "s/127\.0\.0\.1:8888/127.0.0.1:${port}/g" "$config_file"
    
    print_success "Configuration created at $config_file"
    
    # Create symlink
    if [ ! -L "/etc/nginx/sites-enabled/schedulezero" ]; then
        ln -s "$config_file" "/etc/nginx/sites-enabled/schedulezero"
        print_success "Configuration enabled"
    else
        print_warning "Configuration already enabled"
    fi
    
    # Test configuration
    print_info "Testing nginx configuration..."
    if nginx -t 2>&1; then
        print_success "Nginx configuration is valid"
    else
        print_error "Nginx configuration test failed"
        exit 1
    fi
    
    # Reload nginx
    print_info "Reloading nginx..."
    systemctl reload nginx
    print_success "Nginx reloaded"
    
    # Setup SSL if requested
    if [ "$ssl_mode" = "auto" ]; then
        setup_ssl "$domain"
    elif [ "$ssl_mode" = "manual" ]; then
        print_info "SSL setup skipped (manual mode)"
        print_info "Run this command to get SSL certificate:"
        echo "  sudo certbot --nginx -d $domain"
    fi
    
    echo
    print_success "Nginx setup complete!"
    echo
    print_info "Your ScheduleZero instance should be accessible at:"
    if [ "$ssl_mode" != "none" ]; then
        echo "  https://$domain"
    else
        echo "  http://$domain"
    fi
}

setup_ssl() {
    local domain="$1"
    
    print_info "Setting up SSL with Let's Encrypt..."
    
    # Check if certbot is available
    if ! check_certbot; then
        print_error "Cannot setup SSL without certbot"
        return 1
    fi
    
    # Run certbot
    if certbot --nginx -d "$domain" --non-interactive --agree-tos --register-unsafely-without-email; then
        print_success "SSL certificate obtained and configured"
    else
        print_error "SSL certificate setup failed"
        print_info "You can try manually with:"
        echo "  sudo certbot --nginx -d $domain"
        return 1
    fi
}

interactive_setup() {
    print_header
    
    echo "This script will help you set up nginx as a reverse proxy for ScheduleZero."
    echo
    
    # Get configuration type
    echo "Choose configuration type:"
    echo "  1) Subdomain-based (recommended): sz.yourdomain.com"
    echo "  2) Path-based: yourdomain.com/schedulezero/"
    echo
    read -p "Enter choice [1]: " config_type
    config_type="${config_type:-1}"
    
    if [ "$config_type" = "2" ]; then
        print_error "Path-based setup not yet implemented in this script"
        print_info "Please manually configure using the template in:"
        echo "  $FULL_CONFIG"
        exit 1
    fi
    
    # Get domain
    local domain
    domain=$(get_domain)
    
    # Get port
    local port
    port=$(get_port)
    
    # Test ScheduleZero connection
    test_schedulezero "$port"
    
    # Get SSL preference
    echo
    echo "SSL/HTTPS setup:"
    echo "  1) Automatic (Let's Encrypt)"
    echo "  2) Manual (I'll configure SSL myself)"
    echo "  3) None (HTTP only, not recommended)"
    echo
    read -p "Enter choice [1]: " ssl_choice
    ssl_choice="${ssl_choice:-1}"
    
    local ssl_mode
    case "$ssl_choice" in
        1) ssl_mode="auto" ;;
        2) ssl_mode="manual" ;;
        3) ssl_mode="none" ;;
        *) ssl_mode="auto" ;;
    esac
    
    # Confirm
    echo
    print_info "Configuration summary:"
    echo "  Domain: $domain"
    echo "  Port: $port"
    echo "  SSL: $ssl_mode"
    echo
    read -p "Proceed with setup? [Y/n]: " confirm
    confirm="${confirm:-Y}"
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_error "Setup cancelled"
        exit 1
    fi
    
    # Do setup
    setup_subdomain "$domain" "$port" "$ssl_mode"
}

show_help() {
    cat << EOF
ScheduleZero Nginx Setup Script

Usage:
  $0                          Interactive mode
  $0 subdomain auto           Non-interactive subdomain with auto SSL
  $0 subdomain manual         Non-interactive subdomain with manual SSL
  $0 help                     Show this help message

Examples:
  # Interactive setup
  sudo $0
  
  # Automated setup with Let's Encrypt
  sudo $0 subdomain auto
  
  # Setup without SSL (HTTP only)
  sudo $0 subdomain none

Environment Variables:
  DOMAIN    - Domain name (e.g., sz.example.com)
  PORT      - ScheduleZero port (default: 8888)

Example with environment variables:
  sudo DOMAIN=sz.mysite.com PORT=8888 $0 subdomain auto

EOF
}

# Main script
main() {
    local mode="${1:-interactive}"
    local ssl_mode="${2:-auto}"
    
    if [ "$mode" = "help" ] || [ "$mode" = "--help" ] || [ "$mode" = "-h" ]; then
        show_help
        exit 0
    fi
    
    # Check prerequisites
    check_root
    check_nginx
    
    if [ "$mode" = "interactive" ]; then
        interactive_setup
    elif [ "$mode" = "subdomain" ]; then
        NON_INTERACTIVE=1
        local domain="${DOMAIN:-sz.example.com}"
        local port="${PORT:-8888}"
        setup_subdomain "$domain" "$port" "$ssl_mode"
    else
        print_error "Unknown mode: $mode"
        show_help
        exit 1
    fi
}

# Run main
main "$@"
