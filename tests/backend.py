from django.db import models
from django.test import TestCase
from django.db.utils import DatabaseError

class A(models.Model):
    value = models.IntegerField()

class B(A):
    other = models.IntegerField()

class BackendTest(TestCase):
    def test_model_forms(self):
        from django import forms
        class F(forms.ModelForm):
            class Meta:
                model = A

        F({'value': '3'}).save()

    def test_multi_table_inheritance(self):
        B(value=3, other=5).save()
        self.assertEqual(A.objects.count(), 1)
        self.assertEqual(A.objects.all()[0].value, 3)
        self.assertRaises(DatabaseError, B.objects.count)
        self.assertRaises(DatabaseError, lambda: B.objects.all()[0])
