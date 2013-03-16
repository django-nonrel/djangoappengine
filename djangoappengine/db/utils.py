from django.db import DEFAULT_DB_ALIAS

from google.appengine.api.datastore import Key
from google.appengine.datastore.datastore_query import Cursor

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

class CursorQueryMixin(object):
    def clone(self, *args, **kwargs):
        kwargs['_gae_start_cursor'] = getattr(self, '_gae_start_cursor', None)
        kwargs['_gae_end_cursor'] = getattr(self, '_gae_end_cursor', None)
        kwargs['_gae_config'] = getattr(self, '_gae_config', None)
        return super(CursorQueryMixin, self).clone(*args, **kwargs)

def _add_mixin(queryset):
    if isinstance(queryset.query, CursorQueryMixin):
        return queryset

    queryset = queryset.all()

    class CursorQuery(CursorQueryMixin, queryset.query.__class__):
        pass

    queryset.query = queryset.query.clone(klass=CursorQuery)
    return queryset

def get_cursor(queryset):
    # Evaluate QuerySet
    if queryset._result_cache is None:
        len(queryset)

    cursor = None
    if hasattr(queryset.query, '_gae_cursor'):
        cursor = queryset.query._gae_cursor()
    return Cursor.to_websafe_string(cursor) if cursor else None

def set_cursor(queryset, start=None, end=None):
    queryset = _add_mixin(queryset)

    if start is not None:
        start = Cursor.from_websafe_string(start)
        setattr(queryset.query, '_gae_start_cursor', start)
    if end is not None:
        end = Cursor.from_websafe_string(end)
        setattr(queryset.query, '_gae_end_cursor', end)

    return queryset

def get_config(queryset):
    return getattr(queryset.query, '_gae_config', None)

def set_config(queryset, **kwargs):
    queryset = _add_mixin(queryset)
    setattr(queryset.query, '_gae_config', kwargs)
    return queryset

def commit_locked(func_or_using=None, retries=None, xg=False, propagation=None):
    """
    Decorator that locks rows on DB reads.
    """

    def inner_commit_locked(func, using=None):

        def _commit_locked(*args, **kw):
            from google.appengine.api.datastore import RunInTransactionOptions
            from google.appengine.datastore.datastore_rpc import TransactionOptions

            option_dict = {}

            if retries:
                option_dict['retries'] = retries

            if xg:
                option_dict['xg'] = True

            if propagation:
                option_dict['propagation'] = propagation

            options = TransactionOptions(**option_dict)
            return RunInTransactionOptions(options, func, *args, **kw)

        return wraps(func)(_commit_locked)

    if func_or_using is None:
        func_or_using = DEFAULT_DB_ALIAS
    if callable(func_or_using):
        return inner_commit_locked(func_or_using, DEFAULT_DB_ALIAS)
    return lambda func: inner_commit_locked(func, func_or_using)

class AncestorKey(object):
    def __init__(self, key):
        self.key = key

def as_ancestor(key_or_model):
    if key_or_model is None:
        raise ValueError("key_or_model must not be None")

    if isinstance(key_or_model, models.Model):
        key_or_model = Key.from_path(key_or_model._meta.db_table, key_or_model.pk)

    return AncestorKey(key_or_model)

def make_key(*args, **kwargs):
    parent = kwargs.pop('parent', None)

    if kwargs:
        raise AssertionError('Excess keyword arguments; received %s' % kwargs)

    if not args or len(args) % 2:
        raise AssertionError('A non-zero even number of positional arguments is required; received %s' % args)

    if isinstance(parent, models.Model):
        parent = Key.from_path(parent._meta.db_table, parent.pk)

    converted_args = []
    for i in xrange(0, len(args), 2):
        model, id_or_name = args[i:i+2]
        converted_args.extend((model._meta.db_table, id_or_name))

    return Key.from_path(*converted_args, parent=parent)
