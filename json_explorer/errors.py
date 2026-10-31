"""Exception hierarchy for json_explorer.

Every error raised on purpose by the package derives from
:class:`JsonExplorerError`, so callers can catch all of them at once::

    try:
        code = quick_generate(data, "go")
    except JsonExplorerError as e:
        ...
"""


class JsonExplorerError(Exception):
    """Base class for all json_explorer errors."""
