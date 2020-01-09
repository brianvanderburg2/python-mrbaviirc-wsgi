""" Web app helper class. """

from __future__ import absolute_import

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2018 Brian Allen Vanderburg II"
__license__ = "Apache License 2.0"


__all__ = ["WsgiApp"]


import html
import io
import traceback

from mrbaviirc.common.app import BaseApp
from mrbaviirc.common.functools import lazy_property
from mrbaviirc.common.logging import SharedLogFile

from .dispatcher import Dispatcher
from .error import * # pylint: disable=wildcard-import,unused-wildcard-import
from .request import Request


class WsgiApp(BaseApp):
    """ A helper class for web applications. """

    def __init__(self):
        """ Initialize a web application. """
        BaseApp.__init__(self)

        # Configs
        self.config.set("webapp.debug", False)

        self.config.set("webapp.logfile.error", None)
        self.config.set("webapp.logfile.request", None)

        self.config.set("webapp.request.maxsize", 1024000)
        self.config.set("webapp.request.maxtime", 30)

    def create_request(self, environ):
        """ Create the request object. """
        return Request(self, environ)

    @property
    def appname(self):
        # pylint: disable=no-self-use
        return "mrbaviirc.wsgi.app"

    @lazy_property
    def dispatcher(self):
        # pylint: disable=no-self-use
        """ Return this dispatcher. """
        return Dispatcher()

    @lazy_property
    def error_log(self):
        """ Get the error log. """
        filename = self.config.get("webapp.logfile.error")
        if filename is None:
            raise ConfigError("webapp.logfile.error not configured")
        return SharedLogFile(filename)

    @lazy_property
    def request_log(self):
        """ Get the request log. """
        filename = self.config.get("webapp.logfile.request")
        if filename is None:
            raise ConfigError("webapp.logfile.request not configured")
        return SharedLogFile(filename)

    def __call__(self, environ, start_response):

        # Create request object
        try:
            request = self.create_request(environ)
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
            debug = bool(self.config.get("webapp.debug", False))
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
