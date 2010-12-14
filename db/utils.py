from google.appengine.datastore.datastore_query import Cursor

def get_cursor(queryset):
    # Evaluate QuerySet
    len(queryset)
    cursor = getattr(queryset.query, '_gae_cursor', None)
    return Cursor.to_websafe_string(cursor)

def set_cursor(queryset, start=None, end=None):
    if start is not None:
        start = Cursor.from_websafe_string(start)
        queryset.query._gae_start_cursor = start
    if end is not None:
        end = Cursor.from_websafe_string(end)
        queryset.query._gae_end_cursor = end
    # Evaluate QuerySet
    len(queryset)
