from .testmodels import OrderedModel
from django.test import TestCase

class OrderTest(TestCase):
    def create_ordered_model_items(self):
        pks = []
        priorities = [5, 2, 9, 1]
        for pk, priority in enumerate(priorities):
            pk += 1
            model = OrderedModel(pk=pk, priority=priority)
            model.save()
            pks.append(model.pk)
        return pks, priorities

    def test_default_order(self):
        pks, priorities = self.create_ordered_model_items()
        self.assertEquals([item.priority
                           for item in OrderedModel.objects.all()],
                          sorted(priorities, reverse=True))

    def test_override_default_order(self):
        pks, priorities = self.create_ordered_model_items()
        self.assertEquals([item.priority
                           for item in OrderedModel.objects.all().order_by('priority')],
                          sorted(priorities))

    def test_remove_default_order(self):
        pks, priorities = self.create_ordered_model_items()
        self.assertEquals([item.pk
                           for item in OrderedModel.objects.all().order_by()],
                          sorted(pks))

    def test_order_with_pk_filter(self):
        pks, priorities = self.create_ordered_model_items()
        self.assertEquals([item.priority
                           for item in OrderedModel.objects.filter(pk__in=pks)],
                          sorted(priorities, reverse=True))

        # test with id__in
        self.assertEquals([item.priority
                           for item in OrderedModel.objects.filter(id__in=pks)],
                          sorted(priorities, reverse=True))

        # test reverse
        self.assertEquals([item.priority
                           for item in OrderedModel.objects.filter(
                           pk__in=pks).reverse()], sorted(priorities,
                           reverse=False))

    def test_remove_default_order_with_pk_filter(self):
        pks, priorities = self.create_ordered_model_items()
        self.assertEquals([item.priority
                           for item in OrderedModel.objects.filter(pk__in=pks).order_by()],
                          priorities)

    # TODO: test multiple orders
