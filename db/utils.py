from google.appengine.datastore.datastore_query import Cursor
from django.db import models, DEFAULT_DB_ALIAS

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.


class CursorQueryMixin(object):

    def clone(self, *args, **kwargs):
        kwargs['_gae_cursor'] = getattr(self, '_gae_cursor', None)
        kwargs['_gae_start_cursor'] = getattr(self, '_gae_start_cursor', None)
        kwargs['_gae_end_cursor'] = getattr(self, '_gae_end_cursor', None)
        return super(CursorQueryMixin, self).clone(*args, **kwargs)


def get_cursor(queryset):
    # Evaluate QuerySet.
    len(queryset)
    cursor = getattr(queryset.query, '_gae_cursor', None)
    return Cursor.to_websafe_string(cursor)


def set_cursor(queryset, start=None, end=None):
    queryset = queryset.all()

    class CursorQuery(CursorQueryMixin, queryset.query.__class__):
        pass

    queryset.query = queryset.query.clone(klass=CursorQuery)
    if start is not None:
        start = Cursor.from_websafe_string(start)
    queryset.query._gae_start_cursor = start
    if end is not None:
        end = Cursor.from_websafe_string(end)
    queryset.query._gae_end_cursor = end
    return queryset


def commit_locked(func_or_using=None):
    """
    Decorator that locks rows on DB reads.
    """

    def inner_commit_locked(func, using=None):

        def _commit_locked(*args, **kw):
            from google.appengine.api.datastore import RunInTransaction
            return RunInTransaction(func, *args, **kw)

        return wraps(func)(_commit_locked)

    if func_or_using is None:
        func_or_using = DEFAULT_DB_ALIAS
    if callable(func_or_using):
        return inner_commit_locked(func_or_using, DEFAULT_DB_ALIAS)
    return lambda func: inner_commit_locked(func, func_or_using)
