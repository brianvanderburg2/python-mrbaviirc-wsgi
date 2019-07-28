""" Web app request base class. """

from __future__ import absolute_import

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2018 Brian Allen Vanderburg II"
__license__ = "Apache License 2.0"


__all__ = ["Request"]


import cgi
from http.cookies import SimpleCookie, CookieError
import tempfile
import time
from urllib.parse import urlsplit
from urllib.parse import parse_qs

from mrbaviirc.common.util.functools import lazyprop


class _FakeFile:
    """ A fake file-like object for initiating a callback every so often
        on reading data. For use with cgi.FieldStorage.  The read and readline
        methods of the fp object should return bytes."""
    def __init__(self, fp, callback, threshold=1024000):
        self._fp = fp
        self._callback = callback
        self._threshold = threshold if threshold > 0 else 1024000
        self._current = 0
        self._bytes_read = 0

    def _fake_read(self, size, readline=False):
        """ Read some of the file. """

        this_total = 0
        this_data = []
        if size is not None and size <= 0:
            size = None

        if readline:
            readfunc = self._fp.readline
        else:
            readfunc = self._fp.read

        while True:
            size_to_read = self._threshold - self._current
            if size is not None:
                size_to_read = min(size - this_total, size_to_read)

            data = readfunc(size_to_read)
            this_data.append(data)

            this_total += len(data)
            self._current += len(data)
            self._bytes_read += len(data)

            if self._current >= self._threshold:
                self._current = 0
                self._callback(self._bytes_read)

            if (size is not None and this_total >= size) or len(data) == 0:
                # Call callback one more time with final size read
                self._callback(self._bytes_read)
                return b''.join(this_data)

            if readline and this_data[-1][-1:] == b"\n":
                # Handle if this was a readline, return on end of line
                self._callback(self._bytes_read)
                return b''.join(this_data)

    def read(self, size=None):
        return self._fake_read(size, readline=False)

    def readline(self, size=None):
        return self._fake_read(size, readline=True)


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
            
        return tempfile.TemporaryFile("w+", dir=tmpdir,
            encoding=self.encoding, newline="\n")


class _FileInfo:
    def __init__(self, file, filename):
        self.file = file # The file object for reading
        self.filename = filename # Filename on upload


class Request:
    """ Represent a request. """

    def __init__(self, app, environ):
        self.app = app
        self.environ = environ

        self.cookies = {}
        self.get = {}
        self.post = {}
        self.params = {} # Parsed from router
        self.userdata = {} # Customer parameters to pass around
        self.files = {}
        self.timer = None

        # wsgi specific information
        self.wsgi_multithreaded = environ.get("wsgi.multithread", "")
        self.wsgi_multiprocess = environ.get("wsgi.multiprocess", "")
        self.wsgi_run_once = environ.get("wsgi.run_once", "")
        self.wsgi_input = environ.get("wsgi.input", None)


        # Details about request
        self.scheme = environ.get("wsgi.scheme")
        self.request_uri = environ.get("REQUEST_URI", "")
        self.method = environ.get("REQUEST_METHOD", "UNKNOWN").lower()
        self.path_info = environ.get("PATH_INFO", "")
        self.script_name = environ.get("SCRIPT_NAME", "")
        self.query_string = environ.get("QUERY_STRING", "")
        self.user_agent = environ.get("HTTP_USER_AGENT", "")
        self.remote_addr = environ.get("REMOTE_ADDR", "")

        self.request_size = 0
        if self.method == "post":
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

    def init(self):
        """ Initialize the request. """
        # TODO: some of the above should probably be moved here. Or perhaps
        # All of this should be in __init__

        self.timer = time.monotonic()

        # Handle POST request
        if self.method == "post":
            self._handle_post()

        # Handle sessions

    def finalize(self):
        """ Cleanup the request. """
        pass


    def _handle_post_callback(self, bytes_read):
        """ Callback for reading info into field storage. """

        self.request_size = bytes_read
        try:
            max_request_size = int(self.app.get_config("webapp.request.maxsize", 102400))
        except ValueError:
            max_request_size = 102400

        try:
            max_request_time = int(self.app.get_config("webapp.request.maxtime", 30))
        except ValueError:
            max_request_time = 30

        if bytes_read > max_request_size:
            raise OverflowError("Request body size exceeded maximum size of " + str(max_request_size))

        if time.monotonic() - self.timer > max_request_time:
            raise TimeoutError("Request time exceeded maximum time of " + str(max_request_time))

    def _handle_post(self):
        """ Handle any POST data. """

        fakefile = _FakeFile(self.wsgi_input, self._handle_post_callback)

        # We do not want FieldStorage to get parameters from QUERY_STRING
        tmpdir = self.app.get_config("webapp.upload.tmpdir", None)
        postenv = self.environ.copy()
        postenv["QUERY_STRING"] = "" # Don't want POST getting fields from query string
        form = _FieldStorage(fp=fakefile, environ=postenv, keep_blank_values=True, tmpdir=tmpdir)

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

        # TODO: Check webapp.upload.maxcount/maxfilesize

    @lazyprop
    def response(self):
        """ Create our response object for this request. """
        return self.app.call_factory("webapp.response", self)
