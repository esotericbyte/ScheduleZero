"""CLI entry point for ScheduleZero server.

This module provides the command-line interface for starting the server.
Delegates to the main tornado_app_server module.
"""

from .tornado_app_server import main

if __name__ == "__main__":
    main()
