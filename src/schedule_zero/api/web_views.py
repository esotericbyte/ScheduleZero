"""Web view handlers that display formatted HTML pages for browsing data."""
import tornado.web


class HandlersViewHandler(tornado.web.RequestHandler):
    """Web page to view handlers with formatted display."""
    
    def get(self):
        """Render handlers view page that fetches JSON from API."""
        self.render("handlers.html")


class SchedulesViewHandler(tornado.web.RequestHandler):
    """Web page to view schedules with formatted display."""
    
    def get(self):
        """Render schedules view page that fetches JSON from API."""
        self.render("schedules.html")
