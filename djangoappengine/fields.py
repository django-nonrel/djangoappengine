from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import smart_unicode

from djangoappengine.db.utils import AncestorKey

from google.appengine.api.datastore import Key, datastore_errors

class DbKeyField(models.Field):
    description = "A field for native database key objects"
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True

        self.parent_key_attname = kwargs.pop('parent_key_name', None)

        if self.parent_key_attname is not None and kwargs.get('primary_key', None) is None:
            raise ValueError("Primary key must be true to use parent_key_name")

        super(DbKeyField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        if self.primary_key:
            assert not cls._meta.has_auto_field, "A model can't have more than one auto field."
            cls._meta.has_auto_field = True
            cls._meta.auto_field = self

            if self.parent_key_attname is not None:
                def get_parent_key(instance, instance_type=None):
                    if instance is None:
                        return self

                    return instance.__dict__.get(self.parent_key_attname)

                def set_parent_key(instance, value):
                    if instance is None:
                        raise AttributeError("Attribute must be accessed via instance")

                    if not isinstance(value, Key):
                        raise ValueError("'%s' must be a Key" % self.parent_key_attname)

                    instance.__dict__[self.parent_key_attname] = value

                setattr(cls, self.parent_key_attname, property(get_parent_key, set_parent_key))

        super(DbKeyField, self).contribute_to_class(cls, name)

    def to_python(self, value):
        if value is None:
            return None
        if isinstance(value, Key):
            return value
        if isinstance(value, basestring):
            if len(value) == 0:
                return None

            try:
                return Key(encoded=value)
            except datastore_errors.BadKeyError:
                return Key.from_path(self.model._meta.db_table, long(value))
        if isinstance(value, (int, long)):
            return Key.from_path(self.model._meta.db_table, value)

        raise ValidationError("DbKeyField does not accept %s" % type(value))

    def get_prep_value(self, value):
        if isinstance(value, AncestorKey):
            return value
        return self.to_python(value)

    def pre_save(self, model_instance, add):
        value = super(DbKeyField, self).pre_save(model_instance, add)

        if add and value is None and self.parent_key_attname is not None and hasattr(model_instance, self.parent_key_attname):
            stashed_parent = getattr(model_instance, self.parent_key_attname)
            value = Key.from_path(self.model._meta.db_table, 0, parent=stashed_parent)

        return value

    def formfield(self, **kwargs):
        return None

    def value_to_string(self, obj):
        return smart_unicode(self._get_val_from_obj(obj))
