 # -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from django.contrib.contenttypes.models import ContentType

#from creme_core.models import CremePropertyType, CremeProperty, CremeEntity, SetCredentials
from creme_core.models import HistoryLine
from creme_core.tests.views.base import ViewsTestCase

from persons.models import Organisation, Sector


__all__ = ('HistoryTestCase',)


class HistoryTestCase(ViewsTestCase):
    def _build_organisation(self, name, **kwargs):
        data = {'name': name}
        data.update(kwargs)

        response = self.client.post('/persons/organisation/add', follow=True, data=data)
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        try:
            orga = Organisation.objects.get(name=name)
        except Organisation.DoesNotExist, e:
            self.fail(str(e))

        return orga

    def test_creation(self):
        self.login()

        old_count = HistoryLine.objects.count()
        gainax = self._build_organisation(user=self.other_user.id, name='Gainax')
        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,                 hline.entity.id)
        self.assertEqual(gainax.entity_type,        hline.entity_ctype)
        self.assertEqual(self.other_user,           hline.entity_owner)
        self.assertEqual('',                        hline.username) #TODO: self.user.username
        self.assertEqual(HistoryLine.TYPE_CREATION, hline.type)
        self.assertEqual([],                        hline.modifications)
        self.assert_((datetime.now() - hline.date) < timedelta(seconds=1))

    def test_edition01(self):
        self.login()

        old_count = HistoryLine.objects.count()

        name = 'gainax'
        old_capital = 12000
        gainax = self._build_organisation(user=self.user.id, name=name, capital=old_capital)

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        capital = old_capital * 2
        response = self.client.post('/persons/organisation/edit/%s' % gainax.id, follow=True,
                                    data={
                                            'user':    self.user.id,
                                            'name':    name,
                                            'capital': capital,
                                         }
                                   )
        self.assertNoFormError(response)

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,                hline.entity.id)
        self.assertEqual(HistoryLine.TYPE_EDITION, hline.type)
        self.assertEqual([['capital', old_capital, capital]], hline.modifications)

    #TODO: change 'name' but keep the old unicode() ???
    def test_edition02(self):
        self.login()

        old_count = HistoryLine.objects.count()

        sector01 = Sector.objects.create(title='Studio')
        sector02 = Sector.objects.create(title='Animation studio')

        name = 'Gainax'
        old_phone = '7070707'
        description = """Oh this is an long description
text that takes several lines
about this fantastic animation studio."""
        gainax = self._build_organisation(user=self.user.id, name=name, phone=old_phone, description=description, sector=sector01.id)

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        phone = old_phone + '07'
        email = 'contact@gainax.jp'
        description += 'In this studio were created lots of excellent animes like "Evangelion" or "Fushigi no umi no Nadia".'
        response = self.client.post('/persons/organisation/edit/%s' % gainax.id, follow=True,
                                    data={
                                            'user':        self.user.id,
                                            'name':        name,
                                            'phone':       phone,
                                            'email':       email,
                                            'description': description,
                                            'sector':      sector02.id,
                                         }
                                   )
        self.assertNoFormError(response)

        hline = HistoryLine.objects.latest('date')
        modif = hline.modifications
        self.assert_(isinstance(modif, list))
        self.assertEqual(4, len(modif))
        self.assert_(['phone', old_phone, phone] in modif)
        self.assert_(['email', email] in modif)
        self.assert_(['description'] in modif)
        self.assert_(['sector', sector01.id, sector02.id] in modif)

    def test_edition03(self):
        self.login()

        name = 'gainax'
        capital = 12000
        gainax = self._build_organisation(user=self.user.id, name=name, capital=capital)

        old_count = HistoryLine.objects.count()

        response = self.client.post('/persons/organisation/edit/%s' % gainax.id, follow=True,
                                    data={
                                            'user':    self.user.id,
                                            'name':    name,
                                            'capital': capital,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_deletion(self):
        self.login()

        old_count = HistoryLine.objects.count()
        gainax = Organisation.objects.create(user=self.other_user, name='Gainax')
        entity_repr = unicode(gainax)

        creation_line = HistoryLine.objects.get(entity=gainax)

        self.assertEqual(200, self.client.post('/creme_core/entity/delete/%s' % gainax.id, follow=True).status_code)
        self.failIf(Organisation.objects.filter(pk=gainax.id).count())

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-1]
        self.assert_(hline.entity is None, hline.entity)
        self.assertEqual(entity_repr,               hline.entity_repr)
        self.assertEqual(self.other_user,           hline.entity_owner)
        self.assertEqual(HistoryLine.TYPE_DELETION, hline.type)
        self.assert_((datetime.now() - hline.date) < timedelta(seconds=1))
        self.assertEqual([],                        hline.modifications)

        creation_line = HistoryLine.objects.get(pk=creation_line.id) #refresh
        self.assert_(hline.entity is None)
        self.assertEqual(entity_repr, hline.entity_repr)
