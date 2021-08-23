# -*- coding: utf-8 -*-

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import HistoryConfigItem, RelationType
from creme.creme_core.tests.base import CremeTestCase


class HistoryConfigTestCase(CremeTestCase):
    ADD_URL = reverse('creme_config__create_history_configs')

    def setUp(self):
        super().setUp()
        self.login()

    def test_portal(self):
        response = self.assertGET200(reverse('creme_config__history'))
        self.assertTemplateUsed(response, 'creme_config/portals/history.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

    def test_add01(self):
        self.assertFalse(HistoryConfigItem.objects.exists())

        create_rt = RelationType.objects.smart_update_or_create
        rtype01 = create_rt(('test-subject_foo', 'fooes'), ('test-object_foo', 'fooed'))[0]
        rtype02 = create_rt(('test-subject_bar', 'bars'),  ('test-object_bar', 'bared'))[0]

        url = self.ADD_URL
        response = self.assertGET200(url)
        self.assertEqual(_('New relation types'), response.context.get('title'))

        rtype_ids = [rtype01.id, rtype02.id]
        self.assertNoFormError(self.client.post(url, data={'relation_types': rtype_ids}))

        hc_items = HistoryConfigItem.objects.all()
        self.assertEqual(2, len(hc_items))
        self.assertSetEqual(
            {*rtype_ids},
            {hc_item.relation_type.id for hc_item in hc_items},
        )

    def test_add02(self):
        "No duplicates."
        create_rt = RelationType.objects.smart_update_or_create
        rtype01 = create_rt(('test-subject_foo', 'fooes'), ('test-object_foo', 'fooed'))[0]
        rtype02 = create_rt(('test-subject_bar', 'bars'),  ('test-object_bar', 'bared'))[0]

        HistoryConfigItem.objects.create(relation_type=rtype01)

        rtype_ids = [rtype01.id, rtype02.id]
        response = self.client.post(self.ADD_URL, data={'relation_types': rtype_ids})
        self.assertFormError(
            response, 'form', field='relation_types',
            errors=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': rtype01.id},
        )

    def test_delete(self):
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foo', 'fooes'),
            ('test-object_foo', 'fooed'),
        )[0]
        hci = HistoryConfigItem.objects.create(relation_type=rtype)

        self.assertPOST200(reverse('creme_config__remove_history_config'), data={'id': hci.id})
        self.assertDoesNotExist(hci)
