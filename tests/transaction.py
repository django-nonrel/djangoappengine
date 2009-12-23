from .testmodels import FieldsWithOptionsModel
from datetime import datetime
from django.db.transaction import commit_locked
from django.test import TestCase

class TxTest(TestCase):
    def test_tx(self):
        item = FieldsWithOptionsModel(time=datetime.now().time())
        item.save()
        self.run_tx(item.pk)
        item = FieldsWithOptionsModel.objects.get(pk=item.pk)
        self.assertEquals(item.text, 'Wooooo!')
        self.assertRaises(Exception, self.run_nested_tx, [item.pk])

    @commit_locked
    def run_tx(self, pk):
        item = FieldsWithOptionsModel.objects.get(pk=pk)
        item.text = 'Wooooo!'
        item.save()

    @commit_locked
    def run_nested_tx(self, pk):
        self.run_tx(pk)
