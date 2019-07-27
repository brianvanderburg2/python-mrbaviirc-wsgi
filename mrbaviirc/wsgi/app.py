""" Web app helper class. """

from __future__ import absolute_import

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2018 Brian Allen Vanderburg II"
__license__ = "Apache License 2.0"


__all__ = ["WsgiAppHelper"]


from mrbaviirc.common.app.base import BaseAppHelper
from mrbaviirc.common.logging import SharedLogFile

from .dispatcher import Dispatcher
from .request import Request
from .response import Response


class WsgiAppHelper(BaseAppHelper):
    """ A helper class for web applications. """

    def __init__(self):
        """ Initialize a web application. """
        BaseAppHelper.__init__(self)

        # Register our factories
        self.register_factory("webapp.request", Request)
        self.register_factory("webapp.response", Response)
        self.register_singleton("webapp.dispatcher", Dispatcher)

        # Log file related
        def _get_logfile(opt):
            filename = self.get_config(opt)
            if filename is None:
                raise LookupError("Log file not specified: " + opt)
            return SharedLogFile(filename)

        self.register_singleton(
            "webapp.logfile.error",
            lambda: _get_logfile("webapp.logfile.error")
        )
        self.register_singleton(
            "webapp.logfile.request",
            lambda: _get_logfile("webapp.logfile.request")
        )

        self.set_config("webapp.logfile.error", None)
        self.set_config("webapp.logfile.request", None)

    @property
    def dispatcher(self):
        """ Return this dispatcher. """
        return self.get_singleton("webapp.dispatcher")

    @property
    def error_log(self):
        """ Get the error log. """
        return self.get_singleton("webapp.logfile.error")

    @property
    def request_log(self):
        """ Get the request log. """
        return self.get_singleton("webapp.logfile.request")

    def __call__(self, environ, start_response):

        # Create request object
        request = self.call_factory("webapp.request", self, environ)

        self.handle_request(request)

        response = request.response
        start_response(
            response.get_status(),
            response.get_headers()
        )
        return response.content


        # Start a timer
        # Based on app settings, handle file upload/etc if needed
        # Call handler
        # Remove uploaded files if not moved
        # from handler generate headers
        # generate body

        #request = Request(...)
        #request.helper
        #request.response
        #...

    def handle_request(self, request):
        """ This method gets called by __call__ to perform request handling. """
        self.dispatcher.dispatch(request)
