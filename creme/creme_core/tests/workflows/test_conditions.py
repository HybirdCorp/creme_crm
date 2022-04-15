from datetime import date, timedelta
from functools import partial

from dateutil.utils import today
from django.utils.formats import date_format
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.core.workflow import (
    WorkflowConditions,
    workflow_registry,
)
from creme.creme_core.models import (
    CustomField,
    EntityFilterCondition,
    FakeContact,
    FakeOrganisation,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    ObjectEntitySource,
    SubjectEntitySource,
)

from ..base import CremeTestCase


class WorkflowConditionsTestCase(CremeTestCase):
    def test_one_condition(self):
        user = self.get_root_user()

        value = 'Acme'
        model = FakeOrganisation
        source = CreatedEntitySource(model=model)
        condition = condition_handler.RegularFieldConditionHandler.build_condition(
            model=model,
            operator=operators.EQUALS, field_name='name', values=[value],
        )
        conditions = WorkflowConditions().add(
            source=source, conditions=[condition],
        )
        self.assertIsInstance(conditions, WorkflowConditions)

        # conditions_for_source() ---
        self.assertTrue(EntityFilterCondition.conditions_equal(
            [condition],
            conditions.conditions_for_source(source),
        ))
        self.assertListEqual(
            [], conditions.conditions_for_source(EditedEntitySource(model=model))
        )

        # Descriptions ---
        descriptions1 = [*conditions.descriptions(user=user)]
        self.assertEqual(1, len(descriptions1), descriptions1)

        exp_description = '{label}<ul><li>{condition}</li></ul>'.format(
            label=_('Conditions on «{source}»:').format(
                source=source.render(user=user, mode=source.RenderMode.HTML),
            ),
            condition=_('«{field}» is {values}').format(
                field=_('Name'), values=_('«{enum_value}»').format(enum_value=value),
            ),
        )
        self.assertHTMLEqual(exp_description, descriptions1[0])

        # Accept ---
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        accept = partial(conditions.accept, user=user, detect_change=False, use_or=False)
        self.assertTrue(accept(context={source.type_id: create_orga(name=value)}))
        self.assertFalse(accept(context={source.type_id: create_orga(name=f'Not {value}')}))

        # (de)serialization ---
        serialized = [{
            'entity': source.to_dict(),
            'conditions': [{
                'name': 'name',
                'type': condition_handler.RegularFieldConditionHandler.type_id,
                'value': {'operator': operators.EQUALS, 'values': [value]},
            }],
        }]
        self.assertListEqual(serialized, conditions.to_dicts())

        deserialized = WorkflowConditions.from_dicts(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, WorkflowConditions)

        descriptions2 = [*deserialized.descriptions(user=user)]
        self.assertEqual(1, len(descriptions2), descriptions2)
        self.assertHTMLEqual(exp_description, descriptions2[0])

    def test_zero_condition(self):
        user = self.get_root_user()

        model = FakeContact
        source = EditedEntitySource(model=model)
        conditions = WorkflowConditions().add(source=source, conditions=[])
        self.assertIsInstance(conditions, WorkflowConditions)
        self.assertListEqual([], conditions.conditions_for_source(source))

        # Descriptions ---
        exp_description = _('No condition on «{source}»').format(
            source=_('Modified entity ({type})').format(type='Test Contact'),
        )
        self.assertListEqual([exp_description], [*conditions.descriptions(user=user)])

        # Accept ---
        accept = partial(
            conditions.accept,
            user=user,
            context={source.type_id: FakeOrganisation.objects.create(user=user, name='Acme')},
            detect_change=False,
        )
        self.assertTrue(accept(use_or=False))
        self.assertTrue(accept(use_or=True))

        # (de)serialization ---
        serialized = [{'entity': source.to_dict(), 'conditions': []}]
        self.assertListEqual(serialized, conditions.to_dicts())

        deserialized = WorkflowConditions.from_dicts(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, WorkflowConditions)
        self.assertListEqual([exp_description], [*deserialized.descriptions(user=user)])

    def test_two_conditions(self):
        user = self.get_root_user()

        model = FakeOrganisation
        source = CreatedEntitySource(model=model)
        value1 = 'AcmeCorp'
        conditions = WorkflowConditions().add(
            source=source,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=model,
                    operator=operators.ISTARTSWITH, field_name='name', values=[value1],
                ),
                condition_handler.DateRegularFieldConditionHandler.build_condition(
                    model=model,
                    field_name='creation_date', date_range='current_year',
                ),
            ],
        )

        # Descriptions ---
        descriptions1 = [*conditions.descriptions(user=user)]
        self.assertEqual(1, len(descriptions1), descriptions1)

        exp_description = (
            '{label}'
            '<ul>'
            ' <li>{condition1}</li>'
            ' <li>{condition2}</li>'
            '</ul>'
        ).format(
            label=_('Conditions on «{source}»:').format(
                source=source.render(user=user, mode=source.RenderMode.HTML),
            ),
            condition1=_(
                '«{field}» starts with {values} (case insensitive)'
            ).format(
                field=_('Name'),
                values=_('«{enum_value}»').format(enum_value=value1),
            ),
            condition2=_('«{field}» is «{value}»').format(
                field=_('Date of creation'), value=_('Current year'),
            ),
        )
        self.assertHTMLEqual(exp_description, descriptions1[0])

        # Accept ---
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        ctxt_key = source.type_id

        # 2 conditions are filled
        ctxt1 = {ctxt_key: create_orga(name=f'{value1} 2000', creation_date=today())}
        self.assertTrue(conditions.accept(
            user=user, context=ctxt1, detect_change=False, use_or=False,
        ))
        self.assertTrue(conditions.accept(
            user=user, context=ctxt1, detect_change=False, use_or=True,
        ))

        # Only second condition is filled
        ctxt2 = {ctxt_key: create_orga(name=f'Not {value1}', creation_date=today())}
        self.assertFalse(conditions.accept(
            user=user, context=ctxt2, detect_change=False, use_or=False,
        ))
        self.assertTrue(conditions.accept(
            user=user, context=ctxt2, detect_change=False, use_or=True,
        ))

        # Only first condition is filled
        ctxt3 = {ctxt_key: create_orga(
            name=value1, creation_date=today() - timedelta(weeks=100),
        )}
        self.assertFalse(conditions.accept(
            user=user, context=ctxt3, detect_change=False, use_or=False,
        ))
        self.assertTrue(conditions.accept(
            user=user, context=ctxt3, detect_change=False, use_or=True,
        ))

        # 0 condition filled
        ctxt4 = {ctxt_key: create_orga(
            name=f'Not {value1}', creation_date=today() - timedelta(weeks=100),
        )}
        self.assertFalse(conditions.accept(
            user=user, context=ctxt4, detect_change=False, use_or=False,
        ))
        self.assertFalse(conditions.accept(
            user=user, context=ctxt4, detect_change=False, use_or=True,
        ))

        # (de)serialization ---
        serialized = [{
            'entity': source.to_dict(),
            'conditions': [
                {
                    'name': 'name',
                    'type': condition_handler.RegularFieldConditionHandler.type_id,
                    'value': {'operator': operators.ISTARTSWITH, 'values': [value1]},
                }, {
                    'name': 'creation_date',
                    'type': condition_handler.DateRegularFieldConditionHandler.type_id,
                    'value': {'name': 'current_year'}
                },
            ],
        }]
        self.assertListEqual(serialized, conditions.to_dicts())

        deserialized = WorkflowConditions.from_dicts(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, WorkflowConditions)

        descriptions2 = [*deserialized.descriptions(user=user)]
        self.assertEqual(1, len(descriptions2), descriptions2)
        self.assertHTMLEqual(exp_description, descriptions2[0])

    def test_two_sources(self):
        user = self.get_root_user()

        model1 = FakeOrganisation
        model2 = FakeContact

        create_cfield = CustomField.objects.create
        cfield1 = create_cfield(
            name='Building(s)', field_type=CustomField.INT, content_type=model1,
        )
        cfield2 = create_cfield(
            name='Party', field_type=CustomField.DATE, content_type=model2,
        )

        source1 = SubjectEntitySource(model=model1)
        source2 = ObjectEntitySource(model=model2)

        condition1 = condition_handler.CustomFieldConditionHandler.build_condition(
            custom_field=cfield1, operator=operators.GTE, values=[3],
        )
        start = date(year=2025, month=5, day=1)
        condition2 = condition_handler.DateCustomFieldConditionHandler.build_condition(
            custom_field=cfield2, start=start,
        )

        conditions = WorkflowConditions().add(
            source=source1, conditions=[condition1],
        ).add(source=source2, conditions=[condition2])

        self.assertTrue(EntityFilterCondition.conditions_equal(
            [condition1], conditions.conditions_for_source(source1),
        ))
        self.assertTrue(EntityFilterCondition.conditions_equal(
            [condition2], conditions.conditions_for_source(source2),
        ))

        # Descriptions ---
        descriptions1 = [*conditions.descriptions(user=user)]
        self.assertEqual(2, len(descriptions1), descriptions1)

        desc_fmt = (
            '{label}'
            '<ul>'
            ' <li>{condition}</li>'
            '</ul>'
        ).format
        exp_description1 = desc_fmt(
            label=_('Conditions on «{source}»:').format(
                source=source1.render(user=user, mode=source1.RenderMode.HTML),
            ),
            condition=_('«{field}» is greater than or equal to {values}').format(
                field=cfield1.name,
                values=_('«{enum_value}»').format(enum_value=3),
            ),
        )
        self.assertHTMLEqual(exp_description1, descriptions1[0])

        exp_description2 = desc_fmt(
            label=_('Conditions on «{source}»:').format(
                source=source2.render(user=user, mode=source2.RenderMode.HTML),
            ),
            condition=_('«{field}» starts «{date}»').format(
                field=cfield2.name, date=date_format(start, 'DATE_FORMAT'),
            ),
        )
        self.assertHTMLEqual(exp_description2, descriptions1[1])

        # Accept ---
        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        contact = FakeContact.objects.create(user=user, first_name='John', last_name='Doe')

        def build_ctxt():
            return {
                source1.type_id: self.refresh(orga),
                source2.type_id: self.refresh(contact),
            }

        # 2 conditions are false
        cfield1.value_class(custom_field=cfield1, entity=orga).set_value_n_save(2)
        accept = partial(conditions.accept, user=user, detect_change=False, use_or=False)
        self.assertFalse(accept(context=build_ctxt()))

        # 1 condition only is true
        cfield1.value_class(custom_field=cfield1, entity=orga).set_value_n_save(4)
        self.assertFalse(accept(context=build_ctxt()))

        # 2 conditions are true
        cfield2.value_class(custom_field=cfield2, entity=contact).set_value_n_save(
            now() + timedelta(days=5)
        )
        self.assertTrue(accept(context=build_ctxt()))

        # (de)serialization ---
        serialized = [
            {
                'entity': source1.to_dict(),
                'conditions': [{
                    'name': str(cfield1.uuid),
                    'type': condition_handler.CustomFieldConditionHandler.type_id,
                    'value': {
                        'operator': operators.GTE,
                        'rname': 'customfieldinteger',
                        'values': ['3'],
                    },
                }],
            }, {
                'entity': source2.to_dict(),
                'conditions': [{
                    'name': str(cfield2.uuid),
                    'type': condition_handler.DateCustomFieldConditionHandler.type_id,
                    'value': {
                        'rname': 'customfielddate',
                        'start': {'day': 1, 'month': 5, 'year': 2025},
                    },
                }],
            },
        ]
        self.maxDiff = None
        self.assertListEqual(serialized, conditions.to_dicts())

        deserialized = WorkflowConditions.from_dicts(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, WorkflowConditions)

        descriptions2 = [*deserialized.descriptions(user=user)]
        self.assertEqual(2, len(descriptions2), descriptions2)
        self.assertHTMLEqual(exp_description1, descriptions2[0])
        self.assertHTMLEqual(exp_description2, descriptions2[1])

    def test_accept__detect_change__error(self):
        user = self.get_root_user()

        value = 'Acme'
        model = FakeOrganisation
        source = CreatedEntitySource(model=model)
        conditions = WorkflowConditions().add(
            source=source,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=model,
                    operator=operators.EQUALS, field_name='name', values=[value],
                ),
            ],
        )
        ctxt = {
            source.type_id: FakeOrganisation.objects.create(user=user, name=value),
        }
        accept = partial(conditions.accept, user=user, context=ctxt, use_or=False)
        self.assertTrue(accept(detect_change=False))

        with self.assertRaises(ValueError):
            self.assertTrue(accept(detect_change=True))

    def test_accept__detect_change(self):
        user = self.get_root_user()

        value = 'Acme'
        model = FakeOrganisation
        source = EditedEntitySource(model=model)
        conditions = WorkflowConditions().add(
            source=source,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=model,
                    operator=operators.EQUALS, field_name='name', values=[value],
                ),
            ],
        )

        orga = self.refresh(FakeOrganisation.objects.create(user=user, name=f'Not {value}'))
        ctxt = {source.type_id: orga}
        accept = partial(conditions.accept, user=user, context=ctxt, use_or=False)

        # Condition not filled ---
        self.assertFalse(accept(detect_change=False))
        self.assertFalse(accept(detect_change=True))

        # Condition filled after a change ---
        orga.name = value
        self.assertTrue(accept(detect_change=False))
        self.assertTrue(accept(detect_change=True))

        # Condition filled + no change ---
        orga.save()
        ctxt[source.type_id] = self.refresh(orga)
        self.assertTrue(accept(detect_change=False))
        self.assertFalse(accept(detect_change=True))
