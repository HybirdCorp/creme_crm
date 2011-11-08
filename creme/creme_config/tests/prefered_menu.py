# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme_core.models import PreferedMenuItem
    from creme_core.gui.menu import creme_menu
    from creme_core.tests.base import CremeTestCase
    from creme_core import autodiscover
except Exception as e:
    print 'Error:', e


__all__ = ('PreferedMenuTestCase',)


class PreferedMenuTestCase(CremeTestCase):
    def _find_field_index(self, formfield, entry_name):
        for i, (f_entry_name, f_entry_vname) in enumerate(formfield.choices):
            if f_entry_name == entry_name:
                return i

        self.fail('No "%s" in field' % entry_name)

    def test_edit01(self):
        self.populate('creme_core', 'creme_config')
        self.login()
        autodiscover()

        self.assertFalse(PreferedMenuItem.objects.exists())

        reg_item = creme_menu.get_app_item('creme_config').register_item
        url1 = '/creme_config/test_edit01/test_view1'; label1 = u"Test view1"
        url2 = '/creme_config/test_edit01/test_view2'; label2 = u"Test view2"
        reg_item(url1, _(label1), 'creme_config.can_admin')
        reg_item(url2, _(label2), 'creme_config.can_admin')

        url = '/creme_config/prefered_menu/edit/'
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            entries = response.context['form'].fields['menu_entries']
        except KeyError as e:
            self.fail(str(e))

        index1 = self._find_field_index(entries, url1)
        index2 = self._find_field_index(entries, url2)
        response = self.client.post(url,
                                    data={
                                            'menu_entries_check_%s' % index1: 'on',
                                            'menu_entries_value_%s' % index1: url1,
                                            'menu_entries_order_%s' % index1: 1,

                                            'menu_entries_check_%s' % index2: 'on',
                                            'menu_entries_value_%s' % index2: url2,
                                            'menu_entries_order_%s' % index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        items = PreferedMenuItem.objects.order_by('order')
        self.assertEqual(2, len(items))

        item = items[0]
        self.assertIsNone(item.user)
        self.assertEqual(url1,   item.url)
        self.assertEqual(label1, item.label)

        item = items[1]
        self.assertIsNone(item.user)
        self.assertEqual(url2,   item.url)
        self.assertEqual(label2, item.label)
