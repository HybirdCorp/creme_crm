# -*- coding: utf-8 -*-

from datetime import date
from functools import partial
from json import dumps as json_dump

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext, pgettext

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    EF_USER,
    _EntityFilterRegistry,
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
    CustomField,
    EntityFilter,
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeFolder,
    FakeImage,
    FakeOrganisation,
    FakeProduct,
    HeaderFilter,
    RelationType,
)

from .base import ViewsTestCase


class EntityFilterViewsTestCase(ViewsTestCase):
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
    def _build_get_filter_url(ct):
        return reverse('creme_core__efilters') + f'?ct_id={ct.id}'

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

    @override_settings(FILTERS_INITIAL_PRIVATE=False)
    def test_create01(self):
        "Check app credentials."
        self.login(is_superuser=False, allowed_apps=['documents'])

        ct = self.ct_contact
        self.assertFalse(EntityFilter.objects.filter(entity_type=ct).count())

        uri = self._build_add_url(ct)
        self.assertGET403(uri)

        self.role.allowed_apps = ['documents', 'creme_core']
        self.role.save()
        response = self.assertGET200(uri)
        self.assertTemplateUsed(response, 'creme_core/forms/entity-filter.html')
        self.assertContains(
            response,
            _('Create a filter for «%(ctype)s»') % {'ctype': 'Test Contact'},
        )

        context = response.context
        with self.assertNoException():
            form = context['form']
            # NB: difficult to test the content in a robust way (depends on the DB config)
            context['help_message']  # NOQA

        self.assertIs(form.initial.get('is_private'), False)

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

        name = 'Filter 01'
        operator = operators.IEQUALS
        field_name = 'last_name'
        value = 'Ikari'
        response = self.client.post(
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
        self.assertNoFormError(response)

        efilters = EntityFilter.objects.filter(entity_type=ct)
        self.assertEqual(1, len(efilters))

        efilter = efilters[0]
        self.assertEqual(name, efilter.name)
        self.assertTrue(efilter.is_custom)
        self.assertFalse(efilter.is_private)
        self.assertIsNone(efilter.user)
        self.assertFalse(efilter.use_or)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(field_name,                           condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

        lv_url = FakeContact.get_lv_absolute_url()
        self.assertRedirects(response, lv_url)

        # --
        context = self.assertGET200(lv_url).context
        selected_efilter = context['entity_filters'].selected
        self.assertIsInstance(selected_efilter, EntityFilter)
        self.assertEqual(efilter.id, selected_efilter.id)
        self.assertEqual(efilter.id, context['list_view_state'].entity_filter_id)

    def test_create02(self):
        user = self.login()
        ct = self.ct_orga

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

        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_kawaii', text='Kawaii',
        )

        create_cf = partial(CustomField.objects.create, content_type=ct)
        custom_field = create_cf(name='Profits',        field_type=CustomField.INT)
        datecfield   = create_cf(name='Last gathering', field_type=CustomField.DATETIME)

        url = self._build_add_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            sb_f = fields['subfiltercondition']

        subfilter_ids = {f.id for f in sb_f.queryset}
        self.assertIn(subfilter.id, subfilter_ids)
        self.assertNotIn(relsubfilfer.id, subfilter_ids)

        name = 'Filter 03'
        field_operator = operators.CONTAINS
        field_name = 'name'
        field_value = 'NERV'
        date_field_name = 'creation_date'
        daterange_type = 'current_year'
        cfield_operator = operators.GT
        cfield_value = 10000
        datecfield_rtype = 'previous_quarter'
        response = self.client.post(
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
                    rtype_id=srtype.id,
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
        self.assertNoFormError(response)

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
        self.assertEqual(str(custom_field.id),                condition.name)
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
        self.assertEqual(str(datecfield.id),                      condition.name)
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
        self.assertEqual(srtype.id,                                 condition.name)
        self.assertDictEqual(
            {'has': False, 'filter_id': relsubfilfer.id},
            condition.value,
        )

        condition = next(iter_conds)
        self.assertEqual(PropertyConditionHandler.type_id, condition.type)
        self.assertEqual(ptype.id,                         condition.name)
        self.assertIs(condition.value, True)

        condition = next(iter_conds)
        self.assertEqual(SubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(subfilter.id,                      condition.name)

    def test_create03(self):
        "Existing state session is kept."
        self.login()

        lv_url = FakeOrganisation.get_lv_absolute_url()
        ct = self.ct_orga

        # Set a header filter in the session (should be kept)
        hfilter1 = HeaderFilter.objects.filter(entity_type=ct).first()
        self.assertIsNotNone(hfilter1)
        hfilter2 = HeaderFilter.objects.create_if_needed(
            pk='creme_core-tests_views_entity_filter_test_create03',
            name='Ze last FakeContact view',
            model=FakeOrganisation,
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'email'}),
            ],
        )
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

    def test_create04(self):
        "Date sub-field + callback_url."
        self.login()

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

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(field_name,                               condition.name)
        self.assertDictEqual({'name': daterange_type}, condition.value)

        self.assertRedirects(response, callback_url)

    def test_create05(self):
        "Error: no conditions of any type."
        self.login()

        response = self.client.post(
            self._build_add_url(self.ct_orga),
            data={
                'name': 'Filter 01',
                'user': self.user.id,
                'use_or': 'False',
            },
        )
        self.assertFormError(
            response, 'form', field=None,
            errors=_('The filter must have at least one condition.'),
        )

    def test_create06(self):
        "Cannot create a private filter for another user (but OK with one of our teams)."
        user = self.login()

        User = get_user_model()
        my_team = User.objects.create(username='TeamTitan', is_team=True)
        my_team.teammates = [user, self.other_user]

        a_team = User.objects.create(username='A-team', is_team=True)
        a_team.teammates = [self.other_user]

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

        response = post(self.other_user)
        msg = _('A private filter must belong to you (or one of your teams).')
        self.assertFormError(response, 'form', 'user', msg)

        response = post(a_team)
        self.assertFormError(response, 'form', 'user', msg)

        response = post(my_team)
        self.assertNoFormError(response)
        self.get_object_or_fail(EntityFilter, name=name)

    def test_create07(self):
        "A staff  user can create a private filter for another user."
        user = self.login(is_staff=True)

        team = get_user_model().objects.create(username='A-team', is_team=True)
        team.teammates = [user]

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
        self.assertFalse(subfilter.can_view(self.other_user)[0])

        name = 'Katsuragi'
        data = {
            'name':       name,
            'user':       self.other_user.id,
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
            response, 'form', None,
            ngettext(
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

    def test_create08(self):
        "Not an Entity type."
        self.login()
        self.assertGET409(self._build_add_url(ContentType.objects.get_for_model(RelationType)))

    @override_settings(FILTERS_INITIAL_PRIVATE=True)
    def test_create_initial_private(self):
        "Use FILTERS_INITIAL_PRIVATE."
        self.login()

        response = self.assertGET200(self._build_add_url(self.ct_contact))
        self.assertIs(response.context['form'].initial.get('is_private'), True)

    def test_create_missing_lv_absolute_url(self):
        "Missing get_lv_absolute_url() classmethod."
        with self.assertRaises(AttributeError):
            FakeProduct.get_lv_absolute_url()

        user = self.login()

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

    def test_create_creatorfield_fk_filter(self):
        user = self.login()
        folder = FakeFolder.objects.create(title='Folder 01', user=self.user)

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
        conditions = efilter.conditions.all()

        self.assertEqual(1, len(conditions))
        condition = conditions[0]

        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual('linked_folder',                      condition.name)
        self.assertDictEqual(
            {
                'operator': operators.EQUALS,
                'values':   [str(folder.id)],
            },
            condition.value,
        )

    def test_create_currentuser_filter(self):
        user = self.login()
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

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))
        iter_conds = iter(conditions)

        condition = next(iter_conds)
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual('user',                               condition.name)
        self.assertDictEqual(
            {
                'operator': operators.EQUALS,
                'values':   [operand_id],
            },
            condition.value,
        )

    def test_edit_filter_with_integer_values(self):
        self.login()
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

    def test_create_subfilters_n_private01(self):
        "Cannot choose a private sub-filter which belongs to another user."
        user = self.login()

        subfilter = EntityFilter.objects.smart_update_or_create(
            'creme_core-subfilter', 'Misato', model=FakeContact,
            user=self.other_user, is_private=True, is_custom=True,
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
            return self.assertPOST200(
                self._build_add_url(ct=self.ct_contact),
                follow=True, data=post_data,
            )

        response = post({**data, 'subfiltercondition': [subfilter.id]})
        self.assertFormError(
            response, 'form', 'subfiltercondition',
            _('Select a valid choice. %(value)s is not one of the available choices.') % {
                'value': subfilter.id,
            },
        )

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by')
        )[0]
        response = post({
            **data,
            'relationsubfiltercondition': self._build_subfilters_data(
                rtype_id=rtype.id,
                ct_id=self.ct_contact.id,
                efilter_id=subfilter.id,
            ),
        })
        self.assertFormError(
            response, 'form', 'relationsubfiltercondition', _('This filter is invalid.')
        )

    def test_create_subfilters_n_private02(self):
        """Private sub-filter (owned by a regular user):
            - OK in a private filter (with the same owner).
            - Error in a public filter.
        """
        user = self.login()

        team = get_user_model().objects.create(username='A-team', is_team=True)
        team.teammates = [user, self.other_user]

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

        response = post('')
        self.assertEqual(200, response.status_code)
        self.assertFormError(
            response, 'form', None,
            ngettext(
                'Your filter must be private in order to use this private sub-filter: {}',
                'Your filter must be private in order to use these private sub-filters: {}',
                2
            ).format(f'{subfilter2.name}, {subfilter1.name}'),
        )

        response = post('on')
        self.assertNoFormError(response)
        self.get_object_or_fail(EntityFilter, name=name)

    def test_create_subfilters_n_private03(self):
        """Private filter owned by a team:
            - OK with a public sub-filter.
            - OK with a private sub-filter which belongs to the team.
            - Error with a private sub-filter which does not belong to the team.
        """
        user = self.login()
        other_user = self.other_user

        User = get_user_model()
        team = User.objects.create(username='A-team', is_team=True)
        team.teammates = [user, other_user]

        other_team = User.objects.create(username='TeamTitan', is_team=True)
        other_team.teammates = [user, other_user]

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

        response = post(subfilter3)
        self.assertEqual(200, response.status_code)
        self.assertFormError(
            response, 'form', None,
            ngettext(
                'A private filter which belongs to a team can only use public sub-filters & '
                'private sub-filters which belong to this team.'
                ' So this private sub-filter cannot be chosen: {}',
                'A private filter which belongs to a team can only use public sub-filters & '
                'private sub-filters which belong to this team.'
                ' So these private sub-filters cannot be chosen: {}',
                1
            ).format(subfilter3.name),
        )

        response = post(subfilter1, subfilter2)
        self.assertNoFormError(response)
        self.get_object_or_fail(EntityFilter, name=name)

    def test_non_filterable_fields01(self):
        "FileFields cannot be filtered."
        self.login()

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
            response, 'form', 'regularfieldcondition',
            _('This field is invalid with this model.')
        )

    def test_non_filterable_fields02(self):
        "FileFields cannot be filtered (sub-field version)"
        self.login()

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
            response, 'form', 'regularfieldcondition',
            _('This field is invalid with this model.'),
        )

    def test_edit01(self):
        self.login()

        # Cannot be a simple sub-filter (bad content type)
        relsubfilfer = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeOrganisation, is_custom=True,
        )

        subfilter = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
        )

        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by')
        )
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_kawaii', text='Kawaii',
        )

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
                model=FakeContact, rtype=srtype, has=True, subfilter=relsubfilfer,
            ),
            PropertyConditionHandler.build_condition(model=FakeContact, ptype=ptype, has=True),
            SubFilterConditionHandler.build_condition(subfilter),
        ])

        parent_filter = EntityFilter.objects.smart_update_or_create(
            'test-filter04', 'Filter 04', FakeContact, is_custom=True,
        )
        parent_filter.set_conditions([SubFilterConditionHandler.build_condition(efilter)])

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
                    start='2011-5-23',
                    end='2012-6-27',
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
                    rtype_id=srtype.id,
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
        self.assertEqual(str(custom_field.id),                condition.name)
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
        self.assertEqual(str(datecfield.id),                      condition.name)
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
        self.assertEqual(srtype.id,                                 condition.name)
        self.assertDictEqual(
            {'has': False, 'filter_id': relsubfilfer.id},
            condition.value,
        )

        condition = next(iter_conds)
        self.assertEqual(PropertyConditionHandler.type_id, condition.type)
        self.assertEqual(ptype.id,                         condition.name)
        self.assertIs(condition.value, False)

        condition = next(iter_conds)
        self.assertEqual(SubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(subfilter.id,                      condition.name)

        self.assertRedirects(response, FakeContact.get_lv_absolute_url())

    def test_edit02(self):
        "Not custom -> edit owner & conditions, but not the name + callback_url"
        user = self.login()

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
        self.assertEqual(self.user, efilter.user)

        conditions = efilter.conditions.order_by('id')
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(field_name,                           condition.name)
        self.assertDictEqual(
            {'operator': field_operator, 'values': [field_value]},
            condition.value,
        )

        self.assertRedirects(response, callback_url)

    def test_edit03(self):
        "Can not edit Filter that belongs to another user."
        self.login(is_superuser=False, allowed_apps=['creme_core'])

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact, user=self.other_user, is_custom=True,
        )
        self.assertGET403(efilter.get_edit_absolute_url())

    def test_edit04(self):
        "User do not have the app credentials."
        self.login(is_superuser=False, allowed_apps=['documents'])

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact, user=self.user, is_custom=True,
        )
        self.assertGET403(efilter.get_edit_absolute_url())

    def test_edit05(self):
        "Cycle error."
        self.login()

        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )

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
            response, 'form', field=None,
            errors=_('There is a cycle with a sub-filter.'),
        )

    def test_edit06(self):
        "Versioned PK (odd chars)."
        self.login()
        base_pk = 'creme_core-testfilter'
        create_ef = partial(
            EntityFilter.objects.create,
            name='My filter', entity_type=self.ct_contact,
        )
        self.assertGET200(create_ef(pk=base_pk).get_edit_absolute_url())
        self.assertGET200(create_ef(pk=base_pk + '[1.5]').get_edit_absolute_url())
        self.assertGET200(create_ef(pk=base_pk + '[1.10.2 rc2]').get_edit_absolute_url())
        self.assertGET200(create_ef(pk=base_pk + '[1.10.2 rc2]3').get_edit_absolute_url())

    def test_edit07(self):
        "Staff users can edit all EntityFilters + private filters must be assigned."
        self.login(is_staff=True)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'My Filter', FakeContact,
            is_custom=True, is_private=True, user=self.other_user,
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
            response, 'form', None,
            _('A private filter must be assigned to a user/team.'),
        )

    def test_edit08(self):
        "Private filter -> cannot be edited by another user (even a super-user)."
        self.login()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'My Filter', FakeContact,
            is_custom=True, is_private=True, user=self.other_user,
        )
        self.assertGET403(efilter.get_edit_absolute_url())

    def test_edit09(self):
        "Not custom filter cannot be private"
        user = self.login()

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

    def test_edit10(self):
        "Cannot edit a system filter."
        self.login()

        efilter = EntityFilter.objects.create(
            id='test-system_filter', name='System filter',
            entity_type=FakeContact, is_custom=True,
            filter_type=EF_CREDENTIALS,
        )
        self.assertGET403(efilter.get_edit_absolute_url())

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

    def test_edit_subfilter01(self):
        "Edit a filter which is a sub-filter for another one -> both are public."
        user = self.login()

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response = self._aux_edit_subfilter(efilter1)
        self.assertNoFormError(response)
        self.assertEqual(user, self.refresh(efilter1).user)

    def test_edit_subfilter02(self):
        "The sub-filter becomes public."
        user = self.login()

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
            is_private=True, user=user,
        )
        EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            is_private=True, user=user,
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response = self._aux_edit_subfilter(efilter1)
        self.assertNoFormError(response)
        self.assertFalse(self.refresh(efilter1).is_private)

    def test_edit_subfilter03(self):
        "The sub-filter becomes private + public parent => error."
        self.login()

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response = self._aux_edit_subfilter(efilter1, is_private='on')
        msg = _(
            'This filter cannot be private because it is a sub-filter for '
            'the public filter "{}"'
        ).format(efilter2.name)
        self.assertFormError(response, 'form', None, msg)

        # ----
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by')
        )[0]

        efilter2.set_conditions([
            RelationSubFilterConditionHandler.build_condition(
                model=FakeContact, rtype=rtype, has=True, subfilter=efilter1,
            ),
        ])
        response = self._aux_edit_subfilter(efilter1, is_private='on')
        self.assertFormError(response, 'form', None, msg)

    def test_edit_subfilter04(self):
        """The sub-filter becomes private:
            - invisible private parent => error
            - owned private filter => OK
        """
        self.login()

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            is_private=True, user=self.other_user,
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response = self._aux_edit_subfilter(efilter1, is_private='on')
        self.assertFormError(
            response, 'form', None,
            _(
                'This filter cannot be private because it is a sub-filter '
                'for a private filter of another user.'
            ),
        )

        efilter2.user = self.user
        efilter2.save()

        response = self._aux_edit_subfilter(efilter1, is_private='on')
        self.assertNoFormError(response)

    def test_edit_subfilter05(self):
        """The sub-filter becomes private + private parent belonging to a team:
            - owner is not a team => error
            - owner is a different team => error
            - owner is the same team => OK
        """
        user = self.login()

        User = get_user_model()
        team = User.objects.create(username='A-team', is_team=True)
        team.teammates = [user, self.other_user]

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            is_private=True, user=team,
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response = self._aux_edit_subfilter(efilter1, is_private='on')
        self.assertFormError(
            response, 'form', None,
            _(
                'This filter cannot be private and belong to a user because it '
                'is a sub-filter for the filter "{}" which belongs to a team.'
            ).format(efilter2.name),
        )

        other_team = User.objects.create(username='TeamTitan', is_team=True)
        other_team.teammates = [user, self.other_user]

        response = self._aux_edit_subfilter(efilter1, is_private='on', user=other_team)
        self.assertFormError(
            response, 'form', None,
            _(
                'This filter cannot be private and belong to this team '
                'because it is a sub-filter for the filter "{filter}" '
                'which belongs to the team "{team}".'
            ).format(filter=efilter2.name, team=team),
        )

        response = self._aux_edit_subfilter(efilter1, is_private='on', user=team)
        self.assertNoFormError(response)

    def test_edit_subfilter06(self):
        """The sub-filter becomes private to a team + private parent belonging to a user:
            - user not in teammates => error
            - user not teammates => OK
        """
        user = self.login()

        team = get_user_model().objects.create(username='A-team', is_team=True)
        team.teammates = [user]

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter 02', FakeContact, is_custom=True,
            is_private=True, user=self.other_user,
            conditions=[SubFilterConditionHandler.build_condition(efilter1)],
        )

        response = self._aux_edit_subfilter(efilter1, is_private='on', user=team)
        self.assertFormError(
            response, 'form', None,
            _(
                'This filter cannot be private and belong to this team '
                'because it is a sub-filter for the filter "{filter}" '
                'which belongs to the user "{user}" (who is not a member of this team).'
            ).format(filter=efilter2.name, user=self.other_user)
        )

        team.teammates = [user, self.other_user]

        response = self._aux_edit_subfilter(efilter1, is_private='on', user=team)
        self.assertNoFormError(response)

    def _delete(self, efilter, **kwargs):
        return self.client.post(
            reverse('creme_core__delete_efilter'),
            data={'id': efilter.id},
            **kwargs
        )

    def test_delete01(self):
        self.login()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter 01', FakeContact, is_custom=True,
        )
        response = self._delete(efilter, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertRedirects(response, FakeContact.get_lv_absolute_url())
        self.assertDoesNotExist(efilter)

    def test_delete02(self):
        "Not custom -> can not delete."
        self.login()

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

    def test_delete03(self):
        "Belongs to another user."
        self.login(is_superuser=False)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact,
            is_custom=True, user=self.other_user,
        )
        self._delete(efilter)
        self.assertStillExists(efilter)

    def test_delete04(self):
        "Belongs to my team -> OK."
        user = self.login(is_superuser=False)

        my_team = get_user_model().objects.create(username='TeamTitan', is_team=True)
        my_team.teammates = [user]

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact,
            is_custom=True, user=my_team,
        )
        self._delete(efilter)
        self.assertDoesNotExist(efilter)

    def test_delete05(self):
        "Belongs to a team (not mine) -> KO."
        user = self.login(is_superuser=False)

        User = get_user_model()
        my_team = User.objects.create(username='A-team', is_team=True)
        my_team.teammates = [user]

        a_team = User.objects.create(username='TeamTitan', is_team=True)
        a_team.teammates = [self.other_user]

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact,
            is_custom=True, user=a_team,
        )
        self._delete(efilter)
        self.assertStillExists(efilter)

    def test_delete06(self):
        "Logged as super-user."
        self.login()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact,
            is_custom=True, user=self.other_user,
        )
        self._delete(efilter)
        self.assertDoesNotExist(efilter)

    def test_delete07(self):
        "Can not delete if used as sub-filter."
        self.login()

        efilter01 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact, is_custom=True,
        )
        EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter02', FakeContact, is_custom=True,
            conditions=[SubFilterConditionHandler.build_condition(efilter01)],
        )

        self._delete(efilter01)
        self.assertStillExists(efilter01)

    def test_delete08(self):
        "Can not delete if used as subfilter (for relations)"
        self.login()

        srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by')
        )[1]

        efilter01 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact, is_custom=True,
        )
        EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Filter02', FakeContact, is_custom=True,
            conditions=[
                RelationSubFilterConditionHandler.build_condition(
                    model=FakeContact, rtype=srtype, has=True, subfilter=efilter01,
                ),
            ],
        )

        self._delete(efilter01)
        self.assertStillExists(efilter01)

    def test_get_content_types01(self):
        self.login()

        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )

        response = self.assertGET200(self._build_get_ct_url(rtype))

        content = response.json()
        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 1)
        self.assertTrue(all(len(t) == 2 for t in content))
        self.assertTrue(all(isinstance(t[0], int) for t in content))
        self.assertEqual([0, pgettext('creme_core-filter', 'All')], content[0])

    def test_get_content_types02(self):
        self.login()

        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving',),
            ('test-object_love',  'Is loved by', (FakeContact,))
        )

        response = self.assertGET200(self._build_get_ct_url(rtype))

        ct = self.ct_contact
        self.assertListEqual(
            [
                [0, pgettext('creme_core-filter', 'All')],
                [ct.id, str(ct)],
            ],
            response.json(),
        )

    def test_filters_for_ctype01(self):
        self.login()

        response = self.assertGET200(self._build_get_filter_url(self.ct_contact))
        self.assertListEqual([], response.json())

    def test_filters_for_ctype02(self):
        user = self.login()
        create_efilter = EntityFilter.objects.smart_update_or_create

        name1 = 'Filter 01'
        name2 = 'Filter 02'
        name3 = 'Filter 03'

        pk_fmt = 'test-contact_filter{}'.format
        efilter01 = create_efilter(pk_fmt(1), name1, FakeContact, is_custom=True)
        efilter02 = create_efilter(
            pk_fmt(2), name2, FakeContact, is_custom=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='first_name',
                    operator=operators.EQUALS, values=['Misato'],
                ),
            ],
        )
        create_efilter(
            'test-orga_filter', 'Orga Filter', FakeOrganisation, is_custom=True,
        )
        efilter03 = create_efilter(
            pk_fmt(3), name3, FakeContact, is_custom=True, is_private=True, user=user,
        )
        create_efilter(
            pk_fmt(4), 'Private', FakeContact, is_custom=True,
            is_private=True, user=self.other_user,
        )
        expected = [
            [efilter01.id, name1],
            [efilter02.id, name2],
            [efilter03.id, name3],
        ]

        response = self.assertGET200(self._build_get_filter_url(self.ct_contact))
        self.assertEqual(expected, response.json())

        url = self._build_get_filter_url(self.ct_contact)
        response = self.assertGET200(url)
        self.assertEqual(expected, response.json())

        response = self.assertGET200(url + '&all=0')
        self.assertEqual(expected, response.json())

        response = self.assertGET200(url + '&all=false')
        self.assertEqual(expected, response.json())

        self.assertGET404(url + '&all=invalid')

    def test_filters_for_ctype03(self):
        self.login(is_superuser=False, allowed_apps=['documents'])
        self.assertGET403(self._build_get_filter_url(self.ct_contact))

    def test_filters_for_ctype04(self):
        "Include 'All' fake filter."
        self.login()

        create_filter = EntityFilter.objects.smart_update_or_create
        efilter01 = create_filter('test-filter01', 'Filter 01', FakeContact, is_custom=True)
        efilter02 = create_filter('test-filter02', 'Filter 02', FakeContact, is_custom=True)
        create_filter('test-filter03', 'Filter 03', FakeOrganisation, is_custom=True)

        expected = [
            ['',           pgettext('creme_core-filter', 'All')],
            [efilter01.id, 'Filter 01'],
            [efilter02.id, 'Filter 02'],
        ]

        url = self._build_get_filter_url(self.ct_contact)
        response = self.assertGET200(url + '&all=1')
        self.assertEqual(expected, response.json())

        response = self.assertGET200(url + '&all=true')
        self.assertEqual(expected, response.json())

        response = self.assertGET200(url + '&all=True')
        self.assertEqual(expected, response.json())


class UserChoicesTestCase(ViewsTestCase):
    EF_TEST = 26
    URL = reverse('creme_core__efilter_user_choices')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class CivOperand(operands.ConditionDynamicOperand):
            type_id = '__mainciv__'
            model = FakeCivility

        class SuperUsersOperand(operands.ConditionDynamicOperand):
            type_id = '__superusers__'
            verbose_name = 'Super users'
            model = CremeUser

        class MainUserOperand(operands.ConditionDynamicOperand):
            type_id = '__mainuser__'
            verbose_name = 'Main user'
            model = CremeUser

        entity_filter_registries.register(_EntityFilterRegistry(
            id=cls.EF_TEST,
            verbose_name='Test registry',
        ).register_operands(
            CivOperand,
            SuperUsersOperand,
            MainUserOperand,
        ))

        cls.SuperUsersOperand = SuperUsersOperand
        cls.MainUserOperand   = MainUserOperand

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        entity_filter_registries.unregister(cls.EF_TEST)

    def test_user_choices01(self):
        user = self.login()

        # Alphabetically-first user (__str__, not username)
        first_user = CremeUser.objects.create_user(
            username='noir', email='chloe@noir.jp',
            first_name='Chloe', last_name='Noir',
            password='uselesspw',
        )
        self.assertGreater(str(user), str(first_user))

        url = self.URL
        choices1 = self.assertGET200(url).json()
        self.assertIsList(choices1, min_length=3)

        self.assertListEqual(
            ['__currentuser__', _('Current user')],
            choices1[0],
        )

        def find_user(u):
            user_id = u.id

            for i, choice in enumerate(choices1):
                if user_id == choice[0]:
                    return i, choice[1]

            self.fail(f'User "{u}" not found in {choices1}')

        user_index, user_label = find_user(user)
        self.assertEqual(user_label, str(user))

        other_user = self.other_user
        other_index, other_label = find_user(self.other_user)
        self.assertEqual(other_label, str(other_user))

        first_index, first_label = find_user(first_user)
        self.assertEqual(first_label, str(first_user))

        self.assertGreater(other_index, user_index)
        self.assertGreater(user_index,  first_index)

        # "filter_type" ---
        choices2 = self.assertGET200(
            f'{url}?filter_type={EF_USER}'
        ).json()
        self.assertEqual(choices1, choices2)

        choices3 = self.assertGET200(
            f'{url}?filter_type={EF_CREDENTIALS}'
        ).json()
        self.assertEqual(choices1, choices3)

        self.assertGET404(url + '?filter_type=1024')

    def test_user_choices02(self):
        "Other registered operands."
        self.login()

        choices = self.assertGET200(
            f'{self.URL}?filter_type={self.EF_TEST}'
        ).json()
        self.assertEqual(self.MainUserOperand.type_id,   choices[0][0])
        self.assertEqual(self.SuperUsersOperand.type_id, choices[1][0])
