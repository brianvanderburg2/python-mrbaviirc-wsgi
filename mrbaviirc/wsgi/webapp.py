""" Web app helper class. """

from __future__ import absolute_import

__author__      =   "Brian Allen Vanderburg II"
__copyright__   =   "Copyright (C) 2018 Brian Allen Vanderburg II"
__license__     =   "Apache License 2.0"


from ...util.imp import Exporter
from ..base import BaseAppHelper

from .request import Request
from .response import Response


export = Exporter(globals())


@export
class WebAppHelper(BaseAppHelper):
    """ A helper class for web applications. """

    def __init__(self):
        """ Initialize a web application. """
        BaseAppHelper.__init__(self)

    def setup(self):
        """ Set up the web app. """
        self.register_factory("webapp.request", Request)
        self.register_factory("webapp.response", Response)

    def __call__(self, environ, start_response):

        # Create request object
        request = self.resolve_service("webapp.request", self, environ)

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
        pass
        

