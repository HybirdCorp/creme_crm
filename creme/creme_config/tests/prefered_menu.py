# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import PreferedMenuItem
    from creme.creme_core.gui.menu import creme_menu
    from creme.creme_core.tests.base import CremeTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('PreferedMenuTestCase',)


class PreferedMenuTestCase(CremeTestCase):
    items_info = [{'url': '/creme_config/test_view1', 'label': u"Test view1"},
                  {'url': '/creme_config/test_view2', 'label': u"Test view2"},
                 ]

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')
        cls.autodiscover()

        reg_item = creme_menu.get_app_item('creme_config').register_item
        for item in cls.items_info:
            reg_item(item['url'], _(item['label']), 'creme_config.can_admin')

    def setUp(self):
        self.login()

    def _find_field_index(self, formfield, entry_name):
        for i, (f_entry_name, f_entry_vname) in enumerate(formfield.choices):
            if f_entry_name == entry_name:
                return i

        self.fail('No "%s" in field' % entry_name)

    def _get_indices(self, context, *urls):
        try:
            entries = context['form'].fields['menu_entries']
        except KeyError as e:
            self.fail(str(e))

        find_index = self._find_field_index

        return [find_index(entries, url) for url in urls]

    def _build_post_data(self, *indices_n_urls):
        data = {}

        for i, (index, url) in enumerate(indices_n_urls):
            data['menu_entries_check_%s' % index] = 'on'
            data['menu_entries_value_%s' % index] = url
            data['menu_entries_order_%s' % index] = i

        return data

    def test_edit(self):
        self.assertFalse(PreferedMenuItem.objects.all())

        url = '/creme_config/prefered_menu/edit/'
        response = self.assertGET200(url)

        items_info = self.items_info
        url1 = items_info[0]['url']
        url2 = items_info[1]['url']
        index1, index2 = self._get_indices(response.context, url1, url2)

        response = self.client.post(url, self._build_post_data((index1, url1), (index2, url2)))
        self.assertNoFormError(response, status=302)

        items = PreferedMenuItem.objects.order_by('order')
        self.assertEqual(2, len(items))

        for info, item in zip(items_info, items):
            self.assertIsNone(item.user)
            self.assertEqual(info['url'],   item.url)
            self.assertEqual(info['label'], item.label)

    def test_edit_mine(self):
        url = '/creme_config/prefered_menu/mine/edit/'
        response = self.assertGET200(url)

        items_info = self.items_info
        url1 = items_info[0]['url']
        url2 = items_info[1]['url']
        index1, index2 = self._get_indices(response.context, url1, url2)

        self.assertNoFormError(self.client.post(url, self._build_post_data((index1, url1),
                                                                           (index2, url2),
                                                                          )
                                               )
                              )

        items = PreferedMenuItem.objects.order_by('order')
        self.assertEqual(2, len(items))

        for info, item in zip(items_info, items):
            self.assertEqual(self.user,     item.user)
            self.assertEqual(info['url'],   item.url)
            self.assertEqual(info['label'], item.label)
