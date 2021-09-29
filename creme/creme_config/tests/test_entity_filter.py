# -*- coding: utf-8 -*-

from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_config.bricks import EntityFiltersBrick
from creme.creme_core.core.entity_filter import operators
from creme.creme_core.core.entity_filter.condition_handler import (
    RegularFieldConditionHandler,
)
from creme.creme_core.models import EntityFilter, FakeContact
from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class EntityFilterConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    @staticmethod
    def _build_add_url(ct):
        return reverse('creme_config__create_efilter', args=(ct.id,))

    @staticmethod
    def _build_edit_url(efilter):
        return reverse('creme_config__edit_efilter', args=(efilter.id,))

    @staticmethod
    def _build_rfields_data(name, operator, value):
        return json_dump([{
            'field':    {'name': name},
            'operator': {'id': str(operator)},
            'value':    value,
        }])

    def _ctype_labels_from_brick(self, response):
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            EntityFiltersBrick.id_,
        )

        return [
            ct_group[0].tail.strip()
            for ct_group in brick_node.findall(
                './/div[@class="entityfilter-config-group-title"]'
            )
        ]

    def test_portal01(self):
        "Super-user."
        self.login()

        response = self.assertGET200(reverse('creme_config__efilters'))
        self.assertTemplateUsed(response, 'creme_config/portals/entity-filter.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        ct_labels = self._ctype_labels_from_brick(response)
        if len(ct_labels) < EntityFiltersBrick.page_size:
            self.assertIn(FakeContact._meta.verbose_name, ct_labels)

    @skipIfNotInstalled('creme.documents')
    def test_portal02(self):
        "Not super-user."
        from creme import documents

        self.login(is_superuser=False, allowed_apps=['documents'])

        response = self.assertGET200(reverse('creme_config__efilters'))
        self.assertCountEqual(
            self._ctype_labels_from_brick(response),
            [
                model._meta.verbose_name
                for model in (documents.get_document_model(), documents.get_folder_model())
            ],
        )

    @override_settings(FILTERS_INITIAL_PRIVATE=False)
    def test_create01(self):
        "Check app credentials."
        self.login(is_superuser=False, allowed_apps=['documents'])

        ct = ContentType.objects.get_for_model(FakeContact)

        uri = self._build_add_url(ct)
        self.assertGET403(uri)

        self.role.allowed_apps = ['documents', 'creme_core']
        self.role.save()
        response1 = self.assertGET200(uri)
        context1 = response1.context
        self.assertEqual(
            _('Create a filter for «{model}»').format(model='Test Contact'),
            context1.get('title'),
        )

        with self.assertNoException():
            form = context1['form']
            # NB: difficult to test the content in a robust way (depends on the DB config)
            context1['help_message']  # NOQA

        self.assertIs(form.initial.get('is_private'), False)

        name = 'Filter 01'
        operator = operators.IEQUALS
        field_name = 'last_name'
        value = 'Ikari'
        response = self.client.post(
            uri,
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

        efilter = self.get_object_or_fail(EntityFilter, name=name)
        self.assertEqual(ct, efilter.entity_type)
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

    @override_settings(FILTERS_INITIAL_PRIVATE=True)
    def test_create02(self):
        self.login(is_superuser=False)

        context = self.assertGET200(
            self._build_add_url(ContentType.objects.get_for_model(FakeContact))
        ).context

        with self.assertNoException():
            form = context['form']

        self.assertIs(form.initial.get('is_private'), True)

    def test_edit01(self):
        self.login()

        name = 'My filter'
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', name, FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='first_name',
                    operator=operators.CONTAINS, values=['Atom'],
                ),
            ],
        )

        url = self._build_edit_url(efilter)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Edit «{object}»').format(object=efilter.name),
            context1.get('title'),
        )

        with self.assertNoException():
            submit_label = context1['submit_label']

            # NB: difficult to test the content in a robust way (depends on the DB config)
            context1['help_message']  # NOQA

        self.assertEqual(_('Save the filter'), submit_label)

        # ---
        name += ' (edited)'
        field_operator = operators.IEQUALS
        field_name = 'last_name'
        field_value = 'Ikari'
        response2 = self.client.post(
            url, follow=True,
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
        self.assertEqual(name, efilter.name)
        self.assertIs(efilter.is_custom, True)
        self.assertIsNone(efilter.user)

        conditions = efilter.conditions.order_by('id')
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(field_name,                           condition.name)
        self.assertDictEqual(
            {'operator': field_operator, 'values': [field_value]},
            condition.value,
        )

    def test_edit02(self):
        "Can not edit Filter that belongs to another user."
        self.login(is_superuser=False, allowed_apps=['creme_core'])

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Filter01', FakeContact, user=self.other_user, is_custom=True,
        )
        self.assertGET403(self._build_edit_url(efilter))
