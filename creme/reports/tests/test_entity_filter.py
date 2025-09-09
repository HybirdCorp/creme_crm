from functools import partial
from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    EF_REGULAR,
    condition_handler,
    operators,
)
from creme.creme_core.models import (
    EntityFilter,
    FakeContact,
    FakeOrganisation,
    RelationType,
)
from creme.creme_core.tests.views import base as test_base
from creme.creme_core.utils.translation import smart_model_verbose_name
from creme.creme_core.views.entity_filter import (
    EntityFilterInfoBrick,
    EntityFilterParentsBrick,
)

from ..bricks import ReportEntityFiltersBrick
from ..constants import EF_REPORTS
from ..core.entity_filter import (
    ReportRelationSubFilterConditionHandler,
    ReportRelationSubfiltersConditionsField,
    ReportSubFilterConditionHandler,
)
from .base import BaseReportsTestCase, Report


class ReportRelationSubfiltersConditionsFieldTestCase(BaseReportsTestCase):
    def _create_rtype(self):
        return RelationType.objects.builder(
            id='test-subject_freelance', predicate='Is a freelance for',
            models=[FakeContact],
        ).symmetric(
            id='test-object_freelance', predicate='Works with the freelance',
        ).get_or_create()[0]

    def test_clean_empty_required(self):
        field = ReportRelationSubfiltersConditionsField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='[]')

    def test_clean_incomplete_data_required(self):
        rtype = self._create_rtype()
        field = ReportRelationSubfiltersConditionsField(model=FakeContact)
        msg = _('This field is required.')
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=json_dump([{'rtype': rtype.id}]),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=json_dump([{'has': True}]),
        )

    def test_unknown_filter(self):
        rtype = self._create_rtype()
        field = ReportRelationSubfiltersConditionsField(model=FakeContact)
        field.user = self.get_root_user()
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'rtype': rtype.id, 'has': False,
                'ctype': ContentType.objects.get_for_model(FakeContact).id,
                'filter': '3213213543',  # <==
            }]),
            messages=_('This filter is invalid.'),
            codes='invalidfilter',
        )

    def test_ok(self):
        user = self.get_root_user()
        team = self.create_team('My team', user)

        rtype1 = self._create_rtype()
        rtype2 = rtype1.symmetric_type

        efilter1 = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
        )
        efilter2 = EntityFilter.objects.create(
            id='reports-organisation_filter1',
            name='Organisation filter (only reports)',
            entity_type=FakeOrganisation,
            filter_type=EF_REPORTS,
            is_private=True,
            user=user,
        )
        efilter3 = EntityFilter.objects.create(
            id='reports-organisation_filter2',
            name='Team filter (only reports)',
            entity_type=FakeOrganisation,
            filter_type=EF_REPORTS,
            is_private=True,
            user=team,
        )

        with self.assertNumQueries(0):
            field = ReportRelationSubfiltersConditionsField(model=FakeContact)
            field.user = user

        field.efilter_type = EF_REPORTS

        conditions = field.clean(json_dump([
            {
                'rtype': rtype1.id,
                'has': True,
                'ctype': efilter1.entity_type_id,
                'filter': efilter1.id,
            }, {
                'rtype': rtype2.id,
                'has': False,
                'ctype': efilter2.entity_type_id,
                'filter': efilter2.id,
            }, {
                'rtype': rtype2.id,
                'has': False,
                'ctype': efilter3.entity_type_id,
                'filter': efilter3.id,
            },
        ]))
        self.assertEqual(3, len(conditions))

        type_id = ReportRelationSubFilterConditionHandler.type_id
        condition1 = conditions[0]
        self.assertEqual(type_id,    condition1.type)
        self.assertEqual(rtype1.id,  condition1.name)
        self.assertEqual(EF_REPORTS, condition1.filter_type)
        self.assertDictEqual(
            {'has': True, 'filter_id': efilter1.id},
            condition1.value,
        )

        condition2 = conditions[1]
        self.assertEqual(type_id,   condition2.type)
        self.assertEqual(rtype2.id, condition2.name)
        self.assertDictEqual(
            {'has': False, 'filter_id': efilter2.id},
            condition2.value,
        )

        self.assertDictEqual(
            {'has': False, 'filter_id': efilter3.id},
            conditions[2].value,
        )

    def test_forbidden_filter1(self):
        user = self.get_root_user()
        other = self.create_user()

        rtype = self._create_rtype()
        efilter = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
            is_private=True,
            user=other,
        )

        field = ReportRelationSubfiltersConditionsField(model=FakeContact, user=user)
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'rtype': rtype.id, 'has': False,
                'ctype': efilter.entity_type_id,
                'filter': efilter.id,
            }]),
            messages=_('This filter is invalid.'),
            codes='invalidfilter',
        )

    def test_forbidden_filter2(self):
        user = self.get_root_user()

        rtype = self._create_rtype()
        efilter = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS
        )

        field = ReportRelationSubfiltersConditionsField(model=FakeContact, user=user)
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'rtype': rtype.id, 'has': False,
                'ctype': efilter.entity_type_id,
                'filter': efilter.id,
            }]),
            messages=_('This filter is invalid.'),
            codes='invalidfilter',
        )

    def test_staff(self):
        user = self.login_as_super(is_staff=True)
        other_user = self.create_user(index=1)
        rtype = self._create_rtype()
        efilter = EntityFilter.objects.create(
            id='reports-organisation_filter',
            name='Organisation filter (only reports)',
            entity_type=FakeOrganisation,
            filter_type=EF_REPORTS,
            is_private=True,
            user=other_user,
        )
        field = ReportRelationSubfiltersConditionsField(
            model=FakeContact, user=user, efilter_type=EF_REPORTS,
        )

        condition = self.get_alone_element(field.clean(json_dump([{
            'rtype': rtype.id,
            'has': True,
            'ctype': efilter.entity_type_id,
            'filter': efilter.id,
        }])))
        self.assertDictEqual(
            {'has': True, 'filter_id': efilter.id}, condition.value,
        )

    def test_disabled_rtype01(self):
        efilter = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )

        rtype = self._create_rtype()
        rtype.enabled = False
        rtype.save()

        self.assertFormfieldError(
            field=ReportRelationSubfiltersConditionsField(
                model=FakeContact, user=self.get_root_user(),
            ),
            value=json_dump([{
                'rtype': rtype.id, 'has': True,
                'ctype': efilter.entity_type_id,
                'filter': efilter.id,
            }]),
            messages=_('This type of relationship type is invalid with this model.'),
            codes='invalidrtype',
        )

    def test_disabled_rtype02(self):
        "Disabled RelationType is already used => still proposed."
        efilter = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )

        rtype = self._create_rtype()
        rtype.enabled = False
        rtype.save()

        field = ReportRelationSubfiltersConditionsField(
            model=FakeContact, user=self.get_root_user(), efilter_type=EF_REPORTS,
        )

        ct = ContentType.objects.get_for_model(FakeContact)
        field.initialize(
            ctype=ct,
            conditions=[
                ReportRelationSubFilterConditionHandler.build_condition(
                    model=FakeContact, rtype=rtype, subfilter=efilter,
                ),
            ],
        )
        efilter_id = efilter.id
        condition = self.get_alone_element(field.clean(json_dump([{
            'rtype': rtype.id, 'has': True, 'ctype': ct.id, 'filter': efilter_id,
        }])))
        self.assertEqual(ReportRelationSubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(rtype.id, condition.name)
        self.assertDictEqual(
            {'has': True, 'filter_id': efilter_id}, condition.value,
        )


class EntityFilterTestCase(test_base.BrickTestCaseMixin,
                           test_base.ButtonTestCaseMixin,
                           BaseReportsTestCase):
    @staticmethod
    def _build_add_url(ct_or_model):
        ct = (
            ct_or_model
            if isinstance(ct_or_model, ContentType) else
            ContentType.objects.get_for_model(FakeContact)
        )
        return reverse('reports__create_efilter', args=(ct.id,))

    @staticmethod
    def _build_edit_popup_url(efilter):
        return reverse('reports__edit_efilter_popup', args=(efilter.id,))

    @staticmethod
    def _build_rfields_data(name, operator, value):
        return json_dump([{
            'field':    {'name': name},
            'operator': {'id': str(operator)},
            'value':    value,
        }])

    def test_str(self):
        efilter = EntityFilter(
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )
        self.assertEqual(f'{efilter.name} [{_("Report")}]', str(efilter))

    def test_portal(self):
        apps = ['creme_core', 'reports', 'persons']
        self.login_as_standard(allowed_apps=apps, admin_4_apps=apps)

        regular_efilter = EntityFilter.objects.create(
            id='test-regular_filter',
            name='Regular Contact filter',
            entity_type=FakeContact,
            filter_type=EF_REGULAR,
        )
        system_efilter = EntityFilter.objects.create(
            id='test-system_filter',
            name='Credentials special filter',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )
        report_efilter = EntityFilter.objects.create(
            id='test-reports_filter',
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )

        response = self.assertGET200(
            reverse('creme_config__app_portal', args=('reports',))
        )
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=ReportEntityFiltersBrick,
        )
        # TODO: retrieve number of ContentTypes
        # self.assertBrickTitleEqual(
        #     brick_node,
        #     count=...,
        #     title='Filters: {count} configurable type of resource',
        #     plural_title='Filters: {count} configurable types of resource',
        # )

        fake_contact_node = None
        for div in brick_node.findall('.//div'):
            if 'entityfilter-config-item-creme_core-fakecontact' in div.attrib.get('class'):
                fake_contact_node = div
                break
        else:
            self.fail('<div> for FakeContact not found')

        efilters_ids = [
            efilter_id
            for li in fake_contact_node.findall('.//li')
            if (efilter_id := li.attrib.get('data-efilter-id'))
        ]
        self.assertIn(report_efilter.id, efilters_ids)
        self.assertNotIn(system_efilter.id,  efilters_ids)
        self.assertNotIn(regular_efilter.id, efilters_ids)

        # TODO: check URLs in buttons

    def test_detailview(self):
        user = self.login_as_standard(allowed_apps=['creme_core', 'reports'])
        self.add_credentials(role=user.role, own=['VIEW'])

        efilter = EntityFilter.objects.create(
            pk='reports-test_filter_detailview01', name='My Filter',
            entity_type=FakeContact, is_custom=True,
            filter_type=EF_REPORTS,
            user=user,
        )

        parent_filter = EntityFilter.objects.create(
            pk='reports-test_filter_detailview01_parent', name='Parent Filter',
            entity_type=FakeContact, is_custom=True,
            filter_type=EF_REPORTS,
        ).set_conditions([
            condition_handler.SubFilterConditionHandler.build_condition(
                efilter, filter_type=EF_REPORTS,
            ),
        ])

        create_report = partial(Report.objects.create, user=user, ct=efilter.entity_type)
        report1 = create_report(name='My report with filter', filter=efilter)
        report2 = create_report(name='My simple report')

        url = efilter.get_absolute_url()
        self.assertEqual(reverse('reports__efilter', args=(efilter.id,)), url)

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'reports/detail/entity-filter.html')

        reload_url = reverse('reports__reload_efilter_bricks', args=(efilter.id,))
        self.assertEqual(reload_url, response.context.get('bricks_reload_url'))

        with self.assertNoException():
            ctxt_efilter = response.context['object']
        self.assertEqual(efilter, ctxt_efilter)

        tree = self.get_html_tree(response.content)

        config_button_node = self.get_alone_element(
            self.iter_button_nodes(self.get_global_buttons_node(tree))
        )
        self.assertEqual('a', config_button_node.tag)
        self.assertEqual(
            reverse('creme_config__app_portal', args=('reports',)),
            config_button_node.attrib.get('href'),
        )

        self.get_brick_node(tree, EntityFilterInfoBrick)

        parents_node = self.get_brick_node(tree, EntityFilterParentsBrick)
        self.assertBrickTitleEqual(
            parents_node,
            count=1,
            title='{count} Parent filter',
            plural_title='{count} Parent filters',
        )
        self.assertInstanceLink(parents_node, parent_filter)

        reports_brick_node = self.get_brick_node(
            tree, 'linked_to_efilter-reports-report-filter',
        )
        self.assertEqual(
            _('Filter used by %(count)s %(model)s (field «%(field)s»)') % {
                'count': 1,
                'model': smart_model_verbose_name(model=Report, count=1),
                'field': _('Filter'),
            },
            self.get_brick_title(reports_brick_node),
        )
        self.assertInstanceLink(reports_brick_node, report1)
        self.assertNoInstanceLink(reports_brick_node, report2)

        msg_node = self.get_html_node_or_fail(reports_brick_node, ".//div[@class='help']")
        self.assertEqual(
            _('You cannot delete the filter because of this dependency.'),
            msg_node.text.strip(),
        )

        # Reload ---
        brick_id = EntityFilterParentsBrick.id
        reload_response = self.assertGET200(
            reverse('reports__reload_efilter_bricks', args=(efilter.id,)),
            data={'brick_id': brick_id},
        )

        with self.assertNoException():
            results = reload_response.json()

        self.assertIsList(results, length=1)

        result = results[0]
        self.assertIsList(result, length=2)
        self.assertEqual(brick_id, result[0])

        document = self.get_html_tree(result[1])
        brick_node = self.get_brick_node(document, brick_id)
        self.assertInstanceLink(brick_node, parent_filter)

    def test_detailview__permissions01(self):
        self.login_as_standard(allowed_apps=['creme_core'])  # 'reports'
        efilter = EntityFilter.objects.create(
            pk='reports-test_filter_detailview_perm01', name='My Filter',
            entity_type=FakeContact, is_custom=True,
            filter_type=EF_REPORTS,
        )
        self.assertGET403(efilter.get_absolute_url())

        # Reload ---
        self.assertGET403(
            reverse('reports__reload_efilter_bricks', args=(efilter.id,)),
            data={'brick_id': EntityFilterParentsBrick.id},
        )

    def test_detailview__permissions02(self):
        self.login_as_standard(allowed_apps=['reports'])  # 'creme_core'
        efilter = EntityFilter.objects.create(
            pk='reports-test_filter_detailview_perm02', name='My Filter',
            entity_type=FakeContact, is_custom=True,
            filter_type=EF_REPORTS,
        )
        self.assertGET403(efilter.get_absolute_url())

    def test_create__permissions01(self):
        self.login_as_standard(allowed_apps=['reports'])
        self.assertGET403(self._build_add_url(FakeContact))

    def test_create__permissions02(self):
        self.login_as_standard(allowed_apps=['creme_core'])
        self.assertGET403(self._build_add_url(FakeContact))

    def test_create(self):
        self.login_as_standard(allowed_apps=['reports', 'creme_core'])

        url = self._build_add_url(FakeContact)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Create a filter for «{model}» specific to Reports').format(model='Test Contact'),
            context1.get('title'),
        )
        self.assertEqual(_('Save the filter'), context1.get('submit_label'))

        with self.assertNoException():
            # NB: difficult to test the content in a robust way (depends on the DB config)
            context1['help_message']  # NOQA

        # ---
        name = 'Filter 01'
        operator = operators.IEQUALS
        field_name = 'last_name'
        value = 'Ikari'
        response2 = self.client.post(
            url,
            data={
                'name': name,
                'use_or': 'False',
                'regularfieldcondition': self._build_rfields_data(
                    operator=operator,
                    name=field_name,
                    value=value,
                ),
            },
        )
        self.assertNoFormError(response2)

        efilter = self.get_alone_element(EntityFilter.objects.filter(filter_type=EF_REPORTS))
        self.assertEqual(FakeContact, efilter.entity_type.model_class())
        self.assertStartsWith(efilter.pk, 'reports-userfilter_')
        self.assertEqual(name, efilter.name)
        self.assertTrue(efilter.is_custom)
        self.assertFalse(efilter.is_private)
        self.assertIsNone(efilter.user)
        self.assertFalse(efilter.use_or)

        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(field_name, condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

    def test_create__subfilters(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()
        my_team = self.create_team('My team', user, other_user)

        regular_efilter = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
        )
        public_report_efilter = EntityFilter.objects.create(
            id='reports-contacts_filter1',
            name='Public Contact filter (only reports)',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )
        private_report_efilter1 = EntityFilter.objects.create(
            id='creme_core-private_contacts_filter1',
            name='My Contact filter',
            entity_type=FakeContact,
            is_private=True,
            user=user,
        )
        private_report_efilter2 = EntityFilter.objects.create(
            id='creme_core-private_contacts_filter2',
            name='Contact filter of my team',
            entity_type=FakeContact,
            is_private=True,
            user=my_team,
        )
        forbidden_efilter1 = EntityFilter.objects.create(
            id='creme_core-forbidden_contacts_filter1',
            name='Forbidden Contact filter',
            entity_type=FakeContact,
            is_private=True,
            user=other_user,
        )
        other_ct_efilter = EntityFilter.objects.create(
            id='reports-organisations_filter',
            name='Organisation filter (only reports)',
            entity_type=FakeOrganisation,
            filter_type=EF_REPORTS,
        )
        creds_efilter = EntityFilter.objects.create(
            id='creme_core-creds_filter',
            name='Internal filter',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )

        url = self._build_add_url(FakeContact)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            sub_filters_choices = [
                *response1.context['form'].fields['reportsubfiltercondition'].choices
            ]

        self.assertInChoices(
            value=regular_efilter.id,
            label=regular_efilter.name,
            choices=sub_filters_choices,
        )
        self.assertInChoices(
            value=public_report_efilter.id,
            label=f'{public_report_efilter.name} [{_("Report")}]',
            choices=sub_filters_choices,
        )
        self.assertInChoices(
            value=private_report_efilter1.id,
            label=private_report_efilter1.name,
            choices=sub_filters_choices,
        )
        self.assertInChoices(
            value=private_report_efilter2.id,
            label=private_report_efilter2.name,
            choices=sub_filters_choices,
        )

        self.assertNotInChoices(value=forbidden_efilter1.id, choices=sub_filters_choices)
        self.assertNotInChoices(value=other_ct_efilter.id,   choices=sub_filters_choices)
        self.assertNotInChoices(value=creds_efilter.id,      choices=sub_filters_choices)

        # ---
        name = 'Filter with sub-filters 01'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name': name,
                'is_private': 'on',
                'user': user.id,
                'use_or': 'True',
                'reportsubfiltercondition': [public_report_efilter.id],
            },
        ))

        efilter = self.get_alone_element(
            EntityFilter.objects.filter(filter_type=EF_REPORTS, name=name)
        )
        self.assertEqual(FakeContact, efilter.entity_type.model_class())
        self.assertTrue(efilter.is_private)
        self.assertEqual(user, efilter.user)
        self.assertTrue(efilter.use_or)

        condition = self.get_alone_element(efilter.conditions.all())
        cond_type_id = condition_handler.SubFilterConditionHandler.type_id
        self.assertEqual(cond_type_id, ReportSubFilterConditionHandler.type_id)
        self.assertEqual(cond_type_id, condition.type)
        self.assertIsInstance(condition.handler, ReportSubFilterConditionHandler)

        self.assertEqual(public_report_efilter.id, condition.name)

    def test_create__subfilters_staff(self):
        self.login_as_super(is_staff=True)
        other_user = self.create_user(index=1)

        regular_efilter = EntityFilter.objects.create(
            id='creme_core-contacts_filter1',
            name='Contact filter',
            entity_type=FakeContact,
        )
        not_forbidden_efilter = EntityFilter.objects.create(
            id='reports-contacts_filter2',
            name='Private Contact filter',
            entity_type=FakeContact,
            is_private=True,
            user=other_user,
        )

        response = self.assertGET200(self._build_add_url(FakeContact))

        with self.assertNoException():
            sub_filters_choices = [
                *response.context['form'].fields['reportsubfiltercondition'].choices
            ]

        self.assertInChoices(
            value=regular_efilter.id,
            label=regular_efilter.name,
            choices=sub_filters_choices,
        )
        self.assertInChoices(
            value=not_forbidden_efilter.id,
            label=not_forbidden_efilter.name,
            choices=sub_filters_choices,
        )

    def test_create__relation_subfilters(self):
        user = self.login_as_root_and_get()

        rtype = RelationType.objects.builder(
            id='reports-subject_early_adopter', predicate='Is as early adopter of',
        ).symmetric(
            id='reports-object_early_adopter', predicate='Is early adopted by',
        ).get_or_create()[0]
        orga_efilter = EntityFilter.objects.create(
            id='creme_core-orga_filter',
            name='My Organisation filter',
            entity_type=FakeOrganisation,
            filter_type=EF_REPORTS,
            is_private=True,
            user=user,
        )

        url = self._build_add_url(FakeContact)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            rel_sub_filters_f = response1.context['form'].fields[
                'reportrelationsubfiltercondition'
            ]

        self.assertIsInstance(rel_sub_filters_f, ReportRelationSubfiltersConditionsField)
        self.assertEqual(FakeContact, rel_sub_filters_f.model)

        # ---
        name = 'Filter with sub-filters 01'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name': name,
                'is_private': 'on',
                'user': user.id,
                'use_or': 'True',
                'reportrelationsubfiltercondition': json_dump([{
                    'rtype': rtype.id,
                    'has': False,
                    'ctype': orga_efilter.entity_type_id,
                    'filter': orga_efilter.id,
                }])
            },
        ))

        efilter = self.get_alone_element(
            EntityFilter.objects.filter(filter_type=EF_REPORTS, name=name)
        )
        self.assertEqual(FakeContact, efilter.entity_type.model_class())
        self.assertTrue(efilter.is_private)
        self.assertEqual(user, efilter.user)
        self.assertTrue(efilter.use_or)

        condition = self.get_alone_element(efilter.conditions.all())
        cond_type_id = condition_handler.RelationSubFilterConditionHandler.type_id
        self.assertEqual(cond_type_id, ReportRelationSubFilterConditionHandler.type_id)
        self.assertEqual(cond_type_id, condition.type)
        self.assertIsInstance(condition.handler, ReportRelationSubFilterConditionHandler)
        self.assertEqual(rtype.id, condition.name)
        self.assertDictEqual(
            {'has': False, 'filter_id': orga_efilter.id},
            condition.value,
        )

    def test_edit(self):
        user = self.login_as_standard(
            allowed_apps=['reports', 'creme_core'],
            listable_models=[Report],
        )

        efilter = EntityFilter.objects.create(
            id='test-reports_filter',
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
            user=user,
        )
        self.assertGET409(reverse('creme_core__edit_efilter', args=(efilter.id,)))

        url = efilter.get_edit_absolute_url()
        self.assertEqual(reverse('reports__edit_efilter', args=(efilter.id,)), url)

        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/forms/entity-filter.html')

        context1 = response1.context
        self.assertEqual(
            _('Edit «{object}»').format(object=efilter), context1.get('title'),
        )

        with self.assertNoException():
            submit_label = context1['submit_label']

            # NB: difficult to test the content in a robust way (depends on the DB config)
            context1['help_message']  # NOQA

        self.assertEqual(_('Save the modified filter'), submit_label)

        # ---
        name = f'{efilter.name} (edited)'
        field_operator = operators.IEQUALS
        field_name = 'last_name'
        field_value = 'Ikari'
        callback_url = reverse('reports__list_reports')
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'name': name,
                'use_or': 'True',

                'regularfieldcondition': self._build_rfields_data(
                    operator=field_operator,
                    name=field_name,
                    value=field_value,
                ),

                # 'callback_url': callback_url, TODO?
                'cancel_url': callback_url,
            },
        )
        self.assertNoFormError(response2)

        efilter = self.refresh(efilter)
        self.assertEqual(EF_REPORTS, efilter.filter_type)
        self.assertEqual(name,       efilter.name)
        self.assertIs(efilter.is_custom, True)
        self.assertIsNone(efilter.user)

        condition = self.get_alone_element(efilter.conditions.order_by('id'))
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(field_name, condition.name)
        self.assertDictEqual(
            {'operator': field_operator, 'values': [field_value]},
            condition.value,
        )

        self.assertRedirects(response2, callback_url)

    def test_edit__subfilters(self):
        self.login_as_root()

        sub_efilter1 = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
        )
        sub_efilter2 = EntityFilter.objects.create(
            id='reports-contacts_filter1',
            name='Public Contact filter (only reports)',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )

        efilter = EntityFilter.objects.create(
            id='reports-filter_to_edit',
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        ).set_conditions([
            condition_handler.SubFilterConditionHandler.build_condition(
                sub_efilter1, filter_type=EF_REPORTS,
            ),
        ])

        url = efilter.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            sub_filters_f = response1.context['form'].fields['reportsubfiltercondition']
            sub_filters_choices = [*sub_filters_f.choices]

        self.assertInChoices(
            value=sub_efilter1.id, label=str(sub_efilter1), choices=sub_filters_choices,
        )
        self.assertInChoices(
            value=sub_efilter2.id, label=str(sub_efilter2), choices=sub_filters_choices,
        )

        self.assertNotInChoices(value=efilter.id, choices=sub_filters_choices)

        self.assertEqual([sub_efilter1.id], sub_filters_f.initial)

    def test_edit_popup(self):
        user = self.login_as_standard(allowed_apps=['reports', 'creme_core'])

        efilter = EntityFilter.objects.create(
            id='test-reports_filter',
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
            user=user,
        )
        url = self._build_edit_popup_url(efilter)

        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context1 = response1.context
        self.assertEqual(
            _('Edit «{object}»').format(object=efilter), context1.get('title'),
        )

        with self.assertNoException():
            submit_label = context1['submit_label']

            # NB: difficult to test the content in a robust way (depends on the DB config)
            context1['help_message']  # NOQA

        self.assertEqual(_('Save the filter'), submit_label)

        # ---
        name = f'{efilter.name} (edited)'
        field_operator = operators.IEQUALS
        field_name = 'last_name'
        field_value = 'Ikari'
        response2 = self.client.post(
            url,
            data={
                'name': name,
                'use_or': 'True',

                'regularfieldcondition': self._build_rfields_data(
                    operator=field_operator,
                    name=field_name,
                    value=field_value,
                ),
            },
        )
        self.assertNoFormError(response2)

        efilter = self.refresh(efilter)
        self.assertEqual(EF_REPORTS, efilter.filter_type)
        self.assertEqual(name,       efilter.name)
        self.assertIs(efilter.is_custom, True)
        self.assertIsNone(efilter.user)

        condition = self.get_alone_element(efilter.conditions.order_by('id'))
        self.assertEqual(
            condition_handler.RegularFieldConditionHandler.type_id,
            condition.type,
        )
        self.assertEqual(field_name, condition.name)
        self.assertDictEqual(
            {'operator': field_operator, 'values': [field_value]},
            condition.value,
        )

    def test_edit__private(self):
        self.login_as_root()
        other = self.create_user()

        efilter = EntityFilter.objects.create(
            id='reports-test_edit__private',
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
            is_private=True,
            user=other,
        )
        self.assertGET403(efilter.get_edit_absolute_url())
        self.assertGET403(self._build_edit_popup_url(efilter))

    def test_edit__permissions01(self):
        self.login_as_standard(allowed_apps=['reports'])
        efilter = EntityFilter.objects.create(
            id='reports-test_edit__permissions01',
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )
        self.assertGET403(efilter.get_edit_absolute_url())
        self.assertGET403(self._build_edit_popup_url(efilter))

    def test_edit__permissions02(self):
        self.login_as_standard(allowed_apps=['creme_core'])
        efilter = EntityFilter.objects.create(
            id='reports-test_edit__permissions02',
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )
        self.assertGET403(efilter.get_edit_absolute_url())

    def test_delete(self):
        user = self.login_as_standard(
            allowed_apps=['reports', 'creme_core'], listable_models=[Report],
        )

        efilter = EntityFilter.objects.create(
            id='reports-test_delete',
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
            user=user,
        )
        url = efilter.get_delete_absolute_url()
        self.assertEqual(reverse('reports__delete_efilter', args=(efilter.id,)), url)

        response = self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(efilter)
        self.assertRedirects(response, reverse('reports__list_reports'))

    def test_delete__not_custom(self):
        "Not custom -> can not delete."
        self.login_as_root()

        efilter = EntityFilter.objects.create(
            id='reports-test_delete__not_custom',
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
            is_custom=False,
        )
        self.assertPOST403(efilter.get_delete_absolute_url(), follow=True)
        self.assertStillExists(efilter)

    def test_delete__permissions01(self):
        self.login_as_standard(allowed_apps=['reports'])  # 'creme_core'

        efilter = EntityFilter.objects.create(
            id='reports-test_delete__permissions01',
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )
        self.assertPOST403(efilter.get_delete_absolute_url(), follow=True)
        self.assertStillExists(efilter)

    def test_delete__permissions02(self):
        self.login_as_standard(allowed_apps=['creme_core'])  # 'reports'

        efilter = EntityFilter.objects.create(
            id='reports-test_delete__permissions02',
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )
        self.assertPOST403(efilter.get_delete_absolute_url(), follow=True)
        self.assertStillExists(efilter)

    def test_filter_choices(self):
        self.login_as_root()

        efilter = EntityFilter.objects.create(
            pk='reports-test_filter_choices', name='Contacts',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )

        response = self.assertGET200(
            reverse(
                'creme_core__efilters',
                query={'ct_id': efilter.entity_type_id, 'type': EF_REPORTS},
            )
        )
        self.assertListEqual(
            [[efilter.id, f'{efilter.name} [{_("Report")}]']],
            response.json(),
        )
