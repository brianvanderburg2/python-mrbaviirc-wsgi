""" Dispatch requests. """

from __future__ import absolute_import

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2019 Brian Allen Vanderburg II"
__license__ = "Apache License 2.0"


__all__ = ["Dispatcher"]


from .response import Response
from .router import Router


class Dispatcher:
    """ Dispatch requests to registered callbacks. """

    def __init__(self):
        """ Initialize the dispatcher. """

        self._routes = {}
        self._notfound_callback = None
        self._error_handler = None

    def register(self, path, callback, name=None, method="get"):
        """ Register a route to dispatch. """

        method = method.lower()
        if method in self._routes:
            routes = self._routes[method]
        else:
            routes = self._routes[method] = Router()

        routes.register(path, callback, name=name)

    def get(self, name, params, method="get"):
        """ Get a path from a named route. """

        method = method.lower()
        routes = self._routes.get(method, None)
        if routes is None:
            raise LookupError("No routes for method: " + method)

        return routes.get(name, params)

    def dispatch(self, request):
        """ Dispatch a request to a callback. """
        method = request.method.lower()
        path = request.path_info

        routes = self._routes.get(method, None)
        if routes is None:
            self._notfound(request)
            return

        try:
            (callback, params) = routes.route(path)
        except LookupError:
            self._notfound(request)
            return

        try:
            request.params.update(params)
            callback(request)
            return
        except Exception as ex:
            if self._error_handler:
                self._error_handler(ex, request)
                return
            raise

    def _notfound(self, request):
        """ Handle a not found route. """
        if self._notfound_callback:
            self._notfound_callback(request)
            return

        response = request.response
        response.status = 404
        response.content_type = "text/html"
        response.content = [
            b"<html><body>"
            b"<h1>Not Found</h1>"
            b"<p>The requested resource was not found on this server.</p>"
            b"</body></html>"
        ]

    def set_notfound_callback(self, callback):
        """ Set the callback to use for a notfound result. """
        self._notfound_callback = callback

    def set_error_handler(self, handler):
        """ Set a handler to handle exceptions caught from the dispatch.
            If a handler is not set, then the exception will be reraised. """
        self._error_handler = handler
