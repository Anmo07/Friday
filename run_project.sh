#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="$SCRIPT_DIR/venv/bin/python"
FRIDAY_BIN="$SCRIPT_DIR/venv/bin/friday"

ACTION="${1:-start}"

# Auto-install dependencies if venv is missing
if [[ ! -f "$PYTHON_EXEC" ]]; then
    echo "First-time setup: Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
    "$SCRIPT_DIR/venv/bin/pip" install -e .
fi

case "$ACTION" in
    start)
        echo "Launching Friday Tahoe Edition (Desktop)..."
        # Run in background and disown to persist after terminal closure
        nohup "$FRIDAY_BIN" > "$SCRIPT_DIR/logs/menubar.log" 2>&1 &
        echo "Friday is now running in your Menu Bar. Look for the Orb!"
        ;;
    stop)
        echo "Stopping Friday..."
        pkill -9 -f "macos_menu_bar" || pkill -9 -f "friday/bin" || echo "Friday was not running."
        ;;
    restart)
        "$0" stop
        sleep 2
        "$0" start
        ;;
    status)
        if pgrep -f "macos_menu_bar" > /dev/null; then
            echo "Friday is ACTIVE and running in the Menu Bar."
        else
            echo "Friday is INACTIVE."
        fi
        ;;
    logs)
        tail -f "$SCRIPT_DIR/logs/menubar.log"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
