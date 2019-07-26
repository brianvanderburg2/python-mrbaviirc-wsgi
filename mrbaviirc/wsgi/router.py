""" Route requests. """

from __future__ import absolute_import

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2019 Brian Allen Vanderburg II"
__license__ = "Apache License 2.0"

__all__ = ["Router"]


from collections import OrderedDict
import re


class _RouteEntry:
    """ An entry for a route segment. """

    def __init__(self):
        """ Initialize our subroutes and target for self. """
        self.static = OrderedDict() # Dict keys are path component
        self.dynamic = OrderedDict() # Dict keys are (matchall, regex)
        self.callback = None

    def find_match(self, parts, params):
        """ Find a submatch of the given path. """

        # No more parts, we are the match
        if not parts:
            if self.callback is None:
                # Raise error so we can seach other branches to find router with callback
                raise LookupError("No callback found.")

            return (self.callback, params)


        part = parts[0]

        # Check the static first
        if part in self.static:
            try:
                return self.static[part].find_match(parts[1:], params)
            except LookupError:
                pass # Unable to find in static, we'll check dynamic next

        for (matchall, regex) in self.dynamic:
            if matchall:
                matchpart = "/".join(parts)
            else:
                matchpart = part

            matched = regex.match(matchpart)
            if matched:
                # clone so if subroutes fail we don't mess up parent route parameters
                matched_params = dict(params)
                matched_params.update(matched.groupdict())

                if matchall:
                    subparts = []
                else:
                    subparts = parts[1:]

                try:
                    return self.dynamic[(matchall, regex)].find_match(subparts, matched_params)
                except LookupError:
                    pass # Try next dynamic route

        # Got here with no match
        raise LookupError("Unmatched path: " + "/".join(parts))


class Router:
    """ Route a request. """

    _VAR_SPLIT_RE = re.compile("(<.*?>)")
    _NAMED_STRIP_RE = re.compile("<([a-zA-Z0-9_]+)(:[^>]+)?>")
    _NAMED_REPLACE_RE = re.compile("<([a-zA-Z0-9_]+)>")

    def __init__(self):
        """ Initialize router. """

        self._routes = _RouteEntry()
        self._named = {}

        # We keep our own route cache to ensure identical regular expressions
        # are represented by the same tree node, even if for some reason the
        # Python compiled RE cache gets cleared between route additions.
        self._re_cache = {}

    def register(self, route, callback, name=None):
        """ Register a given route. """

        # Register the path -> route
        segments = self._split(route)
        target = self._routes

        for part in segments:
            if isinstance(part, tuple):
                target = target.dynamic.setdefault(part, _RouteEntry())
            else:
                target = target.static.setdefault(part, _RouteEntry())

        target.callback = callback

        # Register the name -> path
        if name is not None:
            self._named[name] = self._NAMED_STRIP_RE.sub(
                "<\\1>",
                route
            )

    def _split(self, route):
        """  split our route into individual components. """

        parts = route.split("/")
        if parts[0] == "":
            parts.pop(0)

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
                # Reuse the same regex from cache if already compiled
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

    def route(self, path):
        """ Route a given request. """

        parts = path.split("/")
        if parts[0] == "":
            parts.pop(0)

        params = {}

        # We do recursive lookup so if a match isn't found in one path of the
        # registered trees (such as a static name), but another path such as
        # a regex can match, it will still return a result.  Will also handle
        # if two different regex patterns may match a result.
        return self._routes.find_match(parts, params)

    def get(self, name, params):
        """ Get a path from a named route. """
        if name not in self._named:
            raise LookupError("No such named route: " + name)

        def subfn(mo):
            key = mo.group(1)
            if key not in params:
                raise LookupError("No parameter for named route: " + key)

            return str(params[key])

        return self._NAMED_REPLACE_RE.sub(subfn, self._named[name])
