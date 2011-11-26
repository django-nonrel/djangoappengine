from django.db import models
from google.appengine.api.datastore import Key
from .models import GAEKey, GAEAncestorKey

class GAEKeyField(models.Field):
    description = "A field for Google AppEngine Key objects"
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        assert kwargs.get('primary_key', False) is True, "%ss must have primary_key=True." % self.__class__.__name__
        kwargs['null'] = True
        kwargs['blank'] = True
        self.parent_key_attname = kwargs.pop('parent_key_name', None)

        super(GAEKeyField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        assert not cls._meta.has_auto_field, "A model can't have more than one auto field."
        super(GAEKeyField, self).contribute_to_class(cls, name)
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

                if not isinstance(value, GAEKey):
                    raise ValueError("parent must be a GAEKey")

                instance.__dict__[self.parent_key_attname] = value

            setattr(cls, self.parent_key_attname, property(get_parent_key, set_parent_key))

    def to_python(self, value):
        if value is None:
            return None
        if isinstance(value, GAEKey):
            return value
        if isinstance(value, Key):
            return GAEKey(real_key=value)
        if isinstance(value, basestring):
            return GAEKey(real_key=Key(encoded=value))
        return GAEKey(id_or_name=value)

    def get_prep_value(self, value):
        if value is None:
            return None
        if not isinstance(value, (GAEKey, GAEAncestorKey)):
            raise ValueError('must by type GAEKey or GAEAncestorKey, not <%s>' % type(value))
        return value

    def formfield(self, **kwargs):
        return None

    def pre_save(self, model_instance, add):
        if add and self.parent_key_attname is not None:
            parent_key = getattr(model_instance, self.parent_key_attname)
            if parent_key is not None:
                key = GAEKey(parent_key=parent_key)
                setattr(model_instance, self.attname, key)
                return key

        return super(GAEKeyField, self).pre_save(model_instance, add)
