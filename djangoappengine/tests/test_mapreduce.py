from django.db import models
from django.test import TestCase
from django.utils import unittest

from google.appengine.api.datastore import Key

try:
    from djangoappengine.mapreduce.input_readers import DjangoModelInputReader, DjangoModelIterator

    import mapreduce

    from mapreduce import input_readers
    from mapreduce.lib import key_range
    from mapreduce import model
except ImportError:
    mapreduce = None

class TestModel(models.Model):
    test_property = models.IntegerField(default=0)

    def __unicode__(self):
        return str(self.test_property)

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

    def testValidate_BadNamespace(self):
        """Test validate function with bad namespace."""
        params = {
            "entity_kind": ENTITY_KIND,
            "namespace": 'namespace',
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
        for i in range(0, 100):
            entity = TestModel(test_property=i)
            entity.save()
            expected_entities.append(entity)

        params = {
            "entity_kind": ENTITY_KIND,
            }
        mapper_spec = model.MapperSpec(
            "FooHandler",
            "djangoappengine.mapreduce.input_readers.DjangoModelInputReader",
            params, 1)

        input_ranges = DjangoModelInputReader.split_input(mapper_spec)

        entities = []
        for query_range in input_ranges:
            for entity in query_range:
                entities.append(entity)

        self.assertEquals(100, len(entities))
        self.assertEquals(expected_entities, entities)

@unittest.skipUnless(mapreduce, 'mapreduce not installed')
class DjangoModelIteratorTest(TestCase):
    def setUp(self):
        expected_entities = []
        for i in range(0, 100):
            entity = TestModel(test_property=i)
            entity.save()
            expected_entities.append(entity)

        self.expected_entities = expected_entities

    def testCursors(self):
        qs = model.QuerySpec(TestModel, model_class_path=ENTITY_KIND)
        kr = key_range.KeyRange(key_start=key(1), key_end=key(10000), direction="ASC")

        json = { 'key_range': kr.to_json(), 'query_spec': qs.to_json(), 'cursor': None }

        entities = []
        while True:
            model_iter = DjangoModelIterator.from_json(json)

            c = False
            count = 0
            for entity in model_iter:
                count += 1
                entities.append(entity)
                if count == 10:
                    c = True
                    break

            if c:
                json = model_iter.to_json()
            else:
                break

        self.assertEquals(100, len(entities))
        self.assertEquals(self.expected_entities, entities)
