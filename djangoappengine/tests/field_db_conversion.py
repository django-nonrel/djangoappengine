import datetime

from django.test import TestCase

from google.appengine.api.datastore import Get
from google.appengine.api.datastore_types import Text, Category, Email, \
    Link, PhoneNumber, PostalAddress, Text, Blob, ByteString, GeoPt, IM, \
    Key, Rating, BlobKey

from .testmodels import FieldsWithoutOptionsModel

# TODO: Add field conversions for ForeignKeys?


class FieldDBConversionTest(TestCase):

    def test_db_conversion(self):
        actual_datetime = datetime.datetime.now()
        entity = FieldsWithoutOptionsModel(
            datetime=actual_datetime, date=actual_datetime.date(),
            time=actual_datetime.time(), floating_point=5.97, boolean=True,
            null_boolean=False, text='Hallo', email='hallo@hallo.com',
            comma_seperated_integer='5,4,3,2',
            ip_address='194.167.1.1', slug='you slugy slut :)',
            url='http://www.scholardocs.com', long_text=1000 * 'A',
            indexed_text='hello', xml=2000 * 'B',
            integer=-400, small_integer=-4, positive_integer=400,
            positive_small_integer=4)
        entity.save()

        # Get the gae entity (not the django model instance) and test
        # if the fields have been converted right to the corresponding
        # GAE database types.
        gae_entity = Get(
            Key.from_path(FieldsWithoutOptionsModel._meta.db_table,
            entity.pk))
        opts = FieldsWithoutOptionsModel._meta
        for name, types in [('long_text', Text),
                ('indexed_text', unicode), ('xml', Text),
                ('text', unicode), ('ip_address', unicode), ('slug', unicode),
                ('email', unicode), ('comma_seperated_integer', unicode),
                ('url', unicode), ('time', datetime.datetime),
                ('datetime', datetime.datetime), ('date', datetime.datetime),
                ('floating_point', float), ('boolean', bool),
                ('null_boolean', bool), ('integer', (int, long)),
                ('small_integer', (int, long)),
                ('positive_integer', (int, long)),
                ('positive_small_integer', (int, long))]:
            column = opts.get_field_by_name(name)[0].column
            if not isinstance(types, (list, tuple)):
                types = (types, )
            self.assertTrue(type(gae_entity[column]) in types)

        # Get the model instance and check if the fields convert back
        # to the right types.
        model = FieldsWithoutOptionsModel.objects.get()
        for name, types in [
                ('long_text', unicode),
                ('indexed_text', unicode), ('xml', unicode),
                ('text', unicode), ('ip_address', unicode),
                ('slug', unicode),
                ('email', unicode), ('comma_seperated_integer', unicode),
                ('url', unicode), ('datetime', datetime.datetime),
                ('date', datetime.date), ('time', datetime.time),
                ('floating_point', float), ('boolean', bool),
                ('null_boolean', bool), ('integer', (int, long)),
                ('small_integer', (int, long)),
                ('positive_integer', (int, long)),
                ('positive_small_integer', (int, long))]:
            if not isinstance(types, (list, tuple)):
                types = (types, )
            self.assertTrue(type(getattr(model, name)) in types)
