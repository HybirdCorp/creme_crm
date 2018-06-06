# -*- coding: utf-8 -*-

try:
    # from unittest import skipIf
    from xml.etree import ElementTree

    import html5lib

    # from django.conf import settings
    from django.test.client import RequestFactory

    from ..base import CremeTestCase
    from creme.creme_core.tests.fake_models import FakeContact, FakeOrganisation, FakeDocument, FakeActivity

    # if not settings.OLD_MENU:
    from creme.creme_core.gui.menu import (ViewableItem, URLItem, LabelItem,
           ItemGroup, ContainerItem, CreationFormsItem, Menu)  # OnClickItem
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


# @skipIf(settings.OLD_MENU, 'Old menu is used, so we do not test the new one.')
class MenuTestCase(CremeTestCase):
    theme = 'icecream'

    def setUp(self):
        super(MenuTestCase, self).setUp()
        self.factory = RequestFactory()
        self.maxDiff = None

    def build_context(self):
        user = getattr(self, 'user', None) or self.login()

        return {'request': self.factory.get('/'),
                'user': user,
                'THEME_NAME': self.theme,
               }

    def test_item_id(self):
        item_id = 'persons-add_contact'
        self.assertEqual(item_id, ViewableItem(item_id).id)

        # Invalid id
        with self.assertRaises(ValueError):
            ViewableItem('persons-add_"contact"')  # " char is forbidden

        with self.assertRaises(ValueError):
            ViewableItem("persons-add_'contact'")  # ' char is forbidden

    def test_item_label(self):
        self.assertEqual('', ViewableItem('add_contact').label)  # TODO: None ??

        my_label = 'Add a contact'
        self.assertEqual(my_label, ViewableItem('add_contact', label=my_label).label)

    def test_item_perm(self):
        self.assertIsNone(ViewableItem('add_contact').perm)

        my_perm = 'persons.add_contact'
        self.assertEqual(my_perm, ViewableItem('add_contact', perm=my_perm).perm)

    def test_item_icon01(self):
        item = ViewableItem('add_contact')
        self.assertIsNone(item.icon)
        self.assertEqual('', item.icon_label)

    def test_item_icon02(self):
        my_icon = 'contact'
        my_icon_label = 'Contact'
        item = ViewableItem('add_contact', icon=my_icon, icon_label=my_icon_label)
        self.assertEqual(my_icon, item.icon)
        self.assertEqual(my_icon_label, item.icon_label)

    def test_item_icon03(self):
        "No icon_label => use label"
        my_label = 'Contact'
        item = ViewableItem('add_contact', icon='contact', label=my_label)
        self.assertEqual(my_label, item.icon_label)

    def test_add_items01(self):
        menu = Menu()
        item1 = ViewableItem('add_contact')
        self.assertIsNone(item1.priority)

        item2 = ViewableItem('add_orga')

        menu.add(item1).add(item2)
        self.assertEqual([item1, item2], list(menu))

        self.assertEqual(1, item1.priority)

    def test_add_items02(self):
        "Duplicated ID"
        menu = Menu()
        id_ = 'add_contact'
        item1 = ViewableItem(id_)
        item2 = ViewableItem(id_)

        menu.add(item1)

        with self.assertRaises(ValueError):
            menu.add(item2)

    def test_group_id(self):
        group_id = 'persons'
        self.assertEqual(group_id, ItemGroup(group_id).id)

        # Invalid id
        with self.assertRaises(ValueError):
            ItemGroup('"persons"-app')  # " char ...

    def test_group_label(self):
        self.assertEqual('', ItemGroup('creations').label)

        my_label = 'Add entities...'
        self.assertEqual(my_label, ItemGroup('creations', label=my_label).label)

    def test_add_groups(self):
        menu = Menu()
        group = ItemGroup('creations')
        item1 = ViewableItem('add_contact')
        item2 = ViewableItem('add_orga')
        item3 = ViewableItem('add_activity')

        group.add(item2).add(item3)
        menu.add(item1).add(group)
        self.assertEqual([item1, item2, item3], list(menu))

        # Add an Item already added
        with self.assertRaises(ValueError):
            group.add(item2)

    def test_url_item01(self):
        my_label = 'Add a contact'
        url = '/persons/add_a_contact'
        item = URLItem('add_contact', label=my_label, url=url)
        self.assertEqual(my_label, item.label)
        self.assertEqual(url,      item.url)

        url = '/tests/customers'
        item.url = lambda: url
        self.assertEqual(url, item.url)

    def test_url_item02(self):
        "For list-view"
        id_ = 'add_contact'
        item = URLItem.list_view(id_, model=FakeContact)
        self.assertIsInstance(item, URLItem)
        self.assertEqual(id_,               item.id)
        self.assertEqual('/tests/contacts', item.url)
        self.assertEqual(u'Test Contacts',  item.label)
        self.assertEqual('creme_core',      item.perm)

        # Custom attributes
        label = 'My contacts'
        url = '/tests/my_contacts'
        perm = 'persons'
        item = URLItem.list_view(id_, model=FakeContact, perm=perm,
                                 label=label, url=url,
                                 )
        self.assertEqual(label, item.label)
        self.assertEqual(url,   item.url)
        self.assertEqual(perm,  item.perm)

    def test_url_item03(self):
        "For creation view"
        id_ = 'add_contact'
        item = URLItem.creation_view(id_, model=FakeContact)
        self.assertIsInstance(item, URLItem)
        self.assertEqual(id_,                          item.id)
        self.assertEqual('/tests/contact/add',         item.url)
        self.assertEqual(u'Test Contact',              item.label)
        self.assertEqual('creme_core.add_fakecontact', item.perm)

        # Custom attributes
        label = 'My contact'
        url = '/tests/my_contacts/add'
        perm = 'persons'
        item = URLItem.creation_view(id_, model=FakeContact, perm=perm,
                                     label=label, url=url,
                                    )
        self.assertEqual(label, item.label)
        self.assertEqual(url,   item.url)
        self.assertEqual(perm,  item.perm)

    # def test_onclick_item(self):
    #     my_label = 'Add a contact'
    #     js = 'creme.utils.popupCreation()'
    #     item = OnClickItem('add_contact', label=my_label, onclick=js)
    #     self.assertEqual(my_label, item.label)
    #     self.assertEqual(js,       item.onclick)

    def test_add_items_to_group01(self):
        group = ItemGroup('persons')
        item1 = ViewableItem('add_contact')
        item2 = ViewableItem('add_orga')

        group.add(item1)
        group.add(item2)

        self.assertEqual([item1, item2], list(group))

    def test_add_items_to_group02(self):
        "Priority"
        group = ItemGroup('persons')
        item1 = ViewableItem('add_contact')
        item2 = ViewableItem('add_orga')
        item3 = ViewableItem('add_address')
        item4 = ViewableItem('add_customer')
        item5 = ViewableItem('add_shipping_addr')
        item6 = ViewableItem('add_billing_addr')

        group.add(item1)
        group.add(item2, priority=1)
        self.assertEqual([item1, item2], list(group))

        group.add(item3, priority=3)
        group.add(item4, priority=2)
        self.assertEqual([item1, item2, item4, item3], list(group))
        self.assertEqual(3, item3.priority)

        # Not property => end
        group.add(item5)
        group.add(item6, priority=2)  # priority of previous has been set
        self.assertEqual([item1, item2, item4, item6, item3, item5], list(group))

    def test_add_items_to_group03(self):
        "Several items at once"
        group = ItemGroup('persons')
        item1 = ViewableItem('add_contact')
        item2 = ViewableItem('add_orga')

        group.add(item2, item1)
        self.assertEqual([item2, item1], list(group))

    def test_add_items_to_group04(self):
        "First has priority"
        group = ItemGroup('persons')
        item1 = ViewableItem('add_contact')
        item2 = ViewableItem('add_orga')

        group.add(item1, priority=10)
        group.add(item2, priority=1)
        self.assertEqual([item2, item1], list(group))

    def test_container_get01(self):
        group = ItemGroup('creations')
        item1 = ViewableItem('add_contact')
        item2 = ViewableItem('add_orga')
        group.add(item1).add(item2)

        self.assertEqual(item1, group.get(item1.id))
        self.assertEqual(item2, group.get(item2.id))
        self.assertRaises(KeyError, group.get, 'unknown_id')

    def test_container_get02(self):
        menu = Menu()
        container1 = ContainerItem('creations')
        container2 = ContainerItem('editions')
        group1 = ItemGroup('add_persons')
        group2 = ItemGroup('add_tickets')
        item1 = ViewableItem('add_contact')
        item2 = ViewableItem('add_orga')
        item3 = ViewableItem('add_ticket')

        menu.add(container1.add(group1.add(item1).add(item2)).add(group2.add(item3))) \
            .add(container2)

        self.assertEqual(group1, menu.get(container1.id, group1.id))
        self.assertEqual(item1,  menu.get(container1.id, group1.id, item1.id))
        self.assertEqual(item3,  menu.get(container1.id, group2.id, item3.id))
        self.assertRaises(KeyError, menu.get, container2.id, group1.id)
        self.assertRaises(KeyError, menu.get, container1.id, group1.id, 'unknown_id')
        # 'item1' is not a container
        self.assertRaises(KeyError, menu.get, container1.id, group1.id, item1.id, 'whatever')

    def test_remove_items_from_group(self):
        group = ItemGroup('creations')
        item1 = ViewableItem('add_contact')
        item2 = ViewableItem('add_orga')
        item3 = ViewableItem('add_event')
        item4 = ViewableItem('add_activity')
        group.add(item1, item2, item3, item4)

        group.remove(item2.id)
        self.assertEqual([item1, item3, item4], list(group))

        group.remove(item1.id, item4.id)
        self.assertEqual([item3], list(group))

        group.remove('unknown_id')  # TODO: exception ?? boolean ??

        with self.assertNoException():
            group.add(item1)

    def test_clear_group(self):
        group = ItemGroup('creations')
        item1 = ViewableItem('add_contact')
        item2 = ViewableItem('add_orga')

        group.add(item1).add(item2)
        group.clear()
        self.assertFalse(list(group))

        with self.assertNoException():
            group.add(item1)

    def test_pop_group(self):
        group = ItemGroup('creations')
        item1 = ViewableItem('add_contact')
        item2 = ViewableItem('add_orga')
        group.add(item1, priority=2).add(item2, priority=3)

        item2b = group.pop(item2.id)
        self.assertEqual(item2, item2b)
        self.assertEqual([item1], list(group))

        self.assertRaises(KeyError, group.pop, item2.id)

        group.add(item2b, priority=1)
        self.assertEqual([item2b, item1], list(group))

    def test_change_priority_group(self):
        group = ItemGroup('creations')
        item1 = ViewableItem('add_contact')
        item2 = ViewableItem('add_orga')
        item3 = ViewableItem('add_event')
        group.add(item1, priority=2).add(item2, priority=3).add(item3, priority=4)

        group.change_priority(1, item3.id, item2.id)
        self.assertEqual([item3, item2, item1], list(group))

    def test_container_item(self):
        my_label = 'Creations...'
        container = ContainerItem('persons', label=my_label)
        self.assertEqual(my_label, container.label)

        child1 = ViewableItem('persons-add_contact')
        child2 = ViewableItem('persons-add_orga')

        container.add(child2, child1)
        self.assertEqual([child2, child1], list(container))

    def test_get_or_create(self):
        menu = Menu()

        id_ = 'analysis'
        label = u'Analysis'
        container1 = menu.get_or_create(ContainerItem, id_, priority=5,
                                        defaults={'label': label},
                                       )
        self.assertIsInstance(container1, ContainerItem)
        self.assertEqual(id_,   container1.id)
        self.assertEqual(label, container1.label)

        container2 = menu.get_or_create(ContainerItem, id_, priority=5,
                                        defaults={'label': label + ' #2'},
                                       )
        self.assertIs(container1, container2)
        self.assertEqual(label, container2.label)
        self.assertEqual([container1], list(menu))

        with self.assertRaises(ValueError):
            menu.get_or_create(ItemGroup, id_, priority=5,
                               defaults={'label': label},
                              )

        # defaults is None
        gid = 'my_group'
        group = menu.get_or_create(ItemGroup, gid, priority=5,
                                        # defaults={'label': label},
                                  )
        self.assertIsInstance(group, ItemGroup)
        self.assertEqual(gid, group.id)
        self.assertFalse(group.label)

    def test_creation_forms_item01(self):
        user = self.login()
        cfi = CreationFormsItem('any_forms', label=u'Other type of entity')

        cfi.get_or_create_group('persons', u'Directory') \
           .add_link('add_contact', label='Contact', url='/tests/contact/add', perm='creme_core.add_fakecontact')
        self.assertEqual(
            [[{'label': u'Directory', 'links': [{'label': 'Contact', 'url': '/tests/contact/add'}]}]],
            cfi.as_grid(user)
        )

        cfi.get_or_create_group('persons', u'Directory') \
           .add_link('add_orga', label='Organisation', url='/tests/organisation/add', perm='creme_core.add_fakeorganisation')
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Contact',      'url': '/tests/contact/add'},
                         {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
              },
             ]
            ],
            cfi.as_grid(user)
        )

        cfi.get_or_create_group('activities', u'Activities') \
           .add_link('add_pcall',   label='Phone call', url='/tests/phone_call/add', perm='creme_core.add_fakeactivity') \
           .add_link('add_meeting', label='Meeting',    url='/tests/meeting/add',    perm='creme_core.add_fakeactivity')
        cfi.get_or_create_group('tools', u'Tools')\
           .add_link('add_doc', label='Document', url='/tests/document/add', perm='creme_core.add_fakedocument')
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Contact',      'url': '/tests/contact/add'},
                         {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
              },
             ],
             [{'label': u'Activities',
               'links': [{'label': 'Phone call', 'url': '/tests/phone_call/add'},
                         {'label': 'Meeting',    'url': '/tests/meeting/add'},
                        ],
              },
              {'label': u'Tools',
               'links': [{'label': 'Document', 'url': '/tests/document/add'}],
              },
             ],
            ],
            cfi.as_grid(user)
        )

        cfi.get_or_create_group('analysis', u'Analysis')\
           .add_link('add_report', label='Report', url='/tests/report/add', perm='creme_core.add_fakereport')
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Contact',      'url': '/tests/contact/add'},
                         {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
              },
              {'label': u'Activities',
               'links': [{'label': 'Phone call', 'url': '/tests/phone_call/add'},
                         {'label': 'Meeting',    'url': '/tests/meeting/add'},
                        ],
              },
             ],
             [{'label': u'Tools',
               'links': [{'label': 'Document', 'url': '/tests/document/add'}],
              },
              {'label': u'Analysis',
               'links': [{'label': 'Report', 'url': '/tests/report/add'}],
              },
             ],
            ],
            cfi.as_grid(user)
        )

        cfi.get_or_create_group('management', u'Management') \
           .add_link('add_invoice', label='Invoice', url='/tests/invoice/add', perm='creme_core.add_fakeinvoice')
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Contact',      'url': '/tests/contact/add'},
                         {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
              },
             ],
             [{'label': u'Activities',
               'links': [{'label': 'Phone call', 'url': '/tests/phone_call/add'},
                         {'label': 'Meeting',    'url': '/tests/meeting/add'},
                        ],
              },
              {'label': u'Tools',
               'links': [{'label': 'Document', 'url': '/tests/document/add'}],
              },
             ],
             [{'label': u'Analysis',
               'links': [{'label': 'Report', 'url': '/tests/report/add'}],
              },
              {'label': u'Management',
               'links': [{'label': 'Invoice', 'url': '/tests/invoice/add'}],
              },
             ]
            ],
            cfi.as_grid(user)
        )

        cfi.get_or_create_group('commercial', u'Commercial') \
           .add_link('add_act', label='Act', url='/tests/act/add', perm='creme_core')
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Contact',      'url': '/tests/contact/add'},
                         {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
              },
              {'label': u'Activities',
               'links': [{'label': 'Phone call', 'url': '/tests/phone_call/add'},
                         {'label': 'Meeting',    'url': '/tests/meeting/add'},
                        ],
              },
             ],
             [{'label': u'Tools',
               'links': [{'label': 'Document', 'url': '/tests/document/add'}],
              },
              {'label': u'Analysis',
               'links': [{'label': 'Report', 'url': '/tests/report/add'}],
              },
             ],
             [{'label': u'Management',
               'links': [{'label': 'Invoice', 'url': '/tests/invoice/add'}],
              },
              {'label': u'Commercial',
               'links': [{'label': 'Act', 'url': '/tests/act/add'}],
              },
             ]
            ],
            cfi.as_grid(user)
        )

        cfi.get_or_create_group('marketing', u'Marketing') \
           .add_link('add_campaign', label='Campaign', url='/tests/campaign/add', perm='creme_core')
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Contact',      'url': '/tests/contact/add'},
                         {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
              },
              {'label': u'Activities',
               'links': [{'label': 'Phone call', 'url': '/tests/phone_call/add'},
                         {'label': 'Meeting',    'url': '/tests/meeting/add'},
                        ],
              },
             ],
             [{'label': u'Tools',
               'links': [{'label': 'Document', 'url': '/tests/document/add'}],
              },
              {'label': u'Analysis',
               'links': [{'label': 'Report', 'url': '/tests/report/add'}],
              },
             ],
             [{'label': u'Management',
               'links': [{'label': 'Invoice', 'url': '/tests/invoice/add'}],
              },
              {'label': u'Commercial',
               'links': [{'label': 'Act', 'url': '/tests/act/add'}],
              },
              {'label': u'Marketing',
               'links': [{'label': 'Campaign', 'url': '/tests/campaign/add'}],
              },
             ]
            ],
            cfi.as_grid(user)
        )

    def test_creation_forms_item02(self):
        "Simplified API"
        user = self.login()
        cfi = CreationFormsItem('any_forms', label=u'Other type of entity')

        cfi.get_or_create_group('persons', u'Directory').add_link('add_contact', FakeContact)
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
              },
             ],
            ],
            cfi.as_grid(user)
        )

        # ----
        cfi = CreationFormsItem('any_forms', label=u'Other types')

        label = 'Contact'
        url = '/tests/customer/add'
        cfi.get_or_create_group('persons', u'Directory')\
           .add_link('add_contact', FakeContact, label=label, url=url)
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': label, 'url': url}],
              },
             ],
            ],
            cfi.as_grid(user)
        )

        # ----
        group = CreationFormsItem('any_forms', label=u'Other types').get_or_create_group('persons', u'Directory')

        with self.assertRaises(TypeError):
           group.add_link('add_contact', label=label, url=url)  # No model + missing perm

    def test_creation_forms_item03(self):
        "Link priority"
        user = self.login()
        cfi = CreationFormsItem('any_forms', label=u'Other type of entity')
        group = cfi.get_or_create_group('persons', u'Directory')

        group.add_link('add_contact', FakeContact,      priority=10) \
             .add_link('add_orga',    FakeOrganisation, priority=5)
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Test Organisation', 'url': '/tests/organisation/add'},
                         {'label': 'Test Contact',      'url': '/tests/contact/add'},
                        ],
              },
             ],
            ],
            cfi.as_grid(user)
        )

        group.add_link('add_customer', label='Customer', url='/tests/customer/add', perm='creme_core.add_fakecontact')
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Test Organisation', 'url': '/tests/organisation/add'},
                         {'label': 'Test Contact',      'url': '/tests/contact/add'},
                         {'label': 'Customer',          'url': '/tests/customer/add'},
                        ],
              },
             ],
            ],
            cfi.as_grid(user)
        )

        group.add_link('add_propect', label='Prospect', url='/tests/prospect/add',
                       perm='creme_core.add_fakecontact', priority=15,
                      )
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Test Organisation', 'url': '/tests/organisation/add'},
                         {'label': 'Test Contact',      'url': '/tests/contact/add'},
                         {'label': 'Customer',          'url': '/tests/customer/add'},
                         {'label': 'Prospect',          'url': '/tests/prospect/add'},
                        ],
              },
             ],
            ],
            cfi.as_grid(user)
        )

        group.change_priority(1, 'add_propect', 'add_customer')
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Prospect',          'url': '/tests/prospect/add'},
                         {'label': 'Customer',          'url': '/tests/customer/add'},
                         {'label': 'Test Organisation', 'url': '/tests/organisation/add'},
                         {'label': 'Test Contact',      'url': '/tests/contact/add'},
                        ],
              },
             ],
            ],
            cfi.as_grid(user)
        )

        with self.assertRaises(KeyError):
            group.change_priority(2, 'add_customer', 'unknown')

    def test_creation_forms_item04(self):
        "Remove Link"
        user = self.login()
        cfi = CreationFormsItem('any_forms', label=u'Other type of entity')
        group = cfi.get_or_create_group('persons', u'Directory')

        group.add_link('add_contact', FakeContact) \
             .add_link('add_orga',    FakeOrganisation) \
             .add_link('add_propect', label='Propect', url='/tests/propect/add', perm='creme_core.add_fakecontact')

        group.remove('add_contact', 'add_propect', 'invalid')
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Test Organisation', 'url': '/tests/organisation/add'}],
              },
             ],
            ],
            cfi.as_grid(user)
        )

    def test_creation_forms_item05(self):
        "Group priority"
        user = self.login()
        cfi = CreationFormsItem('any_forms', label=u'Other type of entity')

        cfi.get_or_create_group('persons', u'Directory', priority=10).add_link('add_contact', FakeContact)
        cfi.get_or_create_group('tools', u'Tools', priority=2).add_link('add_doc', FakeDocument)

        self.assertEqual(
            [[{'label': u'Tools',
               'links': [{'label': 'Test Document', 'url': ''}],
              },
             ],
             [{'label': u'Directory',
               'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
              },
             ],
            ],
            cfi.as_grid(user)
        )

        cfi.change_priority(1, 'persons')
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
              },
             ],
             [{'label': u'Tools',
               'links': [{'label': 'Test Document', 'url': ''}],
              },
             ],
            ],
            cfi.as_grid(user)
        )

    def test_creation_forms_item06(self):
        "Remove Group"
        user = self.login()
        cfi = CreationFormsItem('any_forms', label=u'Other type of entity')

        cfi.get_or_create_group('tools', u'Tools').add_link('add_doc', FakeDocument)
        cfi.get_or_create_group('persons', u'Directory').add_link('add_contact', FakeContact)
        cfi.get_or_create_group('activities', u'Activities').add_link('add_act', FakeActivity)

        cfi.remove('tools', 'activities', 'unknown')
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
              },
             ],
            ],
            cfi.as_grid(user)
        )

    def test_creation_forms_item07(self):
        "Credentials"
        user = self.login(is_superuser=False, creatable_models=[FakeContact])
        cfi = CreationFormsItem('any_forms', label=u'Other type of entity')

        cfi.get_or_create_group('persons', u'Directory') \
           .add_link('add_contact', FakeContact) \
           .add_link('add_orga',    FakeOrganisation)
        self.assertEqual(
            [[{'label': u'Directory',
               'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'},
                         {'label': 'Test Organisation'},
                        ],
              },
             ],
            ],
            cfi.as_grid(user)
        )

    def test_creation_forms_item08(self):
        "ID uniqueness"
        cfi = CreationFormsItem('any_forms', label=u'Other type of entity')

        group = cfi.get_or_create_group('persons', u'Directory') \
                   .add_link('add_contact', FakeContact)

        with self.assertRaises(ValueError):
            group.add_link('add_contact', FakeContact, label='Contact')

    def test_render_url_item01(self):
        "URLItem with icon"
        url = '/'
        icon = 'creme'
        label = 'Home'
        item = URLItem('home', url=url, icon=icon, icon_label=label)

        elt = html5lib.parse(item.render(self.build_context()), namespaceHTMLElements=False)
        a_node = elt.find('.//a')
        self.assertEqual(url, a_node.get('href'))

        children = list(a_node)
        self.assertEqual(1, len(children))

        img_node = children[0]
        self.assertEqual('img',              img_node.tag)
        self.assertEqual('header-menu-icon', img_node.get('class'))
        self.assertEqual(label,              img_node.get('alt'))
        self.assertEqual(label,              img_node.get('title'))
        self.assertIn(icon,                  img_node.get('src', ''))
        self.assertFalse(img_node.tail)

    def test_render_url_item02(self):
        "URLItem with icon and label"
        icon = 'creme'
        my_label = 'HOME'
        item = URLItem('home', url='/', label=my_label,
                       icon=icon, icon_label='Home',
                       perm='creme_core',
                      )

        elt = html5lib.parse(item.render(self.build_context()), namespaceHTMLElements=False)
        img_node = elt.find('.//a/img')
        self.assertEqual('header-menu-icon', img_node.get('class'))
        self.assertEqual(my_label,           img_node.tail)

    def test_render_url_item03(self):
        "Not allowed (string perm)"
        self.login(is_superuser=False, allowed_apps=['creme_core'])

        icon = 'creme'
        my_label = 'HOME'
        item = URLItem('home', url='/', label=my_label, icon=icon, icon_label='Home',
                       perm='creme_core.add_fakecontact',
                      )

        elt = html5lib.parse(item.render(self.build_context()), namespaceHTMLElements=False)
        span_node = elt.find('.//span')
        self.assertEqual('ui-creme-navigation-text-entry forbidden', span_node.get('class'))

        children = list(span_node)
        self.assertEqual(1, len(children))
        self.assertEqual('img', children[0].tag)

    def test_render_url_item04(self):
        "Perm is callable"
        self.login(is_superuser=False)

        url = '/creme/add_contact'
        item = URLItem('home', url=url, label='Create contact',
                       perm=lambda user: user.is_superuser
                      )

        elt = html5lib.parse(item.render(self.build_context()), namespaceHTMLElements=False)
        span_node = elt.find('.//span')
        self.assertEqual('ui-creme-navigation-text-entry forbidden', span_node.get('class'))

        # ---
        item.perm = lambda user: True
        elt = html5lib.parse(item.render(self.build_context()), namespaceHTMLElements=False)
        self.assertIsNone(elt.find('.//span'))

        a_node = elt.find('.//a')
        self.assertEqual(url, a_node.get('href'))

    def test_render_label_item(self):
        item_id = 'tools-title'
        label= 'Important title'
        item = LabelItem(item_id, label=label)

        self.assertHTMLEqual('<span class="ui-creme-navigation-text-entry">'
                                '{label}'
                             '</span>'.format(label=label),
                             item.render(self.build_context())
                            )

#     def test_render_onclick_item01(self):
#         "No icon"
#         item = OnClickItem('add_contact', label='Add a contact',
#                            onclick='creme.persons.contact_popup("Create a contact")',  # Should be escaped
#                           )
#
#         self.assertXMLEqual('<a onclick="creme.persons.contact_popup(\u0022Create a contact\u0022)">'
#                                 'Add a contact'
#                             '</a>',
#                             item.render(self.build_context())
#                            )
#
#     def test_render_onclick_item02(self):
#         "Icon & label"
#         icon = 'images/creme_30.png'
#         item = OnClickItem('add_contact', label='Add a contact',
#                            icon=icon, icon_label='Contact',
#                            onclick='creme.persons.add_contact()',
#                           )
#
#         self.assertXMLEqual('<a onclick="creme.persons.add_contact()">'
#                                 '<img src="%s" height="30" width="30" alt="Contact" />'
#                                 'Add a contact'
#                             '</a>' % get_creme_media_url(self.theme, icon),
#                             item.render(self.build_context())
#                            )
#
#
#     def test_render_onclick_item03(self):
#         "Not allowed"
#         self.login(is_superuser=False)
#
#         icon = 'images/creme_30.png'
#         item = OnClickItem('add_contact', label='Add a contact',
#                            icon=icon, icon_label='Contact',
#                            onclick='creme.persons.add_contact()',
#                            perm='creme_core.add_fakecontact',
#                           )
#
#         self.assertXMLEqual('<span class="forbidden">'
#                                 '<img src="%s" height="30" width="30" alt="Contact" />'
#                                 'Add a contact'
#                             '</span>' % get_creme_media_url(self.theme, icon),
#                             item.render(self.build_context())
#                            )

    def test_render_container_item01(self):
        "No icon"
        context = self.build_context()

        label = 'Creations'
        container = ContainerItem('persons', label=label) \
                        .add(URLItem('contacts', url='/persons/contacts',      label='List of contacts'),
                             URLItem('orgas',    url='/persons/organisations', label='List of organisations'),
                            )

        render = container.render(context)
        self.assertTrue(render.startswith(label))
        self.assertHTMLEqual('<ul>'
                                 '<li class="ui-creme-navigation-item-id_contacts ui-creme-navigation-item-level1">'
                                     '<a href="/persons/contacts">List of contacts</a>'
                                 '</li>'
                                 '<li class="ui-creme-navigation-item-id_orgas ui-creme-navigation-item-level1">'
                                     '<a href="/persons/organisations">List of organisations</a>'
                                 '</li>'
                             '</ul>',
                             render[len(label):]
                            )

    def test_render_container_item02(self):
        "No icon"
        context = self.build_context()

        label = 'Contacts'
        icon = 'contact'
        icon_label = 'Contact'
        parent = ContainerItem('persons', label=label, icon=icon, icon_label=icon_label) \
                    .add(URLItem('home', url='/persons/contacts', label='List of contacts'))

        render = parent.render(context, level=1)
        elt = html5lib.parse(render, namespaceHTMLElements=False)

        # ElementTree.dump(elt) >>>
        # <html><head /><body>
        #         <img alt="Contact" class="header-menu-icon"
        #              src="/static_media/icecream/images/contact_16-....png" title="Contact" width="16px" />
        #         Contacts
        #         <ul>
        #             <li class="ui-creme-navigation-item-level2 ui-creme-navigation-item-id_home">
        #                  <a href="/persons/contacts">List of contacts</a>
        #             </li>
        #         </ul>
        # </body>
        img_node = elt.find('.//img')
        self.assertIsNotNone(img_node, 'No <img> tag.')
        self.assertEqual('header-menu-icon', img_node.get('class'))
        self.assertEqual(icon_label,         img_node.get('alt'))
        self.assertEqual(icon_label,         img_node.get('title'))
        self.assertIn(icon,                  img_node.get('src', ''))
        self.assertIn(label,                 img_node.tail)

        ul_node = elt.find('.//ul')
        self.assertIsNotNone(ul_node, 'No <ul> tag.')
        self.assertHTMLEqual('<ul>'
                                 '<li class="ui-creme-navigation-item-id_home ui-creme-navigation-item-level2">'
                                     '<a href="/persons/contacts">List of contacts</a>'
                                 '</li>'
                             '</ul>',
                             ElementTree.tostring(ul_node)
                            )

    def test_render_menu(self):
        menu = Menu().add(URLItem('contacts', url='/persons/contacts',      label='List of contacts'),
                          URLItem('orgas',    url='/persons/organisations', label='List of organisations'),
                         )
        self.assertHTMLEqual('<ul class="ui-creme-navigation">'
                                 '<li class="ui-creme-navigation-item-level0 ui-creme-navigation-item-id_contacts">'
                                     '<a href="/persons/contacts">List of contacts</a>'
                                 '</li>'
                                 '<li class="ui-creme-navigation-item-level0 ui-creme-navigation-item-id_orgas">'
                                     '<a href="/persons/organisations">List of organisations</a>'
                                 '</li>'
                             '</ul>',
                             menu.render(self.build_context())
                            )

# TODO: rendering of group => test separator (2 following group, at start, at end)
