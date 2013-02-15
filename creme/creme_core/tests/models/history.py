 # -*- coding: utf-8 -*-

try:
    from datetime import datetime
    from time import sleep

    from django.utils.translation import ugettext as _

    from creme_core.models import *
    from creme_core.tests.views.base import ViewsTestCase

    from persons.models import Contact, Organisation, Sector
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('HistoryTestCase',)


class HistoryTestCase(ViewsTestCase):
    FSTRING_1_VALUE  = _(u'Set field “%(field)s”')
    FSTRING_2_VALUES = _(u'Set field “%(field)s” to “%(value)s”')
    FSTRING_3_VALUES = _(u'Set field “%(field)s” from “%(oldvalue)s” to “%(value)s”')

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.old_time = datetime.now().replace(microsecond=0)
        self.login()

    def _build_organisation(self, name, extra_args=None, **kwargs):
        data = {'name': name}
        data.update(kwargs)

        if extra_args:
            data.update(extra_args)

        self.assertNoFormError(self.client.post('/persons/organisation/add', follow=True, data=data))

        return self.get_object_or_fail(Organisation, name=name)

    def _build_contact(self, first_name, last_name, extra_args=None, **kwargs):
        data = {'first_name': first_name, 'last_name': last_name}
        data.update(kwargs)

        if extra_args:
            data.update(extra_args)

        self.assertNoFormError(self.client.post('/persons/contact/add', follow=True, data=data))

        return self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)

    def assertBetweenDates(self, hline):
        now = datetime.now()
        hdate = hline.date
        old_time = self.old_time
        self.assertTrue(old_time <= hdate <= now,
                        'old_time=%s ; hline.date=%s ; now=%s' % (old_time, hdate, now)
                       )

    def test_creation01(self):
        old_count = HistoryLine.objects.count()
        gainax = self._build_organisation(user=self.other_user.id, name='Gainax')
        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,                 hline.entity.id)
        self.assertEqual(gainax.entity_type,        hline.entity_ctype)
        self.assertEqual(self.other_user,           hline.entity_owner)
        self.assertEqual(self.user.username,        hline.username)
        self.assertEqual(HistoryLine.TYPE_CREATION, hline.type)
        self.assertEqual([],                        hline.modifications)
        self.assertBetweenDates(hline)

    def test_creation02(self):
        "Double save() beacuse of addresses caused problems"
        old_count = HistoryLine.objects.count()
        country = 'Japan'
        gainax = self._build_organisation(user=self.other_user.id, name='Gainax',
                                          extra_args={'billing_address-country': country}
                                         )
        self.assertIsNotNone(gainax.billing_address)
        self.assertEqual(country, gainax.billing_address.country)

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,                 hline.entity.id)
        self.assertEqual(gainax.entity_type,        hline.entity_ctype)
        self.assertEqual(self.other_user,           hline.entity_owner)
        self.assertEqual(HistoryLine.TYPE_CREATION, hline.type)
        self.assertEqual([],                        hline.modifications)
        self.assertBetweenDates(hline)

    def test_edition01(self):
        old_count = HistoryLine.objects.count()

        name = 'gainax'
        old_capital = 12000
        gainax = self._build_organisation(user=self.user.id, name=name, capital=old_capital)

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        capital = old_capital * 2
        response = self.client.post('/persons/organisation/edit/%s' % gainax.id, follow=True,
                                    data={'user':    self.user.id,
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
        old_count = HistoryLine.objects.count()

        sector01 = Sector.objects.create(title='Studio')
        sector02 = Sector.objects.create(title='Animation studio')

        name = 'Gainax'
        old_phone = '7070707'
        description = """Oh this is an long description
text that takes several lines
about this fantastic animation studio."""
        gainax = self._build_organisation(user=self.user.id, name=name, phone=old_phone,
                                          description=description, sector=sector01.id,
                                          subject_to_vat=False,
                                         )

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        phone = old_phone + '07'
        email = 'contact@gainax.jp'
        description += 'In this studio were created lots of excellent animes like "Evangelion" or "Fushigi no umi no Nadia".'
        response = self.client.post('/persons/organisation/edit/%s' % gainax.id, follow=True,
                                    data={'user':          self.user.id,
                                          'name':          name,
                                          'phone':         phone,
                                          'email':         email,
                                          'description':   description,
                                          'sector':        sector02.id,
                                          'creation_date': '1984-12-24',
                                          'subject_to_vat': True,
                                         }
                                   )
        self.assertNoFormError(response)

        hline = HistoryLine.objects.filter(type=HistoryLine.TYPE_EDITION, entity=gainax).latest('date')
        modifs = hline.modifications
        self.assertIsInstance(modifs, list)
        self.assertEqual(6, len(modifs))
        self.assertIn(['phone', old_phone, phone], modifs)
        self.assertIn(['email', email], modifs)
        self.assertIn(['description'], modifs)
        self.assertIn(['sector', sector01.id, sector02.id], modifs)
        self.assertIn(['creation_date'], modifs)
        self.assertIn(['subject_to_vat', True], modifs, modifs)

        vmodifs = hline.verbose_modifications
        self.assertEqual(6, len(vmodifs))

        self.assertIn(self.FSTRING_3_VALUES % {'field':    _(u'Phone number'),
                                               'oldvalue': old_phone,
                                               'value':    phone,
                                              },
                      vmodifs
                     )
        self.assertIn(self.FSTRING_2_VALUES % {'field': _(u'Email address'),
                                               'value': email,
                                              },
                      vmodifs
                     )
        self.assertIn(self.FSTRING_1_VALUE % {'field': _(u'Description')}, vmodifs)
        self.assertIn(self.FSTRING_3_VALUES % {'field':    _(u'Sector'),
                                               'oldvalue': sector01,
                                               'value':    sector02,
                                              },
                      vmodifs
                     )
        self.assertIn(self.FSTRING_1_VALUE % {'field': _(u'Date of creation of the organisation')},
                      vmodifs
                     )
        self.assertIn(self.FSTRING_2_VALUES % {'field': _(u'Subject to VAT'),
                                               'value': _('True'),
                                              },
                      vmodifs
                     )

    def test_edition03(self):
        "No change"
        name = 'gainax'
        capital = 12000
        gainax = self._build_organisation(user=self.user.id, name=name, capital=capital)
        old_count = HistoryLine.objects.count()

        response = self.client.post('/persons/organisation/edit/%s' % gainax.id, follow=True,
                                    data={'user':    self.user.id,
                                          'name':    name,
                                          'capital': capital,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_edition04(self):
        "Ignore the changes : None -> ''."
        name = 'gainax'
        old_capital = 12000
        gainax = Organisation.objects.create(user=self.user, name=name, capital=old_capital)

        capital = old_capital * 2
        response = self.client.post('/persons/organisation/edit/%s' % gainax.id, follow=True,
                                    data={'user':           self.user.id,
                                          'name':           name,
                                          'capital':        capital,
                                          'subject_to_vat': True,
                                         }
                                   )
        self.assertNoFormError(response)

        hline = HistoryLine.objects.order_by('-id')[0]
        self.assertEqual(gainax.id,                hline.entity.id)
        self.assertEqual(HistoryLine.TYPE_EDITION, hline.type)
        self.assertEqual([['capital', old_capital, capital]], hline.modifications)

    def test_deletion(self):
        old_count = HistoryLine.objects.count()
        gainax = Organisation.objects.create(user=self.other_user, name='Gainax')
        entity_repr = unicode(gainax)

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        creation_line = HistoryLine.objects.get(entity=gainax)

        self.assertPOST200('/creme_core/entity/delete/%s' % gainax.id, follow=True)
        self.assertFalse(Organisation.objects.filter(pk=gainax.id).exists())

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-1]
        self.assertIsNone(hline.entity)
        self.assertEqual(entity_repr,               hline.entity_repr)
        self.assertEqual(self.other_user,           hline.entity_owner)
        self.assertEqual(self.user.username,        hline.username)
        self.assertEqual(HistoryLine.TYPE_DELETION, hline.type)
        self.assertEqual([],                        hline.modifications)
        self.assertBetweenDates(hline)

        creation_line = self.refresh(creation_line)
        self.assertIsNone(hline.entity)
        self.assertEqual(entity_repr, hline.entity_repr)

    def test_related_edition01(self):
        ghibli = self._build_organisation(user=self.user.id, name='Ghibli')

        first_name = 'Hayao'
        last_name  = 'Miyazaki'
        hayao  = self._build_contact(user=self.user.id, first_name=first_name, last_name=last_name)

        rtype, srtype = RelationType.create(('test-subject_employed', 'is employed'),
                                            ('test-object_employed', 'employs')
                                           )
        Relation.objects.create(user=self.user, subject_entity=hayao, object_entity=ghibli, type=rtype)

        old_count = HistoryLine.objects.count()
        response = self.client.post('/persons/contact/edit/%s' % hayao.id, follow=True,
                                    data={'user':        self.user.id,
                                          'first_name':  first_name,
                                          'last_name':   last_name,
                                          'description': 'A great animation movie maker'
                                         }
                                   )
        self.assertNoFormError(response)

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(HistoryLine.TYPE_EDITION, hline.type)
        self.assertIsNone(hline.related_line)

    def test_related_edition02(self):
        ghibli = self._build_organisation(user=self.user.id, name='Ghibli')
        sleep(1) #ensure that 'modified' fields are different

        first_name = 'Hayao'
        last_name  = 'Miyazaki'
        hayao  = self._build_contact(user=self.user.id, first_name=first_name, last_name=last_name)
        self.assertNotEqual(hayao.modified, ghibli.modified)

        rtype, srtype = RelationType.create(('test-subject_employed', 'is employed'),
                                            ('test-object_employed', 'employs')
                                           )
        Relation.objects.create(user=self.user, subject_entity=hayao, object_entity=ghibli, type=rtype)

        HistoryConfigItem.objects.create(relation_type=rtype)

        old_count = HistoryLine.objects.count()
        response = self.client.post('/persons/contact/edit/%s' % hayao.id, follow=True,
                                    data={'user':        self.user.id,
                                          'first_name':  first_name,
                                          'last_name':   last_name,
                                          'description': 'A great animation movie maker',
                                         }
                                   )
        self.assertNoFormError(response)

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 2, len(hlines))

        edition_hline = hlines[-2]
        self.assertEqual(HistoryLine.TYPE_EDITION, edition_hline.type)

        hline = hlines[-1]
        self.assertEqual(ghibli.id,                hline.entity.id)
        self.assertEqual(ghibli.entity_type,       hline.entity_ctype)
        self.assertEqual(self.user,                hline.entity_owner)
        self.assertEqual(HistoryLine.TYPE_RELATED, hline.type)
        self.assertEqual(unicode(ghibli),          hline.entity_repr)
        self.assertEqual([],                       hline.modifications)
        self.assertEqual(edition_hline.id,         hline.related_line.id)
        self.assertBetweenDates(hline)
        self.assertEqual(self.refresh(hayao).modified, hline.date)

    def test_add_property01(self):
        gainax = Organisation.objects.create(user=self.user, name='Gainax')
        old_count = HistoryLine.objects.count()

        sleep(1) #ensure than 'modified' field is not 'now()'

        ptype = CremePropertyType.create(str_pk='test-prop_make_animes', text='Make animes')
        prop = CremeProperty.objects.create(type=ptype, creme_entity=gainax)

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,                 hline.entity.id)
        self.assertEqual(unicode(gainax),           hline.entity_repr)
        self.assertEqual(HistoryLine.TYPE_PROPERTY, hline.type)
        self.assertEqual([ptype.id],                hline.modifications)
        self.assertEqual(False,                     hline.is_about_relation)
        self.assertGreater(hline.date, gainax.modified)

        FSTRING = _(u'Add property “%s”')
        self.assertEqual([FSTRING % ptype.text], hline.verbose_modifications)

        expected = [FSTRING % ptype.id]
        prop.delete(); ptype.delete()
        self.assertEqual(expected, self.refresh(hline).verbose_modifications)

    def test_add_relation(self):
        user = self.user
        nerv = Organisation.objects.create(user=user, name='Nerv')
        rei  = Contact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        old_count = HistoryLine.objects.count()

        sleep(1) #ensure than relation is younger than entities

        rtype, srtype = RelationType.create(('test-subject_employed', 'is employed'),
                                            ('test-object_employed', 'employs')
                                           )
        relation = Relation.objects.create(user=user, subject_entity=rei, object_entity=nerv, type=rtype)
        relation = self.refresh(relation) #refresh to get the right modified value

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-2]
        self.assertEqual(rei.id,                    hline.entity.id)
        self.assertEqual(unicode(rei),              hline.entity_repr)
        self.assertEqual(HistoryLine.TYPE_RELATION, hline.type)
        self.assertEqual([rtype.id],                hline.modifications)
        self.assertEqual(relation.modified,         hline.date)
        self.assertEqual(True,                      hline.is_about_relation)

        hline_sym = hlines[-1]
        self.assertEqual(nerv.id,                        hline_sym.entity.id)
        self.assertEqual(unicode(nerv),                  hline_sym.entity_repr)
        self.assertEqual(HistoryLine.TYPE_SYM_RELATION,  hline_sym.type)
        self.assertEqual([srtype.id],                    hline_sym.modifications)
        self.assertEqual(relation.modified,              hline_sym.date)
        self.assertIs(True,                              hline.is_about_relation)

        self.assertEqual(hline_sym.id, hline.related_line.id)
        self.assertEqual(hline.id,     hline_sym.related_line.id)

        FSTRING = _(u'Add a relationship “%s”')
        self.assertEqual([FSTRING % rtype.predicate], hline.verbose_modifications)
        self.assertEqual([FSTRING % srtype.predicate], hline_sym.verbose_modifications)

        rtype_id = rtype.id
        relation.delete(); rtype.delete()
        self.assertFalse(RelationType.objects.filter(pk=rtype_id).exists())
        self.assertEqual([FSTRING % rtype_id], self.refresh(hline).verbose_modifications)

    def test_multi_save01(self):
        old_last_name = 'Ayami'
        new_last_name = 'Ayanami'

        rei = Contact.objects.create(user=self.user, first_name='Rei', last_name=old_last_name)
        self.assertEqual(1, HistoryLine.objects.filter(entity=rei.id).count())

        rei.last_name = new_last_name
        rei.save()

        hlines = list(HistoryLine.objects.filter(entity=rei.id).order_by('id'))
        self.assertEqual(1, len(hlines))
        self.assertEqual(HistoryLine.TYPE_CREATION, hlines[0].type)

    def test_multi_save02(self):
        "Beware internal backup must be recreated after the save()"
        old_last_name = 'Ayami'; new_last_name = 'Ayanami'
        old_first_name = 'Rey';  new_first_name = 'Rei'

        rei = Contact.objects.create(user=self.user, first_name=old_first_name, last_name=old_last_name)
        self.assertEqual(1, HistoryLine.objects.filter(entity=rei.id).count())

        rei = self.refresh(rei) #force internal backup, we can begin our edition stuffs

        rei.last_name = new_last_name
        rei.save()

        hlines = list(HistoryLine.objects.filter(entity=rei.id).order_by('id'))
        self.assertEqual(2, len(hlines))

        creation_hline = hlines[0]
        self.assertEqual(HistoryLine.TYPE_CREATION, creation_hline.type)

        edition_hline01 = hlines[1]
        self.assertEqual(HistoryLine.TYPE_EDITION, edition_hline01.type)
        self.assertEqual([['last_name', old_last_name, new_last_name]],
                         edition_hline01.modifications
                        )

        rei.first_name = new_first_name
        rei.save()

        hlines = list(HistoryLine.objects.filter(entity=rei.id).order_by('id'))
        self.assertEqual(3, len(hlines))
        self.assertEqual(creation_hline,  hlines[0])
        self.assertEqual(edition_hline01, hlines[1])

        edition_hline02 = hlines[2]
        self.assertEqual(HistoryLine.TYPE_EDITION, edition_hline02.type)
        self.assertEqual([['first_name', old_first_name, new_first_name]],
                         edition_hline02.modifications
                        )

    def test_invalid_field(self):
        nerv = Organisation.objects.create(user=self.user, name='Nerv')
        nerv = self.refresh(nerv) #force internal backup

        nerv.name = nerv.name.upper()
        nerv.save()
        hline = HistoryLine.objects.filter(entity=nerv.id).order_by('-id')[0]
        self.assertEqual(HistoryLine.TYPE_EDITION, hline.type)
        self.assertIn('["NERV", ["name", "Nerv", "NERV"]]', hline.value)

        self.assertEqual([self.FSTRING_3_VALUES % {'field':    _('Name'),
                                                   'oldvalue': 'Nerv',
                                                   'value':    'NERV',
                                                  },
                         ],
                         hline.verbose_modifications
                        )

        fname = 'invalid'
        hline.value = hline.value.replace('name', fname)
        hline.save()
        hline = self.refresh(hline) #clean cache

        with self.assertNoException():
            vmodifs = hline.verbose_modifications

        self.assertEqual([self.FSTRING_1_VALUE % {'field': fname}], vmodifs)

    #TODO: test populate related lines + query counter ??
