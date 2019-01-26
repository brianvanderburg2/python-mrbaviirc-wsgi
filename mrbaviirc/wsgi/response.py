""" Web app response base class. """

from __future__ import absolute_import

__author__      =   "Brian Allen Vanderburg II"
__copyright__   =   "Copyright (C) 2018 Brian Allen Vanderburg II"
__license__     =   "Apache License 2.0"


from ...util.imp import Exporter


export = Exporter(globals())


@export
class Response(object):

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
        306: "unused",
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

    def __init__(self, request):
        self.request = request
        self.app = request.app

        self.status = 500 # If not set, default to server error

        self.headers = {}
        self.cookies = {}
        self.content_type = None
        self.content_length = None

        self.content = ()

    def get_headers(self):
        headers = []
        if self.content_type:
            headers.append(("Content-Type", self.content_type))

        for (name, value) in self.headers.items():
            headers.append((name, value))

        return headers
        
    def get_status(self):
        return "{0} {1}".format(str(self.status), str(self.STATUS_CODES[self.status]))

