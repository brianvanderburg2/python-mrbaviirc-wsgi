""" Web app request base class. """

from __future__ import absolute_import

__author__      =   "Brian Allen Vanderburg II"
__copyright__   =   "Copyright (C) 2018 Brian Allen Vanderburg II"
__license__     =   "Apache License 2.0"


try:
    from urllib.parse import urlsplit
except ImportError:
    from urlparse import urlsplit

try:
    from urllib.parse import parse_qs
except ImportError:
    from urlparse import parse_qs

try:
    from http.cookies import SimpleCookie, CookieError
except ImportError:
    from Cookie import SimpleCookie, CookieError
    

from ...util.imp import Exporter
from ...util.functools import lazyprop


export = Exporter(globals())


@export
class Request(object):
    """ Represent a request. """

    def __init__(self, app, environ):
        self.app = app
        self.environ = environ

        self.cookies = {}
        self.get = {}
        self.post = {}
        self.params = {}
        self.pathparts = []
        self.files = None

        # wsgi specific information
        self.wsgi_multithreaded = environ.get("wsgi.multithread", "")
        self.wsgi_multiprocess = environ.get("wsgi.multiprocess", "")
        self.wsgi_run_once = environ.get("wsgi.run_once", "")

        
        # Details about request
        self.scheme = environ.get("wsgi.scheme")
        self.request_uri = environ.get("REQUEST_URI", "")
        self.method = environ.get("REQEUEST_METHOD", "UNKNOWN").lower()
        self.path_info = environ.get("PATH_INFO", "")
        self.script_name = environ.get("SCRIPT_NAME", "")
        self.query_string = environ.get("QUERY_STRING", "")
        self.user_agent = environ.get("HTTP_USER_AGENT", "")
        self.remote_addr = environ.get("REMOTE_ADDR", "")


        # Determine host, domain, and port
        host = environ.get("HTTP_HOST", None)
        if host is not None:
            # Get host, domain, and port (if possible) from host
            self.host = host
            
            split = urlsplit("//{0}".format(host))
            self.domain = split.hostname
            if split.port:
                self.port = int(split.port)
            else:
                # port wasn't specified in host, determine from scheme
                self.port = {"http": 80, "https": 443}.get(self.scheme) 
        else:
            # Host not specified, build from parts
            self.domain = environ.get("SERVER_NAME")
            port = environ.get("SERVER_PORT", None)
            if port is not None:
                self.port = int(port)
                self.host = "{0}:{1}".format(self.domain, self.port)
            else:
                self.port = {"http": 80, "https": 443}.get(self.scheme)
                self.host = self.domain # Leave without :port 

        # Parse our query string
        self.get = parse_qs(self.query_string)

        # Parse our cookies if any
        cookies = environ.get("HTTP_COOKIE", "")
        if cookies is not None:
            cookies = SimpleCookie(cookies)
            self.cookies = {i: cookies[i].value for i in cookies}
        else:
            self.cookies = {}


    def init(self):
        # We need to parse a bit of the request information
        # to handle any file uploads/post information
        # Uploads are allowed depending on settings
        # webapp.uploads.max-count
        # webapp.uploads.max-total-size
        # webapp.uploads.max-file-size
        # webapp.uploads.max-time
        # webapp.uploads.temp-path
        pass
        

    @lazyprop
    def response(self):
        """ Create our response object for this request. """
        return self.app.resolve_service("webapp.response", self)
        
