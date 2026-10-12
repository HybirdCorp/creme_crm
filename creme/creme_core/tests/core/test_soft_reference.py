from functools import partial

from creme.creme_core import soft_references
from creme.creme_core.core.entity_filter import condition_handler
from creme.creme_core.core.soft_reference import (
    SoftReferenceCollector,
    SoftReferenceRegistry,
    soft_reference_registry,
)
from creme.creme_core.models import (
    CremePropertyType,
    EntityFilter,
    FakeContact,
    Workflow,
)
from creme.creme_core.workflows import PropertyAddingTrigger

from ..base import CremeTestCase


class SoftReferenceRegistryTestCase(CremeTestCase):
    def test_register(self):
        registry = SoftReferenceRegistry()
        self.assertFalse([*registry.collector_classes])

        registry.register(
            soft_references.EFilterConditionPTypeRefCollector,
            soft_references.PropertyAddingTriggerPTypeRefCollector,
        )
        self.assertCountEqual(
            [
                soft_references.EFilterConditionPTypeRefCollector,
                soft_references.PropertyAddingTriggerPTypeRefCollector,
            ],
            [*registry.collector_classes],
        )

        # ---
        registry.unregister(soft_references.EFilterConditionPTypeRefCollector)
        self.assertListEqual(
            [soft_references.PropertyAddingTriggerPTypeRefCollector],
            [*registry.collector_classes],
        )

    def test_register__empty_id(self):
        class TestCollector(SoftReferenceCollector):
            # id = ...
            model = CremePropertyType

        registry = SoftReferenceRegistry()

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestCollector)

    def test_register__duplicated_id(self):
        class TestCollector1(SoftReferenceCollector):
            id = 'creme_core-test_duplicated'
            model = CremePropertyType

        class TestCollector2(SoftReferenceCollector):
            id = TestCollector1.id
            model = CremePropertyType

        registry = SoftReferenceRegistry().register(TestCollector1)

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestCollector2)

    def test_unregister__missing(self):
        class TestCollector(SoftReferenceCollector):
            id = 'creme_core-test_missing'
            model = CremePropertyType

        registry = SoftReferenceRegistry()

        with self.assertRaises(registry.UnRegistrationError):
            registry.unregister(TestCollector)

    def test_references_for__empty(self):
        ptype = CremePropertyType.objects.create(text='is cool')
        self.assertListEqual([], [*SoftReferenceRegistry().collect(ptype)])

    def test_references_for__ptype(self):
        registry = SoftReferenceRegistry().register(
            soft_references.EFilterConditionPTypeRefCollector,
            soft_references.EFilterConditionRTypeRefCollector,
            soft_references.PropertyAddingTriggerPTypeRefCollector,
        )

        create_ptype = partial(CremePropertyType.objects.create, is_custom=True)
        ptype1 = create_ptype(text='is a fighter')
        ptype2 = create_ptype(text='knows kung-fu')

        # ---
        build_cond = partial(
            condition_handler.PropertyConditionHandler.build_condition,
            model=FakeContact,
        )
        efilter1 = EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_views_ptype1',
            name='Fighters', model=FakeContact,
            is_custom=True,
            conditions=[build_cond(ptype=ptype1, has=True)],
        )
        EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_views_ptype2',
            name='Kung fuists', model=FakeContact,
            is_custom=True,
            conditions=[build_cond(ptype=ptype2, has=True)],
        )

        wf = Workflow.objects.create(
            title='Flow #1',
            content_type=FakeContact,
            trigger=PropertyAddingTrigger(entity_model=FakeContact, ptype=ptype1),
            # conditions=...
            # actions=[],
        )
        self.assertCountEqual([efilter1, wf], [*registry.collect(ptype1)])

    def test_global_regsitry(self):
        classes = {*soft_reference_registry.collector_classes}
        self.assertIn(soft_references.RelationTypeConstraintPTypeRefCollector, classes)
        self.assertIn(soft_references.EFilterConditionCFieldRefCollector, classes)
        self.assertIn(soft_references.EFilterConditionCFieldEnumValueRefCollector, classes)
        self.assertIn(soft_references.EFilterConditionPTypeRefCollector, classes)
        self.assertIn(soft_references.EFilterConditionRTypeRefCollector, classes)
        self.assertIn(soft_references.EFilterConditionPortableKeyedRefCollector, classes)
        self.assertIn(soft_references.PropertyAddingTriggerPTypeRefCollector, classes)
        self.assertIn(soft_references.RelationAddingTriggerRTypeRefCollector, classes)
        self.assertIn(soft_references.WorkflowConditionCFieldRefCollector, classes)
        self.assertIn(soft_references.WorkflowConditionCFieldEnumValueRefCollector, classes)
        self.assertIn(soft_references.WorkflowConditionPortableKeyedRefCollector, classes)
        self.assertIn(soft_references.PropertyAddingActionPTypeRefCollector, classes)
        self.assertIn(soft_references.RelationAddingActionRTypeRefCollector, classes)
        self.assertIn(soft_references.NotificationSendingActionUserRefCollector, classes)
