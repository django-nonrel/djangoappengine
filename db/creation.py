from djangotoolbox.db.creation import NonrelDatabaseCreation

from .db_settings import get_model_indexes
from .stubs import stub_manager


class DatabaseCreation(NonrelDatabaseCreation):

    # For TextFields and XMLFields we'll default to the unindexable,
    # but not length-limited, db.Text (db_type of "string" fields is
    # overriden indexed / unindexed fields).
    # GAE datastore cannot process sets directly, so we'll store them
    # as lists, it also can't handle dicts so we'll store DictField and
    # EmbeddedModelFields pickled as Blobs (pickled using the binary
    # protocol 2, even though they used to be serialized with the ascii
    # protocol 0 -- the deconversion is the same for both).
    data_types = dict(NonrelDatabaseCreation.data_types, **{
        'TextField':          'text',
        'XMLField':           'text',
        'SetField':           'list',
        'DictField':          'bytes',
        'EmbeddedModelField': 'bytes',
    })

    def db_type(self, field):
        """
        Provides a choice to continue using db.Key just for primary key
        storage or to use it for all references (ForeignKeys and other
        relations).

        We also force the "string" db_type (plain string storage) if a
        field is to be indexed, and the "text" db_type (db.Text) if
        it's registered as unindexed.
        """
        if self.connection.settings_dict.get('STORE_RELATIONS_AS_DB_KEYS'):
            if field.primary_key or field.rel is not None:
                return 'key'

        # Primary keys were processed as db.Keys; for related fields
        # the db_type of primary key of the referenced model was used,
        # but RelatedAutoField type was not defined and resulted in
        # "integer" being used for relations to models with AutoFields.
        # TODO: Check with Positive/SmallIntegerField primary keys.
        else:
            if field.primary_key:
                return 'key'
            if field.rel is not None:
                related_field = field.rel.get_related_field()
                if related_field.get_internal_type() == 'AutoField':
                    return 'integer'
                else:
                    return related_field.db_type(connection=self.connection)

        db_type = field.db_type(connection=self.connection)

        # Override db_type of "string" fields according to indexing.
        if db_type in ('string', 'text'):
            indexes = get_model_indexes(field.model)
            if field.attname in indexes['indexed']:
                return 'string'
            elif field.attname in indexes['unindexed']:
                return 'text'

        return db_type


    def _create_test_db(self, *args, **kw):
        self._had_test_stubs = stub_manager.active_stubs != 'test'
        if self._had_test_stubs:
            stub_manager.activate_test_stubs(self.connection)

    def _destroy_test_db(self, *args, **kw):
        if self._had_test_stubs:
            stub_manager.deactivate_test_stubs()
            stub_manager.setup_stubs(self.connection)
        del self._had_test_stubs
