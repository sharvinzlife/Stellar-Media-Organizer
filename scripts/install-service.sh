#!/usr/bin/env bash
#
# Install Stellar Media Organizer as a systemd service
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$SCRIPT_DIR/systemd/stellar-media-organizer.service"
SYSTEMD_DIR="/etc/systemd/system"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Stellar Media Organizer - Service Installer         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Note: This script needs sudo to install the systemd service.${NC}"
    echo ""
fi

# Update paths in service file based on current user
CURRENT_USER=$(whoami)
CURRENT_HOME=$(eval echo ~$CURRENT_USER)

echo "📋 Configuration:"
echo "   User: $CURRENT_USER"
echo "   Home: $CURRENT_HOME"
echo "   Project: $PROJECT_ROOT"
echo ""

# Create a temporary service file with correct paths
TEMP_SERVICE="/tmp/stellar-media-organizer.service"
sed -e "s|/home/sharvinzlife|$CURRENT_HOME|g" \
    -e "s|User=sharvinzlife|User=$CURRENT_USER|g" \
    -e "s|Group=sharvinzlife|Group=$CURRENT_USER|g" \
    "$SERVICE_FILE" > "$TEMP_SERVICE"

echo "📦 Installing systemd service..."

# Copy service file
sudo cp "$TEMP_SERVICE" "$SYSTEMD_DIR/stellar-media-organizer.service"
rm -f "$TEMP_SERVICE"

# Reload systemd
sudo systemctl daemon-reload

echo ""
echo -e "${GREEN}✅ Service installed successfully!${NC}"
echo ""
echo "Available commands:"
echo "  sudo systemctl start stellar-media-organizer    # Start the service"
echo "  sudo systemctl stop stellar-media-organizer     # Stop the service"
echo "  sudo systemctl restart stellar-media-organizer  # Restart the service"
echo "  sudo systemctl status stellar-media-organizer   # Check status"
echo "  sudo systemctl enable stellar-media-organizer   # Enable on boot"
echo "  sudo systemctl disable stellar-media-organizer  # Disable on boot"
echo ""
echo "Or use the service manager directly:"
echo "  ./scripts/stellar-service.sh start|stop|restart|status|watch|logs"
echo ""

# Ask if user wants to enable on boot
read -p "Enable service to start on boot? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl enable stellar-media-organizer
    echo -e "${GREEN}✅ Service enabled for auto-start on boot${NC}"
fi

echo ""
echo "Done! 🎉"
