from django.db import models
from google.appengine.api.datastore import Key

# TODO: look for better exceptions to raise

class GAEAncestorKey(object):
    def __init__(self, key):
        if not isinstance(key, Key):
            raise ValueError('key must be of type Key')

        self._key = key

    def key(self):
        return self._key

class GAEKey(object):
    def __init__(self, id_or_name=None, parent_key=None, real_key=None):
        self._id_or_name = id_or_name
        self._parent_key = parent_key
        self._real_key = None

        if real_key is not None:
            if id_or_name is not None or parent_key is not None:
                raise ValueError("You can't set both a real_key and an id_or_name or parent_key")

            self._real_key = real_key
            if real_key.parent():
                self._parent_key = GAEKey(real_key=real_key.parent())
            self._id_or_name = real_key.id_or_name()

    def _get_id_or_name(self):
        return self._id_or_name
    id_or_name = property(_get_id_or_name)

    def _get_parent_key(self):
        return self._parent_key
    parent_key = property(_get_parent_key)

    def _get_real_key(self):
        if self._real_key is None:
            raise ValueError("Incomplete key, please save the entity first.")
        return self._real_key
    real_key = property(_get_real_key)

    def has_real_key(self):
        return self._real_key is not None

    def as_ancestor(self):
        return GAEAncestorKey(self._get_real_key())

    def __cmp__(self, other):
        if not isinstance(other, GAEKey):
            return 1
        if self._real_key is None or other._real_key is None:
            raise ValueError("You can't compare unsaved keys.")

        return cmp(self._real_key, other._real_key)

    def __hash__(self):
        if self._real_key is None:
            raise ValueError("You can't hash an unsaved key.")

        return hash(self._real_key)

    def __str__(self):
        return str(self._real_key)
