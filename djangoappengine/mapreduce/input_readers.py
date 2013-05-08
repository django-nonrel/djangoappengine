from djangoappengine.db.utils import get_cursor, set_cursor, set_config

from google.appengine.api.datastore import Key

from mapreduce.datastore_range_iterators import AbstractKeyRangeIterator, _KEY_RANGE_ITERATORS
from mapreduce.input_readers import AbstractDatastoreInputReader, _get_params, BadReaderParamsError
from mapreduce import util

class DjangoModelIterator(AbstractKeyRangeIterator):
    def __iter__(self):
        k_range = self._key_range

        # Namespaces are not supported by djangoappengine
        if k_range.namespace:
            return

        model_class = util.for_name(self._query_spec.model_class_path)

        q = model_class.objects.all()

        if k_range.key_start:
            if k_range.include_start:
                q = q.filter(pk__gte=k_range.key_start.id_or_name())
            else:
                q = q.filter(pk__gt=k_range.key_start.id_or_name())

        if k_range.key_end:
            if k_range.include_end:
                q = q.filter(pk__lte=k_range.key_end.id_or_name())
            else:
                q = q.filter(pk__lt=k_range.key_end.id_or_name())

        q = q.order_by('pk')

        q = set_config(q, batch_size=self._query_spec.batch_size)

        if self._cursor:
            q = set_cursor(q, self._cursor)

        self._query = q

        for entity in self._query.iterator():
            yield entity

    def _get_cursor(self):
        if self._query is not None:
            return get_cursor(self._query)

_KEY_RANGE_ITERATORS[DjangoModelIterator.__name__] = DjangoModelIterator

class DjangoModelInputReader(AbstractDatastoreInputReader):
    """
    An input reader that takes a Django model ('app.models.Model')
    and yields Django model instances

    Note: This ignores all entities not in the default namespace.
    """

    _KEY_RANGE_ITER_CLS = DjangoModelIterator

    @classmethod
    def _get_raw_entity_kind(cls, entity_kind):
        """Returns an datastore entity kind from a Django model."""
        model_class = util.for_name(entity_kind)
        return model_class._meta.db_table

    @classmethod
    def validate(cls, mapper_spec):
        super(DjangoModelInputReader, cls).validate(mapper_spec)

        params = _get_params(mapper_spec)

        if cls.NAMESPACE_PARAM in params:
            raise BadReaderParamsError("Namespaces are not supported.")

        entity_kind_name = params[cls.ENTITY_KIND_PARAM]
        try:
            util.for_name(entity_kind_name)
        except ImportError, e:
            raise BadReaderParamsError("Bad entity kind: %s" % e)
