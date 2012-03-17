from django.db import models
from google.appengine.api.datastore import Key

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

    def id_or_name(self):
        return self._id_or_name

    def parent_key(self):
        return self._parent_key

    def real_key(self):
        if self._real_key is None:
            raise AttributeError("Incomplete key, please save the entity first.")
        return self._real_key

    def has_real_key(self):
        return self._real_key is not None

    def as_ancestor(self):
        return GAEAncestorKey(self.real_key())

    def __cmp__(self, other):
        if not isinstance(other, GAEKey):
            return 1

        if self._real_key is not None and other._real_key is not None:
            return cmp(self._real_key, other._real_key)

        if self._id_or_name is None or other._id_or_name is None:
            raise ValueError("You can't compare unsaved keys: %s %s" % (self, other))

        result = 0
        if self._parent_key is not None:
            result = cmp(self._parent_key, other._parent_key)

        if result == 0:
            result = cmp(self._id_or_name, other._id_or_name)

        return result

    def __hash__(self):
        if self._real_key is None:
            raise ValueError("You can't hash an unsaved key.")

        return hash(self._real_key)

    def __str__(self):
        return str(self._id_or_name)

    def __repr__(self):
        return "%s(id_or_name=%r, parent_key=%r, real_key=%r)" % (self.__class__, self._id_or_name, self._parent_key, self._real_key)
