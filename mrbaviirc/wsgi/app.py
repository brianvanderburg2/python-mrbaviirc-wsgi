""" Web app helper class. """

from __future__ import absolute_import

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2018 Brian Allen Vanderburg II"
__license__ = "Apache License 2.0"


__all__ = ["WsgiApp"]


import html
import io
import traceback

import logging

from mrbaviirc.common.app import BaseApp
from mrbaviirc.common.functools import lazy_property
from mrbaviirc.common.logging import SharedLogFile

from .router import Router
from .error import * # pylint: disable=wildcard-import,unused-wildcard-import
from .exchange import Exchange

class WsgiApp(BaseApp):
    """ A helper class for web applications. """

    def __init__(self):
        """ Initialize a web application. """
        BaseApp.__init__(self)

        # Configs
        self.config.set("webapp.debug", False)

        # Properties
        self.__startup_called = False

        self.router = Router()

        # TODO: better logging
        # leave request logging to the application server (apache/etc)
        # leave error logging as well, just write errors to stderr)
        self._logger = logging.getLogger(self.appname)
        self._logger.propagate = False
        self._logger.addHandler(logging.StreamHandler())

    def startup(self):
        """ Startup the application.
            This must be called after the application is created but before
            it is used for request handling. If the "run" method is used
            it automatically calls startup.
        """
        BaseApp.startup(self)
        self.__startup_called = True

    @property
    def appname(self):
        # pylint: disable=no-self-use
        return "mrbaviirc.wsgi.app"

    def create_exchange(self, environ):
        """ Create the exchange object.
        """
        return Exchange(self, environ)

    def route(self, path, method="GET", name=None):
        def wrapper(fn):
            self.router.register(path, fn, method=method, name=name)
            return fn
        return wrapper

    def run(self, host, port, threaded=False, processes=1):
        """ Run the app. """
        if not self.__startup_called:
            self.startup()

        from werkzeug.serving import run_simple

        run_simple(host, port, self, threaded=threaded, processes=processes)

        # call shutdown even though it normally isn't used since other methods
        # of serving may not provide support to call the shutdown method
        self.shutdown()

    def __call__(self, environ, start_response):
        """ Handle a request call """

        if not self.__startup_called:
            raise AppError("startup must be called before requests are handled")

        exchange = self.create_exchange(environ)

        # Process request
        try:
            exchange.start()
            self.handle_request(exchange)
            exchange.finalize()
        except Exception as ex: # pylint: disable=broad-except
            self.handle_exception(ex, exchange)

        # Return the response
        response = exchange.response
        try:
            start_response(
                response.get_status(),
                response.get_headers()
            )

            # Build return based on type
            if isinstance(response.content, str):
                return [response.content.encode("utf-8")]

            if isinstance(response.content, bytes):
                return [response.content]

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

    def handle_request(self, exchange):
        """ This method gets called by __call__ to perform request handling. """
        request = exchange.request
        method = request.method.upper()
        path = request.path_info

        # Find route
        result = self.router.route(path, method=method)
        if result is None:
            self.handle_notfound(exchange)
        else:
            (route, params) = result
            request.params.update(params)
            route(exchange)

    def handle_exception(self, ex, exchange=None):
        """ Handle an exception. """

        try:
            debug = bool(self.config.get("webapp.debug", False))
        except ValueError:
            debug = False

        # Get the traceback
        tbcapture = io.StringIO()
        traceback.print_exception(
            etype=type(ex),
            value=ex,
            tb=ex.__traceback__,
            file=tbcapture
        )

        error_message = tbcapture.getvalue()

        # Write to the error log
        self._logger.error(error_message)

        # Write to the client
        if exchange is None:
            return

        try:
            response = exchange.response
            response.reset()
            response.status = 500
            response.content_type = "text/html"

            if not debug:
                response.content = (
                    "<html><body>"
                    "<h1>Internal Server Error</h1>"
                    "<p>An internal server error has occurred.</p>"
                    "</body></html>"
                )
                return

            response.content = (
                "<html><body>"
                "<h1>Exception Occurred</h1>"
                "<pre>" + html.escape(error_message) + "</pre>"
                "</body></html>"
            )
            return

        except: # pylint: disable=bare-except
            # Not ideal but we don't want to dump the exceptions to the user
            pass

    def handle_notfound(self, exchange):
        request = exchange.request
        response = exchange.response

        response.status = 404
        response.content_type = "text/html"
        response.content = (
            "The requested page could not be found.  Please try again."
        )
