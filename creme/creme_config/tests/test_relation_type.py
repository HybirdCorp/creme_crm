from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core import workflows
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    condition_handler,
    operators,
)
from creme.creme_core.models import (
    CremePropertyType,
    EntityFilter,
    FakeContact,
    FakeOrganisation,
    Relation,
    RelationType,
    SemiFixedRelationType,
    Workflow,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.utils.translation import smart_model_verbose_name


class _RelationTypeBaseTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.basic_user = cls.create_user(
            index=0,
            password=cls.USER_PASSWORD,
            role=cls.create_role(
                name='Basic',
                allowed_apps=('creme_core',),
                # admin_4_apps=('creme_core',),  NOPE
            ),
        )

        admin_role = cls.create_role(
            name='Core admin',
            allowed_apps=('creme_core',),
            admin_4_apps=('creme_core',),
        )
        cls.add_credentials(role=admin_role, all='*')

        cls.core_admin = cls.create_user(
            index=1,
            password=cls.USER_PASSWORD,
            role=admin_role,
        )

    def _login_as_admin(self):
        self.client.login(username=self.core_admin.username, password=self.USER_PASSWORD)

    def _login_as_basic(self):
        self.client.login(username=self.basic_user.username, password=self.USER_PASSWORD)


class RelationTypeTestCase(_RelationTypeBaseTestCase):
    ADD_URL = reverse('creme_config__create_rtype')
    DEL_URL = reverse('creme_config__delete_rtype')

    @staticmethod
    def _build_edit_not_custom_url(rtype):
        return reverse('creme_config__edit_not_custom_rtype', args=(rtype.id,))

    @staticmethod
    def _build_edit_url(rtype):
        return reverse('creme_config__edit_rtype', args=(rtype.id,))

    def test_portal(self):
        self._login_as_admin()

        response = self.assertGET200(reverse('creme_config__rtypes'))
        self.assertTemplateUsed(response, 'creme_config/portals/relation-type.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

    def test_create(self):
        self._login_as_admin()
        url = self.ADD_URL

        context = self.assertGET200(url).context
        self.assertEqual(_('New custom type'),    context.get('title'))
        self.assertEqual(RelationType.save_label, context.get('submit_label'))

        count = RelationType.objects.count()
        subject_pred = 'loves'
        object_pred  = 'is loved by'
        response = self.client.post(
            url,
            data={
                'subject_predicate': subject_pred,
                'object_predicate':  object_pred,

                'subject_is_copiable': 'on',
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(count + 2, RelationType.objects.count())  # 2 freshly created

        rel_type = self.get_object_or_fail(RelationType, predicate=subject_pred)
        self.assertTrue(rel_type.is_custom)
        self.assertTrue(rel_type.is_copiable)
        self.assertFalse(rel_type.minimal_display)
        self.assertFalse(rel_type.subject_ctypes.all())
        self.assertFalse(rel_type.subject_properties.all())
        self.assertFalse(rel_type.subject_forbidden_properties.all())

        sym_type = rel_type.symmetric_type
        self.assertEqual(object_pred, sym_type.predicate)
        self.assertFalse(sym_type.is_copiable)
        self.assertFalse(sym_type.minimal_display)
        self.assertFalse(sym_type.subject_ctypes.all())
        self.assertFalse(sym_type.subject_properties.all())
        self.assertFalse(sym_type.subject_forbidden_properties.all())

    def test_create__property_constaints(self):
        "Property types (mandatory & forbidden)."
        self._login_as_admin()

        create_pt = CremePropertyType.objects.create
        pt_sub = create_pt(text='has cash').set_subject_ctypes(FakeOrganisation)
        pt_obj = create_pt(text='need cash').set_subject_ctypes(FakeContact)

        forbidden_pt_sub = create_pt(text='is greedy')
        forbidden_pt_obj = create_pt(text='is shy')

        subject_pred = 'employs (test version)'
        self.assertFalse(RelationType.objects.filter(predicate=subject_pred))

        get_ct = ContentType.objects.get_for_model
        data = {
            'subject_predicate': subject_pred,
            'object_predicate': 'is employed by (test version)',

            'subject_ctypes': [get_ct(FakeOrganisation).id],
            'object_ctypes': [get_ct(FakeContact).id],

            'subject_properties': [pt_sub.id],
            'object_properties': [pt_obj.id],

            'object_is_copiable': 'on',
        }
        # Error ---
        response1 = self.client.post(
            self.ADD_URL,
            data={
                **data,
                'subject_forbidden_properties': [forbidden_pt_sub.id, pt_sub.id],
                'object_forbidden_properties':  [forbidden_pt_obj.id, pt_obj.id],
            },
        )
        form = response1.context['form']
        msg = _(
            'These property types cannot be mandatory and forbidden at the '
            'same time: %(properties)s'
        )
        self.assertFormError(
            form,
            field='subject_forbidden_properties',
            errors=msg % {'properties': pt_sub.text},
        )
        self.assertFormError(
            form,
            field='object_forbidden_properties',
            errors=msg % {'properties': pt_obj.text},
        )

        # OK ---
        response2 = self.client.post(
            self.ADD_URL,
            data={
                **data,
                'subject_forbidden_properties': [forbidden_pt_sub.id],
                'object_forbidden_properties':  [forbidden_pt_obj.id],
            },
        )
        self.assertNoFormError(response2)

        rel_type = self.get_object_or_fail(RelationType, predicate=subject_pred)
        self.assertListEqual([FakeOrganisation], [*rel_type.subject_models])
        self.assertCountEqual([pt_sub], rel_type.subject_properties.all())
        self.assertCountEqual(
            [forbidden_pt_sub], rel_type.subject_forbidden_properties.all(),
        )

        self.assertFalse(rel_type.is_copiable)
        self.assertFalse(rel_type.minimal_display)

        sym_type = rel_type.symmetric_type
        self.assertTrue(sym_type.is_copiable)
        self.assertFalse(sym_type.minimal_display)
        self.assertListEqual([FakeContact], [*sym_type.subject_models])
        self.assertCountEqual([pt_obj], sym_type.subject_properties.all())
        self.assertCountEqual(
            [forbidden_pt_obj], sym_type.subject_forbidden_properties.all(),
        )

    def test_create__minimal_display_subject(self):
        self._login_as_admin()

        subject_pred = 'loves'
        response = self.client.post(
            self.ADD_URL,
            data={
                'subject_predicate': subject_pred,
                'object_predicate':  'is loved by',

                'subject_min_display': 'on',
            },
        )
        self.assertNoFormError(response)

        rel_type = self.get_object_or_fail(RelationType, predicate=subject_pred)
        self.assertTrue(rel_type.is_custom)
        self.assertFalse(rel_type.is_copiable)
        self.assertTrue(rel_type.minimal_display)

        sym_type = rel_type.symmetric_type
        self.assertFalse(sym_type.is_copiable)
        self.assertFalse(sym_type.minimal_display)

    def test_create__minimal_display_object(self):
        self._login_as_admin()

        subject_pred = 'loves'
        response = self.client.post(
            self.ADD_URL,
            data={
                'subject_predicate': subject_pred,
                'object_predicate':  'is loved by',

                'object_min_display': 'on',
            },
        )
        self.assertNoFormError(response)

        rel_type = self.get_object_or_fail(RelationType, predicate=subject_pred)
        self.assertTrue(rel_type.is_custom)
        self.assertFalse(rel_type.is_copiable)
        self.assertFalse(rel_type.minimal_display)

        sym_type = rel_type.symmetric_type
        self.assertFalse(sym_type.is_copiable)
        self.assertTrue(sym_type.minimal_display)

    def test_create__perm(self):
        self._login_as_basic()
        url = self.ADD_URL
        self.assertGET403(url)
        self.assertPOST403(
            url,
            data={
                'subject_predicate': 'loves',
                'object_predicate': 'is loved by',
            },
        )

    def test_edit_not_custom01(self):
        self._login_as_admin()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate', models=[FakeContact],
            # is_custom=False,
        ).symmetric(
            id='test-objfoo', predicate='object_predicate', minimal_display=True,
        ).get_or_create()[0]

        # Normal edition should not work
        self.assertGET404(self._build_edit_url(rt))

        url = self._build_edit_not_custom_url(rt)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            pgettext(
                'creme_config-relationship', 'Edit the standard type «{object}»',
            ).format(object=rt),
            context1.get('title'),
        )

        with self.assertNoException():
            fields = context1['form'].fields
            subject_min_display_f = fields['subject_min_display']
            object_min_display_f = fields['object_min_display']

        self.assertFalse(subject_min_display_f.initial)
        self.assertTrue(object_min_display_f.initial)
        self.assertEqual(2, len(fields))

        # ---
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'subject_min_display': 'on',
                'object_min_display': '',
            },
        )
        self.assertNoFormError(response2)

        rt: RelationType = self.refresh(rt)
        self.assertTrue(rt.minimal_display)
        self.assertFalse(rt.is_custom)
        self.assertFalse(rt.is_internal)
        self.assertListEqual([FakeContact], [*rt.subject_models])

        self.assertFalse(rt.symmetric_type.minimal_display)

    def test_edit_not_custom02(self):
        self._login_as_admin()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='Subject predicate', minimal_display=True,
            # is_custom=False,
        ).symmetric(
            id='test-objfoo', predicate='Object predicate', models=[FakeContact],
        ).get_or_create()[0]

        url = self._build_edit_not_custom_url(rt)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            subject_min_display_f = fields['subject_min_display']
            object_min_display_f = fields['object_min_display']

        self.assertTrue(subject_min_display_f.initial)
        self.assertFalse(object_min_display_f.initial)

        # ---
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'subject_min_display': '',
                'object_min_display': 'on',
            },
        )
        self.assertNoFormError(response2)

        rt: RelationType = self.refresh(rt)
        self.assertFalse(rt.minimal_display)

        sym_rt = rt.symmetric_type
        self.assertTrue(sym_rt.minimal_display)
        self.assertFalse(sym_rt.is_custom)
        self.assertFalse(sym_rt.is_internal)
        self.assertListEqual([FakeContact], [*sym_rt.subject_models])

    def test_edit_not_custom__disabled(self):
        self._login_as_admin()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='Subject predicate', enabled=False,
            # is_custom=False,
        ).symmetric(
            id='test-objfoo', predicate='Object predicate', models=[FakeContact],
        ).get_or_create()[0]
        self.assertGET404(self._build_edit_not_custom_url(rt))

    def test_edit_not_custom__perm(self):
        self._login_as_basic()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate',  # is_custom=False,
        ).symmetric(
            id='test-objfoo', predicate='Object predicate', models=[FakeContact],
        ).get_or_create()[0]
        self.assertGET403(self._build_edit_not_custom_url(rt))

    def test_edit_custom(self):
        "Edit a custom type."
        self._login_as_admin()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='Subject predicate', is_custom=True,
        ).symmetric(id='test-objfoo', predicate='Object predicate').get_or_create()[0]
        self.assertGET404(self._build_edit_not_custom_url(rt))

        url = self._build_edit_url(rt)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(
            pgettext(
                'creme_config-relationship', 'Edit the type «{object}»'
            ).format(object=rt),
            context.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        # ---
        subject_pred = 'loves'
        object_pred  = 'is loved by'
        response = self.client.post(
            url,
            data={
                'subject_predicate': subject_pred,
                'object_predicate':  object_pred,
            },
        )
        self.assertNoFormError(response)

        rel_type = RelationType.objects.get(pk=rt.id)
        self.assertEqual(subject_pred, rel_type.predicate)
        self.assertEqual(object_pred,  rel_type.symmetric_type.predicate)

    def test_edit_custom__disabled(self):
        "Edit a disabled type."
        self._login_as_admin()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate',
            is_custom=True, enabled=False,
        ).symmetric(id='test-objfoo', predicate='Object predicate').get_or_create()[0]
        self.assertGET404(self._build_edit_url(rt))

    def test_edit_custom__perm(self):
        self._login_as_basic()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate', is_custom=True,
        ).symmetric(id='test-objfoo', predicate='Object predicate').get_or_create()[0]

        self.assertGET403(self._build_edit_url(rt))

    def test_disable(self):
        self._login_as_admin()

        rt = RelationType.objects.builder(
            id='test-subject_foo', predicate='Subject predicate',
        ).symmetric(id='test-object_foo', predicate='Object predicate').get_or_create()[0]

        url = reverse('creme_config__disable_rtype', args=(rt.id,))
        self.assertGET405(url)

        self.assertPOST200(url)

        rt = self.refresh(rt)
        self.assertFalse(rt.enabled)
        self.assertFalse(rt.symmetric_type.enabled)

        self.assertPOST404(reverse('creme_config__disable_rtype', args=('test-subject_bar',)))

    def test_disable__internal(self):
        "Disable internal type => error."
        self._login_as_admin()

        rt = RelationType.objects.builder(
            id='test-subject_foo', predicate='Subject predicate',
            is_internal=True,
        ).symmetric(id='test-object_foo', predicate='Object predicate').get_or_create()[0]
        self.assertPOST409(reverse('creme_config__disable_rtype', args=(rt.id,)))

    def test_disable__perm(self):
        self._login_as_basic()

        rt = RelationType.objects.builder(
            id='test-subject_foo', predicate='subject_predicate',
        ).symmetric(id='test-object_foo', predicate='Object predicate').get_or_create()[0]
        self.assertPOST403(reverse('creme_config__disable_rtype', args=(rt.id,)))

    def test_enable(self):
        self._login_as_admin()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='Subject predicate', enabled=False,
        ).symmetric(id='test-objfoo', predicate='Object predicate').get_or_create()[0]

        url = reverse('creme_config__enable_rtype', args=(rt.id,))
        self.assertGET405(url)

        self.assertPOST200(url)
        rt = self.refresh(rt)
        self.assertTrue(rt.enabled)
        self.assertTrue(rt.symmetric_type.enabled)

    def test_delete__standard(self):
        self._login_as_admin()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='Subject predicate',  # is_custom=False,
        ).symmetric(id='test-objfoo', predicate='Object predicate').get_or_create()[0]
        self.assertGET405(self.DEL_URL, data={'id': rt.id})

    def test_delete__custom(self):
        self._login_as_admin()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='Subject predicate',
            is_custom=True,
        ).symmetric(id='test-objfoo', predicate='Object predicate').get_or_create()[0]
        self.assertPOST200(self.DEL_URL, data={'id': rt.id})
        self.assertDoesNotExist(rt)
        self.assertDoesNotExist(rt.symmetric_type)

    def test_delete__perm(self):
        self._login_as_basic()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate', is_custom=True,
        ).symmetric(id='test-objfoo', predicate='object_predicate').get_or_create()[0]
        self.assertPOST403(self.DEL_URL, data={'id': rt.id})
        self.assertStillExists(rt)
        self.assertStillExists(rt.symmetric_type)

    def test_delete__used_by_relationships(self):
        user = self.login_as_root_and_get()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='Subject predicate', is_custom=True,
        ).symmetric(id='test-subfoo', predicate='Object predicate').get_or_create()[0]

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Subject inc.')
        orga2 = create_orga(name='Object corp.')

        rel = Relation.objects.create(
            user=user, subject_entity=orga1, object_entity=orga2, type=rt,
        )

        response = self.assertPOST409(
            self.DEL_URL, HTTP_X_REQUESTED_WITH='XMLHttpRequest', data={'id': rt.id},
        )
        self.assertStillExists(rt)
        self.assertStillExists(rel)
        self.assertEqual(
            _(
                'The relationship type cannot be deleted because of its '
                'dependencies: {dependencies}'
            ).format(
                dependencies=_('{count} {model}').format(
                    count=2,
                    model=smart_model_verbose_name(model=Relation, count=2),
                )
            ),
            response.text,
        )

    def test_delete__used_by_efilter(self):
        self.login_as_root()

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
            name='Related', model=FakeContact,
            is_custom=True,
            conditions=[build_cond(rtype=rtype1, has=True)],
        )
        efilter2 = EntityFilter.objects.create(
            id='creme_core-tests_views_rtype2',
            name='Not related',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [build_cond(rtype=rtype1.symmetric_type, has=False, filter_type=EF_CREDENTIALS)],
            check_cycles=False, check_privacy=False,
        )
        EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_views_rtype3',
            name='Related but different', model=FakeContact,
            is_custom=True,
            conditions=[build_cond(rtype=rtype2, has=True)],
        )

        response = self.assertPOST409(
            self.DEL_URL, HTTP_X_REQUESTED_WITH='XMLHttpRequest', data={'id': rtype1.id},
        )
        self.assertStillExists(rtype1)

        efilter1 = self.assertStillExists(efilter1)
        self.assertEqual(1, efilter1.conditions.count())

        self.assertHTMLEqual(
            _(
                'The relationship type cannot be deleted because it is used in '
                'filter conditions: {filters}'
            ).format(
                filters=(
                    f'<ul class="limited-list">'
                    f'<li>{efilter2.name} *{_("Credentials filter")}*</li>'
                    f'<li>'
                    f'<a href="{efilter1.get_absolute_url()}" target="_blank">{efilter1.name}</a>'
                    f'</li>'
                    f'</ul>'
                ),
            ),
            response.text,
        )

    def test_delete__used_by_efilter__subfilter(self):
        self.login_as_root()

        rtype = RelationType.objects.builder(
            id='test-subject_foo', predicate='Subject predicate', is_custom=True,
        ).symmetric(id='test-object_foo', predicate='Object predicate').get_or_create()[0]
        sub_filter = EntityFilter.objects.smart_update_or_create(
            'creme_core-tests_views_rtype_sub',
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
            'creme_core-tests_views_rtype',
            name='Related to corps', model=FakeContact,
            is_custom=True,
            conditions=[
                condition_handler.RelationSubFilterConditionHandler.build_condition(
                    model=FakeContact, rtype=rtype, subfilter=sub_filter,
                ),
            ],
        )
        response = self.assertPOST409(
            self.DEL_URL, HTTP_X_REQUESTED_WITH='XMLHttpRequest', data={'id': rtype.id},
        )
        self.assertStillExists(rtype)

        efilter = self.assertStillExists(efilter)
        self.assertEqual(1, efilter.conditions.count())
        self.assertHTMLEqual(
            _(
                'The relationship type cannot be deleted because it is used in '
                'filter conditions: {filters}'
            ).format(
                filters=(
                    f'<a href="{efilter.get_absolute_url()}" target="_blank">{efilter.name}</a>'
                ),
            ),
            response.text,
        )

    def test_delete__used_by_workflow__trigger(self):
        self.login_as_root()

        rtype1 = RelationType.objects.builder(
            id='test-subject_foo', predicate='Subject predicate #1', is_custom=True,
        ).symmetric(id='test-object_foo', predicate='Object predicate #1').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_bar', predicate='Subject predicate #2', is_custom=True,
        ).symmetric(id='test-object_bar', predicate='Object predicate #2').get_or_create()[0]

        wf1 = Workflow.objects.create(
            title='Flow #1',
            content_type=FakeContact,
            trigger=workflows.RelationAddingTrigger(
                subject_model=FakeContact, rtype=rtype1, object_model=FakeOrganisation,
            ),
            # conditions=...
            # actions=[],
        )
        Workflow.objects.create(
            title='Flow on other ptype',
            content_type=FakeContact,
            trigger=workflows.RelationAddingTrigger(
                subject_model=FakeContact, rtype=rtype2, object_model=FakeOrganisation,
            ),
            # conditions=...,
            # actions=[],
        )
        wf3 = Workflow.objects.create(
            title='Flow #3',
            content_type=FakeOrganisation,
            trigger=workflows.RelationAddingTrigger(
                subject_model=FakeOrganisation,
                rtype=rtype1.symmetric_type,
                object_model=FakeContact,
            ),
            # conditions=...,
            # actions=[],
        )

        response = self.assertPOST409(
            self.DEL_URL, HTTP_X_REQUESTED_WITH='XMLHttpRequest', data={'id': rtype1.id},
        )
        self.assertStillExists(rtype1)
        self.assertEqual(
            _(
                'The relationship type cannot be deleted because it is used by '
                'triggers of Workflow: {workflows}'
            ).format(workflows=f'«{wf1.title}», «{wf3.title}»'),
            response.text,
        )


class SemiFixedRelationTypeTestCase(_RelationTypeBaseTestCase):
    ADD_URL = reverse('creme_config__create_semifixed_rtype')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.loves = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is loving',
        ).symmetric(id='test-object_foobar', predicate='is loved by').get_or_create()[0]

        cls.iori = FakeContact.objects.create(
            user=cls.get_root_user(), first_name='Iori', last_name='Yoshizuki',
        )

    def test_create(self):
        self._login_as_admin()

        url = self.ADD_URL
        self.assertGET200(url)

        predicate = 'Is loving Iori'
        iori = self.iori
        response = self.client.post(
            url,
            data={
                'predicate':     predicate,
                'semi_relation': self.formfield_value_relation_entity(self.loves, iori),
            },
        )
        self.assertNoFormError(response)

        smr = self.get_alone_element(SemiFixedRelationType.objects.all())
        self.assertEqual(predicate,  smr.predicate)
        self.assertEqual(self.loves, smr.relation_type)
        self.assertEqual(iori.entity_type, smr.object_ctype)
        self.assertEqual(iori, smr.object_entity.get_real_entity())
        self.assertEqual(iori, smr.real_object)

    def test_create__predicate_uniqueness(self):
        "Predicate is unique."
        self._login_as_admin()

        predicate = 'Is loving Iori'
        SemiFixedRelationType.objects.create(
            predicate=predicate,
            relation_type=self.loves,
            real_object=self.iori,
        )

        itsuki = FakeContact.objects.create(
            user=self.core_admin, first_name='Itsuki', last_name='Akiba',
        )
        response = self.assertPOST200(
            self.ADD_URL,
            data={
                'predicate':     predicate,
                'semi_relation': self.formfield_value_relation_entity(self.loves, itsuki),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='predicate',
            errors=_('%(model_name)s with this %(field_label)s already exists.') % {
                'model_name': _('Semi-fixed type of relationship'),
                'field_label': _('Predicate'),
            },
        )

    def test_create__ref_uniqueness(self):
        "('relation_type', 'object_entity') => unique together."
        self._login_as_admin()

        predicate = 'Is loving Iori'
        SemiFixedRelationType.objects.create(
            predicate=predicate,
            relation_type=self.loves,
            real_object=self.iori,
        )

        url = self.ADD_URL
        predicate += ' (other)'
        response1 = self.assertPOST200(url, data={'predicate': predicate})
        self.assertFormError(
            response1.context['form'],
            field='semi_relation',
            errors=_('This field is required.'),
        )

        # ---
        response2 = self.assertPOST200(
            url,
            data={
                'predicate':     predicate,
                'semi_relation': self.formfield_value_relation_entity(self.loves, self.iori),
            },
        )
        self.assertFormError(
            response2.context['form'],
            field=None,
            errors=_(
                'A semi-fixed type of relationship with this type and this object already exists.'
            ),
        )

    def test_create__perm(self):
        self._login_as_basic()

        url = self.ADD_URL
        self.assertGET403(url)
        self.assertPOST403(
            url,
            data={
                'predicate':     'Is loving Iori',
                'semi_relation': self.formfield_value_relation_entity(self.loves, self.iori),
            },
        )

    def test_edit(self):
        self._login_as_admin()

        predicate = 'Is loving Iori'
        sfrt = SemiFixedRelationType.objects.create(
            predicate=predicate,
            relation_type=self.loves,
            real_object=self.iori,
        )

        url = reverse('creme_config__edit_semifixed_rtype', args=(sfrt.id,))
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields

        self.assertNotIn('semi_relation', fields)
        self.assertNotIn('relation_type', fields)
        self.assertNotIn('object_entity', fields)

        predicate += ' very much'
        self.assertNoFormError(self.client.post(url, data={'predicate': predicate}))
        self.assertEqual(predicate, self.refresh(sfrt).predicate)

    def test_edit__disabled(self):
        "The relation type is disabled => error."
        self._login_as_admin()

        rtype = self.loves
        rtype.enabled = False
        rtype.save()

        sfrt = SemiFixedRelationType.objects.create(
            predicate='Is loving Iori',
            relation_type=rtype,
            real_object=self.iori,
        )
        self.assertGET404(
            reverse('creme_config__edit_semifixed_rtype', args=(sfrt.id,))
        )

    def test_edit__perm(self):
        self._login_as_basic()

        sfrt = SemiFixedRelationType.objects.create(
            predicate='Is loving Iori',
            relation_type=self.loves,
            real_object=self.iori,
        )

        url = reverse('creme_config__edit_semifixed_rtype', args=(sfrt.id,))
        self.assertGET403(url)
        self.assertPOST403(url, data={'predicate': f'{sfrt.predicate} very much'})

    def test_delete(self):
        self._login_as_admin()

        sfrt = SemiFixedRelationType.objects.create(
            predicate='Is loving Iori',
            relation_type=self.loves,
            real_object=self.iori,
        )
        self.assertPOST200(
            reverse('creme_config__delete_semifixed_rtype'),
            data={'id': sfrt.id},
        )
        self.assertDoesNotExist(sfrt)

    def test_delete__perm(self):
        self._login_as_basic()

        sfrt = SemiFixedRelationType.objects.create(
            predicate='Is loving Iori',
            relation_type=self.loves,
            real_object=self.iori,
        )
        self.assertPOST403(
            reverse('creme_config__delete_semifixed_rtype'),
            data={'id': sfrt.id},
        )
        self.assertStillExists(sfrt)
