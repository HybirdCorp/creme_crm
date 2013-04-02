# -*- coding: utf-8 -*-

try:
    from functools import partial
    from time import sleep

    from django.contrib.sessions.models import Session

    from ..base import CremeTestCase
    from creme.creme_core.models import CremeEntity
    from creme.creme_core.gui.listview import get_field_name_from_pattern
    from creme.creme_core.gui.last_viewed import LastViewedItem

    from creme.persons.models import Contact
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class GuiTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def test_last_viewed_items(self):
        self.login()

        class FakeRequest(object):
            def __init__(self):
                sessions = Session.objects.all()
                assert 1 == len(sessions)
                self.session = sessions[0].get_decoded()

        def get_items():
            with self.assertNoException():
                return FakeRequest().session['last_viewed_items']

        self.assertEqual(0, len(LastViewedItem.get_all(FakeRequest())))

        create_contact = partial(Contact.objects.create, user=self.user)
        contact01 = create_contact(first_name='Casca',    last_name='Mylove')
        contact02 = create_contact(first_name='Puck',     last_name='Elfman')
        contact03 = create_contact(first_name='Judo',     last_name='Doe')
        contact04 = create_contact(first_name='Griffith', last_name='Femto')

        self.assertGET200(contact01.get_absolute_url())
        items = get_items()
        self.assertEqual(1, len(items))
        self.assertEqual(contact01.pk, items[0].pk)

        self.assertGET200(contact02.get_absolute_url())
        self.assertGET200(contact03.get_absolute_url())
        self.assertGET200(contact04.get_absolute_url())
        items = get_items()
        self.assertEqual(4, len(items))
        self.assertEqual([contact04.pk, contact03.pk, contact02.pk, contact01.pk],
                         [i.pk for i in items]
                        )

        sleep(1)
        contact01.last_name = 'ILoveYou'
        contact01.save()
        self.assertGET200(Contact.get_lv_absolute_url())
        old_item = get_items()[-1]
        self.assertEqual(contact01.pk,       old_item.pk)
        self.assertEqual(unicode(contact01), old_item.name)

        self.assertGET200(contact02.get_absolute_url())
        self.assertEqual([contact02.pk, contact04.pk, contact03.pk, contact01.pk],
                         [i.pk for i in get_items()]
                        )

        contact03.delete()
        self.assertFalse(CremeEntity.objects.filter(pk=contact03.id))
        self.assertGET200(Contact.get_lv_absolute_url())
        self.assertEqual([contact02.pk, contact04.pk, contact01.pk],
                         [i.pk for i in get_items()]
                        )

        contact04.trash()
        self.assertGET200(Contact.get_lv_absolute_url())
        self.assertEqual([contact02.pk, contact01.pk],
                         [i.pk for i in get_items()]
                        )


class ListViewStateTestCase(CremeTestCase):
    def test_get_field_name_from_pattern(self):
        self.assertEqual('foo__bar__plop', get_field_name_from_pattern('foo__bar__plop__icontains'))
        self.assertEqual('foo__bar',       get_field_name_from_pattern('foo__bar__icontains'))
        self.assertEqual('foo__bar',       get_field_name_from_pattern('foo__bar__exact'))
        self.assertEqual('foo__bar',       get_field_name_from_pattern('foo__bar__creme-boolean'))
        self.assertEqual('foo__bar',       get_field_name_from_pattern('foo__bar__exact'))
        self.assertEqual('foo__bar',       get_field_name_from_pattern('foo__bar'))
        self.assertEqual('foo',            get_field_name_from_pattern('foo'))
        self.assertEqual('foo',            get_field_name_from_pattern('foo__isnull'))


from bulk_update import *
from block import *
