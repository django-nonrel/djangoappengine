from google.appengine.datastore.datastore_pb import CompiledCursor
import base64

def get_cursor(queryset):
    # Evaluate QuerySet
    len(queryset)
    cursor = getattr(queryset.query, '_gae_cursor', None)
    return base64.urlsafe_b64encode(cursor.Encode())

def set_cursor(queryset, start=None, end=None):
    if start is not None:
        start = base64.urlsafe_b64decode(str(start))
        start = CompiledCursor(start)
        queryset.query._gae_start_cursor = start
    if end is not None:
        end = base64.urlsafe_b64decode(str(end))
        end = CompiledCursor(end)
        queryset.query._gae_end_cursor = end
    # Evaluate QuerySet
    len(queryset)
