""" Store and lookup path to route maps. """

from __future__ import absolute_import

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2019 Brian Allen Vanderburg II"
__license__ = "Apache License 2.0"

__all__ = ["Router"]


from collections import OrderedDict
import re

from .error import RouteError


class _PathSegment:
    """ An entry for a path segment. """

    def __init__(self):
        """ Initialize our subpath segments and route for this segment. """
        self.static = OrderedDict() # Dict keys are path component
        self.dynamic = OrderedDict() # Dict keys are (matchall, regex)
        self.route = None

    def find_match(self, parts, params):
        """ Find a submatch of the given path. """

        # No more parts, we are the match
        if not parts:
            if self.route is not None:
                return (self.route, params)

            return None

        part = parts[0]

        # Check the static first
        if part in self.static:
            result = self.static[part].find_match(parts[1:], params)
            if result is not None:
                return result

        # Unable to find in static, we'll check dynamic next
        for (matchall, regex) in self.dynamic:
            if matchall:
                matchpart = "/".join(parts)
            else:
                matchpart = part

            matched = regex.match(matchpart)
            if matched:
                # clone so if subpath segments fail we don't mess up parent path parameters
                matched_params = dict(params)
                matched_params.update(matched.groupdict())

                if matchall:
                    subparts = []
                else:
                    subparts = parts[1:]

                result = self.dynamic[(matchall, regex)].find_match(subparts, matched_params)
                if result is not None:
                    return result

        # Got here with no match
        return None


class Router:
    """ A path -> router router. """

    _VAR_SPLIT_RE = re.compile("(<.*?>)")
    _NAMED_STRIP_RE = re.compile("<([a-zA-Z0-9_]+)(:[^>]+)?>")
    _NAMED_REPLACE_RE = re.compile("<([a-zA-Z0-9_]+)>")


    def __init__(self):
        """ Initialize the method entry. """

        self._routes = {} # path -> route for each method
        self._named = {} # name -> path for each method

        # We keep our own regex cache to ensure identical regular expressions
        # always match the same regex compiled object even if the python
        # internal cache is cleared
        self._re_cache = {}

    def register(self, path, route, name=None, method="GET"):
        """ Register a path to a given route. """

        method = method.upper()
        if method in self._routes:
            target = self._routes[method]
        else:
            target = self._routes[method] = _PathSegment()

        # Register the path -> route
        segments = self._split_path(path)
        for part in segments:
            if isinstance(part, tuple):
                target = target.dynamic.setdefault(part, _PathSegment())
            else:
                target = target.static.setdefault(part, _PathSegment())

        target.route = route

        # Register the name -> path
        if name is not None:
            if method not in self._named:
                self._named[method] = {}

            self._named[method][name] = self._NAMED_STRIP_RE.sub(
                "<\\1>",
                path
            )

    def _split_path(self, path):
        """  split our path into individual components. """

        parts = path.split("/")
        # We keep any leading blanks that way a path can be registered that
        # matches empty PATHINFO as well

        if not parts:
            return []

        for poffset, part in enumerate(parts):

            re_found = False # Is this part static or regex
            matchall_found = False # Is this regex a match all regex

            matches = list(i for i in self._VAR_SPLIT_RE.split(part) if i) # strip blanks
            for moffset, match in enumerate(matches):
                if match[0:1] == "<" and match[-1:] == ">":
                    re_found = True

                    (matchall, matches[moffset]) = self._parse_var(match[1:-1])
                    if matchall:
                        matchall_found = True

                        # matchall should be the last part and the last match
                        if poffset < len(parts) - 1:
                            raise ValueError("Match all filter should only be the last part of the last component")

                        if moffset < len(matches) - 1:
                            raise ValueError("match all filter should only be the last part of the last component")
                else:
                    matches[moffset] = re.escape(match)

            # If this was regex, then compile it, else no changes
            if re_found:
                # Reuse the same regex from cache if already compiled to ensure
                # matching regex adds under a given segmetn always go to the same
                # _PathSegment object
                regex_str = "^" + "".join(matches) + "$"
                regex = self._re_cache.get(regex_str, None)
                if regex is None:
                    regex = self._re_cache[regex_str] = re.compile(regex_str)

                parts[poffset] = (matchall_found, regex)

        return parts

    @staticmethod
    def _parse_var(part):
        """ Parse the variable part for a regular expression.
            Return value is a  tuple (matchall, regex).
        """
        parts = part.split(":", 1)
        name = parts[0]

        if len(parts) == 1:
            matchall = False
            regex = "[^\\/]+"
        else:
            vartype = parts[1]

            if vartype == "int":
                matchall = False
                regex = "-?\\d+"
            elif vartype == "float":
                matchall = False
                regex = "-?[\\d.]+"
            elif vartype == "path":
                matchall = True
                regex = ".*" # Note that path can match blank elements as well
            elif vartype[0:3] == "re:":
                matchall = False
                regex = vartype[3:]
            elif vartype[0:4] == "re*:":
                matchall = True
                regex = vartype[4:]
            else:
                raise ValueError("Unknown route filter: " + vartype)

        return (matchall, "(?P<{0}>{1})".format(name, regex))

    def route(self, path, method="GET"):
        """ For a given path return the route or None. """
        method = method.upper()
        parts = path.split("/")
        # Keep leading blanks as well to be able to match empty PATHINFO

        if method not in self._routes:
            return None

        params = {}
        return self._routes[method].find_match(parts, params)

    def get(self, name, params, method="GET"):
        """ Get a path from a named entry. """
        method = method.upper()
        if method not in self._named:
            raise RouteError("No such named path: " + name)

        if name not in self._named[method]:
            raise RouteError("No such named path: " + name)

        def subfn(mo):
            key = mo.group(1)
            if key not in params:
                raise RouteError("No parameter for named path: " + key)

            return str(params[key])

        return self._NAMED_REPLACE_RE.sub(subfn, self._named[method][name])


