from django.db import models
from django.test import TestCase

class A(models.Model):
    value = models.IntegerField()

class BackendTest(TestCase):
    def test_model_forms(self):
        from django import forms
        class F(forms.ModelForm):
            class Meta:
                model = A

        F({'value': '3'}).save()
