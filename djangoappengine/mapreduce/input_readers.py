from djangoappengine.db.utils import get_cursor, set_cursor

from google.appengine.api.datastore import Key

from mapreduce.input_readers import DatastoreEntityInputReader, _get_params, BadReaderParamsError
from mapreduce import util

class DjangoModelInputReader(DatastoreEntityInputReader):
    """
    An input reader that takes a Django model ('app.models.Model')
    and yields Django model instances

    Note: This ignores all entities not in the default namespace.
    """

    @classmethod
    def _get_raw_entity_kind(cls, entity_kind):
        """Returns an datastore entity kind from a Django model."""
        model_class = util.for_name(entity_kind)
        return model_class._meta.db_table

    @classmethod
    def validate(cls, mapper_spec):
        super(DjangoModelInputReader, cls).validate(mapper_spec)

        params = _get_params(mapper_spec)
        entity_kind_name = params[cls.ENTITY_KIND_PARAM]
        try:
            util.for_name(entity_kind_name)
        except ImportError, e:
            raise BadReaderParamsError("Bad entity kind: %s" % e)

    def _iter_key_range(self, k_range):
        # Namespaces are not supported by djangoappengine
        if k_range.namespace:
            return

        model_class = util.for_name(self._entity_kind)

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

        cursor = None
        while True:
            if cursor:
                q = set_cursor(q, cursor)

            results = q[:self._batch_size]

            if not results:
                break

            for entity in results.iterator():
                if has_gae_pk:
                    key = entity.pk
                else:
                    key = Key.from_path(model_class._meta.db_table, entity.pk)

                yield key, entity

            cursor = get_cursor(results)
            if not cursor:
                break
