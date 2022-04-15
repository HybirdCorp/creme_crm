from functools import partial
from json import dumps as json_dump

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_config.bricks import WorkflowsBrick
from creme.creme_config.forms.workflow import TriggerField
from creme.creme_core.forms.workflows import (
    PropertyAddingActionForm,
    RelationAddingActionForm,
)
from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    RelationType,
    Workflow,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EntityCreationTrigger,
    EntityEditionTrigger,
    FixedEntitySource,
    PropertyAddingAction,
    RelationAddingAction,
    RelationAddingTrigger,
)


class TriggerFieldTestCase(CremeTestCase):
    def test_ok(self):
        model = FakeContact
        field = TriggerField(model=model)
        self.assertEqual(model, field.model)

        rtype = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is concerned by'),
            ('creme_core-object_client',  'concerns'),
        )[0]
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
        self.login_as_standard(admin_4_apps=('creme_core',))

        old_wf_ids = [*Workflow.objects.values_list('id', flat=True)]
        model = FakeContact
        title = 'My Contact workflow'
        ct = ContentType.objects.get_for_model(FakeContact)
        url = reverse('creme_config__create_workflow', args=(ct.id,))

        ptype = CremePropertyType.objects.create(text='Is cool')

        # Step 1: Trigger ---
        trigger_step_get_resp = self.assertGET200(url)
        context1 = trigger_step_get_resp.context
        self.assertEqual(
            _('Create a workflow for «{model}»').format(model='Test Contact'),
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

        # TODO
        # with self.assertNoException():
        #     cond_f = trigger_step_post_resp.context['form'].fields['conditions...']
        #
        # self.assertIsInstance(trigger_f, TriggerField)
        # self.assertEqual(model, cond_f.model)
        # [...]

        conditions_step_post_resp = self.client.post(
            url,
            data={
                step_key: '1',
                '1-conditions': json_dump({
                    # 'ctype': {'id': str(entity.entity_type_id)},
                    # 'entity': str(entity.id),
                }),
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
        self.assertEqual(_('Save the workflow'), context3.get('submit_label'))
        # TODO: test fields

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
        self.assertEqual(ct,    workflow.content_type)
        self.assertFalse(workflow.enabled)
        self.assertTrue(workflow.is_custom)
        self.assertEqual(EntityCreationTrigger(model=model), workflow.trigger)
        self.assertFalse(workflow.conditions)
        self.assertTupleEqual(
            (
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model), ptype=ptype,
                ),
            ),
            workflow.actions,
        )

    # TODO: def test_create__with_conditions(self):
    # TODO: CustomEntity is deleted => error at creation

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

        rtype = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is concerned by'),
            ('creme_core-object_client', 'concerns'),
        )[0]
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
            _('Edit the action «{}»').format(_('Adding a property')),
            context1.get('title'),
        )

        with self.assertNoException():
            form1 = context1['form']
        self.assertIsInstance(form1, PropertyAddingActionForm)

        # with self.assertNoException():
        #     fields1 = form1.fields
        #     ptype_f = fields1['ptype']
        # TODO: test source (created, not edited)

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
        rtype1, rtype2 = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is concerned by'),
            ('creme_core-object_client', 'concerns'),
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        fixed1 = create_orga(name='Acme #1')
        fixed2 = create_orga(name='Acme #2')

        model = FakeContact
        wf = Workflow.objects.create(
            title='WF for Contact',
            content_type=model,
            trigger=EntityCreationTrigger(model=model),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=model), ptype=ptype,
                ),
                RelationAddingAction(
                    subject_source=CreatedEntitySource(model=model),
                    rtype=rtype1,
                    object_source=FixedEntitySource(entity=fixed1),
                ),
            ],
        )

        url = self._build_edit_action_url(wf, 1)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Edit the action «{}»').format(_('Adding a relationship')),
            context1.get('title'),
        )

        with self.assertNoException():
            form1 = context1['form']
        self.assertIsInstance(form1, RelationAddingActionForm)

        # TODO: test source (created, not edited)

        # POST ---
        self.assertNoFormError(self.client.post(
            url, data={
                'subject_source': 'created_entity',
                'subject_source_created_entity': '',

                'rtype': rtype2.id,

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
                    entity_source=CreatedEntitySource(model=model), ptype=ptype,
                ),
                RelationAddingAction(
                    subject_source=CreatedEntitySource(model=model),
                    rtype=rtype2,
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
