from datetime import date
from functools import partial

from django.db.models import Model

from creme.creme_core import soft_references, workflows
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    condition_handler,
    operators,
)
from creme.creme_core.core.notification import OUTPUT_WEB
from creme.creme_core.core.workflow import WorkflowConditions
from creme.creme_core.models import (
    CremePropertyType,
    CremeUser,
    CustomField,
    CustomFieldEnumValue,
    EntityFilter,
    FakeContact,
    FakeOrganisation,
    FakePosition,
    FakeSector,
    FakeTodo,
    NotificationChannel,
    RelationType,
    Workflow,
)

from .base import CremeTestCase


class RelationTypeSoftReferencesTestCase(CremeTestCase):
    def test_property_type(self):
        collector = soft_references.RelationTypeConstraintPTypeRefCollector()
        self.assertEqual(CremePropertyType, collector.model)
        self.assertEqual('creme_core-rtype_constraints-ptype', collector.id)

        ptype = CremePropertyType.objects.create(text='is a fighter', is_custom=True)
        rtype1 = RelationType.objects.builder(
            id='test-subject_foo', predicate='has killed',
            models=[FakeContact], properties=[ptype],
        ).symmetric(
            id='test-object_foo', predicate='has been killed by',
        ).get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_bar', predicate='has beaten',
            models=[FakeContact], forbidden_properties=[ptype],
        ).symmetric(
            id='test-object_bar', predicate='has been beaten by',
        ).get_or_create()[0]

        self.assertCountEqual([rtype1, rtype2], collector.collect(ptype))


class EntityFilterSoftReferencesTestCase(CremeTestCase):
    def test_custom_field(self):
        collector = soft_references.EFilterConditionCFieldRefCollector()
        self.assertEqual(CustomField, collector.model)
        self.assertEqual('creme_core-efilter_condition_cfield-cfield', collector.id)

        create_cf = partial(
            CustomField.objects.create, content_type=FakeContact, is_deleted=True,
        )
        cfield1 = create_cf(name='HP', field_type=CustomField.INT)
        cfield2 = create_cf(name='First fight', field_type=CustomField.DATE)

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'creme_config-tests_views_cfield1',
            name='Tanks', model=FakeContact,
            is_custom=True,
            conditions=[condition_handler.CustomFieldConditionHandler.build_condition(
                custom_field=cfield1, operator=operators.GTE, values=[1000],
            )],
        )
        efilter2 = EntityFilter.objects.create(
            id='creme_config-tests_views_cfield2',
            name='Mid',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.CustomFieldConditionHandler.build_condition(
                    custom_field=cfield1, operator=operators.GTE, values=[160],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False, check_privacy=False,
        )
        efilter3 = EntityFilter.objects.smart_update_or_create(
            'creme_config-tests_views_cfield3',
            name='Magician', model=FakeContact, is_custom=True,
            conditions=[condition_handler.DateCustomFieldConditionHandler.build_condition(
                custom_field=cfield2, start=date(year=2025, month=6, day=21),
            )],
        )
        self.assertCountEqual([efilter1, efilter2], collector.collect(cfield1))
        self.assertCountEqual([efilter3],           collector.collect(cfield2))

    def test_custom_field_enum(self):
        collector = soft_references.EFilterConditionCFieldEnumValueRefCollector()
        self.assertEqual(CustomFieldEnumValue, collector.model)
        self.assertEqual('creme_core-efilter_condition_cfield-evalue', collector.id)

        create_cfield = partial(CustomField.objects.create, content_type=FakeContact)
        cfield1 = create_cfield(name='Programming languages', field_type=CustomField.ENUM)
        cfield2 = create_cfield(name='Extra info',            field_type=CustomField.STR)

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield1)
        eval1 = create_evalue(value='C')
        eval2 = create_evalue(value='bash')

        sector = FakeSector.objects.create(title='Colliding', uuid=eval1.uuid)

        efilter1 = EntityFilter.objects.create(
            id='creme_config-tests_blocked_deletion1',
            name='C developers',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.CustomFieldConditionHandler.build_condition(
                    custom_field=cfield1,
                    operator=operators.EqualsOperator,
                    values=[eval1.id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False, check_privacy=False,
        )
        EntityFilter.objects.create(
            id='creme_config-tests_blocked_deletion2',
            name='C developers (regular)',
            entity_type=FakeContact,
            # filter_type=EF_CREDENTIALS,  NOPE
        ).set_conditions(
            [
                condition_handler.CustomFieldConditionHandler.build_condition(
                    custom_field=cfield1,
                    operator=operators.EqualsOperator,
                    values=[eval1.id],
                ),
            ],
            check_cycles=False, check_privacy=False,
        )
        efilter3 = EntityFilter.objects.create(
            id='creme_config-tests_blocked_deletion3',
            name='Not C developers',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.CustomFieldConditionHandler.build_condition(
                    custom_field=cfield1,
                    operator=operators.EqualsNotOperator,
                    values=[eval1.id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False, check_privacy=False,
        )
        efilter4 = EntityFilter.objects.create(
            id='creme_config-tests_blocked_deletion4',
            name='Related to second value',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.CustomFieldConditionHandler.build_condition(
                    custom_field=cfield1,
                    operator=operators.EqualsOperator,
                    values=[eval2.id],  # <===
                    filter_type=EF_CREDENTIALS,
                ),
                condition_handler.RegularFieldConditionHandler.build_condition(   # <===
                    model=FakeContact,
                    operator=operators.EqualsOperator,
                    field_name='sector',
                    values=[str(sector.uuid)],
                    filter_type=EF_CREDENTIALS,
                ),
                condition_handler.CustomFieldConditionHandler.build_condition(
                    custom_field=cfield2,  # <===
                    operator=operators.EqualsOperator,
                    values=[str(eval1.uuid)],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False, check_privacy=False,
        )

        self.assertCountEqual([efilter1, efilter3], collector.collect(eval1))
        self.assertCountEqual([efilter4],           collector.collect(eval2))

    def test_property_type(self):
        collector = soft_references.EFilterConditionPTypeRefCollector()
        self.assertEqual(CremePropertyType, collector.model)
        self.assertEqual('creme_core-efilter_condition_ptype-ptype', collector.id)

        create_ptype = partial(CremePropertyType.objects.create, is_custom=True)
        ptype1 = create_ptype(text='is a fighter')
        ptype2 = create_ptype(text='knows kung-fu')
        self.assertFalse([*collector.collect(ptype1)])
        self.assertFalse([*collector.collect(ptype2)])

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
        efilter2 = EntityFilter.objects.create(
            id='creme_core-tests_views_ptype2',
            name='Not fighters',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [build_cond(ptype=ptype1, has=False, filter_type=EF_CREDENTIALS)],
            check_cycles=False, check_privacy=False,
        )
        efilter3 = EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_views_ptype3',
            name='Martialists', model=FakeContact,
            is_custom=True,
            conditions=[build_cond(ptype=ptype2, has=True)],
        )
        self.assertCountEqual([efilter1, efilter2], collector.collect(ptype1))
        self.assertCountEqual([efilter3],           collector.collect(ptype2))

    def test_relation_type(self):
        collector = soft_references.EFilterConditionRTypeRefCollector()
        self.assertEqual(RelationType, collector.model)
        self.assertEqual('creme_core-efilter_condition_rtypes-rtype', collector.id)

        rtype1 = RelationType.objects.builder(
            id='test-subject_foo', predicate='Subject predicate #1', is_custom=True,
        ).symmetric(id='test-object_foo', predicate='Object predicate #1').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_bar', predicate='Subject predicate #2', is_custom=True,
        ).symmetric(id='test-object_bar', predicate='Object predicate #2').get_or_create()[0]

        build_cond = partial(
            condition_handler.RelationConditionHandler.build_condition,
            model=FakeContact,
        )
        efilter1 = EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_views_rtype1',
            name='Related to #1', model=FakeContact,
            is_custom=True,
            conditions=[build_cond(rtype=rtype1, has=True)],
        )
        efilter2 = EntityFilter.objects.create(
            id='creme_core-tests_views_rtype2',
            name='Related to #1 (symmetric)',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [build_cond(rtype=rtype1.symmetric_type, has=False, filter_type=EF_CREDENTIALS)],
            check_cycles=False, check_privacy=False,
        )
        efilter3 = EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_views_rtype3',
            name='Related to #2', model=FakeContact,
            is_custom=True,
            conditions=[build_cond(rtype=rtype2, has=True)],
        )
        self.assertCountEqual([efilter1, efilter2], collector.collect(rtype1))
        self.assertCountEqual([efilter3],           collector.collect(rtype2))

    def test_relation_type_subfilter(self):
        collector = soft_references.EFilterConditionRTypeRefCollector()

        rtype = RelationType.objects.builder(
            id='test-subject_foo', predicate='Subject predicate', is_custom=True,
        ).symmetric(id='test-object_foo', predicate='Object predicate').get_or_create()[0]
        sub_filter = EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_softref_rtype_sub',
            name='Corps', model=FakeOrganisation,
            is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.EndsWithOperator,
                    field_name='name',
                    values=[' Corp'],
                ),
            ],
        )
        efilter = EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_softref_rtype',
            name='Related to corps', model=FakeContact,
            is_custom=True,
            conditions=[
                condition_handler.RelationSubFilterConditionHandler.build_condition(
                    model=FakeContact, rtype=rtype, subfilter=sub_filter,
                ),
            ],
        )
        self.assertCountEqual([efilter], collector.collect(rtype))

    def test_portable_key__minion(self):
        collector = soft_references.EFilterConditionPortableKeyedRefCollector()
        self.assertEqual(Model, collector.model)
        self.assertEqual('creme_core-efilter_condition_rfield-portable_keyed', collector.id)

        create_sector = FakeSector.objects.create
        sector1 = create_sector(title='Music')
        sector2 = create_sector(title='Drawing')
        sector3 = create_sector(title='Art')

        pos = FakePosition.objects.create(title='Colliding', uuid=sector1.uuid)

        ptype = CremePropertyType.objects.create(text='is cool', is_custom=True)

        efilter1 = EntityFilter.objects.create(
            id='creme_config-tests_ref_collector1',
            name='Musicians (system)',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EqualsOperator,
                    field_name='sector', values=[str(sector1.uuid)],
                    filter_type=EF_CREDENTIALS,
                ),
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EqualsOperator,
                    field_name='sector',
                    # NB: sector1 appears a second time for the same filter
                    values=[str(sector3.uuid), str(sector1.uuid)],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False, check_privacy=False,
        )
        EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_ref_collector2',
            name='Musicians', model=FakeOrganisation,
            is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.EqualsOperator,
                    field_name='sector', values=[str(sector1.uuid)],
                ),
            ],
        )
        EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_ref_collector3',
            name='Other (ptype)', model=FakeContact, is_custom=True,
            conditions=[condition_handler.PropertyConditionHandler.build_condition(
                model=FakeContact, ptype=ptype, has=True,
            )],
        )
        efilter4 = EntityFilter.objects.create(
            id='creme_config-tests_ref_collector4',
            name='Drawers (system)',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EqualsOperator,
                    field_name='sector', values=[str(sector2.uuid)],
                    filter_type=EF_CREDENTIALS,
                ),
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EqualsOperator,
                    field_name='position', values=[str(pos.uuid)],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False, check_privacy=False,
        )
        self.assertListEqual([efilter1], [*collector.collect(sector1)])
        self.assertListEqual([efilter4], [*collector.collect(sector2)])

        # ----
        self.assertHasNoAttr(FakeTodo, 'portable_key')
        nopk = FakeTodo.objects.create(
            title='My todo',
            creme_entity=FakeOrganisation.objects.create(user=self.get_root_user()),
        )

        with self.assertNoException():
            empty = [*collector.collect(nopk)]
        self.assertFalse(empty)

    def test_portable_key__user(self):
        collector = soft_references.EFilterConditionPortableKeyedRefCollector()

        user = self.get_root_user()
        user_to_ref = self.create_user()

        sector = FakeSector.objects.create(title='Colliding', uuid=user_to_ref.uuid)

        efilter1 = EntityFilter.objects.create(
            id='creme_config-tests_blocked_deletion1',
            name=f"Contacts belonging to {user.username}",
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EqualsOperator,
                    field_name='user', values=[str(user_to_ref.uuid)],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False, check_privacy=False,
        )
        EntityFilter.objects.create(
            id='creme_config-tests_blocked_deletion2',
            name=f"Contacts belonging to {user.username} (regular)",
            entity_type=FakeContact,
            # filter_type=EF_CREDENTIALS,  # Nope
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EqualsOperator,
                    field_name='user', values=[str(user.uuid)],
                ),
            ],
            check_cycles=False, check_privacy=False,
        )
        efilter3 = EntityFilter.objects.create(
            id='creme_config-tests_blocked_deletion3',
            name=f"The Contact corresponding to {user.username}",
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EqualsOperator,
                    field_name='is_user', values=[str(user_to_ref.uuid)],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False, check_privacy=False,
        )
        EntityFilter.objects.create(
            id='creme_config-tests_blocked_deletion4',
            name='Other ignored contact filter',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EqualsOperator,
                    field_name='description', values=['Important'],
                    filter_type=EF_CREDENTIALS,
                ),
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EqualsOperator,
                    field_name='is_user', values=[str(user.uuid)],
                    filter_type=EF_CREDENTIALS,
                ),
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EqualsOperator,
                    field_name='sector', values=[str(sector.uuid)],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False, check_privacy=False,
        )
        self.assertListEqual([efilter1, efilter3], [*collector.collect(user_to_ref)])


class WorkflowSoftReferencesTestCase(CremeTestCase):
    def test_trigger__property_type(self):
        collector = soft_references.PropertyAddingTriggerPTypeRefCollector()
        self.assertEqual('creme_core-workflow_prop_added-ptype', collector.id)
        self.assertEqual(CremePropertyType, collector.model)

        create_ptype = partial(CremePropertyType.objects.create, is_custom=True)
        ptype1 = create_ptype(text='is a fighter')
        ptype2 = create_ptype(text='knows kung-fu')

        wf1 = Workflow.objects.create(
            title='Flow #1', content_type=FakeContact,
            trigger=workflows.PropertyAddingTrigger(
                entity_model=FakeContact, ptype=ptype1,
            ),
            # conditions=..., actions=[],
        )
        wf2 = Workflow.objects.create(
            title='Flow on other ptype', content_type=FakeContact,
            trigger=workflows.PropertyAddingTrigger(
                entity_model=FakeContact, ptype=ptype2,
            ),
            # conditions=..., actions=[],
        )
        wf3 = Workflow.objects.create(
            title='Flow #3', content_type=FakeOrganisation,
            trigger=workflows.PropertyAddingTrigger(
                entity_model=FakeOrganisation, ptype=ptype1,
            ),
            # conditions=..., actions=[],
        )

        self.clear_global_info()
        self.assertCountEqual([wf1, wf3], collector.collect(ptype1))
        self.assertCountEqual([wf2],      collector.collect(ptype2))

    def test_trigger__relation_type(self):
        collector = soft_references.RelationAddingTriggerRTypeRefCollector()
        self.assertEqual('creme_core-workflow_relation_added-rtype', collector.id)
        self.assertEqual(RelationType, collector.model)

        rtype1 = RelationType.objects.builder(
            id='test-subject_foo', predicate='Subject predicate #1', is_custom=True,
        ).symmetric(id='test-object_foo', predicate='Object predicate #1').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_bar', predicate='Subject predicate #2', is_custom=True,
        ).symmetric(id='test-object_bar', predicate='Object predicate #2').get_or_create()[0]

        wf1 = Workflow.objects.create(
            title='Flow #1', content_type=FakeContact,
            trigger=workflows.RelationAddingTrigger(
                subject_model=FakeContact, rtype=rtype1, object_model=FakeOrganisation,
            ),
            # conditions=..., actions=[],
        )
        wf2 = Workflow.objects.create(
            title='Flow on other ptype',
            content_type=FakeContact,
            trigger=workflows.RelationAddingTrigger(
                subject_model=FakeContact, rtype=rtype2, object_model=FakeOrganisation,
            ),
            # conditions=..., actions=[],
        )
        wf3 = Workflow.objects.create(
            title='Flow #3',
            content_type=FakeOrganisation,
            trigger=workflows.RelationAddingTrigger(
                subject_model=FakeOrganisation,
                rtype=rtype1.symmetric_type,
                object_model=FakeContact,
            ),
            # conditions=..., actions=[],
        )
        self.assertCountEqual([wf1, wf3], collector.collect(rtype1))
        self.assertCountEqual([wf2],      collector.collect(rtype2))

    def test_condition__custom_field(self):
        collector = soft_references.WorkflowConditionCFieldRefCollector()
        self.assertEqual('creme_core-workflow_condition_cfield-cfield', collector.id)
        self.assertEqual(CustomField, collector.model)

        model = FakeContact
        create_cf = partial(CustomField.objects.create, content_type=model, is_deleted=True)
        cfield1 = create_cf(name='HP', field_type=CustomField.INT)
        cfield2 = create_cf(name='First fight', field_type=CustomField.DATE)

        trigger = workflows.EntityCreationTrigger(model=model)
        source = workflows.CreatedEntitySource(model=model)
        wf1 = Workflow.objects.create(
            title='Flow #1', content_type=model, trigger=trigger,
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[condition_handler.CustomFieldConditionHandler.build_condition(
                    custom_field=cfield1, operator=operators.GTE, values=[1000],
                )],
            ),
            # actions=[],
        )
        wf2 = Workflow.objects.create(
            title='Flow on other cfield',
            content_type=model,
            trigger=trigger,
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[condition_handler.DateCustomFieldConditionHandler.build_condition(
                    custom_field=cfield2, start=date(year=2025, month=6, day=21),
                )],
            ),
            # actions=[],
        )
        wf3 = Workflow.objects.create(
            title='Flow #3', content_type=model, trigger=trigger,
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[condition_handler.CustomFieldConditionHandler.build_condition(
                    custom_field=cfield1, operator=operators.GTE, values=[1500]
                )],
            ),
            # actions=[],
        )
        self.assertCountEqual([wf1, wf3], collector.collect(cfield1))
        self.assertCountEqual([wf2],      collector.collect(cfield2))

    def test_condition__custom_field_enum_value(self):
        collector = soft_references.WorkflowConditionCFieldEnumValueRefCollector()
        self.assertEqual('creme_core-workflow_condition_cfield-evalue', collector.id)
        self.assertEqual(CustomFieldEnumValue, collector.model)

        create_cfield = partial(CustomField.objects.create, content_type=FakeContact)
        cfield1 = create_cfield(name='Programming languages', field_type=CustomField.ENUM)
        cfield2 = create_cfield(name='Extra info',            field_type=CustomField.STR)

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield1)
        eval1 = create_evalue(value='C')
        eval2 = create_evalue(value='bash')

        sector = FakeSector.objects.create(title='Colliding', uuid=eval1.uuid)

        wf1 = Workflow.objects.create(
            title='My blocking WF #1',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            conditions=WorkflowConditions().add(
                source=workflows.CreatedEntitySource(model=FakeContact),
                conditions=[
                    condition_handler.CustomFieldConditionHandler.build_condition(
                        custom_field=cfield1,
                        operator=operators.EqualsOperator,
                        values=[eval1.id],
                    ),
                ],
            ),
        )
        wf2 = Workflow.objects.create(
            title='Not blocking WF',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            conditions=WorkflowConditions().add(
                source=workflows.CreatedEntitySource(model=FakeContact),
                conditions=[
                    condition_handler.CustomFieldConditionHandler.build_condition(
                        custom_field=cfield1,
                        operator=operators.EqualsOperator,
                        values=[eval2.id],  # <===
                    ),
                    condition_handler.RegularFieldConditionHandler.build_condition(   # <===
                        model=FakeContact,
                        operator=operators.EqualsOperator,
                        field_name='sector',
                        values=[str(sector.uuid)],
                    ),
                    condition_handler.CustomFieldConditionHandler.build_condition(
                        custom_field=cfield2,  # <===
                        operator=operators.EqualsOperator,
                        values=[str(eval1.uuid)],
                        filter_type=EF_CREDENTIALS,
                    ),
                ],
            ),
        )
        wf3 = Workflow.objects.create(
            title='My blocking WF #2',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            conditions=WorkflowConditions().add(
                source=workflows.CreatedEntitySource(model=FakeContact),
                conditions=[
                    condition_handler.CustomFieldConditionHandler.build_condition(
                        custom_field=cfield1,
                        operator=operators.EqualsNotOperator,
                        values=[eval1.id],
                    ),
                ],
            ),
        )
        self.assertCountEqual([wf1, wf3], collector.collect(eval1))
        self.assertCountEqual([wf2],      collector.collect(eval2))

    def test_condition__portable_key__minion(self):
        collector = soft_references.WorkflowConditionPortableKeyedRefCollector()
        self.assertEqual('creme_core-workflow_condition_rfield-portable_keyed', collector.id)
        self.assertEqual(Model, collector.model)

        create_sector = FakeSector.objects.create
        sector1 = create_sector(title='Music')
        sector2 = create_sector(title='Drawing')

        pos = FakePosition.objects.create(title='Colliding', uuid=sector1.uuid)

        trigger = workflows.EntityCreationTrigger(model=FakeContact)
        source = workflows.CreatedEntitySource(model=FakeContact)
        build_cond = partial(
            condition_handler.RegularFieldConditionHandler.build_condition,
            model=FakeContact, operator=operators.EQUALS,
        )
        wf1 = Workflow.objects.create(
            title='Singers',
            content_type=FakeContact,
            trigger=trigger,
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[build_cond(field_name='sector', values=[sector1.uuid])],
            ),
        )
        wf2 = Workflow.objects.create(
            title='Drawers',
            content_type=FakeContact,
            trigger=trigger,
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[
                    build_cond(field_name='sector', values=[sector2.uuid]),
                    build_cond(field_name='position', values=[pos.uuid]),
                ],
            ),
        )
        wf3 = Workflow.objects.create(
            title='Musicians',
            content_type=FakeContact,
            trigger=trigger,
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[build_cond(field_name='sector', values=[sector1.uuid])],
            ),
        )
        # TODO: alphabetical ordering [wf3, wf1]?
        self.assertListEqual([wf1, wf3], [*collector.collect(sector1)])
        self.assertListEqual([wf2],      [*collector.collect(sector2)])

        # ----
        self.assertHasNoAttr(FakeTodo, 'portable_key')
        nopk = FakeTodo.objects.create(
            title='My todo',
            creme_entity=FakeOrganisation.objects.create(user=self.get_root_user()),
        )

        with self.assertNoException():
            empty = [*collector.collect(nopk)]
        self.assertFalse(empty)

    def test_condition__portable_key__user(self):
        collector = soft_references.WorkflowConditionPortableKeyedRefCollector()

        user = self.get_root_user()
        user_to_ref = self.create_user()

        ptype = CremePropertyType.objects.create(text='is cool',)
        sector = FakeSector.objects.create(title='Colliding', uuid=user_to_ref.uuid)

        wf1 = Workflow.objects.create(
            title='Blocking Flow #1',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            conditions=WorkflowConditions().add(
                source=workflows.CreatedEntitySource(model=FakeContact),
                conditions=[
                    condition_handler.RegularFieldConditionHandler.build_condition(
                        model=FakeContact,
                        operator=operators.EqualsOperator,
                        field_name='user', values=[user_to_ref.uuid],
                    ),
                ],
            ),
            # actions=[],
        )
        wf2 = Workflow.objects.create(
            title='Not blocking Flow #1',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            conditions=WorkflowConditions().add(
                source=workflows.CreatedEntitySource(model=FakeContact),
                conditions=[
                    condition_handler.RegularFieldConditionHandler.build_condition(
                        model=FakeContact,
                        operator=operators.EqualsOperator,
                        field_name='sector', values=[sector.uuid],
                    ),
                    condition_handler.RegularFieldConditionHandler.build_condition(
                        model=FakeContact,
                        operator=operators.EqualsOperator,
                        field_name='user', values=[user.uuid],
                    ),
                    condition_handler.RegularFieldConditionHandler.build_condition(
                        model=FakeContact,
                        operator=operators.ContainsOperator,
                        field_name='description', values=[str(user_to_ref.uuid)],
                    ),
                    condition_handler.PropertyConditionHandler.build_condition(
                        model=FakeContact, ptype=ptype, has=True,
                    ),
                ],
            ),
            # actions=[],
        )
        wf3 = Workflow.objects.create(
            title='Blocking Flow #2',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            conditions=WorkflowConditions().add(
                source=workflows.CreatedEntitySource(model=FakeContact),
                conditions=[
                    condition_handler.RegularFieldConditionHandler.build_condition(
                        model=FakeContact,
                        operator=operators.EqualsOperator,
                        field_name='is_user', values=[str(user_to_ref.uuid)],
                    ),
                ],
            ),
            # actions=[],
        )

        self.clear_global_info()
        self.assertCountEqual([wf1, wf3], collector.collect(user_to_ref))
        self.assertCountEqual([wf2],      collector.collect(user))

    def test_action__property_type(self):
        collector = soft_references.PropertyAddingActionPTypeRefCollector()
        self.assertEqual('creme_core-workflow_prop_action-ptype', collector.id)
        self.assertEqual(CremePropertyType, collector.model)
        # self.assertEqual(_('Action of Workflow'), collector.get_label())

        create_ptype = partial(CremePropertyType.objects.create, is_custom=True)
        ptype1 = create_ptype(text='is a fighter')
        ptype2 = create_ptype(text='knows kung-fu')

        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        rtype = RelationType.objects.builder(
            id='test-subject_linked', predicate='is linked to',
        ).symmetric(id='test-object_linked', predicate='is linked to').get_or_create()[0]

        wf1 = Workflow.objects.create(
            title='Flow #1',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            # conditions=...
            actions=[workflows.PropertyAddingAction(
                entity_source=workflows.CreatedEntitySource(model=FakeContact),
                ptype=ptype1,
            )],
        )
        wf2 = Workflow.objects.create(
            title='Flow which do not use ptype1',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeOrganisation),
            # conditions=...,
            actions=[workflows.PropertyAddingAction(
                entity_source=workflows.CreatedEntitySource(model=FakeContact),
                ptype=ptype2,
            )],
        )
        wf3 = Workflow.objects.create(
            title='Flow #3',
            content_type=FakeOrganisation,
            trigger=workflows.EntityEditionTrigger(model=FakeContact),
            # conditions=...,
            actions=[
                workflows.PropertyAddingAction(
                    entity_source=workflows.EditedEntitySource(model=FakeContact),
                    ptype=ptype1,
                ),
                workflows.RelationAddingAction(
                    subject_source=workflows.EditedEntitySource(model=FakeContact),
                    rtype=rtype.id,
                    object_source=workflows.FixedEntitySource(entity=orga),
                ),
            ],
        )

        self.clear_global_info()
        self.assertCountEqual([wf1, wf3], collector.collect(ptype1))
        self.assertCountEqual([wf2],      collector.collect(ptype2))

    def test_action__relation_type(self):
        collector = soft_references.RelationAddingActionRTypeRefCollector()
        self.assertEqual('creme_core-workflow_relation_action-rtype', collector.id)
        self.assertEqual(RelationType, collector.model)

        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        ptype = CremePropertyType.objects.create(text='is cool')

        rtype1 = RelationType.objects.builder(
            id='test-subject_foo', predicate='Subject predicate #1', is_custom=True,
        ).symmetric(id='test-object_foo', predicate='Object predicate #1').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_bar', predicate='Subject predicate #2', is_custom=True,
        ).symmetric(id='test-object_bar', predicate='Object predicate #2').get_or_create()[0]

        wf1 = Workflow.objects.create(
            title='Flow #1',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            # conditions=...,
            actions=[
                workflows.PropertyAddingAction(
                    entity_source=workflows.EditedEntitySource(model=FakeContact),
                    ptype=ptype,
                ),
                workflows.RelationAddingAction(
                    subject_source=workflows.EditedEntitySource(model=FakeContact),
                    rtype=rtype1.id,
                    object_source=workflows.FixedEntitySource(entity=orga),
                ),
            ],
        )
        wf2 = Workflow.objects.create(
            title='Flow on other ptype',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            # conditions=...,
            actions=[
                workflows.RelationAddingAction(
                    subject_source=workflows.EditedEntitySource(model=FakeContact),
                    rtype=rtype2.id,
                    object_source=workflows.FixedEntitySource(entity=orga),
                ),
            ],
        )
        wf3 = Workflow.objects.create(
            title='Flow #3',
            content_type=FakeOrganisation,
            trigger=workflows.EditedEntitySource(model=FakeOrganisation),
            # conditions=...,
            actions=[
                workflows.RelationAddingAction(
                    subject_source=workflows.EditedEntitySource(model=FakeOrganisation),
                    rtype=rtype1.symmetric_type_id,
                    object_source=workflows.FixedEntitySource(entity=orga),
                ),
            ],
        )

        self.clear_global_info()
        self.assertCountEqual([wf1, wf3], collector.collect(rtype1))
        self.assertCountEqual([wf2],      collector.collect(rtype2))

    def test_action__notification_sending(self):
        collector = soft_references.NotificationSendingActionUserRefCollector()
        self.assertEqual('creme_core-workflow_notification_action-user', collector.id)
        self.assertEqual(CremeUser, collector.model)

        user = self.get_root_user()
        user_to_ref = self.create_user()

        channel = NotificationChannel.objects.create(
            name='Workflow', default_outputs=[OUTPUT_WEB],
            description='Notification for Workflow',
        )

        orga = FakeOrganisation.objects.create(user=user, name='Acme', is_deleted=True)
        ptype = CremePropertyType.objects.create(
            text='is cool',
            uuid=user_to_ref.uuid,  # <== collision
        )

        wf1 = Workflow.objects.create(
            title='Blocking Flow #1',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            # conditions=...,
            actions=[
                workflows.NotificationSendingAction(
                    channel=channel,
                    user_source=workflows.FixedUserSource(user=user_to_ref),
                    entity_source=workflows.CreatedEntitySource(model=FakeContact),
                    subject='subject 1',
                    body='body 1',
                ),
            ],
        )
        wf2 = Workflow.objects.create(
            title='Not blocking Flow #1',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            # conditions=...,
            actions=[
                workflows.NotificationSendingAction(
                    channel=channel,
                    user_source=workflows.FixedUserSource(user=user),
                    entity_source=workflows.CreatedEntitySource(model=FakeContact),
                    subject='subject',
                    body='body',
                ),
                workflows.PropertyAddingAction(
                    entity_source=workflows.FixedEntitySource(entity=orga),
                    ptype=ptype,
                ),
            ],
        )
        wf3 = Workflow.objects.create(
            title='Blocking Flow #2',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            # conditions=...,
            actions=[
                workflows.NotificationSendingAction(
                    channel=channel,
                    user_source=workflows.FixedUserSource(user=user_to_ref),
                    entity_source=workflows.CreatedEntitySource(model=FakeContact),
                    subject='subject 2',
                    body='body 2',
                ),
            ],
        )

        self.clear_global_info()
        self.assertCountEqual([wf1, wf3], collector.collect(user_to_ref))
        self.assertCountEqual([wf2],      collector.collect(user))
