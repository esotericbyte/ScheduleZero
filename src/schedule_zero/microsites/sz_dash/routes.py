"""
Dashboard Microsite Routes

Provides the main dashboard view with schedule overview.
"""

from .handlers import DashboardHandler


# Microsite routes
routes = [
    (r"/", DashboardHandler),
]

