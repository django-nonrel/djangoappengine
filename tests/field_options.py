from django.test import TestCase
from django.db.utils import DatabaseError
from django.db.models.fields import NOT_PROVIDED
from .testmodels import FieldsWithOptionsModel, NullableTextModel
from google.appengine.api.datastore import Get
from google.appengine.ext.db import Key
from google.appengine.api.datastore_types import Text, Category, Email, Link, \
    PhoneNumber, PostalAddress, Text, Blob, ByteString, GeoPt, IM, Key, \
    Rating, BlobKey
from google.appengine.api import users
import datetime

class FieldOptionsTest(TestCase):
    def test_options(self):
        entity = FieldsWithOptionsModel()
        # try to save the entity with non-nullable field time set to None, should
        # raise an exception
        self.assertRaises(DatabaseError, entity.save)

        time = datetime.datetime.now().time()
        entity.time = time
        entity.save()

        # check if primary_key=True is set correctly for the saved entity
        self.assertEquals(entity.pk, u'app-engine@scholardocs.com')
        gae_entity = Get(Key.from_path(FieldsWithOptionsModel._meta.db_table,
            entity.pk))
        self.assertTrue(gae_entity is not None)
        self.assertEquals(gae_entity.key().name(), u'app-engine@scholardocs.com')

        # check if default values are set correctly on the db level,
        # primary_key field is not stored at the db level
        for field in FieldsWithOptionsModel._meta.local_fields:
            if field.default and field.default != NOT_PROVIDED and not \
                    field.primary_key:
                self.assertEquals(gae_entity[field.column], field.default)
            elif field.column == 'time':
                self.assertEquals(gae_entity[field.column], datetime.datetime(
                    1970, 1, 1, time.hour, time.minute, time.second, time.microsecond))
            elif field.null and field.editable:
                self.assertEquals(gae_entity[field.column], None)

        # check if default values are set correct on the model instance level
        entity = FieldsWithOptionsModel.objects.get()
        for field in FieldsWithOptionsModel._meta.local_fields:
            if field.default and field.default != NOT_PROVIDED:
                self.assertEquals(getattr(entity, field.column), field.default)
            elif field.column == 'time':
                self.assertEquals(getattr(entity, field.column), time)
            elif field.null and field.editable:
                self.assertEquals(getattr(entity, field.column), None)

        # check if nullable field with default values can be set to None
        entity.slug = None
        entity.positiv_small_integer = None
        try:
            entity.save()
        except:
            self.fail()

        # check if slug and positiv_small_integer will be retrieved with values
        # set to None (on db level and model instance level)
        gae_entity = Get(Key.from_path(FieldsWithOptionsModel._meta.db_table,
            entity.pk))
        self.assertEquals(gae_entity[FieldsWithOptionsModel._meta.get_field_by_name(
            'slug')[0].column], None)
        self.assertEquals(gae_entity[FieldsWithOptionsModel._meta.get_field_by_name(
            'positiv_small_integer')[0].column], None)

        # on the model instance level
        entity = FieldsWithOptionsModel.objects.get()
        self.assertEquals(getattr(entity, FieldsWithOptionsModel._meta.get_field_by_name(
            'slug')[0].column), None)
        self.assertEquals(getattr(entity, FieldsWithOptionsModel._meta.get_field_by_name(
            'positiv_small_integer')[0].column), None)

        # TODO: check db_column option
        # TODO: change the primary key and check if a new instance with the
        # changed primary key will be saved (not in this test class)

    def test_nullable_text(self):
        # regression test for #48
        entity = NullableTextModel(text=None)
        entity.save()

        db_entity = NullableTextModel.objects.get()
        self.assertEquals(db_entity.text, None)
