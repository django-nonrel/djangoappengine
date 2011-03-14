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

    def test_in_sort(self):
        class Post(models.Model):
            writer = models.IntegerField()
            order = models.IntegerField()
        Post(writer=1, order=1).save()
        Post(writer=1, order=2).save()
        Post(writer=1, order=3).save()
        Post(writer=2, order=4).save()
        Post(writer=2, order=5).save()
        import logging
        posts = Post.objects.filter(writer__in= [1,2]).order_by('order')
        logging.warn('posts %s' % (list(i.order for i in posts)))
        self.assertEqual(posts[0].order, 1)
        self.assertEqual(posts[1].order, 2)
        self.assertEqual(posts[2].order, 3)
        self.assertEqual(posts[3].order, 4)
        self.assertEqual(posts[4].order, 5)
        posts = Post.objects.filter(writer__in= [1,2]).order_by('-order')
        logging.warn('posts %s' % (list(i.order for i in posts)))
        self.assertEqual(posts[0].order, 5)
        self.assertEqual(posts[1].order, 4)
        self.assertEqual(posts[2].order, 3)
        self.assertEqual(posts[3].order, 2)
        self.assertEqual(posts[4].order, 1)

