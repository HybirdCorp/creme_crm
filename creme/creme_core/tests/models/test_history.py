# -*- coding: utf-8 -*-

try:
    from datetime import date, time
    from decimal import Decimal
    from time import sleep

    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.formats import date_format, number_format
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from ..base import CremeTestCase
    from ..fake_constants import FAKE_PERCENT_UNIT, FAKE_AMOUNT_UNIT
    from ..fake_models import (FakeContact, FakeImage, FakeOrganisation, FakeAddress,
            FakeSector, FakeLegalForm, FakeInvoice, FakeInvoiceLine, FakeActivity, FakeActivityType)
    from creme.creme_core.models import (CremeProperty, CremePropertyType,
            Relation, RelationType, HistoryLine, HistoryConfigItem)
    from creme.creme_core.models.history import (TYPE_CREATION, TYPE_EDITION, TYPE_DELETION,
            TYPE_AUX_CREATION, TYPE_AUX_EDITION, TYPE_AUX_DELETION,
            TYPE_RELATED, TYPE_PROP_ADD, TYPE_PROP_DEL,
            TYPE_RELATION, TYPE_SYM_RELATION, TYPE_RELATION_DEL, TYPE_SYM_REL_DEL)
    from creme.creme_core.utils.dates import dt_to_ISO8601
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class HistoryTestCase(CremeTestCase):
    FMT_1_VALUE  = _(u'Set field “{field}”').format
    FMT_2_VALUES = _(u'Set field “{field}” to “{value}”').format
    FMT_3_VALUES = _(u'Set field “{field}” from “{oldvalue}” to “{value}”').format

    @classmethod
    def setUpClass(cls):
        super(HistoryTestCase, cls).setUpClass()
        HistoryLine.objects.all().delete()

    def setUp(self):
        super(HistoryTestCase, self).setUp()
        self.old_time = now().replace(microsecond=0)
        self.login()

    def tearDown(self):
        super(HistoryTestCase, self).tearDown()
        HistoryLine.ENABLED = True

    def _build_organisation(self, name, extra_args=None, **kwargs):
        data = {'name': name}
        data.update(kwargs)

        if extra_args:
            data.update(extra_args)

        self.assertNoFormError(self.client.post('/tests/organisation/add', follow=True, data=data))

        return self.get_object_or_fail(FakeOrganisation, name=name)

    def _build_contact(self, first_name, last_name, **kwargs):
        data = {'first_name': first_name, 'last_name': last_name}
        data.update(kwargs)

        self.assertNoFormError(self.client.post('/tests/contact/add', follow=True, data=data))

        return self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)

    def assertBetweenDates(self, hline):
        now_value = now()
        hdate = hline.date
        old_time = self.old_time
        self.assertTrue(old_time <= hdate <= now_value,
                        'old_time={} ; hline.date={} ; now={}'.format(old_time, hdate, now_value)
                       )

    def _get_hlines(self):
        return list(HistoryLine.objects.order_by('id'))

    def test_creation01(self):
        old_count = HistoryLine.objects.count()
        gainax = self._build_organisation(user=self.other_user.id, name='Gainax')
        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,          hline.entity.id)
        self.assertEqual(gainax.entity_type, hline.entity_ctype)
        self.assertEqual(self.other_user,    hline.entity_owner)
        self.assertEqual(self.user.username, hline.username)
        self.assertEqual(TYPE_CREATION,      hline.type)
        self.assertEqual([],                 hline.modifications)
        self.assertBetweenDates(hline)

    def test_creation_n_aux(self):
        "Address is auxiliary + double save() because of addresses caused problems"
        old_count = HistoryLine.objects.count()
        gainax = FakeOrganisation.objects.create(user=self.other_user, name='Gainax')
        gainax.address = address = FakeAddress.objects.create(entity=gainax, country='Japan')
        gainax.save()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))  # 1 creation + 1 auxiliary (NB: not edition with double save)

        hline = hlines[-2]
        self.assertEqual(gainax.id,          hline.entity.id)
        self.assertEqual(gainax.entity_type, hline.entity_ctype)
        self.assertEqual(self.other_user,    hline.entity_owner)
        self.assertEqual(TYPE_CREATION,      hline.type)
        self.assertEqual([],                 hline.modifications)
        self.assertBetweenDates(hline)

        hline = hlines[-1]
        self.assertEqual(gainax.id,          hline.entity.id)
        self.assertEqual(gainax.entity_type, hline.entity_ctype)
        self.assertEqual(self.other_user,    hline.entity_owner)
        self.assertEqual(TYPE_AUX_CREATION,  hline.type)
        self.assertBetweenDates(hline)
        self.assertEqual([ContentType.objects.get_for_model(address).id, address.id, str(address)],
                         hline.modifications
                        )
        self.assertEqual([_(u'Add <{type}>: “{value}”').format(
                                type='Test address',
                                value=address,
                            )
                         ],
                         hline.get_verbose_modifications(self.user),
                        )

    def test_edition01(self):
        old_count = HistoryLine.objects.count()

        name = 'gainax'
        old_capital = 12000
        gainax = self._build_organisation(user=self.user.id, name=name, capital=old_capital)

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        capital = old_capital * 2
        response = self.client.post(gainax.get_edit_absolute_url(), follow=True,
                                    data={'user':    self.user.id,
                                          'name':    name,
                                          'capital': capital,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(capital, self.refresh(gainax).capital)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,    hline.entity.id)
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertEqual([['capital', old_capital, capital]], hline.modifications)

    # TODO: change 'name' but keep the old unicode() ???
    def test_edition02(self):
        old_count = HistoryLine.objects.count()

        create_sector = FakeSector.objects.create
        sector01 = create_sector(title='Studio')
        sector02 = create_sector(title='Animation studio')

        lform = FakeLegalForm.objects.create(title='Society [OK]')

        name = 'Gainax'
        old_phone = '7070707'
        description = """Oh this is an long description
text that takes several lines
about this fantastic animation studio."""
        gainax = self._build_organisation(user=self.user.id, name=name, phone=old_phone,
                                          description=description, sector=sector01.id,
                                          subject_to_vat=False, legal_form=lform.id,
                                         )

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        phone = old_phone + '07'
        email = 'contact@gainax.jp'
        description += 'In this studio were created lots of excellent animes ' \
                       'like "Evangelion" or "Fushigi no umi no Nadia".'
        creation_date = date(year=1984, month=12, day=24)
        response = self.client.post(gainax.get_edit_absolute_url(), follow=True,
                                    data={'user':          self.user.id,
                                          'name':          name,
                                          'phone':         phone,
                                          'email':         email,
                                          'description':   description,
                                          'sector':        sector02.id,
                                          # 'creation_date': '1984-12-24',
                                          'creation_date': creation_date,
                                          'subject_to_vat': True,
                                         }
                                   )
        self.assertNoFormError(response)

        hline = HistoryLine.objects.filter(type=TYPE_EDITION, entity=gainax).latest('date')
        modifs = hline.modifications
        self.assertIsInstance(modifs, list)
        self.assertEqual(7, len(modifs))
        self.assertIn(['phone', old_phone, phone], modifs)
        self.assertIn(['email', email], modifs)
        self.assertIn(['description'], modifs)
        self.assertIn(['sector', sector01.id, sector02.id], modifs)
        self.assertIn(['creation_date', '1984-12-24'], modifs)
        self.assertIn(['subject_to_vat', True], modifs, modifs)
        self.assertIn(['legal_form', lform.id, None], modifs, modifs)

        vmodifs = hline.get_verbose_modifications(self.user)
        self.assertEqual(7, len(vmodifs))

        self.assertIn(self.FMT_3_VALUES(field=_(u'Phone number'),
                                        oldvalue=old_phone,
                                        value=phone,
                                       ),
                      vmodifs
                     )
        self.assertIn(self.FMT_2_VALUES(field=_(u'Email address'),
                                        value=email,
                                       ),
                      vmodifs
                     )
        self.assertIn(self.FMT_1_VALUE(field=_(u'Description')), vmodifs)
        self.assertIn(self.FMT_3_VALUES(field=_(u'Sector'),
                                        oldvalue=sector01,
                                        value=sector02,
                                       ),
                      vmodifs
                     )
        self.assertIn(self.FMT_2_VALUES(field=_(u'Date of creation'),
                                        value=date_format(creation_date, 'DATE_FORMAT'),
                                       ),
                      vmodifs
                     )
        self.assertIn(self.FMT_2_VALUES(field=_(u'Subject to VAT'),
                                        value=_('Yes'),
                                       ),
                      vmodifs
                     )
        self.assertIn(self.FMT_3_VALUES(field=_(u'Legal form'),
                                        oldvalue=lform,
                                        value='',
                                       ),
                      vmodifs
                     )

    def test_edition03(self):
        "No change"
        name = 'gainax'
        capital = 12000
        gainax = self._build_organisation(user=self.user.id, name=name, capital=capital)
        old_count = HistoryLine.objects.count()

        response = self.client.post(gainax.get_edit_absolute_url(), follow=True,
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
        gainax = FakeOrganisation.objects.create(user=self.user, name=name, capital=old_capital)

        capital = old_capital * 2
        response = self.client.post(gainax.get_edit_absolute_url(), follow=True,
                                    data={'user':           self.user.id,
                                          'name':           name,
                                          'capital':        capital,
                                          'subject_to_vat': True,
                                         }
                                   )
        self.assertNoFormError(response)

        hline = HistoryLine.objects.order_by('-id')[0]
        self.assertEqual(gainax.id,    hline.entity.id)
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertEqual([['capital', old_capital, capital]], hline.modifications)

    def test_edition05(self):
        "Type coercion"
        capital = 12000
        gainax = FakeOrganisation.objects.create(user=self.user, name='Gainax', capital=capital)
        old_count = HistoryLine.objects.count()

        gainax = self.refresh(gainax)
        gainax.capital = str(capital)
        gainax.save()
        self.assertEqual(capital, self.refresh(gainax).capital)  # 'capital' attribute is now an integer
        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_edition06(self):
        "FK to CremeEntity"
        user = self.user
        hayao = self._build_contact(user=user.id, first_name='Hayao', last_name='Miyazaki')
        img = FakeImage.objects.create(user=user, name='Grumpy Hayao')

        hayao.image = img
        hayao.save()

        hline = HistoryLine.objects.order_by('-id')[0]
        self.assertEqual(hayao.id,     hline.entity.id)
        self.assertEqual(TYPE_EDITION, hline.type)

        vmodifs = hline.get_verbose_modifications(user)
        self.assertEqual(1, len(vmodifs))
        self.assertIn(self.FMT_2_VALUES(field=_(u'Photograph'),
                                        value=img,
                                       ),
                      vmodifs[0]
                     )

    def test_edition07(self):
        "New value is None: verbose prints ''"
        old_capital = 1000
        old_date    = date(year=1928, month=5, day=3)
        gainax = FakeOrganisation.objects.create(user=self.user, name='Gainax',
                                                 capital=old_capital,
                                                 creation_date=old_date,
                                                )
        old_count = HistoryLine.objects.count()

        gainax = self.refresh(gainax)
        gainax.capital = None
        gainax.creation_date = None
        gainax.save()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,    hline.entity.id)
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertEqual([['capital',        old_capital,   None],
                          [u'creation_date', u'1928-05-03', None],
                         ],
                         hline.modifications
                        )

        vmodifs = hline.get_verbose_modifications(self.user)
        self.assertEqual(2, len(vmodifs))

        fmt = self.FMT_3_VALUES
        self.assertEqual(fmt(field=_(u'Capital'),
                             oldvalue=old_capital,
                             value='',  # <== not None
                            ),
                         vmodifs[0]
                        )
        self.assertEqual(fmt(field=_(u'Date of creation'),
                             oldvalue=date_format(old_date, 'DATE_FORMAT'),
                             value='',  # <== not None
                            ),
                         vmodifs[1]
                        )

    def test_edition08(self):
        "DateTimeField"
        create_dt = self.create_datetime
        old_start = create_dt(year=2016, month=11, day=22, hour=16, minute=10)
        meeting = FakeActivity.objects.create(user=self.user, title='Meeting with Seele',
                                              start=old_start,
                                              type=FakeActivityType.objects.all()[0],
                                             )
        old_count = HistoryLine.objects.count()

        meeting = self.refresh(meeting)
        meeting.start = start = create_dt(year=2016, month=11, day=22, hour=16, minute=15)
        meeting.end = end = create_dt(year=2016, month=11, day=22, hour=18, minute=30)
        meeting.save()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(meeting.id,  hline.entity.id)
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertEqual([['start', dt_to_ISO8601(old_start), dt_to_ISO8601(start)],
                          ['end', dt_to_ISO8601(end)],
                         ],
                         hline.modifications
                        )

        vmodifs = hline.get_verbose_modifications(self.user)
        self.assertEqual(2, len(vmodifs))
        self.assertEqual(self.FMT_3_VALUES(field=_(u'Start'),
                                           oldvalue=date_format(old_start, 'DATETIME_FORMAT'),
                                           value=date_format(start, 'DATETIME_FORMAT'),
                                          ),
                         vmodifs[0]
                        )

        # Set None -------------------------
        meeting.end = None
        meeting.save()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))
        self.assertEqual(self.FMT_3_VALUES(field=_(u'End'),
                                           oldvalue=date_format(end, 'DATETIME_FORMAT'),
                                           value='',
                                          ),
                         hlines[-1].get_verbose_modifications(self.user)[0]
                        )

    def test_edition09(self):
        "Other fields: TimeField, SlugField, FloatField, NullBooleanField"
        # TODO: use true fields in a fake model

        from creme.creme_core.models.history import _JSONEncoder, _PRINTERS

        encode = _JSONEncoder().encode

        self.assertEqual('"17:23:00.000000"', encode(time(hour=17, minute=23)))
        self.assertNotIn('TimeField', _PRINTERS)

        self.assertNotIn('SlugField', _PRINTERS)

        # ------
        n = 3.14
        self.assertEqual('3.14', encode(n))
        float_printer = _PRINTERS.get('FloatField')
        self.assertIsNotNone(float_printer)
        self.assertEqual(number_format(n, use_l10n=True),
                         float_printer(field=None, user=self.user, val=n)
                        )
        self.assertEqual('', float_printer(field=None, user=self.user, val=None))

        # ------
        nbool_printer = _PRINTERS.get('NullBooleanField')
        self.assertIsNotNone(nbool_printer)
        self.assertEqual(_('Yes'),  nbool_printer(field=None, user=self.user, val=True))
        self.assertEqual(_('No'),   nbool_printer(field=None, user=self.user, val=False))
        self.assertEqual(_('N/A'),  nbool_printer(field=None, user=self.user, val=None))

    def test_deletion01(self):
        old_count = HistoryLine.objects.count()
        gainax = FakeOrganisation.objects.create(user=self.other_user, name='Gainax')
        entity_repr = str(gainax)

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        creation_line = HistoryLine.objects.get(entity=gainax)

        # TODO: log trashing ??
        gainax.trash()

        self.assertPOST200(gainax.get_delete_absolute_url(), follow=True)
        self.assertDoesNotExist(gainax)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-1]
        self.assertIsNone(hline.entity)
        self.assertEqual(entity_repr,        hline.entity_repr)
        self.assertEqual(self.other_user,    hline.entity_owner)
        self.assertEqual(self.user.username, hline.username)
        self.assertEqual(TYPE_DELETION,      hline.type)
        self.assertEqual([],                 hline.modifications)
        self.assertBetweenDates(hline)

        creation_line = self.refresh(creation_line)
        self.assertIsNone(creation_line.entity)
        self.assertEqual(entity_repr, creation_line.entity_repr)

    def test_deletion02(self):
        "With auxiliary models"
        gainax = FakeOrganisation.objects.create(user=self.user, name='Gainax')
        FakeAddress.objects.create(entity=gainax, city='Tokyo')
        old_count = HistoryLine.objects.count()

        gainax.delete()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))
        self.assertEqual(TYPE_DELETION, hlines[-1].type)

    def test_related_edition01(self):
        user = self.user
        ghibli = self._build_organisation(user=user.id, name='Ghibli')

        first_name = 'Hayao'
        last_name  = 'Miyazaki'
        hayao = self._build_contact(user=user.id, first_name=first_name, last_name=last_name)

        rtype, srtype = RelationType.create(('test-subject_employed', 'is employed'),
                                            ('test-object_employed', 'employs')
                                           )
        Relation.objects.create(user=user, subject_entity=hayao, object_entity=ghibli, type=rtype)

        old_count = HistoryLine.objects.count()
        description = 'A great animation movie maker'
        response = self.client.post(hayao.get_edit_absolute_url(), follow=True,
                                    data={'user':        user.id,
                                          'first_name':  first_name,
                                          'last_name':   last_name,
                                          'description': description,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(description, self.refresh(hayao).description)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertIsNone(hline.related_line)

    def test_related_edition02(self):
        user = self.user
        ghibli = self._build_organisation(user=user.id, name='Ghibli')
        sleep(1)  # Ensure that 'modified' fields are different

        first_name = 'Hayao'
        last_name  = 'Miyazaki'
        hayao = self._build_contact(user=user.id, first_name=first_name, last_name=last_name)
        self.assertNotEqual(hayao.modified, ghibli.modified)

        rtype, srtype = RelationType.create(('test-subject_employed', 'is employed'),
                                            ('test-object_employed', 'employs')
                                           )
        Relation.objects.create(user=user, subject_entity=hayao, object_entity=ghibli, type=rtype)

        HistoryConfigItem.objects.create(relation_type=rtype)

        old_count = HistoryLine.objects.count()
        response = self.client.post(hayao.get_edit_absolute_url(), follow=True,
                                    data={'user':        user.id,
                                          'first_name':  first_name,
                                          'last_name':   last_name,
                                          'description': 'A great animation movie maker',
                                         }
                                   )
        self.assertNoFormError(response)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))

        edition_hline = hlines[-2]
        self.assertEqual(TYPE_EDITION, edition_hline.type)

        hline = hlines[-1]
        self.assertEqual(ghibli.id,          hline.entity.id)
        self.assertEqual(ghibli.entity_type, hline.entity_ctype)
        self.assertEqual(user,               hline.entity_owner)
        self.assertEqual(TYPE_RELATED,       hline.type)
        self.assertEqual(str(ghibli),    hline.entity_repr)
        self.assertEqual([],                 hline.modifications)
        self.assertEqual(edition_hline.id,   hline.related_line.id)
        self.assertBetweenDates(hline)
        self.assertEqual(self.refresh(hayao).modified, hline.date)

    def test_add_property01(self):
        user = self.user
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        old_count = HistoryLine.objects.count()

        sleep(1)  # Ensure that 'modified' field is not 'now()'

        ptype = CremePropertyType.create(str_pk='test-prop_make_animes', text='Make animes')
        prop = CremeProperty.objects.create(type=ptype, creme_entity=gainax)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,       hline.entity.id)
        self.assertEqual(str(gainax), hline.entity_repr)
        self.assertEqual(TYPE_PROP_ADD,   hline.type)
        self.assertEqual([ptype.id],      hline.modifications)
        self.assertEqual(False,           hline.line_type.is_about_relation)
        self.assertGreater(hline.date, gainax.modified)

        msg = _(u'Add property “{}”').format
        self.assertEqual([msg(ptype.text)], hline.get_verbose_modifications(user))

        expected = [msg(ptype.id)]
        prop.delete(); ptype.delete()
        self.assertEqual(expected, self.refresh(hline).get_verbose_modifications(user))

    def test_delete_property01(self):
        user = self.user
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        old_count = HistoryLine.objects.count()
        sleep(1)  # Ensure that 'modified' field is not 'now()'

        ptype = CremePropertyType.create(str_pk='test-prop_make_animes', text='make animes')
        prop = CremeProperty.objects.create(type=ptype, creme_entity=gainax)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))
        self.assertEqual(TYPE_PROP_ADD, hlines[-1].type)

        prop.delete()
        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,       hline.entity.id)
        self.assertEqual(str(gainax), hline.entity_repr)
        self.assertEqual(TYPE_PROP_DEL,   hline.type)
        self.assertEqual([ptype.id],      hline.modifications)
        self.assertEqual(False,           hline.line_type.is_about_relation)
        self.assertGreater(hline.date, gainax.modified)

        ptype.text = ptype.text.title()
        ptype.save()
        self.assertEqual([_(u'Delete property “{}”').format(ptype.text)],
                         hline.get_verbose_modifications(user)
                        )

    def test_add_relation01(self):
        user = self.user
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        rei  = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        old_count = HistoryLine.objects.count()

        sleep(1)  # Ensure than relation is younger than entities

        rtype, srtype = RelationType.create(('test-subject_works4', 'is employed'),
                                            ('test-object_works4',  'employs')
                                           )
        relation = Relation.objects.create(user=user, subject_entity=rei, object_entity=nerv, type=rtype)
        relation = self.refresh(relation)  # Refresh to get the right modified value

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-2]
        self.assertEqual(rei.id,            hline.entity.id)
        self.assertEqual(str(rei),      hline.entity_repr)
        self.assertEqual(TYPE_RELATION,     hline.type)
        self.assertEqual([rtype.id],        hline.modifications)
        # self.assertEqual(relation.modified, hline.date)
        self.assertEqual(relation.created,  hline.date)
        self.assertEqual(True,              hline.line_type.is_about_relation)

        hline_sym = hlines[-1]
        self.assertEqual(nerv.id,           hline_sym.entity.id)
        self.assertEqual(str(nerv),     hline_sym.entity_repr)
        self.assertEqual(TYPE_SYM_RELATION, hline_sym.type)
        self.assertEqual([srtype.id],       hline_sym.modifications)
        # self.assertEqual(relation.modified, hline_sym.date)
        self.assertEqual(relation.created,  hline_sym.date)
        self.assertIs(True,                 hline.line_type.is_about_relation)

        self.assertEqual(hline_sym.id, hline.related_line.id)
        self.assertEqual(hline.id,     hline_sym.related_line.id)

        msg = _(u'Add a relationship “{}”').format
        self.assertEqual([msg(rtype.predicate)],  hline.get_verbose_modifications(user))
        self.assertEqual([msg(srtype.predicate)], hline_sym.get_verbose_modifications(user))

        rtype_id = rtype.id
        relation.delete(); rtype.delete()
        self.assertDoesNotExist(rtype)
        self.assertEqual([msg(rtype_id)], self.refresh(hline).get_verbose_modifications(user))

    def test_add_relation02(self):
        "Create the relation using the 'object' relation type"
        user = self.user
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        rei  = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        olds_ids = list(HistoryLine.objects.values_list('id', flat=True))

        rtype, srtype = RelationType.create(('test-subject_works5', 'is employed'),
                                            ('test-object_works5',  'employs')
                                           )
        Relation.objects.create(user=user, subject_entity=nerv, object_entity=rei, type=srtype)

        hlines = list(HistoryLine.objects.exclude(id__in=olds_ids).order_by('id'))
        self.assertEqual(2, len(hlines))

        hline = hlines[-2]
        self.assertEqual(rei.id,            hline.entity.id)
        self.assertEqual(TYPE_RELATION,     hline.type)
        self.assertEqual([rtype.id],        hline.modifications)

        hline_sym = hlines[-1]
        self.assertEqual(nerv.id,           hline_sym.entity.id)
        self.assertEqual(TYPE_SYM_RELATION, hline_sym.type)
        self.assertEqual([srtype.id],       hline_sym.modifications)

        self.assertEqual(hline_sym.id, hline.related_line.id)

    def test_delete_relation(self):
        user = self.user
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        rei  = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        old_count = HistoryLine.objects.count()

        rtype, srtype = RelationType.create(('test-subject_works4', 'is employed'),
                                            ('test-object_works4',  'employs')
                                           )
        relation = Relation.objects.create(user=user, subject_entity=rei, object_entity=nerv, type=rtype)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))
        self.assertEqual(TYPE_RELATION,     hlines[-2].type)
        self.assertEqual(TYPE_SYM_RELATION, hlines[-1].type)

        relation.delete()
        hlines = self._get_hlines()
        self.assertEqual(old_count + 4, len(hlines))

        hline = hlines[-2]
        self.assertEqual(rei,               hline.entity.get_real_entity())
        self.assertEqual(str(rei),      hline.entity_repr)
        self.assertEqual(TYPE_RELATION_DEL, hline.type)
        self.assertEqual([rtype.id],        hline.modifications)
        self.assertEqual(True,              hline.line_type.is_about_relation)
        self.assertDatetimesAlmostEqual(now(), hline.date)

        hline_sym = hlines[-1]
        self.assertEqual(nerv,             hline_sym.entity.get_real_entity())
        self.assertEqual(str(nerv),    hline_sym.entity_repr)
        self.assertEqual(TYPE_SYM_REL_DEL, hline_sym.type)
        self.assertEqual([srtype.id],      hline_sym.modifications)
        self.assertEqual(True,             hline_sym.line_type.is_about_relation)

        rtype.predicate = rtype.predicate.title()
        rtype.save()
        self.assertEqual([_(u'Delete a relationship “{}”').format(rtype.predicate)],
                         hline.get_verbose_modifications(user)
                        )

    def test_add_auxiliary(self):
        "Auxiliary: Address"
        user = self.user
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        old_count = HistoryLine.objects.count()

        city = 'Tokyo'
        response = self.client.post(reverse('creme_core__create_fake_address', args=(nerv.id,)),
                                    data={'city': city},
                                   )
        self.assertNoFormError(response)

        self.get_object_or_fail(FakeAddress, entity=nerv, city=city)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(nerv.id,           hline.entity.id)
        self.assertEqual(nerv.entity_type,  hline.entity_ctype)
        self.assertEqual(user,              hline.entity_owner)
        self.assertEqual(TYPE_AUX_CREATION, hline.type)

    def test_edit_auxiliary01(self):
        "Address"
        country = 'Japan'
        old_city = 'MITAKA'
        gainax = self._build_organisation(user=self.other_user.id, name='Gainax')
        address = FakeAddress.objects.create(entity=gainax, country=country, city=old_city)

        old_count = HistoryLine.objects.count()
        city = old_city.title()
        department = 'Tokyo'
        response = self.client.post(address.get_edit_absolute_url(),
                                    data={'country':    country,
                                          'city':       city,
                                          'department': department,
                                         }
                                   )
        self.assertNoFormError(response)

        address = self.refresh(address)
        self.assertEqual(city, address.city)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,          hline.entity.id)
        self.assertEqual(gainax.entity_type, hline.entity_ctype)
        self.assertEqual(self.other_user,    hline.entity_owner)
        self.assertEqual(TYPE_AUX_EDITION,   hline.type)
        self.assertBetweenDates(hline)
        self.assertEqual([[ContentType.objects.get_for_model(address).id,
                           address.id,
                           str(address),
                          ],
                          ['city', old_city, city],
                          ['department', department],
                         ],
                         hline.modifications
                        )

        vmodifs = hline.get_verbose_modifications(self.user)
        self.assertEqual(3, len(vmodifs))

        self.assertEqual(_(u'Edit <{type}>: “{value}”').format(
                                type='Test address',
                                value=address,
                             ),
                         vmodifs[0]
                        )
        self.assertEqual(self.FMT_3_VALUES(field=_(u'City'),
                                           oldvalue=old_city,
                                           value=city,
                                          ),
                         vmodifs[1]
                        )
        self.assertEqual(self.FMT_2_VALUES(field=_(u'Department'),
                                           value=department,
                                          ),
                         vmodifs[2]
                        )

    def test_edit_auxiliary02(self):
        """Billing.Line
        - an auxiliary + CremeEntity at the same time
        - DecimalField
        - field with choices.
        """
        user = self.user
        invoice = FakeInvoice.objects.create(user=user, name='Invoice',
                                             expiration_date=date(year=2012, month=12, day=15),
                                            )
        old_count = HistoryLine.objects.count()
        pline = FakeInvoiceLine.objects.create(item='DeathNote', user=user,
                                               linked_invoice=invoice, quantity=Decimal('1'),
                                               discount_unit=FAKE_AMOUNT_UNIT,
                                              )

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1,     len(hlines))
        self.assertEqual(TYPE_AUX_CREATION, hlines[-1].type)

        old_count += 1

        pline.quantity = Decimal('2')
        pline.discount_unit = FAKE_PERCENT_UNIT
        pline.save()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(TYPE_AUX_EDITION,   hline.type)

        vmodifs = hline.get_verbose_modifications(user)
        self.assertEqual(3, len(vmodifs))
        self.assertIn(self.FMT_3_VALUES(field=_(u'Quantity'),
                                        oldvalue='1',
                                        value='2',
                                       ),
                      vmodifs[1]
                     )
        self.assertIn(self.FMT_3_VALUES(field=_(u'Discount Unit'),
                                        oldvalue=_(u'Amount'),
                                        value=_(u'Percent'),
                                       ),
                      vmodifs[2]
                     )

    def test_delete_auxiliary(self):
        "Auxiliary: Address"
        user = self.user
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        address = FakeAddress.objects.create(entity=nerv, city='Tokyo')
        old_count = HistoryLine.objects.count()

        address.delete()
        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(nerv.id,           hline.entity.id)
        self.assertEqual(TYPE_AUX_DELETION, hline.type)

        vmodifs = hline.get_verbose_modifications(user)
        self.assertEqual(1, len(vmodifs))

        self.assertEqual(_(u'Delete <{type}>: “{value}”').format(
                                type=u'Test address',
                                value=address,
                            ),
                         vmodifs[0]
                        )

    def test_multi_save01(self):
        old_last_name = 'Ayami'
        new_last_name = 'Ayanami'

        rei = FakeContact.objects.create(user=self.user, first_name='Rei', last_name=old_last_name)
        self.assertEqual(1, HistoryLine.objects.filter(entity=rei.id).count())

        rei.last_name = new_last_name
        rei.save()

        hlines = list(HistoryLine.objects.filter(entity=rei.id).order_by('id'))
        self.assertEqual(1, len(hlines))
        self.assertEqual(TYPE_CREATION, hlines[0].type)

    def test_multi_save02(self):
        "Beware internal backup must be recreated after the save()"
        old_last_name  = 'Ayami'; new_last_name  = 'Ayanami'
        old_first_name = 'Rey';   new_first_name = 'Rei'

        rei = FakeContact.objects.create(user=self.user, first_name=old_first_name, last_name=old_last_name)
        self.assertEqual(1, HistoryLine.objects.filter(entity=rei.id).count())

        rei = self.refresh(rei)  # Force internal backup, we can begin our edition stuffs

        rei.last_name = new_last_name
        rei.save()

        hlines = list(HistoryLine.objects.filter(entity=rei.id).order_by('id'))
        self.assertEqual(2, len(hlines))

        creation_hline = hlines[0]
        self.assertEqual(TYPE_CREATION, creation_hline.type)

        edition_hline01 = hlines[1]
        self.assertEqual(TYPE_EDITION, edition_hline01.type)
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
        self.assertEqual(TYPE_EDITION, edition_hline02.type)
        self.assertEqual([['first_name', old_first_name, new_first_name]],
                         edition_hline02.modifications
                        )

    def test_invalid_field(self):
        user = self.user
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        nerv = self.refresh(nerv)  # Force internal backup

        nerv.name = nerv.name.upper()
        nerv.save()
        hline = HistoryLine.objects.filter(entity=nerv.id).order_by('-id')[0]
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertIn('["NERV", ["name", "Nerv", "NERV"]]', hline.value)

        self.assertEqual([self.FMT_3_VALUES(field=_('Name'),
                                            oldvalue='Nerv',
                                            value='NERV',
                                           ),
                         ],
                         hline.get_verbose_modifications(user)
                        )

        fname = 'invalid'
        hline.value = hline.value.replace('name', fname)
        hline.save()
        hline = self.refresh(hline)  # Clean cache

        with self.assertNoException():
            vmodifs = hline.get_verbose_modifications(user)

        self.assertEqual([self.FMT_1_VALUE(field=fname)], vmodifs)

    def test_disable01(self):
        "CremeEntity creation, edition & deletion"
        old_count = HistoryLine.objects.count()
        nerv = FakeOrganisation(user=self.user, name='nerv')

        HistoryLine.disable(nerv)
        nerv.save()
        self.assertEqual(old_count, HistoryLine.objects.count())

        # -----------------------
        nerv = self.refresh(nerv)
        HistoryLine.disable(nerv)

        nerv.name = nerv.name.title()
        nerv.save()
        self.assertEqual(old_count, HistoryLine.objects.count())

        # -----------------------
        nerv = self.refresh(nerv)
        HistoryLine.disable(nerv)

        nerv.delete()
        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_disable02(self):
        "Relationship creation & deletion"
        user = self.user
        hayao = FakeContact.objects.create(user=user, first_name='Hayao', last_name='Miyazaki')
        ghibli = FakeOrganisation.objects.create(user=user, name='Ghibli')
        rtype = RelationType.create(('test-subject_employed', 'is employed'),
                                    ('test-object_employed', 'employs')
                                   )[0]

        old_count = HistoryLine.objects.count()
        rel = Relation(user=user, subject_entity=hayao, object_entity=ghibli, type=rtype)

        HistoryLine.disable(rel)
        rel.save()
        self.assertEqual(old_count, HistoryLine.objects.count())

        # -----------------------
        rel = self.refresh(rel)
        HistoryLine.disable(rel)

        rel.delete()
        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_disable03(self):
        "Property creation & deletion"
        user = self.user
        hayao = FakeContact.objects.create(user=user, first_name='Hayao', last_name='Miyazaki')

        ptype = CremePropertyType.create(str_pk='test-prop_make_animes', text='Make animes')
        old_count = HistoryLine.objects.count()

        prop = CremeProperty(type=ptype, creme_entity=hayao)
        HistoryLine.disable(prop)
        prop.save()
        self.assertEqual(old_count, HistoryLine.objects.count())

        # -----------------------
        prop = self.refresh(prop)
        HistoryLine.disable(prop)

        prop.delete()
        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_disable04(self):
        "Auxiliary creation, edition & deletion"
        user = self.user
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        old_count = HistoryLine.objects.count()
        address = FakeAddress(entity=nerv, city='tokyo')

        HistoryLine.disable(address)
        address.save()
        self.assertEqual(old_count, HistoryLine.objects.count())

        # -----------------------
        address = self.refresh(address)
        HistoryLine.disable(address)

        address.city = address.city.upper()
        address.save()
        self.assertEqual(old_count, HistoryLine.objects.count())

        # -----------------------
        address = self.refresh(address)
        HistoryLine.disable(address)

        address.delete()
        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_globally_disable(self):
        old_count = HistoryLine.objects.count()

        HistoryLine.ENABLED = False

        nerv = FakeOrganisation.objects.create(user=self.user, name='nerv')
        self.assertEqual(old_count, HistoryLine.objects.count())

        nerv.name = nerv.name.title()
        nerv.save()
        self.assertEqual(old_count, HistoryLine.objects.count())

        FakeAddress.objects.create(entity=nerv, city='Tokyo')
        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_delete_lines(self):
        user = self.user
        hayao = FakeContact.objects.create(user=user, first_name='Hayao', last_name='Miyazaki')
        ghibli = FakeOrganisation.objects.create(user=user, name='Ghibli')

        rtype = RelationType.create(('test-subject_delline_works', 'is employed'),
                                    ('test-object_delline_works',  'employs')
                                   )[0]
        Relation.objects.create(user=user, subject_entity=hayao, object_entity=ghibli, type=rtype)

        HistoryConfigItem.objects.create(relation_type=rtype)
        hayao = self.refresh(hayao)
        hayao.description = 'Dream maker'
        hayao.save()

        hayao_line_qs = HistoryLine.objects.filter(entity=hayao)
        ghibli_line_qs = HistoryLine.objects.filter(entity=ghibli)
        self.assertEqual(3, hayao_line_qs.count())
        self.assertEqual(3, ghibli_line_qs.count())

        HistoryLine.delete_lines(hayao_line_qs)
        self.assertFalse(hayao_line_qs.all())

        ghibli_lines = list(ghibli_line_qs.all())
        self.assertEqual(1, len(ghibli_lines))
        self.assertEqual(TYPE_CREATION, ghibli_lines[0].type)

    def test_populate_users01(self):
        user = self.user

        self._build_organisation(user=user.id, name='Gainax')
        hline = self._get_hlines()[-1]

        with self.assertNumQueries(0):
            HistoryLine.populate_users([hline], user)

        with self.assertNumQueries(0):
            h_user = hline.user

        self.assertEqual(user, h_user)

    def test_populate_users02(self):
        user = self.user
        other_user = self.other_user

        admin = get_user_model().objects.order_by('id').first()
        self.assertNotEqual(user, admin)

        create_orga = FakeOrganisation.objects.create
        create_orga(user=user, name='Gainax')
        create_orga(user=user, name='Seele')
        create_orga(user=user, name='NERV')
        create_orga(user=user, name='Ghibli')

        hlines = self._get_hlines()
        hline1 = hlines[-1]
        hline2 = hlines[-2]
        hline3 = hlines[-3]

        HistoryLine.objects.filter(id=hline1.id).update(username=admin.username)
        HistoryLine.objects.filter(id=hline2.id).update(username=other_user.username)
        HistoryLine.objects.filter(id=hline3.id).update(username=user.username)

        hline1 = self.refresh(hline1)
        hline2 = self.refresh(hline2)
        hline3 = self.refresh(hline3)
        hline4 = hlines[-4]

        with self.assertNumQueries(1):
            HistoryLine.populate_users([hline4, hline3, hline2, hline1], user)

        with self.assertNumQueries(0):
            h_user4 = hline4.user
        self.assertIsNone(h_user4)

        with self.assertNumQueries(0):
            h_user3 = hline3.user
        self.assertEqual(user, h_user3)

        with self.assertNumQueries(0):
            h_user2 = hline2.user
        self.assertEqual(other_user, h_user2)

        with self.assertNumQueries(0):
            h_user1 = hline1.user
        self.assertEqual(admin, h_user1)

    # TODO: test populate related lines + query counter ??
