""" Web app helper class. """

from __future__ import absolute_import

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2018 Brian Allen Vanderburg II"
__license__ = "Apache License 2.0"


__all__ = ["WsgiAppHelper"]


import html
import io
import traceback

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

        # Configs
        self.set_config("webapp.logfile.error", None)
        self.set_config("webapp.logfile.request", None)

        self.set_config("webapp.request.maxsize", 1024000)
        self.set_config("webapp.request.maxtime", 30)

    @property
    def appname(self):
        return "mrbaviirc.wsgi.app"

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
        try:
            request = self.call_factory("webapp.request", self, environ)
        except Exception as ex: # pylint: disable=broad-except
            self.handle_exception(ex)
            start_response(
                "500 Internal Server Error",
                [("Content-Type", "text/html")]
            )
            return [
                b"<html><body>"
                b"<h1>Internal Server Error</h1>"
                b"<p>An internal server error has occurred.</p>"
                b"</body></html>"
            ]

        # Handle the request
        try:
            request.init()
            self.handle_request(request)
            request.finalize()
        except Exception as ex: # pylint: disable=broad-except
            self.handle_exception(ex, request)

        # Return the response
        try:
            response = request.response
            start_response(
                response.get_status(),
                response.get_headers()
            )
            return response.content
        except Exception as ex: # pylint: disable=broad-except
            self.handle_exception(ex)
            start_response(
                "500 Internal Server Error",
                [("Content-Type", "text/html")]
            )
            return [
                b"<html><body>"
                b"<h1>Internal Server Error</h1>"
                b"<p>An internal server error has occurred.</p>"
                b"</body></html>"
            ]

    def handle_request(self, request):
        """ This method gets called by __call__ to perform request handling. """
        self.dispatcher.dispatch(request)

    def handle_exception(self, ex, request=None):
        """ Handle an exception. """

        try:
            debug = bool(self.get_config("webapp.debug", False))
        except ValueError:
            debug = False

        try:
            tbcapture = io.StringIO()
            traceback.print_exception(
                etype=type(ex),
                value=ex,
                tb=ex.__traceback__,
                file=tbcapture
            )

            self.error_log.write(tbcapture.getvalue() + "\n")
            self.error_log.flush()
            if request is None:
                return

            response = request.response
            response.reset()
            response.status = 500
            response.content_type = "text/html"

            if not debug:
                response.content = [
                    b"<html><body>"
                    b"<h1>Internal Server Error</h1>"
                    b"<p>An internal server error has occurred.</p>"
                    b"</body></html>"
                ]
                return

            response.content = [
                b"<html><body>"
                b"<h1>Exception Occurred</h1>"
                b"<pre>" + html.escape(tbcapture.getvalue()).encode("utf-8") + b"</pre>"
                b"</body></html>"
            ]
            return

        except: # pylint: disable=bare-except
            # Not ideal but we don't want to dump the exceptions to the user
            pass
