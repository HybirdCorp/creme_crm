from functools import partial
from json import dumps as json_dump

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_config.bricks import WorkflowsBrick
from creme.creme_config.forms.workflow import TriggerField
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.core.workflow import WorkflowConditions
from creme.creme_core.forms.entity_filter import fields as ef_fields
from creme.creme_core.forms.workflows import (
    PropertyAddingActionForm,
    RelationAddingActionForm,
)
from creme.creme_core.models import (
    CremePropertyType,
    CustomEntityType,
    EntityFilterCondition,
    FakeContact,
    FakeOrganisation,
    RelationType,
    Workflow,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    EntityCreationTrigger,
    EntityEditionTrigger,
    FixedEntitySource,
    ObjectEntitySource,
    PropertyAddingAction,
    RelationAddingAction,
    RelationAddingTrigger,
    SubjectEntitySource,
)


class TriggerFieldTestCase(CremeTestCase):
    def test_ok(self):
        model = FakeContact
        field = TriggerField(model=model)
        self.assertEqual(model, field.model)

        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is concerned by',
        ).symmetric(id='creme_core-object_client', predicate='concerns').get_or_create()[0]
        sub_values = {
            EntityCreationTrigger.type_id: '',
            EntityEditionTrigger.type_id: '',
            RelationAddingTrigger.type_id: json_dump({
                'rtype':  rtype.id,
                'ctype':  ContentType.objects.get_for_model(FakeOrganisation).id,
            }),
        }
        self.assertTupleEqual(
            (EntityCreationTrigger.type_id, EntityCreationTrigger(model=model)),
            field.clean((EntityCreationTrigger.type_id, sub_values)),
        )
        self.assertTupleEqual(
            (EntityEditionTrigger.type_id, EntityEditionTrigger(model=model)),
            field.clean((EntityEditionTrigger.type_id, sub_values)),
        )
        self.assertTupleEqual(
            (
                RelationAddingTrigger.type_id,
                RelationAddingTrigger(
                    subject_model=model,
                    rtype=rtype,
                    object_model=FakeOrganisation,
                )
            ),
            field.clean((RelationAddingTrigger.type_id, sub_values)),
        )

    def test_empty_required(self):
        field = TriggerField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='[]')

    def test_empty_not_required(self):
        field = TriggerField(required=False)
        self.assertIsNone(field.clean(None))
        self.assertIsNone(field.clean((None, None)))
        self.assertIsNone(field.clean(('', '')))

    def test_clean_invalid_data(self):
        field = TriggerField(model=FakeContact)
        self.assertFormfieldError(
            field=field,
            value=(
                'unknown_id',
                {
                    EntityCreationTrigger.type_id: '',
                    EntityEditionTrigger.type_id: '',
                }
            ),
            messages=_('This field is required.'),
            codes='required',
        )
        self.assertFormfieldError(
            field=field,
            value=(
                RelationAddingTrigger.type_id,
                {
                    EntityCreationTrigger.type_id: '',
                    EntityEditionTrigger.type_id: '',
                    RelationAddingTrigger.type_id: json_dump({
                        'rtype': 'unknown',
                        'ctype': ContentType.objects.get_for_model(FakeOrganisation).id,
                    }),
                }
            ),
            messages=_(
                'This type of relationship does not exist or causes a constraint error'
            ),
            codes='rtypenotallowed',
        )


class WorkflowTestCase(BrickTestCaseMixin, CremeTestCase):
    def _build_create_wf_url(self, model):
        ct = ContentType.objects.get_for_model(model)
        return reverse('creme_config__create_workflow', args=(ct.id,))

    def _build_edit_conditions(self, workflow):
        return reverse('creme_config__edit_workflow_conditions', args=(workflow.id,))

    def _build_edit_action_url(self, workflow, index):
        return reverse('creme_config__edit_workflow_action', args=(workflow.id, index))

    def _build_del_action_url(self, workflow):
        return reverse('creme_config__delete_workflow_action', args=(workflow.id,))

    def test_portal(self):
        self.login_as_root()

        response = self.assertGET200(reverse('creme_config__workflows'))
        self.assertTemplateUsed(response, 'creme_config/portals/workflow.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        # brick_node = self.get_brick_node(
        self.get_brick_node(
            self.get_html_tree(response.content),
            WorkflowsBrick.id,
        )
        # TODO
        # self.assertEqual(
        #     _('{count} Configured types of resource').format(count=2),
        #     self.get_brick_title(brick_node),
        # )
        # self.assertSetEqual(
        #     {cfield1.name, cfield2.name, cfield3.name},
        #     {
        #         n.text
        #         for n in brick_node.findall('.//td[@class="cfields-config-name"]')
        #     },
        # )

    def test_create__no_conditions(self):
        user = self.login_as_standard(admin_4_apps=('creme_core',))

        old_wf_ids = [*Workflow.objects.values_list('id', flat=True)]
        model = FakeContact
        title = 'My Contact workflow'
        url = self._build_create_wf_url(model)
        ptype = CremePropertyType.objects.create(text='Is cool')

        # Step 1: Trigger ---
        trigger_step_get_resp = self.assertGET200(url)
        context1 = trigger_step_get_resp.context
        self.assertEqual(
            _('Create a Workflow for «{model}»').format(model='Test Contact'),
            context1.get('title'),
        )
        self.assertEqual(_('Next step'), context1.get('submit_label'))

        with self.assertNoException():
            trigger_f = context1['form'].fields['trigger']

        self.assertIsInstance(trigger_f, TriggerField)
        self.assertEqual(model, trigger_f.model)

        # ---
        step_key = 'workflow_creation_wizard-current_step'
        trigger_step_post_resp = self.client.post(
            url,
            data={
                step_key: '0',
                '0-title': title,

                '0-trigger': EntityCreationTrigger.type_id,
                f'0-trigger_{EntityCreationTrigger.type_id}': '',
            },
        )
        self.assertNoFormError(trigger_step_post_resp)

        # Step 2: conditions ---
        self.assertEqual(
            _('Next step'), trigger_step_post_resp.context.get('submit_label'),
        )

        conditions_step_post_resp = self.client.post(
            url,
            data={
                step_key: '1',
                # '1-...conditions...': ...,
            },
        )
        self.assertNoFormError(conditions_step_post_resp)

        # Step 3: first action selection ---
        context3 = conditions_step_post_resp.context
        self.assertEqual(_('Next step'), context3.get('submit_label'))

        with self.assertNoException():
            actions_choices = context3['form'].fields['action_type'].choices

        self.assertInChoices(
            value=PropertyAddingAction.type_id,
            label=PropertyAddingAction.verbose_name,
            choices=actions_choices,
        )
        self.assertInChoices(
            value=RelationAddingAction.type_id,
            label=RelationAddingAction.verbose_name,
            choices=actions_choices,
        )

        # --
        actionselect_step_post_resp = self.client.post(
            url,
            data={
                step_key: '2',
                '2-action_type': PropertyAddingAction.type_id,
            },
        )
        self.assertNoFormError(actionselect_step_post_resp)

        # Step 4: first action configuration ---
        context3 = actionselect_step_post_resp.context
        self.assertEqual(_('Save the Workflow'), context3.get('submit_label'))

        actionconfig_step_post_resp = self.client.post(
            url,
            data={
                step_key: '3',
                '3-ptype': ptype.id,

                '3-source': 'created_entity',
                '3-source_created_entity': '',
            },
        )
        self.assertNoFormError(actionconfig_step_post_resp)

        new_workflows = [*Workflow.objects.exclude(id__in=old_wf_ids)]
        self.assertEqual(1, len(new_workflows))

        workflow = new_workflows[0]
        self.assertEqual(title, workflow.title)
        self.assertEqual(model, workflow.content_type.model_class())
        self.assertFalse(workflow.enabled)
        self.assertTrue(workflow.is_custom)
        self.assertEqual(EntityCreationTrigger(model=model), workflow.trigger)

        source = CreatedEntitySource(model=model)
        self.assertListEqual(
            [
                _('No condition on «{source}»').format(
                    source=source.render(user=user, mode=source.RenderMode.HTML),
                ),
            ],
            [*workflow.conditions.descriptions(user=user)],
        )
        self.assertTupleEqual(
            (PropertyAddingAction(entity_source=source, ptype=ptype),),
            workflow.actions,
        )

    # TODO: move (Mixin?)
    @staticmethod
    def _build_rfields_data(name, operator, value):
        return json_dump([{
            'field':    {'name': name},
            'operator': {'id': str(operator)},
            'value':    value,
        }])

    def test_create__conditions__one_source(self):
        user = self.login_as_root_and_get()

        old_wf_ids = [*Workflow.objects.values_list('id', flat=True)]
        model = FakeOrganisation
        title = 'Organisation workflow'
        url = self._build_create_wf_url(model)
        ptype = CremePropertyType.objects.create(text='Is cool')

        # Step 1: Trigger ---
        trigger_step_get_resp = self.assertGET200(url)
        context1 = trigger_step_get_resp.context
        self.assertEqual(
            _('Create a Workflow for «{model}»').format(model='Test Organisation'),
            context1.get('title'),
        )

        with self.assertNoException():
            trigger_f = context1['form'].fields['trigger']
        self.assertEqual(model, trigger_f.model)

        # ---
        step_key = 'workflow_creation_wizard-current_step'
        trigger_step_post_resp = self.client.post(
            url,
            data={
                step_key: '0',
                '0-title': title,

                '0-trigger': EntityEditionTrigger.type_id,
                f'0-trigger_{EntityEditionTrigger.type_id}': '',
            },
        )
        self.assertNoFormError(trigger_step_post_resp)

        # Step 2: conditions ---
        f_prefix = EditedEntitySource.type_id
        with self.assertNoException():
            fields2 = trigger_step_post_resp.context['form'].fields
            regular_cond_f = fields2[f'{f_prefix}-regularfieldcondition']
            custom_cond_f = fields2[f'{f_prefix}-customfieldcondition']
            fields2[f'{f_prefix}-dateregularfieldcondition']  # NOQA
            fields2[f'{f_prefix}-datecustomfieldcondition']  # NOQA

        self.assertIsInstance(regular_cond_f, ef_fields.RegularFieldsConditionsField)
        self.assertEqual(model, regular_cond_f.model)
        self.assertIsInstance(custom_cond_f, ef_fields.CustomFieldsConditionsField)
        self.assertEqual(model, custom_cond_f.model)

        field_operator = operators.CONTAINS
        field_name = 'name'
        field_value = 'NERV'
        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '1',
                f'1-{f_prefix}-regularfieldcondition': self._build_rfields_data(
                    operator=field_operator,
                    name=field_name,
                    value=field_value,
                ),
            },
        ))

        # Step 3: first action selection ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '2',
                '2-action_type': PropertyAddingAction.type_id,
            },
        ))

        # Step 4: first action configuration ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '3',
                '3-ptype': ptype.id,

                '3-source': 'edited_entity',
                '3-source_edited_entity': '',
            },
        ))

        workflow = self.get_alone_element([*Workflow.objects.exclude(id__in=old_wf_ids)])
        self.assertEqual(title, workflow.title)
        self.assertEqual(model, workflow.content_type.model_class())
        self.assertEqual(EntityEditionTrigger(model=model), workflow.trigger)

        source = EditedEntitySource(model=model)
        self.assertTupleEqual(
            (PropertyAddingAction(entity_source=source, ptype=ptype),),
            workflow.actions,
        )

        cond_descriptions = [*workflow.conditions.descriptions(user=user)]
        self.assertEqual(1, len(cond_descriptions), cond_descriptions)
        self.assertHTMLEqual(
            '{label}<ul><li>{condition}</li></ul>'.format(
                label=_('Conditions on «{source}»:').format(
                    source=source.render(user=user, mode=source.RenderMode.HTML),
                ),
                condition=_('«{field}» contains {values}').format(
                    field=_('Name'),
                    values=_('«{enum_value}»').format(enum_value=field_value),
                ),
            ),
            cond_descriptions[0],
        )

    def test_create__conditions__two_sources(self):
        user = self.login_as_root_and_get()

        old_wf_ids = [*Workflow.objects.values_list('id', flat=True)]
        model = FakeOrganisation
        title = 'Organisation workflow'
        url = self._build_create_wf_url(model)

        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='has client', models=[FakeOrganisation],
        ).symmetric(
            id='creme_core-object_client', predicate='is client of', models=[FakeContact],
        ).get_or_create()[0]

        ptype = CremePropertyType.objects.create(text='Is cool')

        # Step 1: Trigger ---
        step_key = 'workflow_creation_wizard-current_step'
        trigger_step_post_resp = self.client.post(
            url,
            data={
                step_key: '0',
                '0-title': title,

                '0-trigger': RelationAddingTrigger.type_id,
                f'0-trigger_{RelationAddingTrigger.type_id}': json_dump({
                    'rtype': rtype.id,
                    'ctype': ContentType.objects.get_for_model(FakeContact).id,
                }),
            },
        )
        self.assertNoFormError(trigger_step_post_resp)

        # Step 2: conditions ---
        source1 = SubjectEntitySource(model=model)
        f_prefix1 = source1.type_id

        source2 = ObjectEntitySource(model=FakeContact)
        f_prefix2 = source2.type_id

        with self.assertNoException():
            fields2 = trigger_step_post_resp.context['form'].fields
            regular_cond_f1 = fields2[f'{f_prefix1}-regularfieldcondition']
            regular_cond_f2 = fields2[f'{f_prefix2}-regularfieldcondition']

        self.assertIsInstance(regular_cond_f1, ef_fields.RegularFieldsConditionsField)
        self.assertEqual(model, regular_cond_f1.model)
        self.assertIsInstance(regular_cond_f2, ef_fields.RegularFieldsConditionsField)
        self.assertEqual(FakeContact, regular_cond_f2.model)

        field_operator1 = operators.CONTAINS
        field_name1 = 'name'
        field_value1 = 'NERV'

        field_operator2 = operators.ISEMPTY
        field_name2 = 'email'
        field_value2 = False

        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '1',
                f'1-{f_prefix1}-regularfieldcondition': self._build_rfields_data(
                    operator=field_operator1, name=field_name1, value=field_value1,
                ),
                f'1-{f_prefix2}-regularfieldcondition': self._build_rfields_data(
                    operator=field_operator2, name=field_name2, value=field_value2,
                ),
            },
        ))

        # Step 3: first action selection ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '2',
                '2-action_type': PropertyAddingAction.type_id,
            },
        ))

        # Step 4: first action configuration ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '3',
                '3-ptype': ptype.id,

                '3-source': source1.type_id,
                f'3-source_{source1.type_id}': '',
            },
        ))

        workflow = self.get_alone_element(Workflow.objects.exclude(id__in=old_wf_ids))
        self.assertEqual(
            RelationAddingTrigger(subject_model=model, rtype=rtype, object_model=FakeContact),
            workflow.trigger,
        )
        self.assertTupleEqual(
            (PropertyAddingAction(entity_source=source1, ptype=ptype),),
            workflow.actions,
        )

        cond_descriptions = [*workflow.conditions.descriptions(user=user)]
        self.assertEqual(2, len(cond_descriptions), cond_descriptions)
        self.assertHTMLEqual(
            '{label}<ul><li>{condition}</li></ul>'.format(
                label=_('Conditions on «{source}»:').format(
                    source=source1.render(user=user, mode=source1.RenderMode.HTML),
                ),
                condition=_('«{field}» contains {values}').format(
                    field=_('Name'),
                    values=_('«{enum_value}»').format(enum_value=field_value1),
                ),
            ),
            cond_descriptions[0],
        )
        self.assertHTMLEqual(
            '{label}<ul><li>{condition}</li></ul>'.format(
                label=_('Conditions on «{source}»:').format(
                    source=source2.render(user=user, mode=source2.RenderMode.HTML),
                ),
                condition=_('«{field}» is not empty').format(field=_('Email address')),
            ),
            cond_descriptions[1],
        )

    def test_create__disabled_custom_entity_type(self):
        self.login_as_root()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        self.assertFalse(ce_type.enabled)
        self.assertGET409(self._build_create_wf_url(ce_type.entity_model))

    def test_rename(self):
        self.login_as_standard(admin_4_apps=('creme_core',))

        wf = Workflow.objects.create(
            title='My WF #1',
            content_type=FakeContact,
            enabled=False,
            trigger=EntityCreationTrigger(model=FakeContact),
        )

        url = reverse('creme_config__rename_workflow', args=(wf.id,))
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Rename «{object}»').format(object=wf.title),
            context1.get('title'),
        )

        with self.assertNoException():
            fields1 = context1['form'].fields
            title_f = fields1['title']

        self.assertIsInstance(title_f, forms.CharField)
        self.assertEqual(1, len(fields1))

        # ---
        title = 'Important WF'
        self.assertNoFormError(self.client.post(url, data={'title': title}))
        self.assertEqual(title, self.refresh(wf).title)

    def test_enable(self):
        self.login_as_standard(admin_4_apps=('creme_core',))

        wf1 = Workflow.objects.create(
            title='My WF #1',
            content_type=FakeContact,
            enabled=False,
            trigger=EntityCreationTrigger(model=FakeContact),
        )
        wf2 = Workflow.objects.create(
            title='My WF #2',
            content_type=FakeOrganisation,
            enabled=False,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
        )

        url = reverse('creme_config__enable_workflow', args=(wf1.id,))
        self.assertGET405(url)

        self.assertPOST200(url)
        self.assertTrue(self.refresh(wf1).enabled)
        self.assertFalse(self.refresh(wf2).enabled)

    def test_disable(self):
        self.login_as_standard(admin_4_apps=('creme_core',))

        wf1 = Workflow.objects.create(
            title='My WF #1',
            content_type=FakeContact,
            trigger=EntityCreationTrigger(model=FakeContact),
        )
        wf2 = Workflow.objects.create(
            title='My WF #2',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
        )

        url = reverse('creme_config__disable_workflow', args=(wf1.id,))
        self.assertGET405(url)

        self.assertPOST200(url)
        self.assertFalse(self.refresh(wf1).enabled)
        self.assertTrue(self.refresh(wf2).enabled)

    def test_delete(self):
        self.login_as_standard(admin_4_apps=('creme_core',))

        wf = Workflow.objects.create(
            title='To be deleted',
            content_type=FakeContact,
            trigger=EntityCreationTrigger(model=FakeContact),
        )
        self.assertTrue(wf.is_custom)

        url = reverse('creme_config__delete_workflow')
        data = {'id': wf.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertDoesNotExist(wf)

    def test_delete__not_custom(self):
        self.login_as_root()

        wf = Workflow.objects.create(
            title='To be deleted',
            content_type=FakeContact,
            trigger=EntityCreationTrigger(model=FakeContact),
            is_custom=False,
        )
        self.assertPOST409(
            reverse('creme_config__delete_workflow'), data={'id': wf.id},
        )
        self.assertStillExists(wf)

    def test_delete__invalid(self):
        self.login_as_root()
        self.assertPOST404(
            reverse('creme_config__delete_workflow'),
            data={'id': self.UNUSED_PK},
        )

    def test_edit_conditions__one_source(self):
        user = self.login_as_standard(admin_4_apps=('creme_core',))

        model = FakeContact
        source = CreatedEntitySource(model=model)
        trigger = EntityCreationTrigger(model=model)
        condition = condition_handler.RegularFieldConditionHandler.build_condition(
            model=model,
            operator=operators.ENDSWITH, field_name='email', values=['@acme.org'],
        )
        action = PropertyAddingAction(
            entity_source=source,
            ptype=CremePropertyType.objects.create(text='Is cool'),
        )
        wf = Workflow.objects.create(
            title='WF for Contact',
            content_type=model,
            trigger=trigger,
            conditions=WorkflowConditions().add(source=source, conditions=[condition]),
            actions=[action],
        )

        url = self._build_edit_conditions(wf)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Edit the conditions of «{object}»').format(object=wf.title),
            context1.get('title'),
        )

        f_prefix = source.type_id
        with self.assertNoException():
            fields1 = context1['form'].fields
            regular_cond_f_name = f'{f_prefix}-regularfieldcondition'
            regular_cond_f = fields1[regular_cond_f_name]
            custom_cond_f = fields1[f'{f_prefix}-customfieldcondition']
            fields1[f'{f_prefix}-dateregularfieldcondition']  # NOQA
            fields1[f'{f_prefix}-datecustomfieldcondition']  # NOQA

        self.assertIsInstance(regular_cond_f, ef_fields.RegularFieldsConditionsField)
        self.assertEqual(model, regular_cond_f.model)
        self.assertIsInstance(custom_cond_f, ef_fields.CustomFieldsConditionsField)
        self.assertEqual(model, custom_cond_f.model)

        self.assertIsList(regular_cond_f.initial, length=1)
        self.assertTrue(EntityFilterCondition.conditions_equal(
            [condition], regular_cond_f.initial,
        ))

        # POST ---
        field_operator = operators.EQUALS
        field_name = 'last_name'
        field_value = 'Ayanami'
        self.assertNoFormError(self.client.post(
            url,
            data={
                regular_cond_f_name: self._build_rfields_data(
                    operator=field_operator,
                    name=field_name,
                    value=field_value,
                ),
            },
        ))

        wf = self.refresh(wf)
        self.assertEqual(trigger, wf.trigger)
        self.assertTupleEqual((action,), wf.actions)

        cond_descriptions = [*wf.conditions.descriptions(user=user)]
        self.assertEqual(1, len(cond_descriptions), cond_descriptions)
        self.assertHTMLEqual(
            '{label}<ul><li>{condition}</li></ul>'.format(
                label=_('Conditions on «{source}»:').format(
                    source=source.render(user=user, mode=source.RenderMode.HTML),
                ),
                condition=_('«{field}» is {values}').format(
                    field=_('Last name'),
                    values=_('«{enum_value}»').format(enum_value=field_value),
                ),
            ),
            cond_descriptions[0],
        )

    def test_edit_conditions__two_sources(self):
        user = self.login_as_root_and_get()

        model1 = FakeContact
        model2 = FakeOrganisation

        ptype = CremePropertyType.objects.create(text='Is cool')
        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is client of', models=[model1],
        ).symmetric(
            id='creme_core-object_client', predicate='has client', models=[model2],
        ).get_or_create()[0]

        source1 = SubjectEntitySource(model=model1)
        source2 = ObjectEntitySource(model=model2)

        wf = Workflow.objects.create(
            title='WF for related Contact',
            content_type=model1,
            trigger=RelationAddingTrigger(
                subject_model=model1, rtype=rtype, object_model=model2,
            ),
            # conditions=...
            actions=[PropertyAddingAction(entity_source=source1, ptype=ptype)],
        )

        url = self._build_edit_conditions(wf)
        response1 = self.assertGET200(url)

        f_prefix1 = source1.type_id
        f_prefix2 = source2.type_id
        with self.assertNoException():
            fields1 = response1.context['form'].fields

            regular_cond_f_name1 = f'{f_prefix1}-regularfieldcondition'
            regular_cond_f1 = fields1[regular_cond_f_name1]

            regular_cond_f_name2 = f'{f_prefix2}-regularfieldcondition'
            regular_cond_f2 = fields1[regular_cond_f_name2]

        self.assertIsInstance(regular_cond_f1, ef_fields.RegularFieldsConditionsField)
        self.assertEqual(model1, regular_cond_f1.model)

        self.assertIsInstance(regular_cond_f2, ef_fields.RegularFieldsConditionsField)
        self.assertEqual(model2, regular_cond_f2.model)

        # POST ---
        field_operator = operators.EQUALS
        field_name1 = 'last_name'
        field_value1 = 'Ayanami'
        field_name2 = 'name'
        field_value2 = 'NERV'
        self.assertNoFormError(self.client.post(
            url,
            data={
                regular_cond_f_name1: self._build_rfields_data(
                    operator=field_operator,
                    name=field_name1,
                    value=field_value1,
                ),
                regular_cond_f_name2: self._build_rfields_data(
                    operator=field_operator,
                    name=field_name2,
                    value=field_value2,
                ),
            },
        ))

        cond_descriptions = [*self.refresh(wf).conditions.descriptions(user=user)]
        self.assertEqual(2, len(cond_descriptions), cond_descriptions)
        self.assertHTMLEqual(
            '{label}<ul><li>{condition}</li></ul>'.format(
                label=_('Conditions on «{source}»:').format(
                    source=source1.render(user=user, mode=source1.RenderMode.HTML),
                ),
                condition=_('«{field}» is {values}').format(
                    field=_('Last name'),
                    values=_('«{enum_value}»').format(enum_value=field_value1),
                ),
            ),
            cond_descriptions[0],
        )
        self.assertHTMLEqual(
            '{label}<ul><li>{condition}</li></ul>'.format(
                label=_('Conditions on «{source}»:').format(
                    source=source2.render(user=user, mode=source2.RenderMode.HTML),
                ),
                condition=_('«{field}» is {values}').format(
                    field=_('Name'),
                    values=_('«{enum_value}»').format(enum_value=field_value2),
                ),
            ),
            cond_descriptions[1],
        )

    def test_edit_conditions__not_custom(self):
        self.login_as_root()

        model = FakeContact
        ptype = CremePropertyType.objects.create(text='Is cool')

        wf = Workflow.objects.create(
            title='WF for Contact',
            content_type=model,
            is_custom=False,
            trigger=EntityCreationTrigger(model=model),
            # conditions=...
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model), ptype=ptype,
                ),
            ],
        )
        self.assertGET409(self._build_edit_conditions(wf))

    def test_add_action(self):
        self.login_as_standard(admin_4_apps=('creme_core',))

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is cool')
        ptype2 = create_ptype(text='Is so cool')

        model = FakeContact
        wf = Workflow.objects.create(
            title='WF for Contact',
            content_type=model,
            trigger=EntityCreationTrigger(model=model),
            actions=[PropertyAddingAction(
                entity_source=CreatedEntitySource(model=model), ptype=ptype1,
            )],
        )

        url = reverse('creme_config__add_workflow_action', args=(wf.id,))

        # Step 1: Type selection ---
        type_step_get_resp = self.assertGET200(url)
        context1 = type_step_get_resp.context
        self.assertEqual(
            _('Add an action to «{object}»').format(object=wf.title),
            context1.get('title'),
        )
        self.assertEqual(_('Next step'), context1.get('submit_label'))

        with self.assertNoException():
            actions_choices = context1['form'].fields['action_type'].choices

        self.assertInChoices(
            value=PropertyAddingAction.type_id,
            label=PropertyAddingAction.verbose_name,
            choices=actions_choices,
        )

        # --
        step_key = 'workflow_action_adding_wizard-current_step'
        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '0',
                '0-action_type': PropertyAddingAction.type_id,
            },
        ))

        # Step 2: action configuration ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                step_key: '1',
                '1-ptype': ptype2.id,

                '1-source': 'created_entity',
                '1-source_created_entity': '',
            },
        ))

        source = CreatedEntitySource(model=model)
        self.assertTupleEqual(
            (
                PropertyAddingAction(entity_source=source, ptype=ptype1),
                PropertyAddingAction(entity_source=source, ptype=ptype2),
            ),
            self.refresh(wf).actions,
        )

    def test_add_action__not_custom(self):
        self.login_as_standard(admin_4_apps=('creme_core',))

        model = FakeContact
        wf = Workflow.objects.create(
            title='WF for Contact',
            content_type=model,
            trigger=EntityCreationTrigger(model=model),
            is_custom=False
        )
        self.assertGET409(reverse('creme_config__add_workflow_action', args=(wf.id,)))

    def test_edit_action__first(self):
        user = self.login_as_standard(admin_4_apps=('creme_core',))

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is cool')
        ptype2 = create_ptype(text='Is so cool')

        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is concerned by',
        ).symmetric(id='creme_core-object_client', predicate='concerns').get_or_create()[0]
        fixed = FakeOrganisation.objects.create(user=user, name='Acme')

        model = FakeContact
        wf = Workflow.objects.create(
            title='WF for Contact',
            content_type=model,
            trigger=EntityCreationTrigger(model=model),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model), ptype=ptype1,
                ),
                RelationAddingAction(
                    subject_source=CreatedEntitySource(model=model),
                    rtype=rtype,
                    object_source=FixedEntitySource(entity=fixed),
                ),
            ],
        )

        url = self._build_edit_action_url(wf, 0)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Edit the action «{action}»').format(action=_('Adding a property')),
            context1.get('title'),
        )

        with self.assertNoException():
            form1 = context1['form']
        self.assertIsInstance(form1, PropertyAddingActionForm)

        with self.assertNoException():
            fields1 = form1.fields
            ptype_f = fields1['ptype']
            source_f = fields1['source']

        self.assertEqual(ptype1.id, ptype_f.initial)
        self.assertIn(
            'created_entity',
            [kind_id for kind_id, _field in source_f.fields_choices],
        )
        self.assertEqual(CreatedEntitySource(model=model), source_f.initial)

        # POST ---
        self.assertNoFormError(self.client.post(
            url, data={
                'ptype': ptype2.id,

                'source': 'created_entity',
                'source_created_entity': '',
            },
        ))
        self.assertTupleEqual(
            (
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model), ptype=ptype2,
                ),
                RelationAddingAction(
                    subject_source=CreatedEntitySource(model=model),
                    rtype=rtype,
                    object_source=FixedEntitySource(entity=fixed),
                ),
            ),
            self.refresh(wf).actions,
        )

        # ----
        self.assertGET404(self._build_edit_action_url(wf, 2))

    def test_edit_action__second(self):
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is cool')
        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is concerned by',
        ).symmetric(id='creme_core-object_client', predicate='concerns').get_or_create()[0]

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        fixed1 = create_orga(name='Acme #1')
        fixed2 = create_orga(name='Acme #2')

        model = FakeContact
        wf = Workflow.objects.create(
            title='WF for Contact',
            content_type=model,
            trigger=EntityEditionTrigger(model=model),
            actions=[
                PropertyAddingAction(
                    entity_source=EditedEntitySource(model=model), ptype=ptype,
                ),
                RelationAddingAction(
                    subject_source=EditedEntitySource(model=model),
                    rtype=rtype,
                    object_source=FixedEntitySource(entity=fixed1),
                ),
            ],
        )

        url = self._build_edit_action_url(wf, 1)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Edit the action «{action}»').format(action=_('Adding a relationship')),
            context1.get('title'),
        )

        with self.assertNoException():
            form1 = context1['form']
        self.assertIsInstance(form1, RelationAddingActionForm)

        with self.assertNoException():
            fields1 = form1.fields
            rtype_f = fields1['rtype']
            subject_src_f = fields1['subject_source']
            object_src_f = fields1['object_source']

        self.assertEqual(rtype.id, rtype_f.initial)
        self.assertIn(
            'edited_entity', [kind_id for kind_id, _f in subject_src_f.fields_choices],
        )
        self.assertIn(
            'edited_entity', [kind_id for kind_id, _f in object_src_f.fields_choices],
        )
        self.assertEqual(EditedEntitySource(model=model),  subject_src_f.initial)
        self.assertEqual(FixedEntitySource(entity=fixed1), object_src_f.initial)

        # POST ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                'subject_source': 'edited_entity',
                'subject_source_edited_entity': '',

                'rtype': rtype.symmetric_type_id,

                'object_source': 'fixed_entity',
                'object_source_fixed_entity': json_dump({
                    'ctype': {'create': '', 'id': str(fixed2.entity_type_id)},
                    'entity': fixed2.id,
                }),
            },
        ))
        self.assertTupleEqual(
            (
                PropertyAddingAction(
                    entity_source=EditedEntitySource(model=model), ptype=ptype,
                ),
                RelationAddingAction(
                    subject_source=EditedEntitySource(model=model),
                    rtype=rtype.symmetric_type,
                    object_source=FixedEntitySource(entity=fixed2),
                ),
            ),
            self.refresh(wf).actions,
        )

    def test_delete_action__first(self):
        self.login_as_standard(admin_4_apps=('creme_core',))

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is cool')
        ptype2 = create_ptype(text='Is so cool')

        model = FakeContact
        wf = Workflow.objects.create(
            title='WF for Contact',
            content_type=model,
            trigger=EntityCreationTrigger(model=model),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model), ptype=ptype1,
                ),
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model), ptype=ptype2,
                ),
            ],
        )
        self.assertPOST200(self._build_del_action_url(wf), data={'index': 0})
        self.assertTupleEqual(
            (
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model), ptype=ptype2,
                ),
            ),
            self.refresh(wf).actions,
        )

    def test_delete_action__second(self):
        self.login_as_standard(admin_4_apps=('creme_core',))

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is cool')
        ptype2 = create_ptype(text='Is so cool')

        model = FakeContact
        wf = Workflow.objects.create(
            title='WF for Contact',
            content_type=model,
            trigger=EntityCreationTrigger(model=model),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model), ptype=ptype1,
                ),
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model), ptype=ptype2,
                ),
            ],
        )
        self.assertPOST200(self._build_del_action_url(wf), data={'index': 1})

        self.assertTupleEqual(
            (
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model), ptype=ptype1,
                ),
            ),
            self.refresh(wf).actions,
        )

    def test_delete_action__not_custom(self):
        self.login_as_standard(admin_4_apps=('creme_core',))

        model = FakeContact
        wf = Workflow.objects.create(
            title='WF for Contact',
            content_type=model,
            trigger=EntityCreationTrigger(model=model),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model),
                    ptype=CremePropertyType.objects.create(text='Is cool'),
                ),
            ],
            is_custom=False,
        )
        self.assertPOST409(self._build_del_action_url(wf), data={'index': 0})

    def test_delete_action__out_of_bound(self):
        self.login_as_standard(admin_4_apps=('creme_core',))

        model = FakeContact
        wf = Workflow.objects.create(
            title='WF for Contact',
            content_type=model,
            trigger=EntityCreationTrigger(model=model),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model),
                    ptype=CremePropertyType.objects.create(text='Is cool'),
                ),
            ],
        )
        self.assertPOST409(self._build_del_action_url(wf), data={'index': 1})
