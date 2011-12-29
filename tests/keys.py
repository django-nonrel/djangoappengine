from django.db import models
from django.test import TestCase
from django.db.utils import DatabaseError

from google.appengine.api.datastore import Key

from ..fields import GAEKeyField
from ..models import GAEKey

class ParentModel(models.Model):
    key = GAEKeyField(primary_key=True)

class NonGAEParentModel(models.Model):
    id = models.AutoField(primary_key=True)

class ChildModel(models.Model):
    key = GAEKeyField(primary_key=True, parent_key_name='parent_key')

class AnotherChildModel(models.Model):
    key = GAEKeyField(primary_key=True, parent_key_name='also_parent_key')

class ForeignKeyModel(models.Model):
    id = models.AutoField(primary_key=True)
    relation = models.ForeignKey(ParentModel)

class KeysTest(TestCase):
    def testGAEKeySave(self):
        model = ParentModel()
        model.save()
        
        self.assertIsNotNone(model.pk)

    def testUnsavedParent(self):
        parent = ParentModel()

        with self.assertRaises(ValueError):
            child = ChildModel(parent_key=parent.pk)

    def testNonGAEParent(self):
        parent = NonGAEParentModel()
        parent.save()

        with self.assertRaises(ValueError):
            child = ChildModel(parent_key=parent.pk)

    def testParentChildSave(self):
        parent = ParentModel()
        orig_parent_pk = parent.pk
        parent.save()
        
        child = ChildModel(parent_key=parent.pk)
        orig_child_pk = child.pk
        child.save()
        
        self.assertNotEquals(parent.pk, orig_parent_pk)
        self.assertNotEquals(child.pk, orig_child_pk)
        self.assertEquals(child.pk.parent_key(), parent.pk)
        self.assertEquals(child.pk.parent_key().real_key(), parent.pk.real_key())
    
    def testAncestorFilterQuery(self):
        parent = ParentModel()
        parent.save()
        
        child = ChildModel(parent_key=parent.pk)
        child.save()
        
        results = list(ChildModel.objects.filter(pk=parent.pk.as_ancestor()))
        
        self.assertEquals(1, len(results))
        self.assertEquals(results[0].pk, child.pk)

    def testAncestorGetQuery(self):
        parent = ParentModel()
        parent.save()
        
        child = ChildModel(parent_key=parent.pk)
        child.save()

        result = ChildModel.objects.get(pk=parent.pk.as_ancestor())

        self.assertEquals(result.pk, child.pk)

    def testEmptyAncestorQuery(self):
        parent = ParentModel()
        parent.save()

        results = list(ChildModel.objects.filter(pk=parent.pk.as_ancestor()))

        self.assertEquals(0, len(results))

    def testEmptyAncestorQueryWithUnsavedChild(self):
        parent = ParentModel()
        parent.save()

        child = ChildModel(parent_key=parent.pk)

        results = list(ChildModel.objects.filter(pk=parent.pk.as_ancestor()))

        self.assertEquals(0, len(results))

    def testUnsavedAncestorQuery(self):
        parent = ParentModel()

        with self.assertRaises(AttributeError):
            results = list(ChildModel.objects.filter(pk=parent.pk.as_ancestor()))

    def testDifferentChildrenAncestorQuery(self):
        parent = ParentModel()
        parent.save()

        child1 = ChildModel(parent_key=parent.pk)
        child1.save()
        child2 = AnotherChildModel(also_parent_key=parent.pk)
        child2.save()

        results = list(ChildModel.objects.filter(pk=parent.pk.as_ancestor()))

        self.assertEquals(1, len(results))
        self.assertEquals(results[0].pk, child1.pk)

        results = list(AnotherChildModel.objects.filter(pk=parent.pk.as_ancestor()))
        self.assertEquals(1, len(results))
        self.assertEquals(results[0].pk, child2.pk)

    def testDifferentParentsAncestorQuery(self):
        parent1 = ParentModel()
        parent1.save()

        child1 = ChildModel(parent_key=parent1.pk)
        child1.save()
        
        parent2 = ParentModel()
        parent2.save()
        
        child2 = ChildModel(parent_key=parent2.pk)
        child2.save()

        results = list(ChildModel.objects.filter(pk=parent1.pk.as_ancestor()))

        self.assertEquals(1, len(results))
        self.assertEquals(results[0].pk, child1.pk)

        results = list(ChildModel.objects.filter(pk=parent2.pk.as_ancestor()))
        self.assertEquals(1, len(results))
        self.assertEquals(results[0].pk, child2.pk)

    def testForeignKeyWithGAEKey(self):
        parent = ParentModel()
        parent.save()

        fkm = ForeignKeyModel()
        fkm.relation = parent
        fkm.save()

        results = list(ForeignKeyModel.objects.filter(relation=parent))
        self.assertEquals(1, len(results))
        self.assertEquals(results[0].pk, fkm.pk)

    def testPrimaryKeyQuery(self):
        parent = ParentModel()
        parent.save()

        db_parent = ParentModel.objects.get(pk=parent.pk)

        self.assertEquals(parent.pk, db_parent.pk)

    def testPrimaryKeyQueryStringKey(self):
        parent = ParentModel()
        parent.save()

        db_parent = ParentModel.objects.get(pk=str(parent.pk))

        self.assertEquals(parent.pk, db_parent.pk)

    def testPrimaryKeyQueryIntKey(self):
        parent = ParentModel()
        parent.save()

        db_parent = ParentModel.objects.get(pk=int(str(parent.pk)))

        self.assertEquals(parent.pk, db_parent.pk)
    