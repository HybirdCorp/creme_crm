from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import HistoryConfigItem, RelationType
from creme.creme_core.tests.base import CremeTestCase


class HistoryConfigTestCase(CremeTestCase):
    ADD_URL = reverse('creme_config__create_history_configs')

    def setUp(self):
        super().setUp()
        self.login_as_root()

    def test_portal(self):
        response = self.assertGET200(reverse('creme_config__history'))
        self.assertTemplateUsed(response, 'creme_config/portals/history.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

    def test_add01(self):
        self.assertFalse(HistoryConfigItem.objects.exists())

        rtype1 = RelationType.objects.builder(
            id='test-subject_foo', predicate='fooes',
        ).symmetric(id='test-object_foo', predicate='fooed').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_bar', predicate='bars',
        ).symmetric(id='test-object_bar', predicate='bared').get_or_create()[0]
        rtype3 = RelationType.objects.builder(
            id='test-subject_baz', predicate='bazs',
            enabled=False,
        ).symmetric(id='test-object_baz', predicate='bazed').get_or_create()[0]

        url = self.ADD_URL
        response = self.assertGET200(url)
        self.assertEqual(_('New relation types'), response.context.get('title'))

        with self.assertNoException():
            rtypes_f = response.context['form'].fields['relation_types']

        rtype_ids = {*rtypes_f.queryset.values_list('id', flat=True)}
        self.assertIn(rtype1.id, rtype_ids)
        self.assertIn(rtype2.id, rtype_ids)
        self.assertNotIn(rtype3.id, rtype_ids)

        # ---
        rtype_ids = [rtype1.id, rtype2.id]
        self.assertNoFormError(self.client.post(url, data={'relation_types': rtype_ids}))
        self.assertCountEqual(
            rtype_ids,
            [item.relation_type.id for item in HistoryConfigItem.objects.all()],
        )

    def test_add02(self):
        "No duplicates."
        rtype1 = RelationType.objects.builder(
            id='test-subject_foo', predicate='fooes',
        ).symmetric(id='test-object_foo', predicate='fooed').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_bar', predicate='bars',
        ).symmetric(id='test-object_bar', predicate='bared').get_or_create()[0]

        HistoryConfigItem.objects.create(relation_type=rtype1)

        rtype_ids = [rtype1.id, rtype2.id]
        response = self.client.post(self.ADD_URL, data={'relation_types': rtype_ids})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='relation_types',
            errors=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': rtype1.id},
        )

    def test_delete(self):
        rtype = RelationType.objects.builder(
            id='test-subject_foo', predicate='fooes',
        ).symmetric(id='test-object_foo', predicate='fooed').get_or_create()[0]
        hci = HistoryConfigItem.objects.create(relation_type=rtype)

        self.assertPOST200(reverse('creme_config__remove_history_config'), data={'id': hci.id})
        self.assertDoesNotExist(hci)
