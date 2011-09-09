from .testmodels import DecimalModel
from django.test import TestCase

from decimal import Decimal, InvalidOperation
D = Decimal

class DecimalTest(TestCase):
    DECIMALS = D("12345.6789"), D("5"), D("345.67"), D("45.6"), D("2345.678")

    def setUp(self):
        for d in self.DECIMALS:
            DecimalModel(decimal=d).save()

    def test_filter(self):
        d = DecimalModel.objects.get(decimal=D("5.0"))

        self.assertTrue(isinstance(d.decimal, Decimal))
        self.assertEquals(str(d.decimal), "5.00")

        d = DecimalModel.objects.get(decimal=D("45.60"))
        self.assertEquals(str(d.decimal), "45.60")

        # Filter argument should be converted to Decimal with 2 decimal_places
        d = DecimalModel.objects.get(decimal="0000345.67333333333333333")
        self.assertEquals(str(d.decimal), "345.67")

    def test_order(self):
        rows = DecimalModel.objects.all().order_by('decimal')
        values = list(d.decimal for d in rows)
        self.assertEquals(values, sorted(values))

    def test_sign_extend(self):
        DecimalModel(decimal=D('-0.0')).save()

        try:
            # if we've written a valid string we should be able to
            # retrieve the DecimalModel object without error
            DecimalModel.objects.filter(decimal__lt=1)[0]
        except InvalidOperation:
            self.assertTrue(False)
