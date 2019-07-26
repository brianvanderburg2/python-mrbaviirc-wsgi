""" Test the router module. """


import pytest


from ..router import Router


def _fn1():
    pass

def _fn2():
    pass

def _fn3():
    pass


def test_route():
    r = Router()

    # General registrations
    r.register("/a/b", _fn1)
    r.register("/a/b/<name>", _fn2)
    r.register("/a/b/<name>/<subname>", _fn3)


    (cb, params) = r.route("/a/b")
    assert cb == _fn1
    assert params == {}

    (cb, params) = r.route("/a/b/c")
    assert cb == _fn2
    assert params == {"name": "c"}

    (cb, params) = r.route("/a/b/c/d")
    assert cb == _fn3
    assert params == {"name": "c", "subname": "d"}

    with pytest.raises(LookupError):
        r.route("/a/b/")

    # Ensure if lookup fails, next branch is checked

    r.register("/c/d/<name:int>/<subname>", _fn1)
    r.register("/c/d/<name>", _fn2)
    r.register("/c/d/<name>/<path:path>", _fn3, name="test")

    (cb, params) = r.route("/c/d/37/test")
    assert cb == _fn1
    assert params == {"name": "37", "subname": "test"}

    # this matches the first part, but no callback so next branch is checked
    (cb, params) = r.route("/c/d/38") 
    assert cb == _fn2
    assert params == {"name": "38"}

    r.register("/c/d/<name:int>", _fn3) # adding callback, 
    (cb, params) = r.route("/c/d/38") 
    assert cb == _fn3
    assert params == {"name": "38"}

    (cb, params) = r.route("/c/d/37c/test")
    assert cb == _fn3
    assert params == {"name": "37c", "path": "test"}

    (cb, params) = r.route("/c/d/38/something/else/here/")
    assert cb == _fn3
    assert params == {"name": "38", "path": "something/else/here/"}

    path = r.get("test", {"name": "smith", "path": "nothing/here"})
    assert path == "/c/d/smith/nothing/here"

    with pytest.raises(LookupError):
        r.get("test2", {})
    
