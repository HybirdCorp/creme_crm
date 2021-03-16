# -*- coding: utf-8 -*-

from creme.creme_core.models import MenuConfigItem

from ..base import CremeTestCase
from ..fake_menu import FakeContactsEntry


class MenuConfigItemTestCase(CremeTestCase):
    def test_entry_data01(self):
        "Empty"
        item = MenuConfigItem.objects.create(order=0, entry_id=FakeContactsEntry.id)

        item = self.refresh(item)
        self.assertEqual(0, item.order)
        self.assertDictEqual({}, self.refresh(item).entry_data)

    def test_entry_data02(self):
        "Set with attribute."
        label = 'Django'
        item = MenuConfigItem(order=1, entry_id=FakeContactsEntry.id)
        url = 'https://www.djangoproject.com'
        item.entry_data = {'label': label, 'url': url}
        item.save()

        item = self.refresh(item)
        self.assertEqual(1, item.order)
        self.assertDictEqual({'label': label, 'url': url}, item.entry_data)

    def test_entry_data03(self):
        "Set with init."
        url = 'https://www.djangoproject.com'
        item = MenuConfigItem.objects.create(
            order=0, entry_id=FakeContactsEntry.id, entry_data={'url': url},
        )
        self.assertDictEqual({'url': url}, self.refresh(item).entry_data)
