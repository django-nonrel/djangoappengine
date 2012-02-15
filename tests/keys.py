from __future__ import with_statement
import warnings

from django.db import connection, models
from django.db.utils import DatabaseError
from django.test import TestCase
from django.utils import unittest

from djangotoolbox.fields import ListField


class AutoKey(models.Model):
    pass


class CharKey(models.Model):
    id = models.CharField(primary_key=True, max_length=10)


class IntegerKey(models.Model):
    id = models.IntegerField(primary_key=True)


class Parent(models.Model):
    pass


class Child(models.Model):
    parent = models.ForeignKey(Parent, null=True)


class CharParent(models.Model):
    id = models.CharField(primary_key=True, max_length=10)


class CharChild(models.Model):
    parent = models.ForeignKey(CharParent)


class IntegerParent(models.Model):
    id = models.IntegerField(primary_key=True)


class IntegerChild(models.Model):
    parent = models.ForeignKey(IntegerParent)


class ParentKind(models.Model):
    pass


class ChildKind(models.Model):
    parent = models.ForeignKey(ParentKind)
    parents = ListField(models.ForeignKey(ParentKind))


class KeysTest(TestCase):
    """
    GAE requires that keys are strings or positive integers,
    keys also play a role in defining entity groups.

    Note: len() is a way of forcing evaluation of a QuerySet -- we
    depend on the back-end to do some checks, so sometimes there is no
    way to raise an exception earlier.
    """

    def setUp(self):
        self.save_warnings_state()

    def tearDown(self):
        self.restore_warnings_state()

    def test_auto_field(self):
        """
        GAE keys may hold either strings or positive integers, however
        Django uses integers as well as their string representations
        for lookups, expecting both to be considered equivalent, so we
        limit AutoFields to just ints and check that int or string(int)
        may be used interchangably.

        Nonpositive keys are not allowed, and trying to use them to
        create or look up objects should raise a database exception.

        See: http://code.google.com/appengine/docs/python/datastore/keyclass.html.
        """
        AutoKey.objects.create()
        o1 = AutoKey.objects.create(pk=1)
        o2 = AutoKey.objects.create(pk='1')
#        self.assertEqual(o1, o2) TODO: Not same for Django, same for the database.
        with self.assertRaises(ValueError):
            AutoKey.objects.create(pk='a')
        self.assertEqual(AutoKey.objects.get(pk=1), o1)
        self.assertEqual(AutoKey.objects.get(pk='1'), o1)
        with self.assertRaises(ValueError):
            AutoKey.objects.get(pk='a')

        with self.assertRaises(DatabaseError):
            AutoKey.objects.create(id=-1)
        with self.assertRaises(DatabaseError):
            AutoKey.objects.create(id=0)
        with self.assertRaises(DatabaseError):
            AutoKey.objects.get(id=-1)
        with self.assertRaises(DatabaseError):
            AutoKey.objects.get(id__gt=-1)
        with self.assertRaises(DatabaseError):
            AutoKey.objects.get(id=0)
        with self.assertRaises(DatabaseError):
            AutoKey.objects.get(id__gt=0)
        with self.assertRaises(DatabaseError):
            len(AutoKey.objects.filter(id__gt=-1))
        with self.assertRaises(DatabaseError):
            len(AutoKey.objects.filter(id__gt=0))

    def test_primary_key(self):
        """
        Specifying a field as primary_key should work as long as the
        field values (after get_db_prep_*/value_to_db_* layer) can be
        represented by the back-end key type. In case a value can be
        represented, but lossy conversions, unexpected sorting, range
        limitation or potential future ramifications are possible it
        should warn the user (as early as possible).

        TODO: It may be even better to raise exceptions / issue
              warnings during model validation. And make use of the new
              supports_primary_key_on to prevent validation of models
              using unsupported primary keys.
        """

        # TODO: Move to djangotoolbox or django.db.utils?
        class Warning(StandardError):
            """Database warning (name following PEP 249)."""
            pass

        warnings.simplefilter('error', Warning)

        # This should just work.
        class AutoFieldKey(models.Model):
            key = models.AutoField(primary_key=True)
        AutoFieldKey.objects.create()

        # This one can be exactly represented.
        class CharKey(models.Model):
            id = models.CharField(primary_key=True, max_length=10)
        CharKey.objects.create(id='a')

        # Some rely on unstable assumptions or have other quirks and
        # should warn.

#        # TODO: Warning with a range limitation.
#        with self.assertRaises(Warning):
#
#            class IntegerKey(models.Model):
#                id = models.IntegerField(primary_key=True)
#            IntegerKey.objects.create(id=1)

#        # TODO: date/times could be resonably encoded / decoded as
#        #       strings (in a reversible manner) for key usage, but
#        #       would need special handling and continue to raise an
#        #       exception for now
#        with self.assertRaises(Warning):
#
#            class DateKey(models.Model):
#                id = models.DateField(primary_key=True, auto_now=True)
#            DateKey.objects.create()

#        # TODO: There is a db.Email field that would be better to
#        #       store emails, but that may prevent them from being
#        #       used as keys.
#        with self.assertRaises(Warning):
#
#            class EmailKey(models.Model):
#               id = models.EmailField(primary_key=True)
#            EmailKey.objects.create(id='aaa@example.com')

#        # TODO: Warn that changing field parameters breaks sorting.
#        #       This applies to any DecimalField, so should belong to
#        #       the docs.
#        with self.assertRaises(Warning):
#
#           class DecimalKey(models.Model):
#              id = models.DecimalField(primary_key=True, decimal_places=2,
#                                       max_digits=5)
#           DecimalKey.objects.create(id=1)

        # Some cannot be reasonably represented (e.g. binary or string
        # encoding would prevent comparisons to work as expected).
        with self.assertRaises(DatabaseError):

            class FloatKey(models.Model):
                id = models.FloatField(primary_key=True)
            FloatKey.objects.create(id=1.0)

        # TODO: Better fail during validation or creation than
        # sometimes when filtering (False = 0 is a wrong key value).
        with self.assertRaises(DatabaseError):

            class BooleanKey(models.Model):
                id = models.BooleanField(primary_key=True)
            BooleanKey.objects.create(id=True)
            len(BooleanKey.objects.filter(id=False))

    def test_primary_key_coercing(self):
        """
        Creation and lookups should use the same type casting as
        vanilla Django does, so CharField used as a key should cast
        everything to a string, while IntegerField should cast to int.
        """
        CharKey.objects.create(id=1)
        CharKey.objects.create(id='a')
        CharKey.objects.create(id=1.1)
        CharKey.objects.get(id='1')
        CharKey.objects.get(id='a')
        CharKey.objects.get(id='1.1')

        IntegerKey.objects.create(id=1)
        with self.assertRaises(ValueError):
            IntegerKey.objects.create(id='a')
        IntegerKey.objects.create(id=1.1)
        IntegerKey.objects.get(id='1')
        with self.assertRaises(ValueError):
            IntegerKey.objects.get(id='a')
        IntegerKey.objects.get(id=1.1)

    def test_foreign_key(self):
        """
        Foreign key lookups may use parent instance or parent key value.
        Using null foreign keys needs some special attention.

        TODO: In 1.4 one may also add _id suffix and use the key value.
        """
        parent1 = Parent.objects.create(pk=1)
        child1 = Child.objects.create(parent=parent1)
        child2 = Child.objects.create(parent=None)
        self.assertEqual(child1.parent, parent1)
        self.assertEqual(child2.parent, None)
        self.assertEqual(Child.objects.get(parent=parent1), child1)
        self.assertEqual(Child.objects.get(parent=1), child1)
        self.assertEqual(Child.objects.get(parent='1'), child1)
        with self.assertRaises(ValueError):
            Child.objects.get(parent='a')
        self.assertEqual(Child.objects.get(parent=None), child2)

    def test_foreign_key_backwards(self):
        """
        Following relationships backwards (_set syntax) with typed
        parent key causes a unique problem for the legacy key storage.
        """
        parent = CharParent.objects.create(id=1)
        child = CharChild.objects.create(parent=parent)
        self.assertEqual(list(parent.charchild_set.all()), [child])

        parent = IntegerParent.objects.create(id=1)
        child = IntegerChild.objects.create(parent=parent)
        self.assertEqual(list(parent.integerchild_set.all()), [child])

    @unittest.skipIf(
         not connection.settings_dict.get('STORE_RELATIONS_AS_DB_KEYS'),
         "No key kinds to check with the string/int foreign key storage.")
    def test_key_kind(self):
        """
        Checks that db.Keys stored in the database use proper kinds.

        Key kind should be the name of the table (db_table) of a model
        for primary keys of entities, but for foreign keys, references
        in general, it should be the db_table of the model the field
        refers to.

        Note that Django hides the underlying db.Key objects well, and
        it does work even with wrong kinds, but keeping the data
        consistent may be significant for external tools.

        TODO: Add DictField / EmbeddedModelField and nesting checks.
        """
        parent = ParentKind.objects.create(pk=1)
        child = ChildKind.objects.create(
            pk=2, parent=parent, parents=[parent.pk])
        self.assertEqual(child.parent.pk, parent.pk)
        self.assertEqual(child.parents[0], parent.pk)

        from google.appengine.api.datastore import Get
        from google.appengine.api.datastore_types import Key
        parent_key = Key.from_path(parent._meta.db_table, 1)
        child_key = Key.from_path(child._meta.db_table, 2)
        parent_entity = Get(parent_key)
        child_entity = Get(child_key)
        parent_column = child._meta.get_field('parent').column
        parents_column = child._meta.get_field('parents').column
        self.assertEqual(child_entity[parent_column], parent_key)
        self.assertEqual(child_entity[parents_column][0], parent_key)
