from .testmodels import FieldsWithOptionsModel, OrderedModel
import datetime
from django.test import TestCase
from django.db.models import Q
from google.appengine.api.datastore_errors import BadArgumentError, BadFilterError

class FilterTest(TestCase):
    floats = [5.3, 2.6, 9.1, 1.58]
    emails = ['app-engine@scholardocs.com', 'sharingan@uchias.com',
        'rinnengan@sage.de', 'rasengan@naruto.com']

    def setUp(self):
        for index, (float, email) in enumerate(zip(FilterTest.floats,
                FilterTest.emails)):
            self.last_save_time = datetime.datetime.now().time()
            ordered_instance = OrderedModel(priority=index, pk=index + 1)
            ordered_instance.save()
            model = FieldsWithOptionsModel(floating_point=float,
                                           integer=int(float), email=email,
                                           time=self.last_save_time,
                                           foreign_key=ordered_instance)
            model.save()

    def test_gt(self):
        # test gt on float
        self.assertEquals([entity.floating_point for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          floating_point__gt=3.1).order_by('floating_point')],
                          [5.3, 9.1])

        # test gt on integer
        self.assertEquals([entity.integer for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          integer__gt=3).order_by('integer')],
                          [5, 9])

        # test filter on primary_key field
        self.assertEquals([entity.email for entity in \
                          FieldsWithOptionsModel.objects.filter(email__gt='as').
                          order_by('email')], ['rasengan@naruto.com',
                          'rinnengan@sage.de', 'sharingan@uchias.com', ])

        # test ForeignKeys with id
        self.assertEquals(sorted([entity.email for entity in \
                            FieldsWithOptionsModel.objects.filter(
                            foreign_key__gt=2)]),
                            ['rasengan@naruto.com', 'rinnengan@sage.de', ])

        # and with instance
        ordered_instance = OrderedModel.objects.get(priority=1)
        self.assertEquals(sorted([entity.email for entity in \
                            FieldsWithOptionsModel.objects.filter(
                            foreign_key__gt=ordered_instance)]),
                            ['rasengan@naruto.com', 'rinnengan@sage.de', ])


    def test_lt(self):
        # test lt on float
        self.assertEquals([entity.floating_point for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          floating_point__lt=3.1).order_by('floating_point')],
                          [1.58, 2.6])

        # test lt on integer
        self.assertEquals([entity.integer for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          integer__lt=3).order_by('integer')],
                          [1, 2])

        # test filter on primary_key field
        self.assertEquals([entity.email for entity in \
                          FieldsWithOptionsModel.objects.filter(email__lt='as').
                          order_by('email')], ['app-engine@scholardocs.com', ])

         # filter on datetime
        self.assertEquals([entity.email for entity in \
                            FieldsWithOptionsModel.objects.filter(
                            time__lt=self.last_save_time).order_by('time')],
                            ['app-engine@scholardocs.com', 'sharingan@uchias.com',
                            'rinnengan@sage.de',])

        # test ForeignKeys with id
        self.assertEquals(sorted([entity.email for entity in \
                            FieldsWithOptionsModel.objects.filter(
                            foreign_key__lt=3)]),
                            ['app-engine@scholardocs.com', 'sharingan@uchias.com'])

        # and with instance
        ordered_instance = OrderedModel.objects.get(priority=2)
        self.assertEquals(sorted([entity.email for entity in \
                            FieldsWithOptionsModel.objects.filter(
                            foreign_key__lt=ordered_instance)]),
                            ['app-engine@scholardocs.com', 'sharingan@uchias.com'])


    def test_gte(self):
        # test gte on float
        self.assertEquals([entity.floating_point for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          floating_point__gte=2.6).order_by('floating_point')],
                          [2.6, 5.3, 9.1])

        # test gte on integer
        self.assertEquals([entity.integer for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          integer__gte=2).order_by('integer')],
                          [2, 5, 9])

        # test filter on primary_key field
        self.assertEquals([entity.email for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          email__gte='rinnengan@sage.de').order_by('email')],
                          ['rinnengan@sage.de', 'sharingan@uchias.com', ])

    def test_lte(self):
        # test lte on float
        self.assertEquals([entity.floating_point for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          floating_point__lte=5.3).order_by('floating_point')],
                          [1.58, 2.6, 5.3])

        # test lte on integer
        self.assertEquals([entity.integer for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          integer__lte=5).order_by('integer')],
                          [1, 2, 5])

        # test filter on primary_key field
        self.assertEquals([entity.email for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          email__lte='rinnengan@sage.de').order_by('email')],
                          ['app-engine@scholardocs.com', 'rasengan@naruto.com',
                          'rinnengan@sage.de'])

    def test_equals(self):
        # test equality filter on primary_key field
        self.assertEquals([entity.email for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          email='rinnengan@sage.de').order_by('email')],
                          ['rinnengan@sage.de'])

        # test using exact
        self.assertEquals(FieldsWithOptionsModel.objects.filter(
                          email__exact='rinnengan@sage.de')[0].email,
                          'rinnengan@sage.de')

        self.assertEquals(FieldsWithOptionsModel.objects.filter(
                           pk='app-engine@scholardocs.com')[0].email,
                          'app-engine@scholardocs.com')

    def test_is_null(self):
        self.assertEquals(FieldsWithOptionsModel.objects.filter(
            floating_point__isnull=True).count(), 0)

        FieldsWithOptionsModel(integer=5.4, email='shinra.tensai@sixpaths.com',
            time=datetime.datetime.now().time()).save()

        self.assertEquals(FieldsWithOptionsModel.objects.filter(
            floating_point__isnull=True).count(), 1)


    def test_exclude(self):
        self.assertEquals([entity.email for entity in \
                            FieldsWithOptionsModel.objects.all().exclude(
                            floating_point__lt=9.1).order_by('floating_point')],
                            ['rinnengan@sage.de', ])

        # test exclude with foreignKey
        ordered_instance = OrderedModel.objects.get(priority=1)
        self.assertEquals(sorted([entity.email for entity in \
                            FieldsWithOptionsModel.objects.all().exclude(
                            foreign_key__gt=ordered_instance)]),
                            ['app-engine@scholardocs.com', 'sharingan@uchias.com',])


    def test_chained_filter(self):
        # additionally tests count :)
        self.assertEquals(FieldsWithOptionsModel.objects.filter(
                          floating_point__lt=5.3).filter(floating_point__gt=2.6).
                          count(), 0)

        # test across multiple columns. On app engine only one filter is allowed
        # to be an inequality filter
        self.assertEquals([(entity.floating_point, entity.integer) for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          floating_point__lte=5.3).filter(integer=2).order_by(
                          'floating_point')], [(2.6, 2), ])

        # test multiple filters including the primary_key field
        self.assertEquals([entity.email for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          email__gte='rinnengan@sage.de').filter(integer=2).order_by(
                          'email')], ['sharingan@uchias.com', ])

        # test in filter on primary key with another arbitrary filter
        self.assertEquals([entity.email for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          email__in=['rinnengan@sage.de',
                          'sharingan@uchias.com']).filter(integer__gt=2).order_by(
                          'integer')], ['rinnengan@sage.de', ])

        # Test exceptions

        # test multiple filters exception when filtered and not ordered against
        # the first filter
        self.assertRaises(BadArgumentError, FieldsWithOptionsModel.objects.filter(
                email__gte='rinnengan@sage.de').filter(floating_point=5.3).order_by(
                'floating_point').count)

        # test exception if filtered across multiple columns with inequality filter
        self.assertRaises(BadFilterError, FieldsWithOptionsModel.objects.filter(
                          floating_point__lte=5.3).filter(integer__gte=2).order_by(
                          'floating_point').get)

        # test exception if filtered across multiple columns with inequality filter
        # with exclude
        self.assertRaises(BadFilterError, FieldsWithOptionsModel.objects.filter(
                            email__lte='rinnengan@sage.de').exclude(
                            floating_point__lt=9.1).order_by('email').get)

        self.assertRaises(BadArgumentError, FieldsWithOptionsModel.objects.all().exclude(
                            floating_point__lt=9.1).order_by('email').count)

        # test exception on inequality filter.
        # TODO: support them for appengine via <>
        self.assertRaises(TypeError, FieldsWithOptionsModel.objects.exclude(
                            floating_point=9.1).order_by('floating_point').get)

        # TODO: Maybe check all possible exceptions

    def test_slicing(self):
        # test slicing on filter with primary_key
        self.assertEquals([entity.email for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          email__lte='rinnengan@sage.de').order_by('email')[:2]],
                          ['app-engine@scholardocs.com', 'rasengan@naruto.com', ])

        self.assertEquals([entity.email for entity in \
                          FieldsWithOptionsModel.objects.filter(
                          email__lte='rinnengan@sage.de').order_by('email')[1:2]],
                          ['rasengan@naruto.com', ])

        # test on non pk field
        self.assertEquals([entity.integer for entity in \
                          FieldsWithOptionsModel.objects.all().order_by(
                          'integer')[:2]], [1, 2, ])

        self.assertEquals([entity.email for entity in \
                          FieldsWithOptionsModel.objects.all().order_by(
                            'email')[::2]],
                          ['app-engine@scholardocs.com', 'rinnengan@sage.de',])

    def test_Q_objects(self):
        self.assertEquals([entity.email for entity in \
                          FieldsWithOptionsModel.objects.filter(
                            Q(email__lte='rinnengan@sage.de')).order_by('email')][:2],
                          ['app-engine@scholardocs.com', 'rasengan@naruto.com', ])

        self.assertEquals([entity.integer for entity in \
                          FieldsWithOptionsModel.objects.exclude(Q(integer__lt=5) |
                            Q(integer__gte=9)).order_by('integer')],
                            [5, ])

        self.assertRaises(TypeError, FieldsWithOptionsModel.objects.filter(
            Q(floating_point=9.1), Q(integer=9) | Q(integer=2)))

    def test_pk_in(self):
        # test pk__in with field name email
        self.assertEquals([entity.email for entity in
                            FieldsWithOptionsModel.objects.filter(
                            email__in=['app-engine@scholardocs.com',
                            'rasengan@naruto.com'])], ['app-engine@scholardocs.com',
                            'rasengan@naruto.com'])