""" An exchange represents a request and a response. """

from __future__ import absolute_import

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2018-2020 Brian Allen Vanderburg II"
__license__ = "Apache License 2.0"


__all__ = ["Exchange", "Request", "Response"]


import cgi
from http.cookies import SimpleCookie #, CookieError
import tempfile
import time
from urllib.parse import urlsplit
from urllib.parse import parse_qs

from mrbaviirc.common.functools import lazy_property


class _FieldStorage(cgi.FieldStorage):
    """ Control where the temp files are created. """

    def __init__(self, *args, **kwargs):
        tmpdir = kwargs.pop("tmpdir", None)
        cgi.FieldStorage.__init__(self, *args, **kwargs)
        self.__tmpdir = tmpdir

    def make_file(self):
        tmpdir = self.__dict__.get("_FieldStorage__tmpdir", None)
        if self._binary_file:
            return tempfile.TemporaryFile("wb+", dir=tmpdir)

        return tempfile.TemporaryFile(
            "w+", dir=tmpdir, encoding=self.encoding, newline="\n"
        )


class _FileInfo:
    def __init__(self, file, filename):
        self.file = file # The file object for reading
        self.filename = filename # Filename on upload


class Request:
    """ Represent a request. """

    def __init__(self, exchange):
        """ Initialize the request"""
        self.exchange = exchange

        environ = exchange.environ

        self.cookies = {} # name:value pairs for cookies
        self.get = {} # name: [value, value] GET data
        self.post = {} # name: [value, value] POST data
        self.params = {} # Parsed from router
        self.userdata = {} # Customer parameters to pass around
        self.files = {} # Parsed by upload

        # wsgi specific information
        self.wsgi_multithreaded = environ.get("wsgi.multithread", "")
        self.wsgi_multiprocess = environ.get("wsgi.multiprocess", "")
        self.wsgi_run_once = environ.get("wsgi.run_once", "")
        self.wsgi_input = environ.get("wsgi.input", None)


        # Details about request
        self.scheme = environ.get("wsgi.url_scheme")
        self.request_uri = environ.get("REQUEST_URI", "")
        self.method = environ.get("REQUEST_METHOD", "UNKNOWN").upper()
        self.path_info = environ.get("PATH_INFO", "")
        self.script_name = environ.get("SCRIPT_NAME", "")
        self.query_string = environ.get("QUERY_STRING", "")
        self.user_agent = environ.get("HTTP_USER_AGENT", "")
        self.remote_addr = environ.get("REMOTE_ADDR", "")

        if self.method == "POST":
            self.content_type = environ.get(
                "CONTENT_TYPE",
                "application/x-www-form-urlencoded"
            )
            try:
                self.content_length = int(environ.get("CONTENT_LENGTH", 0))
            except ValueError:
                self.content_length = 0
        else:
            self.content_type = ""
            self.content_length = 0

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

        # Handle POST request
        if self.method == "POST":
            self._handle_post()

    def _handle_post(self):
        """ Handle any POST data. """
        app = self.exchange.app
        environ = self.exchange.environ

        tmpdir = app.config.get("webapp.upload.tmpdir", None)
        postenv = environ.copy()
        postenv["QUERY_STRING"] = "" # Don't want POST getting fields from query string
        form = _FieldStorage(fp=self.wsgi_input, environ=postenv, keep_blank_values=True, tmpdir=tmpdir)

        # Process each item.  In our data, we want to store everything as a list
        for key in form.keys():
            if key is None:
                continue

            items = form[key]
            if not isinstance(items, (list, tuple)):
                items = [items]

            for item in items:
                if item.file and item.filename:
                    # cgi.FieldStorage create a file for everything it seems, even
                    # for regular non-file parameters, so we only treat items with
                    # a filename value as a file.

                    item.file.seek(0)
                    fileslist = self.files.setdefault(item.name, [])
                    fileslist.append(_FileInfo(item.file, item.filename))
                else:
                    # Value
                    valuelist = self.post.setdefault(item.name, [])
                    value = item.value
                    # I think cgi.FieldStorage already decodes the bytes, just to be sure
                    if isinstance(value, bytes):
                        value = value.decode("utf-8") # TODO - get encoding from request
                    if value is not None:
                        valuelist.append(str(value))


class Response:
    """ Represent a response to a request. """

    STATUS_CODES = {
        100: "Continue",
        101: "Switching Protocol",
        102: "Processing (WebDAV)",
        200: "OK",
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        207: "Multi-Status (WebDAV)",
        208: "Multi-Status (WebDAV)",
        226: "IM Used (HTTP Delta encoding)",
        300: "Multiple Choice",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy",
        306: "Unused",
        307: "Temporary Redirect",
        308: "Permanent Redirect",
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request Timeout",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Payload Too Large",
        414: "URI Too Long",
        415: "Unsupported Media Type",
        416: "Requested Range Not Satisfiable",
        417: "Expectation Failed",
        418: "I'm a teapot",
        421: "Misdirected Request",
        422: "Unprocessable Entity (WebDAV)",
        423: "Locked (WebDAV)",
        424: "Failed Dependency (WebDAV)",
        426: "Upgrade Required",
        428: "Precondition Required",
        429: "Too Many Requests",
        431: "Request Header Fields Too Large",
        451: "Unavailable For Legal Reasons",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        505: "HTTP Version Not Supported",
        506: "Variant Also Negotiates",
        507: "Insufficient Storage",
        508: "Loop Detected (WebDAV)",
        510: "Not Extended",
        511: "Network Authentication Required"
    }

    def __init__(self, exchange):
        """ Initialize the response. """
        self.exchange = exchange
        self.reset()

    def reset(self):
        """ Reset the response. """
        self.status = 500 # If not set, default to server error

        self.headers = {}
        self.cookies = {}
        self.content_type = None
        self.content_length = None

        self.content = ()

    def get_headers(self):
        """ Get the headers of the response. """
        headers = []
        if self.content_type:
            headers.append(("Content-Type", self.content_type))

        for (name, value) in self.headers.items():
            headers.append((name, value))

        return headers

    def get_status(self):
        """ Get the status line of the response. """
        return "{0} {1}".format(str(self.status), str(self.STATUS_CODES[self.status]))


class Exchange:
    """ An exchange is just a request and response pair. """

    def __init__(self, app, environ):
        """ Initialize the exchange. """
        self.app = app
        self.environ = environ
        self.timer = None

        self.response = Response(self) # We always have a response object
        self.request = None # Not created until the exchange is started
        # self.session = Session(app)

    def start(self):
        """ Initialize the exchange. """
        self.timer = time.monotonic()
        self.request = Request(self)
        # self.session.init(self.request)

    def finalize(self):
        """ Finalize the exchange. """
        # self.session.finalize(self.response)

