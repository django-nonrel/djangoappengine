from google.appengine.api.datastore import Key

from mapreduce.input_readers import DatastoreEntityInputReader
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

        for entity in q:
            key = Key.from_path(model_class._meta.db_table, entity.pk)
            yield key, entity
