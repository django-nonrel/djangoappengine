import datetime

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.test import TestCase

from .testmodels import FieldsWithOptionsModel, OrderedModel, \
    SelfReferenceModel


class NonReturnSetsTest(TestCase):
    floats = [5.3, 2.6, 9.1, 1.58, 2.4]
    emails = ['app-engine@scholardocs.com', 'sharingan@uchias.com',
              'rinnengan@sage.de', 'rasengan@naruto.com', 'itachi@uchia.com']

    def setUp(self):
        for index, (float, email) in enumerate(zip(NonReturnSetsTest.floats,
                NonReturnSetsTest.emails)):
            self.last_save_time = datetime.datetime.now().time()
            ordered_instance = OrderedModel(priority=index, pk=index + 1)
            ordered_instance.save()
            model = FieldsWithOptionsModel(floating_point=float,
                                           integer=int(float), email=email,
                                           time=self.last_save_time,
                                           foreign_key=ordered_instance)
            model.save()

    def test_get(self):
        self.assertEquals(
            FieldsWithOptionsModel.objects.get(
                email='itachi@uchia.com').email,
            'itachi@uchia.com')

        # Test exception when matching multiple entities.
        self.assertRaises(MultipleObjectsReturned,
                          FieldsWithOptionsModel.objects.get,
                          integer=2)

        # Test exception when entity does not exist.
        self.assertRaises(ObjectDoesNotExist,
                          FieldsWithOptionsModel.objects.get,
                          floating_point=5.2)

        # TODO: Test create when djangos model.save_base is refactored.
        # TODO: Test get_or_create when refactored.

    def test_count(self):
        self.assertEquals(
            FieldsWithOptionsModel.objects.filter(integer=2).count(), 2)

    def test_in_bulk(self):
        self.assertEquals(
            [key in ['sharingan@uchias.com', 'itachi@uchia.com']
             for key in FieldsWithOptionsModel.objects.in_bulk(
                ['sharingan@uchias.com', 'itachi@uchia.com']).keys()],
            [True, ] * 2)

    def test_latest(self):
        self.assertEquals(
            FieldsWithOptionsModel.objects.latest('time').email,
            'itachi@uchia.com')

    def test_exists(self):
        self.assertEquals(FieldsWithOptionsModel.objects.exists(), True)

    def test_deletion(self):
        # TODO: ForeignKeys will not be deleted! This has to be done
        #       via background tasks.
        self.assertEquals(FieldsWithOptionsModel.objects.count(), 5)

        FieldsWithOptionsModel.objects.get(email='itachi@uchia.com').delete()
        self.assertEquals(FieldsWithOptionsModel.objects.count(), 4)

        FieldsWithOptionsModel.objects.filter(email__in=[
            'sharingan@uchias.com', 'itachi@uchia.com',
            'rasengan@naruto.com', ]).delete()
        self.assertEquals(FieldsWithOptionsModel.objects.count(), 2)

    def test_selfref_deletion(self):
        entity = SelfReferenceModel()
        entity.save()
        entity.delete()

    def test_foreign_key_fetch(self):
        # Test fetching the ForeignKey.
        ordered_instance = OrderedModel.objects.get(priority=2)
        self.assertEquals(
            FieldsWithOptionsModel.objects.get(integer=9).foreign_key,
            ordered_instance)

    def test_foreign_key_backward(self):
        entity = OrderedModel.objects.all()[0]
        self.assertEquals(entity.keys.count(), 1)
        # TODO: Add should save the added instance transactional via for
        #       example force_insert.
        new_foreign_key = FieldsWithOptionsModel(
            floating_point=5.6, integer=3,
            email='temp@temp.com', time=datetime.datetime.now())
        entity.keys.add(new_foreign_key)
        self.assertEquals(entity.keys.count(), 2)
        # TODO: Add test for create.
        entity.keys.remove(new_foreign_key)
        self.assertEquals(entity.keys.count(), 1)
        entity.keys.clear()
        self.assertTrue(not entity.keys.exists())
        entity.keys = [new_foreign_key, new_foreign_key]
        self.assertEquals(entity.keys.count(), 1)
        self.assertEquals(entity.keys.all()[0].integer, 3)
