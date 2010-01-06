from django.db import models
from django.test import TestCase

class BackendTest(TestCase):
    def test_multi_table_inheritance(self):
        class A(models.Model):
            value = models.IntegerField()
        class B(A):
            value2 = models.IntegerField()
        self.assertRaises(ValueError, B.objects.count)
        self.assertRaises(ValueError, B.objects.all().get)
        self.assertRaises(ValueError, lambda: B.objects.all()[:10][0])
        self.assertRaises(ValueError, B(value=1, value2=2).save)

        class AbstractB(A):
            value2 = models.IntegerField()
            class Meta:
                abstract = True

        class C(B):
            value3 = models.IntegerField()
        self.assertRaises(ValueError, C(value=1, value2=2, value3=3).save)
