from django.db.models import F
from django.test import TestCase

from .testmodels import EmailModel


class TransactionTest(TestCase):
    emails = ['app-engine@scholardocs.com', 'sharingan@uchias.com',
              'rinnengan@sage.de', 'rasengan@naruto.com']

    def setUp(self):
        EmailModel(email=self.emails[0], number=1).save()
        EmailModel(email=self.emails[0], number=2).save()
        EmailModel(email=self.emails[1], number=3).save()

    def test_update(self):
        self.assertEqual(2, len(EmailModel.objects.all().filter(
            email=self.emails[0])))

        self.assertEqual(1, len(EmailModel.objects.all().filter(
            email=self.emails[1])))

        EmailModel.objects.all().filter(email=self.emails[0]).update(
            email=self.emails[1])

        self.assertEqual(0, len(EmailModel.objects.all().filter(
            email=self.emails[0])))
        self.assertEqual(3, len(EmailModel.objects.all().filter(
            email=self.emails[1])))

    def test_f_object_updates(self):
        self.assertEqual(1, len(EmailModel.objects.all().filter(
            number=1)))
        self.assertEqual(1, len(EmailModel.objects.all().filter(
            number=2)))

        # Test add.
        EmailModel.objects.all().filter(email=self.emails[0]).update(
            number=F('number') + F('number'))

        self.assertEqual(1, len(EmailModel.objects.all().filter(
            number=2)))
        self.assertEqual(1, len(EmailModel.objects.all().filter(
            number=4)))

        EmailModel.objects.all().filter(email=self.emails[1]).update(
            number=F('number') + 10, email=self.emails[0])

        self.assertEqual(1, len(EmailModel.objects.all().filter(number=13)))
        self.assertEqual(self.emails[0],
                         EmailModel.objects.all().get(number=13).email)

        # Complex expression test.
        EmailModel.objects.all().filter(number=13).update(
            number=F('number') * (F('number') + 10) - 5, email=self.emails[0])
        self.assertEqual(1, len(EmailModel.objects.all().filter(number=294)))

       # TODO: Tests for: sub, muld, div, mod, ....
