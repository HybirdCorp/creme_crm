# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import RelationType, HistoryConfigItem
    from creme.creme_core.tests.base import CremeTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('HistoryConfigTestCase',)


class HistoryConfigTestCase(CremeTestCase):
    ADD_URL = '/creme_config/history/add/'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()

    def test_portal(self):
        self.assertGET200('/creme_config/history/portal/')

    def test_add01(self):
        self.assertFalse(HistoryConfigItem.objects.exists())

        create_rt = RelationType.create
        rtype01 = create_rt(('test-subject_foo', 'fooes'), ('test-object_foo', 'fooed'))[0]
        rtype02 = create_rt(('test-subject_bar', 'bars'),  ('test-object_bar', 'bared'))[0]

        url = self.ADD_URL
        self.assertGET200(url)

        rtype_ids = [rtype01.id, rtype02.id]
        self.assertNoFormError(self.client.post(url, data={'relation_types': rtype_ids}))

        hc_items = HistoryConfigItem.objects.all()
        self.assertEqual(2, len(hc_items))
        self.assertEqual(set(rtype_ids), {hc_item.relation_type.id for hc_item in hc_items})

    def test_add02(self):
        "No doublons"
        create_rt = RelationType.create
        rtype01 = create_rt(('test-subject_foo', 'fooes'), ('test-object_foo', 'fooed'))[0]
        rtype02 = create_rt(('test-subject_bar', 'bars'),  ('test-object_bar', 'bared'))[0]

        HistoryConfigItem.objects.create(relation_type=rtype01)

        rtype_ids = [rtype01.id, rtype02.id]
        response = self.client.post(self.ADD_URL, data={'relation_types': rtype_ids})
        self.assertFormError(response, 'form', field='relation_types',
                             errors=_(u'Select a valid choice. %s is not one of the available choices.') % rtype01.id
                            )

    def test_delete(self):
        rtype = RelationType.create(('test-subject_foo', 'fooes'), ('test-object_foo', 'fooed'))[0]
        hci = HistoryConfigItem.objects.create(relation_type=rtype)

        self.assertPOST200('/creme_config/history/delete', data={'id': hci.id})
        self.assertDoesNotExist(hci)
