from datetime import date
from functools import partial
from json import dumps as json_dump
from urllib.parse import urlencode

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext, pgettext

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    EF_REGULAR,
    EntityFilterRegistry,
    entity_filter_registries,
    operands,
    operators,
)
from creme.creme_core.core.entity_filter.condition_handler import (
    CustomFieldConditionHandler,
    DateCustomFieldConditionHandler,
    DateRegularFieldConditionHandler,
    PropertyConditionHandler,
    RegularFieldConditionHandler,
    RelationConditionHandler,
    RelationSubFilterConditionHandler,
    SubFilterConditionHandler,
)
from creme.creme_core.models import (
    CremePropertyType,
    CremeUser,
    CustomEntityType,
    CustomField,
    EntityFilter,
    EntityFilterCondition,
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeFolder,
    FakeImage,
    FakeOrganisation,
    FakeProduct,
    FakeReport,
    HeaderFilter,
    RelationType,
    SettingValue,
)
from creme.creme_core.setting_keys import global_filters_edition_key
from creme.creme_core.utils.translation import smart_model_verbose_name
from creme.creme_core.views import entity_filter as efilter_views

from ..base import CremeTestCase
from .base import BrickTestCaseMixin, ButtonTestCaseMixin


class EntityFilterViewsTestCase(BrickTestCaseMixin,
                                ButtonTestCaseMixin,
                                CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        get_ct = ContentType.objects.get_for_model
        cls.ct_contact = get_ct(FakeContact)
        cls.ct_orga    = get_ct(FakeOrganisation)

    @staticmethod
    def _build_add_url(ct):
        return reverse('creme_core__create_efilter', args=(ct.id,))

    @staticmethod
    def _build_get_ct_url(rtype):
        return reverse('creme_core__ctypes_compatible_with_rtype_as_choices', args=(rtype.id,))

    @staticmethod
    def _build_get_filter_url(ct, all_=None, types=None):
        params = {'ct_id': ct.id}

        if all_ is not None:
            params['all'] = all_

        if types is not None:
            params['type'] = types

        return reverse('creme_core__efilters') + '?' + urlencode(params, doseq=True)

    @staticmethod
    def _build_rfields_data(name, operator, value):
        return json_dump([{
            'field':    {'name': name},
            'operator': {'id': str(operator)},
            'value':    value,
        }])

    @staticmethod
    def _build_rdatefields_data(name, type, start, end):
        return json_dump([{
            'field': {'name': name, 'type': 'date'},
            'range': {'type': type, 'start': start, 'end': end},
        }])

    @staticmethod
    def _build_cfields_data(cfield_id, operator, value):
        return json_dump([{
            'field':    {'id': str(cfield_id)},
            'operator': {'id': str(operator)},
            'value':    value,
        }])

    @staticmethod
    def _build_cdatefields_data(cfield_id, type):
        return json_dump([{'field': str(cfield_id), 'range': {'type': type}}])

    @staticmethod
    def _build_relations_data(rtype_id):
        return json_dump([{'has': True, 'rtype': rtype_id, 'ctype': 0, 'entity': None}])

    @staticmethod
    def _build_properties_data(has, ptype_id):
        return json_dump([{'has': has, 'ptype': ptype_id}])

    @staticmethod
    def _build_subfilters_data(rtype_id, ct_id, efilter_id):
        return json_dump([{
            'rtype': rtype_id, 'has': False, 'ctype': ct_id, 'filter': efilter_id,
        }])

    def _create_rtype(self):
        return RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving',
        ).symmetric(
            id='test-object_love',  predicate='Is loved by',
        ).get_or_create()[0]

    def test_detailview__regular(self):
        user = self.login_as_root_and_get()
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter_detailview__regular', name='My Filter',
            model=FakeContact, is_custom=True,
        )
        parent_filter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter04', name='Parent Filter', model=FakeContact, is_custom=True,
            conditions=[SubFilterConditionHandler.build_condition(efilter)],
        )

        create_report = partial(FakeReport.objects.create, user=user, ctype=efilter.entity_type)
        report1 = create_report(name='My report with filter', efilter=efilter)
        report2 = create_report(name='My simple report')

        response = self.assertGET200(efilter.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/detail/entity-filter.html')
        self.assertEqual(
            reverse('creme_core__reload_efilter_bricks', args=(efilter.id,)),
            response.context.get('bricks_reload_url'),
        )

        with self.assertNoException():
            ctxt_efilter = response.context['object']
        self.assertEqual(efilter, ctxt_efilter)

        tree = self.get_html_tree(response.content)
        config_button_node = self.get_alone_element(
            self.iter_button_nodes(self.get_global_buttons_node(tree))
        )
        self.assertEqual('a', config_button_node.tag)
        self.assertEqual(reverse('creme_config__efilters'), config_button_node.attrib.get('href'))

        self.get_brick_node(tree, efilter_views.EntityFilterBarHatBrick)
        self.get_brick_node(tree, efilter_views.EntityFilterInfoBrick)

        parents_node = self.get_brick_node(tree, efilter_views.EntityFilterParentsBrick)
        self.assertBrickTitleEqual(
            parents_node,
            count=1,
            title='{count} Parent filter',
            plural_title='{count} Parent filters',
        )
        self.assertInstanceLink(parents_node, parent_filter)

        reports_brick_node = self.get_brick_node(
            tree, 'linked_to_efilter-creme_core-fakereport-efilter',
        )
        self.assertEqual(
            _('Filter used by %(count)s %(model)s (field «%(field)s»)') % {
                'count': 1,
                'model': smart_model_verbose_name(model=FakeReport, count=1),
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

    def test_detailview__credentials(self):
        self.login_as_root()
        efilter = EntityFilter.objects.create(
            id='test-filter_detailview__credentials',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )
        self.assertEqual('', efilter.get_absolute_url())
        self.assertGET409(reverse('creme_core__efilter', args=(efilter.id,)))

    def test_reload_bricks_for_detailview__parents(self):
        self.login_as_root()
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter_detailview__parents', name='My Filter',
            model=FakeContact, is_custom=True,
        )
        parent_filter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter04', name='Parent Filter', model=FakeContact, is_custom=True,
            conditions=[SubFilterConditionHandler.build_condition(efilter)],
        )

        brick_id = efilter_views.EntityFilterParentsBrick.id
        response = self.assertGET200(
            reverse('creme_core__reload_efilter_bricks', args=(efilter.id,)),
            data={'brick_id': brick_id},
        )

        with self.assertNoException():
            results = response.json()

        self.assertIsList(results, length=1)

        result = results[0]
        self.assertIsList(result, length=2)
        self.assertEqual(brick_id, result[0])

        document = self.get_html_tree(result[1])
        brick_node = self.get_brick_node(document, brick_id)
        self.assertInstanceLink(brick_node, parent_filter)

    def test_linked_entities_parse_brick_id(self):
        parse = efilter_views.EntityFilterLinkedEntitiesBrick.parse_brick_id
        self.assertTupleEqual(
            (FakeReport, FakeReport._meta.get_field('efilter')),
            parse('linked_to_efilter-creme_core-fakereport-efilter'),
        )

        self.assertIsNone(parse('linked_to_efilter-creme_core-fakereport-efilter-extra_part'))
        self.assertIsNone(parse('invalid_prefix-creme_core-fakereport-efilter'))

        self.assertIsNone(parse('linked_to_efilter-invalid_app-fakereport-efilter'))
        self.assertIsNone(parse('linked_to_efilter-creme_core-invalid_model-efilter'))
        self.assertIsNone(parse('linked_to_efilter-creme_core-fakereport-invalid_field'))

        # Not entity
        self.assertIsNone(parse('linked_to_efilter-creme_core-entityfiltercondition-filter'))

        # Not FK
        self.assertIsNone(parse('linked_to_efilter-creme_core-fakereport-name'))

        # Not FK to EntityFilter
        self.assertIsNone(parse('linked_to_efilter-creme_core-fakereport-ctype'))

    def test_reload_bricks_for_detailview__linked_entities(self):
        user = self.login_as_root_and_get()
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter_detailview01', name='My Filter', model=FakeContact, is_custom=True,
        )
        create_report = partial(FakeReport.objects.create, user=user, ctype=efilter.entity_type)
        report1 = create_report(name='My report with filter', efilter=efilter)
        report2 = create_report(name='My simple report')

        url = reverse('creme_core__reload_efilter_bricks', args=(efilter.id,))
        brick_id = 'linked_to_efilter-creme_core-fakereport-efilter'
        response = self.assertGET200(url, data={'brick_id': brick_id})

        with self.assertNoException():
            results = response.json()

        self.assertIsList(results, length=1)

        result = results[0]
        self.assertIsList(result, length=2)
        self.assertEqual(brick_id, result[0])

        document = self.get_html_tree(result[1])
        brick_node = self.get_brick_node(document, brick_id)
        self.assertInstanceLink(brick_node, report1)
        self.assertNoInstanceLink(brick_node, report2)

        # ---
        self.assertGET404(
            url, data={'brick_id': 'linked_to_efilter-creme_core-fakereport-invalid'},
        )

    def test_reload_bricks_for_detailview__credentials(self):
        self.login_as_root()
        efilter = EntityFilter.objects.create(
            id='test-filter_detailview__credentials',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )
        self.assertGET404(
            reverse('creme_core__reload_efilter_bricks', args=(efilter.id,)),
            data={'brick_id': efilter_views.EntityFilterParentsBrick.id},
        )

    def test_detailview__private(self):
        user = self.login_as_root_and_get()
        other = self.create_user()
        efilter = EntityFilter.objects.create(
            id='test-filter_detailview__private',
            entity_type=FakeContact,
            is_private=True,
            user=other,
        )
        detail_url = efilter.get_absolute_url()
        self.assertGET403(detail_url)

        reload_uri = reverse('creme_core__reload_efilter_bricks', args=(efilter.id,))
        reload_data = {'brick_id': efilter_views.EntityFilterParentsBrick.id}
        self.assertGET403(reload_uri, data=reload_data)

        # ---
        efilter.user = user
        efilter.save()
        self.assertGET200(detail_url)
        self.assertGET200(reload_uri, data=reload_data)

    @override_settings(FILTERS_INITIAL_PRIVATE=False)
    def test_create01(self):
        "Check app credentials."
        user = self.login_as_standard(allowed_apps=['documents'], listable_models=[FakeContact])

        self.assertFalse(
            SettingValue.objects.get_4_key(global_filters_edition_key).value
        )

        ct = self.ct_contact
        self.assertFalse(EntityFilter.objects.filter(entity_type=ct).count())

        uri = self._build_add_url(ct)
        self.assertGET403(uri)

        # ---
        role = user.role
        role.allowed_apps = ['documents', 'creme_core']
        role.save()
        response1 = self.assertGET200(uri)
        self.assertTemplateUsed(response1, 'creme_core/forms/entity-filter.html')
        self.assertContains(
            response1,
            _('Create a filter for «%(ctype)s»') % {'ctype': 'Test Contact'},
        )

        context = response1.context
        with self.assertNoException():
            form = context['form']
            user_f = form.fields['user']
            # NB: difficult to test the content in a robust way (depends on the DB config)
            context['help_message']  # NOQA

        self.assertIs(form.initial.get('is_private'), False)
        self.assertEqual(
            _(
                'If you assign an owner, only the owner can edit or delete the filter; '
                'filters without owner can only be edited/deleted by superusers'
            ),
            user_f.help_text,
        )

        # TODO: test widgets instead
#        with self.assertNoException():
#            fields = response.context['form'].fields
#            cf_f = fields['customfields_conditions']
#            dcf_f = fields['datecustomfields_conditions']
#
#        self.assertEqual('', cf_f.initial)
#        self.assertEqual('', dcf_f.initial)
#        self.assertEqual(_('No custom field at present.'), cf_f.help_text)
#        self.assertEqual(_('No date custom field at present.'), dcf_f.help_text)

        # ---
        name = 'Filter 01'
        operator = operators.IEQUALS
        field_name = 'last_name'
        value = 'Ikari'
        response2 = self.client.post(
            uri, follow=True,
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

        efilter = self.get_alone_element(EntityFilter.objects.filter(entity_type=ct))
        self.assertEqual(name, efilter.name)
        self.assertTrue(efilter.is_custom)
        self.assertFalse(efilter.is_private)
        self.assertIsNone(efilter.user)
        self.assertFalse(efilter.use_or)

        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(field_name,                           condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

        lv_url = FakeContact.get_lv_absolute_url()
        self.assertRedirects(response2, lv_url)

        # --
        context3 = self.assertGET200(lv_url).context
        selected_efilter = context3['entity_filters'].selected
        self.assertIsInstance(selected_efilter, EntityFilter)
        self.assertEqual(efilter.id, selected_efilter.id)
        self.assertEqual(efilter.id, context3['list_view_state'].entity_filter_id)

    def test_create02(self):
        user = self.login_as_root_and_get()
        ct = self.ct_orga

        setting_value = SettingValue.objects.get_4_key(global_filters_edition_key)
        setting_value.value = True
        setting_value.save()

        # Can not be a simple sub-filter (bad content type)
        relsubfilfer = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )

        subfilter = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.GT,
                    field_name='capital', values=[10000],
                ),
            ],
        )

        rtype = self._create_rtype()
        ptype = CremePropertyType.objects.create(text='Kawaii')

        create_cf = partial(CustomField.objects.create, content_type=ct)
        custom_field = create_cf(name='Profits',        field_type=CustomField.INT)
        datecfield   = create_cf(name='Last gathering', field_type=CustomField.DATETIME)

        url = self._build_add_url(ct)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            user_f = fields['user']
            sb_f = fields['subfiltercondition']

        self.assertEqual(
            _(
                'If you assign an owner, only the owner can edit or delete the filter; '
                'filters without owner can be edited/deleted by all users'
            ),
            user_f.help_text,
        )

        subfilter_ids = {f.id for f in sb_f.queryset}
        self.assertIn(subfilter.id, subfilter_ids)
        self.assertNotIn(relsubfilfer.id, subfilter_ids)

        # ---
        name = 'Filter 03'
        field_operator = operators.CONTAINS
        field_name = 'name'
        field_value = 'NERV'
        date_field_name = 'creation_date'
        daterange_type = 'current_year'
        cfield_operator = operators.GT
        cfield_value = 10000
        datecfield_rtype = 'previous_quarter'
        response2 = self.client.post(
            url, follow=True,
            data={
                'name':        name,
                'user':        user.id,
                'is_private': 'on',
                'use_or':     'True',

                'regularfieldcondition': self._build_rfields_data(
                    operator=field_operator,
                    name=field_name,
                    value=field_value,
                ),
                'dateregularfieldcondition': self._build_rdatefields_data(
                    type=daterange_type,
                    start='', end='',
                    name=date_field_name,
                ),
                'customfieldcondition': self._build_cfields_data(
                    cfield_id=custom_field.id,
                    operator=cfield_operator,
                    value=cfield_value,
                ),
                'datecustomfieldcondition': self._build_cdatefields_data(
                    cfield_id=datecfield.id,
                    type=datecfield_rtype,
                ),
                'relationcondition': self._build_relations_data(rtype.id),
                'relationsubfiltercondition': self._build_subfilters_data(
                    rtype_id=rtype.symmetric_type_id,
                    ct_id=self.ct_contact.id,
                    efilter_id=relsubfilfer.id,
                ),
                'propertycondition': self._build_properties_data(
                    has=True,
                    ptype_id=ptype.id,
                ),
                'subfiltercondition': [subfilter.id],
            },
        )
        self.assertNoFormError(response2)

        efilter = self.get_object_or_fail(EntityFilter, name=name)
        self.assertEqual(user.id, efilter.user.id)
        self.assertIs(efilter.is_private, True)
        self.assertIs(efilter.use_or, True)

        conditions = efilter.conditions.order_by('id')
        self.assertEqual(8, len(conditions))
        iter_conds = iter(conditions)

        condition = next(iter_conds)
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(field_name,                           condition.name)
        self.assertDictEqual(
            {'operator': field_operator, 'values': [field_value]},
            condition.value,
        )

        condition = next(iter_conds)
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(date_field_name,                          condition.name)
        self.assertDictEqual({'name': daterange_type}, condition.value)

        condition = next(iter_conds)
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(custom_field.uuid),              condition.name)
        self.assertDictEqual(
            {
                'operator': cfield_operator,
                'rname': 'customfieldinteger',
                'values': [str(cfield_value)],
            },
            condition.value,
        )

        condition = next(iter_conds)
        self.assertEqual(DateCustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(datecfield.uuid),                    condition.name)
        self.assertDictEqual(
            {'rname': 'customfielddatetime', 'name': datecfield_rtype},
            condition.value,
        )

        condition = next(iter_conds)
        self.assertEqual(RelationConditionHandler.type_id, condition.type)
        self.assertEqual(rtype.id,                         condition.name)
        self.assertDictEqual({'has': True}, condition.value)

        condition = next(iter_conds)
        self.assertEqual(RelationSubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(rtype.symmetric_type_id,                   condition.name)
        self.assertDictEqual(
            {'has': False, 'filter_id': relsubfilfer.id},
            condition.value,
        )

        condition = next(iter_conds)
        self.assertEqual(PropertyConditionHandler.type_id, condition.type)
        self.assertEqual(str(ptype.uuid), condition.name)
        self.assertDictEqual({'has': True}, condition.value)

        condition = next(iter_conds)
        self.assertEqual(SubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(subfilter.id,                      condition.name)

    def test_create__session_kept(self):
        "Existing state session is kept."
        self.login_as_root()

        lv_url = FakeOrganisation.get_lv_absolute_url()
        ct = self.ct_orga

        # Set a header filter in the session (should be kept)
        hfilter1 = HeaderFilter.objects.filter(entity_type=ct).first()
        self.assertIsNotNone(hfilter1)
        hfilter2 = HeaderFilter.objects.proxy(
            id='creme_core-tests_views_entity_filter_test_create03',
            name='Ze last FakeContact view',
            model=FakeOrganisation,
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'email'),
            ],
        ).get_or_create()[0]
        self.assertGreater(hfilter2.name, hfilter1.name)

        response = self.assertPOST200(lv_url, data={'hfilter': hfilter2.id})
        self.assertEqual(hfilter2.id, response.context['list_view_state'].header_filter_id)

        # --
        name = 'Filter "nerv"'
        response = self.client.post(
            self._build_add_url(ct), follow=True,
            data={
                'name': name,
                'use_or': 'False',
                'regularfieldcondition': self._build_rfields_data(
                    operator=operators.CONTAINS,
                    name='name',
                    value='NERV',
                ),
            },
        )
        self.assertNoFormError(response)
        self.assertRedirects(response, lv_url)

        efilter = self.get_object_or_fail(EntityFilter, entity_type=ct, name=name)

        self.assertRedirects(response, lv_url)

        # --
        context = self.assertGET200(lv_url).context
        selected_efilter = context['entity_filters'].selected
        self.assertIsInstance(selected_efilter, EntityFilter)
        self.assertEqual(efilter.id, selected_efilter.id)

        lvs = context['list_view_state']
        self.assertEqual(efilter.id, lvs.entity_filter_id)
        self.assertEqual(hfilter2.id, lvs.header_filter_id)

    def test_create__date_subfield(self):
        "Date sub-field + callback_url."
        self.login_as_root()

        ct = self.ct_contact
        name = 'Filter img'
        field_name = 'image__created'
        daterange_type = 'previous_year'
        callback_url = FakeOrganisation.get_lv_absolute_url()
        response = self.client.post(
            self._build_add_url(ct), follow=True,
            data={
                'name': name,
                'use_or': 'False',
                'dateregularfieldcondition': self._build_rdatefields_data(
                    type=daterange_type,
                    name=field_name,
                    start='', end='',
                ),
                'cancel_url': callback_url,
            },
        )
        self.assertNoFormError(response)

        efilter = self.get_object_or_fail(EntityFilter, entity_type=ct, name=name)

        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(field_name,                               condition.name)
        self.assertDictEqual({'name': daterange_type}, condition.value)

        self.assertRedirects(response, callback_url)

    def test_create__no_condition(self):
        "Error: no conditions of any type."
        user = self.login_as_root_and_get()

        response = self.client.post(
            self._build_add_url(self.ct_orga),
            data={
                'name': 'Filter 01',
                'user': user.id,
                'use_or': 'False',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_('The filter must have at least one condition.'),
        )

    def test_create__private_belonging_to_other(self):
        "Cannot create a private filter for another user (but OK with one of our teams)."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        my_team = self.create_team('TeamTitan', user, other_user)
        a_team = self.create_team('A-team', other_user)

        name = 'Katsuragi'

        def post(owner):
            return self.assertPOST200(
                self._build_add_url(ct=self.ct_contact), follow=True,
                data={
                    'name':       name,
                    'user':       owner.id,
                    'use_or':     'False',
                    'is_private': 'on',

                    'regularfieldcondition': self._build_rfields_data(
                        operator=operators.EQUALS,
                        name='last_name',
                        value='Katsuragi',
                    ),
                },
            )

        response1 = post(other_user)
        msg = _('A private filter must belong to you (or one of your teams).')
        self.assertFormError(response1.context['form'], field='user', errors=msg)

        response2 = post(a_team)
        self.assertFormError(response2.context['form'], field='user', errors=msg)

        response3 = post(my_team)
        self.assertNoFormError(response3)
        self.get_object_or_fail(EntityFilter, name=name)

    def test_create__staff(self):
        "A staff user can create a private filter for another user."
        user = self.login_as_super(is_staff=True)
        other_user = self.get_root_user()
        team = self.create_team('A-team', user)

        subfilter = EntityFilter.objects.smart_update_or_create(
            'creme_core-subfilter', 'Misato', model=FakeContact,
            user=team, is_private=True, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name', values=['Misato'],
                ),
            ],
        )
        self.assertTrue(subfilter.can_view(user)[0])
        self.assertFalse(subfilter.can_view(other_user)[0])

        name = 'Katsuragi'
        data = {
            'name':       name,
            'user':       other_user.id,
            'use_or':     'False',
            'is_private': 'on',

            'regularfieldcondition': self._build_rfields_data(
                operator=operators.EQUALS,
                name='last_name',
                value='Katsuragi',
            ),
        }

        url = self._build_add_url(ct=self.ct_contact)
        response = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                'subfiltercondition': [subfilter.id],
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=ngettext(
                'A private filter can only use public sub-filters, & '
                'private sub-filters which belong to the same user and his teams.'
                ' So this private sub-filter cannot be chosen: {}',
                'A private filter can only use public sub-filters, & '
                'private sub-filters which belong to the same user and his teams.'
                ' So these private sub-filters cannot be chosen: {}',
                1
            ).format(subfilter.name),
        )

        response = self.client.post(
            self._build_add_url(ct=self.ct_contact), follow=True, data=data,
        )
        self.assertNoFormError(response)
        self.get_object_or_fail(EntityFilter, name=name)

    def test_create__not_entity_ctype(self):
        "Not an Entity type."
        self.login_as_root()
        self.assertGET409(self._build_add_url(ContentType.objects.get_for_model(RelationType)))

    @override_settings(FILTERS_INITIAL_PRIVATE=True)
    def test_create__initial_private(self):
        "Use FILTERS_INITIAL_PRIVATE."
        self.login_as_root()

        response = self.assertGET200(self._build_add_url(self.ct_contact))
        self.assertIs(self.get_form_or_fail(response).initial.get('is_private'), True)

    def test_create__missing_lv_absolute_url(self):
        "Missing get_lv_absolute_url() classmethod."
        with self.assertRaises(AttributeError):
            FakeProduct.get_lv_absolute_url()

        user = self.login_as_root_and_get()

        response = self.client.post(
            self._build_add_url(ContentType.objects.get_for_model(FakeProduct)),
            data={
                'name':   'Filter 01',
                'user':   user.id,
                'use_or': 'False',
                'regularfieldcondition': self._build_rfields_data(
                    operator=operators.EQUALS,
                    name='name',
                    value='Product',
                ),
            },
        )
        self.assertNoFormError(response, status=302)
        self.assertRedirects(response, '/')

    def test_create__creatorfield_fk_filter(self):
        user = self.login_as_root_and_get()
        folder = FakeFolder.objects.create(title='Folder 01', user=user)

        response = self.client.post(
            self._build_add_url(ContentType.objects.get_for_model(FakeDocument)),
            data={
                'name':   'Filter 01',
                'user':   user.id,
                'use_or': 'True',
                'regularfieldcondition': self._build_rfields_data(
                    operator=operators.EQUALS,
                    name='linked_folder',
                    value=str(folder.id),
                ),
            },
        )
        self.assertNoFormError(response, status=302)

        efilter = self.get_object_or_fail(EntityFilter, name='Filter 01')
        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual('linked_folder',                      condition.name)
        self.assertDictEqual(
            {
                'operator': operators.EQUALS,
                'values':   [str(folder.id)],
            },
            condition.value,
        )

    def test_create__currentuser_filter(self):
        user = self.login_as_root_and_get()
        operand_id = operands.CurrentUserOperand.type_id

        response = self.client.post(
            self._build_add_url(self.ct_orga),
            data={
                'name':   'Filter 01',
                'user':   user.id,
                'use_or': 'True',
                'regularfieldcondition': self._build_rfields_data(
                    operator=operators.EQUALS,
                    name='user',
                    value=operand_id,
                ),
            },
        )
        self.assertNoFormError(response, status=302)

        efilter = self.get_object_or_fail(EntityFilter, name='Filter 01')
        self.assertEqual(user.id, efilter.user.id)
        self.assertIs(efilter.use_or, True)

        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual('user',                               condition.name)
        self.assertDictEqual(
            {
                'operator': operators.EQUALS,
                'values':   [operand_id],
            },
            condition.value,
        )

    def test_create__custom_entity(self):
        self.login_as_root()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Shop'
        ce_type.plural_name = 'Shops'
        ce_type.save()

        model = ce_type.entity_model
        # Avoid an error message ("no view...")
        HeaderFilter.objects.proxy(
            id='creme_core-userhf_creme_core-customeentity1-1',
            name='Shop lite view', model=model,
            cells=[(EntityCellRegularField, 'name')],
        ).get_or_create()

        ct = ContentType.objects.get_for_model(model)
        name = 'Acmes'
        self.assertNoFormError(self.client.post(
            self._build_add_url(ct),
            follow=True,
            data={
                'name': name,
                'use_or': 'False',
                'regularfieldcondition': self._build_rfields_data(
                    operator=operators.STARTSWITH, name='name', value='Acme',
                ),
            },
        ))

    def test_create_subfilters_n_private01(self):
        "Cannot choose a private sub-filter which belongs to another user."
        user = self.login_as_root_and_get()

        subfilter = EntityFilter.objects.smart_update_or_create(
            'creme_core-subfilter', 'Misato', model=FakeContact,
            user=self.create_user(), is_private=True, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name', values=['Misato'],
                ),
            ],
        )

        name = 'Misato Katsuragi'
        data = {
            'name':       name,
            'user':       user.id,
            'use_or':     'False',
            'is_private': 'on',

            'regularfieldcondition': self._build_rfields_data(
                operator=operators.EQUALS,
                name='last_name',
                value='Katsuragi',
            ),
        }

        def post(post_data):
            response = self.assertPOST200(
                self._build_add_url(ct=self.ct_contact),
                follow=True, data=post_data,
            )

            return self.get_form_or_fail(response)

        form1 = post({**data, 'subfiltercondition': [subfilter.id]})
        self.assertFormError(
            form1,
            field='subfiltercondition',
            errors=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': subfilter.id},
        )

        # ---
        rtype = self._create_rtype()
        form2 = post({
            **data,
            'relationsubfiltercondition': self._build_subfilters_data(
                rtype_id=rtype.id,
                ct_id=self.ct_contact.id,
                efilter_id=subfilter.id,
            ),
        })
        self.assertFormError(
            form2, field='relationsubfiltercondition', errors=_('This filter is invalid.'),
        )

    def test_create_subfilters_n_private02(self):
        """Private sub-filter (owned by a regular user):
            - OK in a private filter (with the same owner).
            - Error in a public filter.
        """
        user = self.login_as_root_and_get()
        team = self.create_team('A-team', user, self.create_user())

        subfilter1 = EntityFilter.objects.smart_update_or_create(
            'creme_core-subfilter1', 'Misato', model=FakeContact,
            user=user, is_private=True, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name', values=['Misato'],
                ),
            ],
        )
        subfilter2 = EntityFilter.objects.smart_update_or_create(
            'creme_core-subfilter2', 'Katsuragi', model=FakeContact,
            user=team, is_private=True, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='last_name', values=['Katsuragi'],
                ),
            ],
        )

        name = 'Misato Katsuragi'

        def post(is_private):
            return self.client.post(
                self._build_add_url(ct=self.ct_contact), follow=True,
                data={
                    'name':       name,
                    'user':       user.id,
                    'use_or':     'False',
                    'is_private': is_private,

                    'regularfieldcondition': self._build_rfields_data(
                        operator=operators.EQUALS,
                        name='last_name',
                        value='Katsuragi',
                    ),
                    'subfiltercondition': [subfilter1.id, subfilter2.id],
                },
            )

        response1 = post('')
        self.assertEqual(200, response1.status_code)
        self.assertFormError(
            response1.context['form'],
            field=None,
            errors=ngettext(
                'Your filter must be private in order to use this private sub-filter: {}',
                'Your filter must be private in order to use these private sub-filters: {}',
                2
            ).format(f'{subfilter2.name}, {subfilter1.name}'),
        )

        # ---
        response2 = post('on')
        self.assertNoFormError(response2)
        self.get_object_or_fail(EntityFilter, name=name)

    def test_create_subfilters_n_private03(self):
        """Private filter owned by a team:
            - OK with a public sub-filter.
            - OK with a private sub-filter which belongs to the team.
            - Error with a private sub-filter which does not belong to the team.
        """
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        team = self.create_team('A-team', user, other_user)
        other_team = self.create_team('TeamTitan', user, other_user)

        subfilter1 = EntityFilter.objects.smart_update_or_create(
            'creme_core-subfilter1', 'Miss', model=FakeContact,
            is_private=False, is_custom=True,
        )

        def create_subfilter(idx, owner):
            return EntityFilter.objects.smart_update_or_create(
                f'creme_core-subfilter{idx}',
                f'Misato #{idx}', model=FakeContact,
                user=owner, is_private=True, is_custom=True,
                conditions=[
                    RegularFieldConditionHandler.build_condition(
                        model=FakeContact,
                        operator=operators.EQUALS,
                        field_name='first_name', values=['Misato'],
                    ),
                ],
            )

        subfilter2 = create_subfilter(2, team)
        subfilter3 = create_subfilter(4, other_team)

        name = 'Misato Katsuragi'

        def post(*subfilters):
            return self.client.post(
                self._build_add_url(ct=self.ct_contact), follow=True,
                data={
                    'name':       name,
                    'user':       team.id,
                    'use_or':     'False',
                    'is_private': 'on',

                    'regularfieldcondition': self._build_rfields_data(
                        operator=operators.EQUALS,
                        name='last_name',
                        value='Katsuragi',
                    ),
                    'subfiltercondition': [sf.id for sf in subfilters],
                },
            )

        response1 = post(subfilter3)
        self.assertEqual(200, response1.status_code)
        self.assertFormError(
            response1.context['form'],
            field=None,
            errors=ngettext(
                'A private filter which belongs to a team can only use public sub-filters & '
                'private sub-filters which belong to this team.'
                ' So this private sub-filter cannot be chosen: {}',
                'A private filter which belongs to a team can only use public sub-filters & '
                'private sub-filters which belong to this team.'
                ' So these private sub-filters cannot be chosen: {}',
                1
            ).format(subfilter3.name),
        )

        # ---
        response2 = post(subfilter1, subfilter2)
        self.assertNoFormError(response2)
        self.get_object_or_fail(EntityFilter, name=name)

    def test_non_filterable_fields01(self):
        "FileFields cannot be filtered."
        self.login_as_root()

        with self.assertNoException():
            FakeDocument._meta.get_field('filedata')

        ct = ContentType.objects.get_for_model(FakeDocument)
        response = self.client.post(
            self._build_add_url(ct),
            follow=True,
            data={
                'name': 'Filter 01',
                'use_or': 'False',
                'regularfieldcondition': self._build_rfields_data(
                    operator=operators.IEQUALS,
                    name='filedata',
                    value='foobar',
                ),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='regularfieldcondition',
            errors=_('This field is invalid with this model.'),
        )

    def test_non_filterable_fields02(self):
        "FileFields cannot be filtered (sub-field version)."
        self.login_as_root()

        with self.assertNoException():
            FakeImage._meta.get_field('filedata')

        response = self.assertPOST200(
            self._build_add_url(self.ct_contact),
            follow=True,
            data={
                'name': 'Filter 01',
                'use_or': 'False',
                'regularfieldcondition': self._build_rfields_data(
                    operator=operators.IEQUALS,
                    name='image__filedata',
                    value='foobar',
                ),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='regularfieldcondition',
            errors=_('This field is invalid with this model.'),
        )

    def test_edit(self):
        self.login_as_root()

        # Cannot be a simple sub-filter (bad content type)
        relsubfilfer = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeOrganisation, is_custom=True,
        )

        subfilter = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
        )

        rtype = self._create_rtype()
        ptype = CremePropertyType.objects.create(text='Kawaii')

        create_cf = partial(CustomField.objects.create, content_type=self.ct_contact)
        custom_field = create_cf(name='Nickname',      field_type=CustomField.STR)
        datecfield   = create_cf(name='First meeting', field_type=CustomField.DATETIME)

        name = 'Filter 03'
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter03', name, FakeContact, is_custom=True,
        )
        cf_cond = CustomFieldConditionHandler.build_condition(
            custom_field=custom_field, operator=operators.ICONTAINS, values=['Ed'],
        )
        datecf_cond = DateCustomFieldConditionHandler.build_condition(
            custom_field=datecfield, start=date(year=2010, month=1, day=1),
        )

        efilter.set_conditions([
            RegularFieldConditionHandler.build_condition(
                model=FakeContact, field_name='first_name',
                operator=operators.CONTAINS, values=['Atom'],
            ),
            RegularFieldConditionHandler.build_condition(
                model=FakeContact, field_name='description',
                operator=operators.ISEMPTY, values=[False]
            ),
            DateRegularFieldConditionHandler.build_condition(
                model=FakeContact, field_name='birthday',
                start=date(year=2001, month=1, day=1),
                end=date(year=2010, month=12, day=31),
            ),
            cf_cond, datecf_cond,
            RelationConditionHandler.build_condition(model=FakeContact, rtype=rtype, has=True),
            RelationSubFilterConditionHandler.build_condition(
                model=FakeContact, rtype=rtype.symmetric_type, has=True, subfilter=relsubfilfer,
            ),
            PropertyConditionHandler.build_condition(model=FakeContact, ptype=ptype, has=True),
            SubFilterConditionHandler.build_condition(subfilter),
        ])

        EntityFilter.objects.smart_update_or_create(
            'test-filter04', 'Parent Filter', FakeContact, is_custom=True,
        ).set_conditions([SubFilterConditionHandler.build_condition(efilter)])

        url = efilter.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/forms/entity-filter.html')
        self.assertContains(
            response,
            _('Edit the filter «%(filter)s»') % {'filter': efilter.name},
        )

        with self.assertNoException():
            context = response.context
            submit_label = context['submit_label']
            formfields = context['form'].fields
            # NB: difficult to test the content in a robust way (depends on the DB config)
            context['help_message']  # NOQA

        self.assertEqual(_('Save the modified filter'), submit_label)

        self.assertEqual(FakeContact, formfields['regularfieldcondition'].model)
        self.assertEqual(FakeContact, formfields['relationcondition'].model)
        self.assertEqual(FakeContact, formfields['relationsubfiltercondition'].model)
        self.assertEqual(FakeContact, formfields['propertycondition'].model)
        self.assertListEqual(
            [subfilter.id],
            [f.id for f in formfields['subfiltercondition'].queryset]
        )
        self.assertListEqual(
            [cf_cond], formfields['customfieldcondition'].initial
        )
        self.assertListEqual(
            [datecf_cond],  formfields['datecustomfieldcondition'].initial
        )

        name += ' (edited)'
        field_operator = operators.IEQUALS
        field_name = 'last_name'
        field_value = 'Ikari'
        date_field_name = 'birthday'
        cfield_operator = operators.CONTAINS
        cfield_value = 'Vicious'
        datecfield_rtype = 'previous_year'
        response = self.client.post(
            url, follow=True,
            data={
                'name': name,
                'use_or': 'True',

                'regularfieldcondition': self._build_rfields_data(
                    operator=field_operator,
                    name=field_name,
                    value=field_value,
                ),
                'dateregularfieldcondition': self._build_rdatefields_data(
                    type='',
                    start=self.formfield_value_date(2011, 5, 23),
                    end=self.formfield_value_date(2012, 6, 27),
                    name=date_field_name,
                ),
                'customfieldcondition': self._build_cfields_data(
                    cfield_id=custom_field.id,
                    operator=cfield_operator,
                    value=cfield_value,
                ),
                'datecustomfieldcondition': self._build_cdatefields_data(
                    cfield_id=datecfield.id,
                    type=datecfield_rtype,
                ),
                'relationcondition': self._build_relations_data(rtype.id),
                'relationsubfiltercondition': self._build_subfilters_data(
                    rtype_id=rtype.symmetric_type_id,
                    ct_id=self.ct_orga.id,
                    efilter_id=relsubfilfer.id,
                ),
                'propertycondition': self._build_properties_data(
                    has=False,
                    ptype_id=ptype.id,
                ),
                'subfiltercondition': [subfilter.id],
            },
        )
        self.assertNoFormError(response)

        efilter = self.refresh(efilter)
        self.assertEqual(name, efilter.name)
        self.assertIs(efilter.is_custom, True)
        self.assertIsNone(efilter.user)

        conditions = efilter.conditions.order_by('id')
        self.assertEqual(8, len(conditions))
        iter_conds = iter(conditions)

        condition = next(iter_conds)
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(field_name,                           condition.name)
        self.assertDictEqual(
            {'operator': field_operator, 'values': [field_value]},
            condition.value,
        )

        condition = next(iter_conds)
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(date_field_name,                          condition.name)
        self.assertDictEqual(
            {
                'start': {'year': 2011, 'month': 5, 'day': 23},
                'end':   {'year': 2012, 'month': 6, 'day': 27},
            },
            condition.value,
        )

        condition = next(iter_conds)
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(custom_field.uuid),              condition.name)
        self.assertDictEqual(
            {
                'operator': cfield_operator,
                'rname':    'customfieldstring',
                'values':    [str(cfield_value)],
            },
            condition.value,
        )

        condition = next(iter_conds)
        self.assertEqual(DateCustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(datecfield.uuid),                    condition.name)
        self.assertDictEqual(
            {'rname': 'customfielddatetime', 'name': datecfield_rtype},
            condition.value,
        )

        condition = next(iter_conds)
        self.assertEqual(RelationConditionHandler.type_id, condition.type)
        self.assertEqual(rtype.id,                         condition.name)
        self.assertDictEqual({'has': True}, condition.value)

        condition = next(iter_conds)
        self.assertEqual(RelationSubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(rtype.symmetric_type_id,                   condition.name)
        self.assertDictEqual(
            {'has': False, 'filter_id': relsubfilfer.id},
            condition.value,
        )

        condition = next(iter_conds)
        self.assertEqual(PropertyConditionHandler.type_id, condition.type)
        self.assertEqual(str(ptype.uuid), condition.name)
        self.assertDictEqual({'has': False}, condition.value)

        condition = next(iter_conds)
        self.assertEqual(SubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(subfilter.id,                      condition.name)

        self.assertRedirects(response, FakeContact.get_lv_absolute_url())

    def test_edit__not_custom(self):
        "Not custom -> edit owner & conditions, but not the name + callback_url."
        user = self.login_as_root_and_get()

        name = 'Filter01'
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name, FakeContact, is_custom=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name', values=['Misato'],
                ),
            ],
        )

        url = efilter.get_edit_absolute_url()
        self.assertGET200(url)

        # ---
        field_operator = operators.IEQUALS
        field_name = 'last_name'
        field_value = 'Ikari'
        callback_url = FakeOrganisation.get_lv_absolute_url()
        response = self.client.post(
            url, follow=True,
            data={
                'name':   'Filter01 edited',  # Should not be used
                'user':   user.id,
                'use_or': 'True',

                'regularfieldcondition': self._build_rfields_data(
                    operator=field_operator,
                    name=field_name,
                    value=field_value,
                ),

                'cancel_url': callback_url,
            },
        )
        self.assertNoFormError(response)

        efilter = self.refresh(efilter)
        self.assertEqual(name, efilter.name)  # <== no change
        self.assertFalse(efilter.is_custom)
        self.assertEqual(user, efilter.user)

        condition = self.get_alone_element(efilter.conditions.order_by('id'))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(field_name,                           condition.name)
        self.assertDictEqual(
            {'operator': field_operator, 'values': [field_value]},
            condition.value,
        )

        self.assertRedirects(response, callback_url)

    def test_edit__forbidden_private01(self):
        "Can not edit Filter that belongs to another user."
        self.login_as_standard(allowed_apps=['creme_core'])

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact, user=self.get_root_user(), is_custom=True,
        )
        self.assertGET403(efilter.get_edit_absolute_url())

    def test_edit__forbidden_private02(self):
        "Private filter -> cannot be edited by another user (even a super-user)."
        self.login_as_root()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'My Filter', FakeContact,
            is_custom=True, is_private=True, user=self.create_user(),
        )
        self.assertGET403(efilter.get_edit_absolute_url())

    def test_edit__app_credentials(self):
        "User do not have the app credentials."
        user = self.login_as_standard(allowed_apps=['documents'])

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact, user=user, is_custom=True,
        )
        self.assertGET403(efilter.get_edit_absolute_url())

    def test_edit__cycle_error(self):
        self.login_as_root()

        rtype = RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving',
        ).symmetric(
            id='test-object_love', predicate='Is loved by',
        ).get_or_create()[0]

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='first_name',
                    operator=operators.EQUALS, values=['Misato'],
                ),
            ],
        )

        parent_filter = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            conditions=[SubFilterConditionHandler.build_condition(efilter)],
        )

        response = self.client.post(
            efilter.get_edit_absolute_url(), follow=True,
            data={
                'name': efilter.name,
                'use_or': 'False',
                'relationsubfiltercondition': self._build_subfilters_data(
                    rtype_id=rtype.id,
                    ct_id=self.ct_contact.id,
                    # PROBLEM IS HERE !!!
                    efilter_id=parent_filter.id,
                ),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_('There is a cycle with a sub-filter.'),
        )

    def test_edit__versioned_pk(self):
        "Versioned PK (odd chars)."
        self.login_as_root()
        base_pk = 'creme_core-testfilter'
        create_ef = partial(
            EntityFilter.objects.create,
            name='My filter', entity_type=self.ct_contact,
        )
        self.assertGET200(create_ef(pk=base_pk).get_edit_absolute_url())
        self.assertGET200(create_ef(pk=base_pk + '[1.5]').get_edit_absolute_url())
        self.assertGET200(create_ef(pk=base_pk + '[1.10.2 rc2]').get_edit_absolute_url())
        self.assertGET200(create_ef(pk=base_pk + '[1.10.2 rc2]3').get_edit_absolute_url())

    def test_edit__staff(self):
        "Staff users can edit all EntityFilters + private filters must be assigned."
        self.login_as_super(is_staff=True)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'My Filter', FakeContact,
            is_custom=True, is_private=True, user=self.get_root_user(),
        )
        url = efilter.get_edit_absolute_url()
        self.assertGET200(url)

        response = self.client.post(
            efilter.get_edit_absolute_url(), follow=True,
            data={
                'name':       efilter.name,
                'is_private': 'on',
                'use_or':     'False',

                'regularfieldcondition': self._build_rfields_data(
                    operator=operators.IEQUALS,
                    name='last_name',
                    value='Ikari',
                ),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_('A private filter must be assigned to a user/team.'),
        )

    def test_edit__custom_not_private(self):
        "Not custom filter cannot be private."
        user = self.login_as_root_and_get()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Misatos', FakeContact, is_custom=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='first_name',
                    operator=operators.EQUALS, values=['Misato'],
                ),
            ],
        )
        url = efilter.get_edit_absolute_url()
        self.assertGET200(url)

        response = self.client.post(
            url, follow=True,
            data={
                'name':       efilter.name,
                'user':       user.id,
                'is_private': 'on',  # Should not be used
                'use_or':     'False',

                'regularfieldcondition': self._build_rfields_data(
                    operator=operators.IEQUALS,
                    name='last_name',
                    value='Ikari',
                ),
            },
        )
        self.assertNoFormError(response)
        self.assertFalse(self.refresh(efilter).is_private)

    def test_edit__credentials(self):
        "Cannot edit a system filter."
        self.login_as_root()

        efilter = EntityFilter.objects.create(
            id='test-system_filter', name='System filter',
            entity_type=FakeContact, is_custom=True,
            filter_type=EF_CREDENTIALS,
        )
        self.assertEqual('', efilter.get_edit_absolute_url())
        self.assertGET409(reverse('creme_core__edit_efilter', args=(efilter.id,)))

    def test_edit__with_integer_values(self):
        self.login_as_root()
        civility = FakeCivility.objects.create(title='Other')
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Filter 01', model=FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='civility',
                    values=[civility.pk],
                ),
            ],
        )
        self.assertGET200(efilter.get_edit_absolute_url())

    def _aux_edit_subfilter(self, efilter, user=None, is_private=''):
        user = user or self.user

        return self.client.post(
            efilter.get_edit_absolute_url(), follow=True,
            data={
                'name':       efilter.name,
                'user':       user.id,
                'is_private': is_private,
                'use_or':     'False',

                'regularfieldcondition': self._build_rfields_data(
                    operator=operators.IEQUALS,
                    name='last_name',
                    value='Ikari',
                ),
            },
        )

    def test_edit_subfilter(self):
        "Edit a filter which is a sub-filter for another one -> both are public."
        user = self.login_as_root_and_get()

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response = self._aux_edit_subfilter(efilter1, user=user)
        self.assertNoFormError(response)
        self.assertEqual(user, self.refresh(efilter1).user)

    def test_edit_subfilter__becomes_public(self):
        "The sub-filter becomes public."
        user = self.login_as_root_and_get()

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
            is_private=True, user=user,
        )
        EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            is_private=True, user=user,
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response = self._aux_edit_subfilter(efilter1, user=user)
        self.assertNoFormError(response)
        self.assertFalse(self.refresh(efilter1).is_private)

    def test_edit_subfilter__becomes_private01(self):
        "The sub-filter becomes private + public parent => error."
        user = self.login_as_root_and_get()

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response1 = self._aux_edit_subfilter(efilter1, user=user, is_private='on')
        msg = _(
            'This filter cannot be private because it is a sub-filter for '
            'the public filter "{}"'
        ).format(efilter2.name)
        self.assertFormError(response1.context['form'], field=None, errors=msg)

        # ----
        rtype = self._create_rtype()
        efilter2.set_conditions([
            RelationSubFilterConditionHandler.build_condition(
                model=FakeContact, rtype=rtype, has=True, subfilter=efilter1,
            ),
        ])
        response2 = self._aux_edit_subfilter(efilter1, is_private='on', user=user)
        self.assertFormError(response2.context['form'], field=None, errors=msg)

    def test_edit_subfilter__becomes_private02(self):
        """The sub-filter becomes private:
            - invisible private parent => error
            - owned private filter => OK
        """
        user = self.login_as_root_and_get()

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            is_private=True, user=self.create_user(),
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response = self._aux_edit_subfilter(efilter1, user=user, is_private='on')
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_(
                'This filter cannot be private because it is a sub-filter '
                'for a private filter of another user.'
            ),
        )

        efilter2.user = user
        efilter2.save()

        response = self._aux_edit_subfilter(efilter1, user=user, is_private='on')
        self.assertNoFormError(response)

    def test_edit_subfilter__becomes_private03(self):
        """The sub-filter becomes private + private parent belonging to a team:
            - owner is not a team => error
            - owner is a different team => error
            - owner is the same team => OK
        """
        user = self.login_as_root_and_get()
        other_user = self.create_user()
        team = self.create_team('A-team', user, other_user)

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            is_private=True, user=team,
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response1 = self._aux_edit_subfilter(efilter1, is_private='on', user=user)
        self.assertFormError(
            response1.context['form'],
            field=None,
            errors=_(
                'This filter cannot be private and belong to a user because it '
                'is a sub-filter for the filter "{}" which belongs to a team.'
            ).format(efilter2.name),
        )

        # ---
        other_team = self.create_team('TeamTitan', user, other_user)

        response2 = self._aux_edit_subfilter(efilter1, is_private='on', user=other_team)
        self.assertFormError(
            response2.context['form'],
            field=None,
            errors=_(
                'This filter cannot be private and belong to this team '
                'because it is a sub-filter for the filter "{filter}" '
                'which belongs to the team "{team}".'
            ).format(filter=efilter2.name, team=team),
        )

        # ---
        response3 = self._aux_edit_subfilter(efilter1, is_private='on', user=team)
        self.assertNoFormError(response3)

    def test_edit_subfilter__becomes_private04(self):
        """The sub-filter becomes private to a team + private parent belonging to a user:
            - user not in teammates => error
            - user not teammates => OK
        """
        user = self.login_as_root_and_get()
        other_user = self.create_user()
        team = self.create_team('A-team', user)

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            is_private=True, user=other_user,
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response1 = self._aux_edit_subfilter(efilter1, is_private='on', user=team)
        self.assertFormError(
            response1.context['form'],
            field=None,
            errors=_(
                'This filter cannot be private and belong to this team '
                'because it is a sub-filter for the filter "{filter}" '
                'which belongs to the user "{user}" (who is not a member of this team).'
            ).format(filter=efilter2.name, user=other_user),
        )

        # ---
        team.teammates = [user, other_user]

        response2 = self._aux_edit_subfilter(efilter1, is_private='on', user=team)
        self.assertNoFormError(response2)

    def test_clone(self):
        model = FakeContact
        user = self.login_as_standard(allowed_apps=['creme_core'], listable_models=[model])

        # GET (404) ---
        source_pk = 'test-filter01'
        url = reverse('creme_core__clone_efilter', args=(source_pk,))
        self.assertGET404(url)

        # GET ---
        # Source efilter
        EntityFilter.objects.smart_update_or_create(
            pk=source_pk, name='A filter for Misatos', model=model, is_custom=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=model, field_name='first_name',
                    operator=operators.EQUALS, values=['Misato'],
                ),
            ],
        )

        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/forms/entity-filter.html')
        self.assertContains(
            response1,
            _('Create a filter for «%(ctype)s»') % {'ctype': 'Test Contact'},
        )

        context1 = response1.context
        with self.assertNoException():
            submit_label = context1['submit_label']

            context1['help_message']  # NOQA

            form1 = context1['form']
            edited_instance_id = form1.instance.id

            fields1 = form1.fields
            rfield_conds_f = fields1['regularfieldcondition']
            user_f = fields1['user']
            is_private_f = fields1['is_private']

        self.assertEqual(EntityFilter.save_label, submit_label)
        self.assertEqual('', edited_instance_id)
        self.assertEqual(user.id, user_f.initial)
        self.assertTrue(is_private_f.initial)

        self.assertEqual(FakeContact, rfield_conds_f.model)

        initial_conds = rfield_conds_f.initial
        self.assertIsList(initial_conds, length=1)
        initial_cond = initial_conds[0]
        self.assertIsInstance(initial_cond, EntityFilterCondition)
        self.assertEqual(RegularFieldConditionHandler.type_id, initial_cond.type)
        self.assertEqual('first_name',                         initial_cond.name)

        # ---
        name = 'Cloned Filter'
        operator = operators.IEQUALS
        field_name = 'last_name'
        value = 'Ikari'
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'name': name,
                'user': user.id,
                'is_private': 'on',
                'use_or': 'False',
                'regularfieldcondition': self._build_rfields_data(
                    operator=operator,
                    name=field_name,
                    value=value,
                ),
            },
        )
        self.assertNoFormError(response2)

        efilter = self.get_alone_element(EntityFilter.objects.filter(name=name))
        self.assertNotEqual(source_pk, efilter.id)
        self.assertEqual(FakeContact, efilter.entity_type.model_class())
        self.assertTrue(efilter.is_custom)
        self.assertTrue(efilter.is_private)
        self.assertEqual(user, efilter.user)

        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(field_name,                           condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

        lv_url = FakeContact.get_lv_absolute_url()
        self.assertRedirects(response2, lv_url)

        # List-view ---
        context3 = self.assertGET200(lv_url).context
        selected_efilter = context3['entity_filters'].selected
        self.assertIsInstance(selected_efilter, EntityFilter)
        self.assertEqual(efilter.id, selected_efilter.id)
        self.assertEqual(efilter.id, context3['list_view_state'].entity_filter_id)

    def test_clone__apps_credentials(self):
        self.login_as_standard(allowed_apps=['persons'])

        source_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='A filter for Misatos', model=FakeContact,
            is_custom=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='first_name',
                    operator=operators.EQUALS, values=['Misato'],
                ),
            ],
        )
        self.assertGET403(reverse('creme_core__clone_efilter', args=(source_efilter.id,)))

    def test_clone__custom_entity(self):
        self.login_as_root()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Shop'
        ce_type.plural_name = 'Shops'
        ce_type.save()

        model = ce_type.entity_model
        # Avoid an error message ("no view...")
        HeaderFilter.objects.proxy(
            id='creme_core-userhf_creme_core-customeentity1-1',
            name='Shop lite view', model=model,
            cells=[(EntityCellRegularField, 'name')],
        ).get_or_create()

        source_efilter = EntityFilter.objects.smart_update_or_create(
            pk='creme_core-userfilter_creme_core-customeentity1-1',
            name='A filter for Acmes', model=model,
            is_custom=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=model, field_name='name',
                    operator=operators.EQUALS, values=['Acme'],
                ),
            ],
        )

        name = 'Cloned Filter'
        operator = operators.STARTSWITH
        field_name = 'name'
        value = 'Acmes etc...'
        self.assertNoFormError(self.client.post(
            reverse('creme_core__clone_efilter', args=(source_efilter.pk,)),
            follow=True,
            data={
                'name': name,
                'use_or': 'False',
                'regularfieldcondition': self._build_rfields_data(
                    operator=operator,
                    name=field_name,
                    value=value,
                ),
            },
        ))

        efilter = self.get_alone_element(EntityFilter.objects.filter(name=name))
        self.assertEqual(model, efilter.entity_type.model_class())

        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(field_name,                           condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

    def _delete(self, efilter, callback_url=None, ajax=False):
        data = {}
        if callback_url:
            data['callback_url'] = callback_url

        headers = {'X-Requested-With': 'XMLHttpRequest'} if ajax else None

        return self.client.post(
            reverse('creme_core__delete_efilter', args=(efilter.id,)),
            data=data, headers=headers,
        )

    def test_delete(self):
        self.login_as_root()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        url = efilter.get_delete_absolute_url()
        self.assertEqual(reverse('creme_core__delete_efilter', args=(efilter.id,)), url)

        response = self.assertPOST200(url, follow=True)
        self.assertRedirects(response, FakeContact.get_lv_absolute_url())
        self.assertDoesNotExist(efilter)

    def test_delete__not_custom(self):
        "Not custom -> can not delete."
        self.login_as_root()

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01',
            model=FakeContact, is_custom=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.EQUALS, values=['Ikari'],
                ),
            ],
        )
        self._delete(efilter)
        self.assertStillExists(efilter)

    def test_delete__belongs_to_another_user(self):
        self.login_as_standard()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact,
            is_custom=True, user=self.get_root_user(),
        )
        self._delete(efilter)
        self.assertStillExists(efilter)

    def test_delete__belongs_to_team01(self):
        "Belongs to my team -> OK."
        user = self.login_as_standard()
        my_team = self.create_team('TeamTitan', user)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact,
            is_custom=True, user=my_team,
        )
        self._delete(efilter)
        self.assertDoesNotExist(efilter)

    def test_delete__belongs_to_team02(self):
        "Belongs to a team (not mine) -> KO."
        user = self.login_as_standard()

        self.create_team('A-team', user)
        other_team = self.create_team('TeamTitan', self.get_root_user())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact,
            is_custom=True, user=other_team,
        )
        self._delete(efilter)
        self.assertStillExists(efilter)

    def test_delete__superuser(self):
        "Logged as super-user."
        self.login_as_root()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact,
            is_custom=True, user=self.create_user(),
        )
        self._delete(efilter)
        self.assertDoesNotExist(efilter)

    def test_delete__callback_url(self):
        self.login_as_root()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact, is_custom=True,
        )
        cb_url = reverse('creme_config__efilters')
        response = self._delete(efilter, callback_url=cb_url)
        self.assertDoesNotExist(efilter)
        self.assertRedirects(response, cb_url)

    def test_delete__callback_url__ajax(self):
        self.login_as_root()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact, is_custom=True,
        )
        cb_url = reverse('creme_config__efilters')
        response = self._delete(efilter, callback_url=cb_url, ajax=True)
        self.assertDoesNotExist(efilter)
        self.assertEqual(cb_url, response.text)

    def test_delete__dependencies_error01(self):
        "Can not delete if used as sub-filter."
        self.login_as_root()

        efilter01 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact, is_custom=True,
        )
        EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter02', FakeContact, is_custom=True,
            conditions=[SubFilterConditionHandler.build_condition(efilter01)],
        )

        self._delete(efilter01)
        self.assertStillExists(efilter01)

    def test_delete__dependencies_error02(self):
        "Can not delete if used as subfilter (for relations)."
        self.login_as_root()

        rtype = self._create_rtype()
        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter1', 'Filter01', FakeContact, is_custom=True,
        )
        EntityFilter.objects.smart_update_or_create(
            'test-filter2', 'Filter02', FakeContact, is_custom=True,
            conditions=[RelationSubFilterConditionHandler.build_condition(
                model=FakeContact, rtype=rtype.symmetric_type, has=True, subfilter=efilter1,
            )],
        )

        self._delete(efilter1)
        self.assertStillExists(efilter1)

    def test_delete__dependencies_error03(self):
        "Can not delete if used through some FK."
        user = self.login_as_root_and_get()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter001', 'Filter #01', FakeContact, is_custom=True,
        )
        report = FakeReport.objects.create(
            user=user, ctype=efilter.entity_type, efilter=efilter,
        )

        response = self._delete(efilter)
        self.assertStillExists(efilter)

        with self.assertNoException():
            msg = response.context['error_message']

        self.assertHTMLEqual(
            '<span>{message}</span>'
            '<ul>'
            ' <li>'
            '  <a href="/tests/report/{report_id}" target="_blank">{label}</a>'
            ' </li>'
            '</ul>'.format(
                message=_(
                    'This deletion cannot be performed because of the links '
                    'with some entities (& other elements):'
                ),
                report_id=report.id,
                label=str(report),
            ),
            msg,
        )

    def test_delete__credentials(self):
        "Cannot delete a credentials filter with the regular view."
        self.login_as_root()

        efilter = EntityFilter.objects.create(
            id='test-system_filter', name='System filter',
            entity_type=FakeContact, is_custom=True,
            filter_type=EF_CREDENTIALS,
        )
        self.assertEqual('', efilter.get_delete_absolute_url())
        self.assertPOST409(
            reverse('creme_core__delete_efilter', args=(efilter.id,)),
            follow=True,
        )
        self.assertStillExists(efilter)

    def test_get_content_types01(self):
        self.login_as_root()

        rtype = self._create_rtype()
        response = self.assertGET200(self._build_get_ct_url(rtype))

        content = response.json()
        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 1)
        self.assertTrue(all(len(t) == 2 for t in content))
        self.assertTrue(all(isinstance(t[0], int) for t in content))
        self.assertEqual([0, pgettext('creme_core-filter', 'All')], content[0])

    def test_get_content_types02(self):
        self.login_as_root()

        rtype = RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving',
        ).symmetric(
            id='test-object_love',  predicate='Is loved by', models=[FakeContact],
        ).get_or_create()[0]
        response = self.assertGET200(self._build_get_ct_url(rtype))

        ct = self.ct_contact
        self.assertListEqual(
            [
                [0, pgettext('creme_core-filter', 'All')],
                [ct.id, str(ct)],
            ],
            response.json(),
        )

    def test_filters_for_ctype__empty(self):
        self.login_as_root()

        build_url = self._build_get_filter_url
        response1 = self.assertGET200(build_url(self.ct_contact))
        self.assertListEqual([], response1.json())

        # ---
        response2 = self.assertGET200(build_url(self.ct_contact, types=[EF_REGULAR]))
        self.assertListEqual([], response2.json())

    def test_filters_for_ctype__ok(self):
        user = self.login_as_root_and_get()

        create_efilter = partial(EntityFilter.objects.create, entity_type=FakeContact)

        pk_fmt = 'test-contact_filter{}'.format
        efilter1 = create_efilter(pk=pk_fmt(1), name='Filter 1')
        efilter2 = create_efilter(pk=pk_fmt(2), name='Filter 2', is_custom=False)
        create_efilter(pk='test-orga_filter', name='Orga Filter', entity_type=FakeOrganisation)
        efilter3 = create_efilter(pk=pk_fmt(3), name='Filter 3', is_private=True, user=user)
        create_efilter(
            pk=pk_fmt(4), name='Private', is_private=True, user=self.create_user(),
        )
        cred_filter = create_efilter(pk=pk_fmt(5), name='System', filter_type=EF_CREDENTIALS)

        expected = [
            [efilter1.id, efilter1.name],
            [efilter2.id, efilter2.name],
            [efilter3.id, efilter3.name],
        ]

        build_url = partial(self._build_get_filter_url, ct=self.ct_contact)
        response1 = self.assertGET200(build_url())
        self.assertListEqual(expected, response1.json())

        # ---
        response_all_int = self.assertGET200(build_url(all_=0))
        self.assertListEqual(expected, response_all_int.json())

        # ---
        response_all_bool = self.assertGET200(build_url(all_='false'))
        self.assertListEqual(expected, response_all_bool.json())

        # ---
        response_regular = self.assertGET200(build_url(types=[EF_REGULAR]))
        self.assertListEqual(expected, response_regular.json())

        # ---
        response_creds = self.assertGET200(build_url(types=[EF_CREDENTIALS]))
        self.assertListEqual([
            [cred_filter.id, cred_filter.name],
        ], response_creds.json())

    def test_filters_for_ctype__errors(self):
        self.login_as_root()

        build_url = partial(self._build_get_filter_url, ct=self.ct_contact)
        self.assertContains(
            self.client.get(build_url(all_='invalid')),
            text='Problem with argument &quot;all&quot;',
            status_code=404,
        )
        self.assertContains(
            self.client.get(build_url(types=['invalid'])),
            text='Invalid type of filter &quot;invalid&quot;',
            status_code=404,
        )

    def test_filters_for_ctype__app_perm(self):
        self.login_as_standard(allowed_apps=['documents'])
        self.assertGET403(self._build_get_filter_url(self.ct_contact))

    def test_filters_for_ctype__all_choice(self):
        "Include 'All' fake filter."
        self.login_as_root()

        create_filter = EntityFilter.objects.smart_update_or_create
        efilter01 = create_filter('test-filter01', 'Filter 01', FakeContact, is_custom=True)
        efilter02 = create_filter('test-filter02', 'Filter 02', FakeContact, is_custom=True)
        create_filter('test-filter03', 'Filter 03', FakeOrganisation, is_custom=True)

        expected = [
            ['',           pgettext('creme_core-filter', 'All')],
            [efilter01.id, 'Filter 01'],
            [efilter02.id, 'Filter 02'],
        ]

        build_url = partial(self._build_get_filter_url, ct=self.ct_contact)
        response_int = self.assertGET200(build_url(all_=1))
        self.assertEqual(expected, response_int.json())

        # ---
        response_bool = self.assertGET200(build_url(all_='true'))
        self.assertEqual(expected, response_bool.json())

        # ---
        response_bool_cap = self.assertGET200(build_url(all_='True'))
        self.assertEqual(expected, response_bool_cap.json())


class UserChoicesTestCase(CremeTestCase):
    EF_TEST = 'creme_core-test_user_choices'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class CivOperand(operands.ConditionDynamicOperand):
            type_id = '__mainciv__'
            model = FakeCivility

        class SuperUsersOperand(operands.ConditionDynamicOperand):
            type_id = '__superusers__'
            verbose_name = 'Superusers'
            model = CremeUser

        class MainUserOperand(operands.ConditionDynamicOperand):
            type_id = '__mainuser__'
            verbose_name = 'Main user'
            model = CremeUser

        entity_filter_registries.register(EntityFilterRegistry(
            id=cls.EF_TEST,
            verbose_name='Test registry',
        ).register_operands(
            CivOperand,
            SuperUsersOperand,
            MainUserOperand,
        ))

        cls.SuperUsersOperand = SuperUsersOperand
        cls.MainUserOperand   = MainUserOperand

        cls.contact_ctype = ContentType.objects.get_for_model(FakeContact)

    def _build_url(self, field_name='user'):
        return reverse(
            'creme_core__efilter_user_choices', args=(self.contact_ctype.id, field_name)
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        entity_filter_registries.unregister(cls.EF_TEST)

    def test_user_choices01(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        # Alphabetically-first user (__str__, not username)
        first_user = self.create_user(index=2)
        self.assertGreater(str(user), str(first_user))

        url = self._build_url()
        choices1 = self.assertGET200(url).json()
        self.assertIsList(choices1, min_length=3)

        self.assertEqual(
            {'value': '__currentuser__', 'label': _('Current user')},
            choices1[0],
        )

        def find_user(u):
            user_id = u.id

            for i, choice in enumerate(choices1):
                if user_id == choice['value']:
                    return i, choice['label']

            self.fail(f'User "{u}" not found in {choices1}')

        user_index, user_label = find_user(user)
        self.assertEqual(user_label, str(user))

        other_index, other_label = find_user(other_user)
        self.assertEqual(other_label, str(other_user))

        first_index, first_label = find_user(first_user)
        self.assertEqual(first_label, str(first_user))

        self.assertGreater(other_index, user_index)
        self.assertGreater(user_index,  first_index)

        # "filter_type" ---
        choices2 = self.assertGET200(f'{url}?filter_type={EF_REGULAR}').json()
        self.assertEqual(choices1, choices2)

        choices3 = self.assertGET200(f'{url}?filter_type={EF_CREDENTIALS}').json()
        self.assertEqual(choices1, choices3)

        self.assertGET(400, url + '?filter_type=1024')
        self.assertGET(400, url + '?filter_type=invalid')

    def test_user_choices02(self):
        "Other registered operands."
        self.login_as_root()

        choices = self.assertGET200(
            f'{self._build_url()}?filter_type={self.EF_TEST}'
        ).json()
        self.assertEqual(self.MainUserOperand.type_id,   choices[0]['value'])
        self.assertEqual(self.SuperUsersOperand.type_id, choices[1]['value'])

    def test_field_does_not_exist(self):
        self.login_as_root()
        self.assertGET404(self._build_url(field_name='invalid'))
