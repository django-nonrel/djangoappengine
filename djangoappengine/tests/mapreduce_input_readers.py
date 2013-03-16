from django.db import models
from django.test import TestCase
from django.utils import unittest

from djangoappengine.mapreduce.input_readers import DjangoModelInputReader

from google.appengine.api.datastore import Key

try:
    import mapreduce

    from mapreduce.lib import key_range
    from mapreduce import input_readers
    from mapreduce import model
except ImportError:
    mapreduce = None

class TestModel(models.Model):
    test_property = models.IntegerField(default=0)

ENTITY_KIND = '%s.%s' % (TestModel.__module__, TestModel.__name__)

def key(entity_id, kind=TestModel):
    return Key.from_path(kind._meta.db_table, entity_id)

@unittest.skipUnless(mapreduce, 'mapreduce not installed')
class DjangoModelInputReaderTest(TestCase):
    """Test DjangoModelInputReader class."""

    def testValidate_Passes(self):
        """Test validate function accepts valid parameters."""
        params = {
            "entity_kind": ENTITY_KIND,
            }
        mapper_spec = model.MapperSpec(
                "FooHandler",
                "djangoappengine.mapreduce.input_readers.DjangoModelInputReader",
                params, 1)
        DjangoModelInputReader.validate(mapper_spec)

    def testValidate_NoEntityFails(self):
        """Test validate function raises exception with no entity parameter."""
        params = {}
        mapper_spec = model.MapperSpec(
            "FooHandler",
            "djangoappengine.mapreduce.input_readers.DjangoModelInputReader",
            params, 1)
        self.assertRaises(input_readers.BadReaderParamsError,
                            DjangoModelInputReader.validate,
                            mapper_spec)

    def testValidate_BadEntityKind(self):
        """Test validate function with bad entity kind."""
        params = {
            "entity_kind": "foo",
            }
        mapper_spec = model.MapperSpec(
            "FooHandler",
            "djangoappengine.mapreduce.input_readers.DjangoModelInputReader",
            params, 1)
        self.assertRaises(input_readers.BadReaderParamsError,
                            DjangoModelInputReader.validate,
                            mapper_spec)

    def testGeneratorWithKeyRange(self):
        """Test DjangoModelInputReader as generator using KeyRanges."""
        expected_entities = []
        for _ in range(0, 100):
            entity = TestModel()
            entity.save()
            expected_entities.append(entity)

        kranges = [key_range.KeyRange(key_start=key(1), key_end=key(10000), direction="ASC")]

        query_range = DjangoModelInputReader(ENTITY_KIND, key_ranges=kranges, ns_range=None, batch_size=10)

        entities = []
        for entity in query_range:
            entities.append(entity)

        self.assertEquals(100, len(entities))
        self.assertEquals(expected_entities, entities)
