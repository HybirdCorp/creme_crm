# -*- coding: utf-8 -*-

from django.test import RequestFactory

from creme.creme_core.gui.listview import ListViewButton, ListViewButtonList
from creme.creme_core.tests.base import CremeTestCase


class ListViewButtonListTestCase(CremeTestCase):
    class Button01(ListViewButton):
        pass

    class Button02(ListViewButton):
        pass

    class Button03(ListViewButton):
        pass

    def test_append(self):
        blist = ListViewButtonList([self.Button01]).append(
            self.Button02
        ).append(
            self.Button03
        )
        self.assertIsInstance(blist, ListViewButtonList)
        self.assertEqual([self.Button01, self.Button02, self.Button03], blist)

    def test_replace(self):
        blist = ListViewButtonList([self.Button01, self.Button02])
        blist.replace(old=self.Button01, new=self.Button03)
        self.assertEqual([self.Button03, self.Button02], blist)

    def test_instances01(self):
        "No extra context."
        blist = ListViewButtonList([self.Button01, self.Button02])
        instances = [*blist.instances]
        self.assertEqual(2, len(instances))

        button01 = instances[0]
        self.assertIsInstance(button01, self.Button01)
        self.assertEqual({}, button01.get_context(
            request=RequestFactory().get('/'),  # Url doesn't matter
            lv_context={'foo': 'bar'}),
        )

        self.assertIsInstance(instances[1], self.Button02)

    def test_instances02(self):
        "Extra context."
        extra_context = {'extra': 'info'}
        blist = ListViewButtonList([self.Button01]).update_context(**extra_context)

        button01 = next(blist.instances)
        self.assertIsInstance(button01, self.Button01)

        context = button01.get_context(
            request=RequestFactory().get('/'),  # Url doesn't matter
            lv_context={'foo': 'bar'},
        )
        self.assertEqual(extra_context, context)
        self.assertIsNot(extra_context, context)
