""" Error classes. """

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright 2019 Biran Allen Vanderburg II"
__license__ = "Apache License 2.0"


__all__ = [
    "Error", "AppError", "RouteError", "RequestError"
]


class Error(Exception):
    """ A basic error for mrbaviirc.wsgi. """
    pass

class AppError(Error):
    pass

class ConfigError(Error):
    pass

class RouteError(Error):
    pass

class RequestError(Error):
    pass


