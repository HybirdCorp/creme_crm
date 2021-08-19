# -*- coding: utf-8 -*-

from datetime import date, time, timedelta
from decimal import Decimal
from functools import partial

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.formats import date_format, number_format
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.global_info import clear_global_info
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldEnumValue,
    CustomFieldValue,
    FakeActivity,
    FakeActivityType,
    FakeAddress,
    FakeContact,
    FakeImage,
    FakeImageCategory,
    FakeInvoice,
    FakeInvoiceLine,
    FakeLegalForm,
    FakeOrganisation,
    FakeSector,
    FakeTodo,
    FakeTodoCategory,
    HistoryConfigItem,
    HistoryLine,
    Relation,
    RelationType,
)
from creme.creme_core.models.history import (
    TYPE_AUX_CREATION,
    TYPE_AUX_DELETION,
    TYPE_AUX_EDITION,
    TYPE_CREATION,
    TYPE_CUSTOM_EDITION,
    TYPE_DELETION,
    TYPE_EDITION,
    TYPE_PROP_ADD,
    TYPE_PROP_DEL,
    TYPE_RELATED,
    TYPE_RELATION,
    TYPE_RELATION_DEL,
    TYPE_SYM_REL_DEL,
    TYPE_SYM_RELATION,
    TYPE_TRASH,
)
from creme.creme_core.utils.dates import dt_to_ISO8601

# from ..fake_constants import FAKE_AMOUNT_UNIT, FAKE_PERCENT_UNIT
from ..base import CremeTestCase
from ..fake_constants import FAKE_REL_SUB_EMPLOYED_BY


class HistoryTestCase(CremeTestCase):
    FMT_1_VALUE  = _('Set field “{field}”').format
    FMT_2_VALUES = _('Set field “{field}” to “{value}”').format
    FMT_3_VALUES = _('Set field “{field}” from “{oldvalue}” to “{value}”').format

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        HistoryLine.objects.all().delete()

    def setUp(self):
        super().setUp()
        self.old_time = now().replace(microsecond=0)
        self.login()

    def tearDown(self):
        super().tearDown()
        HistoryLine.ENABLED = True

    def _build_organisation(self, name, extra_args=None, **kwargs):
        data = {'name': name}
        data.update(kwargs)

        if extra_args:
            data.update(extra_args)

        self.assertNoFormError(self.client.post(
            FakeOrganisation.get_create_absolute_url(),
            follow=True, data=data,
        ))

        return self.get_object_or_fail(FakeOrganisation, name=name)

    def _build_contact(self, first_name, last_name, **kwargs):
        data = {'first_name': first_name, 'last_name': last_name}
        data.update(kwargs)

        self.assertNoFormError(self.client.post(
            FakeContact.get_create_absolute_url(),
            follow=True, data=data,
        ))

        return self.get_object_or_fail(
            FakeContact, first_name=first_name, last_name=last_name,
        )

    def assertBetweenDates(self, hline):
        now_value = now()
        hdate = hline.date
        old_time = self.old_time
        self.assertTrue(
            old_time <= hdate <= now_value,
            f'old_time={old_time} ; hline.date={hdate} ; now={now_value}'
        )

    @staticmethod
    def create_old(entity_model, **kwargs):
        # Ensure that 'modified' fields is not now()
        instance = entity_model(**kwargs)
        instance.modified -= timedelta(hours=1)  # Ensure that 'modified' fields are different
        instance.save()

        return instance

    @staticmethod
    def _get_hlines():
        return [*HistoryLine.objects.order_by('id')]

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
        self.assertListEqual([], hline.modifications)
        self.assertBetweenDates(hline)

    def test_creation_n_aux(self):
        "Address is auxiliary + double save() because of addresses caused problems"
        old_count = HistoryLine.objects.count()
        gainax = FakeOrganisation.objects.create(user=self.other_user, name='Gainax')
        gainax.address = address = FakeAddress.objects.create(entity=gainax, country='Japan')
        gainax.save()

        hlines = self._get_hlines()
        # 1 creation + 1 auxiliary (NB: not edition with double save)
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-2]
        self.assertEqual(gainax.id,          hline.entity.id)
        self.assertEqual(gainax.entity_type, hline.entity_ctype)
        self.assertEqual(self.other_user,    hline.entity_owner)
        self.assertEqual(TYPE_CREATION,      hline.type)
        self.assertListEqual([], hline.modifications)
        self.assertBetweenDates(hline)

        hline = hlines[-1]
        self.assertEqual(gainax.id,          hline.entity.id)
        self.assertEqual(gainax.entity_type, hline.entity_ctype)
        self.assertEqual(self.other_user,    hline.entity_owner)
        self.assertEqual(TYPE_AUX_CREATION,  hline.type)
        self.assertBetweenDates(hline)
        self.assertListEqual(
            [ContentType.objects.get_for_model(address).id, address.id, str(address)],
            hline.modifications,
        )
        self.assertListEqual(
            [_('Add <{type}>: “{value}”').format(type='Test address', value=address)],
            hline.get_verbose_modifications(self.user),
        )

    def test_edition01(self):
        old_count = HistoryLine.objects.count()

        name = 'gainax'
        old_capital = 12000
        gainax = self._build_organisation(user=self.user.id, name=name, capital=old_capital)

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        capital = old_capital * 2
        response = self.client.post(
            gainax.get_edit_absolute_url(),
            follow=True,
            data={
                'user':    self.user.id,
                'name':    name,
                'capital': capital,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(capital, self.refresh(gainax).capital)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,    hline.entity.id)
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertListEqual([['capital', old_capital, capital]], hline.modifications)

    # TODO: change 'name' but keep the old unicode() ???
    def test_edition02(self):
        user = self.user
        old_count = HistoryLine.objects.count()

        create_sector = FakeSector.objects.create
        sector01 = create_sector(title='Studio')
        sector02 = create_sector(title='Animation studio')

        lform = FakeLegalForm.objects.create(title='Society [OK]')

        name = 'Gainax'
        old_phone = '7070707'
        old_description = """Oh this is an long description
text that takes several lines
about this fantastic animation studio."""
        gainax = self._build_organisation(
            user=user.id, name=name, phone=old_phone,
            description=old_description,
            sector=sector01.id,
            subject_to_vat=False, legal_form=lform.id,
        )

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        phone = old_phone + '07'
        email = 'contact@gainax.jp'
        description = (
            f'{old_description}\n'
            f'In this studio were created lots of excellent animes '
            f'like "Evangelion" or "Fushigi no umi no Nadia".'
        )
        creation_date = date(year=1984, month=12, day=24)
        response = self.client.post(
            gainax.get_edit_absolute_url(),
            follow=True,
            data={
                'user':           user.id,
                'name':           name,
                'phone':          phone,
                'email':          email,
                'description':    description,
                'sector':         sector02.id,
                'creation_date':  creation_date,
                'subject_to_vat': True,
            },
        )
        self.assertNoFormError(response)

        hline = HistoryLine.objects.filter(type=TYPE_EDITION, entity=gainax).latest('date')
        modifs = hline.modifications
        self.assertIsList(modifs, length=7)
        self.assertIn(['phone', old_phone, phone], modifs)
        self.assertIn(['email', email], modifs)
        # self.assertIn(['description'], modifs)
        self.assertIn(['description', old_description, description], modifs)
        self.assertIn(['sector', sector01.id, sector02.id], modifs)
        self.assertIn(['creation_date', '1984-12-24'], modifs)
        self.assertIn(['subject_to_vat', True], modifs, modifs)
        self.assertIn(['legal_form', lform.id, None], modifs, modifs)

        vmodifs = hline.get_verbose_modifications(user)
        self.assertEqual(7, len(vmodifs))

        self.assertIn(
            self.FMT_3_VALUES(
                field=_('Phone number'), oldvalue=old_phone, value=phone,
            ),
            vmodifs,
        )
        self.assertIn(
            self.FMT_2_VALUES(field=_('Email address'), value=email),
            vmodifs,
        )
        # self.assertIn(self.FMT_1_VALUE(field=_('Description')), vmodifs)
        self.assertIn(
            self.FMT_3_VALUES(
                field=_('Description'), oldvalue=old_description, value=description,
            ),
            vmodifs,
        )
        self.assertIn(
            self.FMT_3_VALUES(
                field=_('Sector'), oldvalue=sector01, value=sector02,
            ),
            vmodifs,
        )
        self.assertIn(
            self.FMT_2_VALUES(
                field=_('Date of creation'),
                value=date_format(creation_date, 'DATE_FORMAT'),
            ),
            vmodifs,
        )
        self.assertIn(
            self.FMT_2_VALUES(field=_('Subject to VAT'), value=_('Yes')),
            vmodifs,
        )
        self.assertIn(
            self.FMT_3_VALUES(field=_('Legal form'), oldvalue=lform, value=''),
            vmodifs,
        )

    def test_edition_no_change(self):
        "No change."
        name = 'gainax'
        capital = 12000
        gainax = self._build_organisation(user=self.user.id, name=name, capital=capital)
        old_count = HistoryLine.objects.count()

        response = self.client.post(
            gainax.get_edit_absolute_url(),
            follow=True,
            data={
                'user':    self.user.id,
                'name':    name,
                'capital': capital,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_edition_ignored_changed(self):
        "Ignore the changes : None -> ''."
        name = 'gainax'
        old_capital = 12000
        gainax = FakeOrganisation.objects.create(user=self.user, name=name, capital=old_capital)

        capital = old_capital * 2
        response = self.client.post(
            gainax.get_edit_absolute_url(),
            follow=True,
            data={
                'user':           self.user.id,
                'name':           name,
                'capital':        capital,
                'subject_to_vat': True,
            },
        )
        self.assertNoFormError(response)

        hline = HistoryLine.objects.order_by('-id')[0]
        self.assertEqual(gainax.id,    hline.entity.id)
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertListEqual([['capital', old_capital, capital]], hline.modifications)

    def test_edition_type(self):
        "Type coercion."
        capital = 12000
        gainax = FakeOrganisation.objects.create(user=self.user, name='Gainax', capital=capital)
        old_count = HistoryLine.objects.count()

        gainax = self.refresh(gainax)
        gainax.capital = str(capital)
        gainax.save()

        # 'capital' attribute is now an integer
        self.assertEqual(capital, self.refresh(gainax).capital)

        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_edition_fk(self):
        "FK to CremeEntity."
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
        self.assertIn(
            self.FMT_2_VALUES(field=_('Photograph'), value=img),
            vmodifs[0],
        )

    def test_edition_none(self):
        "New value is None: verbose prints ''."
        old_capital = 1000
        old_date = date(year=1928, month=5, day=3)
        gainax = FakeOrganisation.objects.create(
            user=self.user, name='Gainax',
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
        self.assertListEqual(
            [
                ['capital',        old_capital, None],
                ['creation_date', '1928-05-03', None],
            ],
            hline.modifications,
        )

        vmodifs = hline.get_verbose_modifications(self.user)
        self.assertEqual(2, len(vmodifs))

        fmt = self.FMT_3_VALUES
        self.assertEqual(
            fmt(
                field=_('Capital'),
                oldvalue=old_capital,
                value='',  # <== not None
            ),
            vmodifs[0],
        )
        self.assertEqual(
            fmt(
                field=_('Date of creation'),
                oldvalue=date_format(old_date, 'DATE_FORMAT'),
                value='',  # <== not None
            ),
            vmodifs[1],
        )

    def test_edition_datetime_field(self):
        "DateTimeField."
        create_dt = self.create_datetime
        old_start = create_dt(year=2016, month=11, day=22, hour=16, minute=10)
        meeting = FakeActivity.objects.create(
            user=self.user, title='Meeting with Seele',
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
        self.assertListEqual(
            [
                ['start', dt_to_ISO8601(old_start), dt_to_ISO8601(start)],
                ['end', dt_to_ISO8601(end)],
            ],
            hline.modifications,
        )

        vmodifs = hline.get_verbose_modifications(self.user)
        self.assertEqual(2, len(vmodifs))
        self.assertEqual(
            self.FMT_3_VALUES(
                field=_('Start'),
                oldvalue=date_format(old_start, 'DATETIME_FORMAT'),
                value=date_format(start, 'DATETIME_FORMAT'),
            ),
            vmodifs[0],
        )

        # Set None -------------------------
        meeting = self.refresh(meeting)  # Reset cache
        meeting.end = None
        meeting.save()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))
        self.assertEqual(
            self.FMT_3_VALUES(
                field=_('End'),
                oldvalue=date_format(end, 'DATETIME_FORMAT'),
                value='',
            ),
            hlines[-1].get_verbose_modifications(self.user)[0],
        )

    def test_edition_other_fields(self):
        "Other fields: TimeField, SlugField, FloatField, NullBooleanField."
        # TODO: use true fields in a fake model

        from creme.creme_core.models.history import _PRINTERS, _JSONEncoder

        encode = _JSONEncoder().encode

        self.assertEqual('"17:23:00.000000"', encode(time(hour=17, minute=23)))
        self.assertNotIn('TimeField', _PRINTERS)

        self.assertNotIn('SlugField', _PRINTERS)

        # ------
        n = 3.14
        self.assertEqual('3.14', encode(n))
        float_printer = _PRINTERS.get('FloatField')
        self.assertIsNotNone(float_printer)
        self.assertEqual(
            number_format(n, use_l10n=True),
            float_printer(field=None, user=self.user, val=n),
        )
        self.assertEqual('', float_printer(field=None, user=self.user, val=None))

        # ------
        nbool_printer = _PRINTERS.get('NullBooleanField')
        self.assertIsNotNone(nbool_printer)
        self.assertEqual(_('Yes'),  nbool_printer(field=None, user=self.user, val=True))
        self.assertEqual(_('No'),   nbool_printer(field=None, user=self.user, val=False))
        self.assertEqual(_('N/A'),  nbool_printer(field=None, user=self.user, val=None))

    def test_edition_m2m01(self):
        "set() to add or remove (not at the same time)."
        user = self.user
        cat1, cat2, cat3 = FakeImageCategory.objects.order_by('id')[:3]

        img = FakeImage.objects.create(user=user, name='Grumpy Hayao')

        img.categories.set([cat1, cat2])

        hline1 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_EDITION, hline1.type)
        self.assertEqual(img.id, hline1.entity.id)
        self.assertListEqual(
            [['categories', [], [cat1.id, cat2.id]]],
            hline1.modifications,
        )

        vmodifs1 = hline1.get_verbose_modifications(user)
        self.assertEqual(1, len(vmodifs1))
        self.assertIn(
            vmodifs1[0],
            (
                f'Field “{_("Categories")}” changed: [{cat1}, {cat2}] added.',
                f'Field “{_("Categories")}” changed: [{cat2}, {cat1}] added.',
            ),
        )

        # ---
        clear_global_info()  # Current line is stored in global cache
        img = self.refresh(img)
        img.categories.set([cat1])

        hline2 = HistoryLine.objects.order_by('-id').first()
        self.assertNotEqual(hline1, hline2)
        self.assertEqual(TYPE_EDITION, hline2.type)
        self.assertEqual(img.id, hline1.entity.id)
        self.assertListEqual(
            [['categories', [cat2.id], []]],
            hline2.modifications,
        )
        self.assertListEqual(
            [f'Field “{_("Categories")}” changed: [{cat2}] removed.'],
            hline2.get_verbose_modifications(user),
        )

    def test_edition_m2m02(self):
        "add()/remove() (not at the same time)."
        user = self.user
        cat = FakeImageCategory.objects.first()
        img = FakeImage.objects.create(user=user, name='Grumpy Hayao')

        img.categories.add(cat)

        hline1 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_EDITION, hline1.type)
        self.assertEqual(img.id, hline1.entity.id)
        self.assertListEqual(
            [['categories', [], [cat.id]]],
            hline1.modifications,
        )

        # ---
        clear_global_info()  # Current line is stored in global cache
        img = self.refresh(img)
        img.categories.remove(cat)

        hline2 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_EDITION, hline2.type)
        self.assertEqual(img.id, hline2.entity.id)
        self.assertListEqual(
            [['categories', [cat.id], []]],
            hline2.modifications,
        )

    def test_edition_m2m03(self):
        "Set() which adds & removes at the same time (1 line, not 2)."
        user = self.user
        cat1, cat2, cat3 = FakeImageCategory.objects.order_by('id')[:3]

        img = FakeImage.objects.create(user=user, name='Grumpy Hayao')
        img.categories.set([cat2, cat3])
        old_count = HistoryLine.objects.count()

        img = self.refresh(img)
        img.categories.set([cat1, cat3])
        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertEqual(img.id, hline.entity.id)
        self.assertListEqual(
            [['categories', [cat2.id], [cat1.id]]],
            hline.modifications,
        )
        self.assertListEqual(
            [f'Field “{_("Categories")}” changed: [{cat2}] removed, [{cat1}] added.'],
            hline.get_verbose_modifications(user),
        )

        # We re-add an element (don't do that...)
        img.categories.add(cat2)
        self.assertListEqual(
            [['categories', [], [cat1.id]]],
            self.refresh(hline).modifications,
        )

        # We re-remove an element (don't do that...)
        img.categories.remove(cat1)
        self.assertListEqual(
            # NB: if your code produces this kind of empty line, change your code
            [['categories', [], []]],
            self.refresh(hline).modifications,
        )

    def test_edition_m2m04(self):
        "clear()."
        user = self.user
        cat = FakeImageCategory.objects.first()

        img = FakeImage.objects.create(user=user, name='Grumpy Hayao')
        img.categories.set([cat])
        old_count = HistoryLine.objects.count()

        img = self.refresh(img)
        img.categories.clear()
        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertEqual(img.id, hline.entity.id)
        self.assertListEqual(
            [['categories', [cat.id], []]],
            hline.modifications,
        )

    def test_edition_regular_n_m2m(self):
        user = self.user
        cat = FakeImageCategory.objects.first()

        old_name = 'Hayao'
        img = FakeImage.objects.create(user=user, name=old_name)
        old_count = HistoryLine.objects.count()

        clear_global_info()  # Current line is stored in global cache
        img = self.refresh(img)

        new_name = 'Grumpy Hayao'
        img.name = new_name
        img.save()
        img.categories.set([cat])

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertListEqual(
            [
                ['name', old_name, new_name],
                ['categories', [], [cat.id]],
            ],
            hline.modifications,
        )

    def test_edition_customfield01(self):
        "One custom field at once."
        user = self.user

        ct = ContentType.objects.get_for_model(FakeOrganisation)
        cfield = CustomField.objects.create(
            name='ID number', content_type=ct, field_type=CustomField.STR,
        )

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        old_count = HistoryLine.objects.count()

        value1 = 'ABCD123'
        CustomFieldValue.save_values_for_entities(cfield, [gainax], value1)
        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline1 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(gainax.id, hline1.entity.id)
        self.assertEqual(FakeOrganisation, hline1.entity_ctype.model_class())
        self.assertEqual(TYPE_CUSTOM_EDITION, hline1.type)
        self.assertEqual(user, hline1.entity_owner)
        self.assertListEqual(
            [[cfield.id, value1]],
            hline1.modifications,
        )

        vmodifs1 = hline1.get_verbose_modifications(user)
        self.assertEqual(1, len(vmodifs1))
        self.assertEqual(
            self.FMT_2_VALUES(field=cfield.name, value=value1),
            vmodifs1[0],
        )

        # Old & new values ---
        clear_global_info()  # Current line is stored in global cache
        value2 = 'ABCD12345'
        CustomFieldValue.save_values_for_entities(cfield, [gainax], value2)
        self.assertEqual(old_count + 2, HistoryLine.objects.count())

        hline2 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_CUSTOM_EDITION, hline2.type)
        self.assertListEqual(
            [[cfield.id, value1, value2]],
            hline2.modifications,
        )

        vmodifs2 = hline2.get_verbose_modifications(user)
        self.assertEqual(1, len(vmodifs2))
        self.assertEqual(
            self.FMT_3_VALUES(field=cfield.name, oldvalue=value1, value=value2),
            vmodifs2[0],
        )

    def test_edition_customfield02(self):
        "Several modifications at once => only one lines."
        user = self.user

        ct = ContentType.objects.get_for_model(FakeOrganisation)
        create_cfield = partial(CustomField.objects.create, content_type=ct)
        cfield1 = create_cfield(name='ID number',      field_type=CustomField.STR)
        cfield2 = create_cfield(name='Holidays start', field_type=CustomField.DATE)

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        CustomFieldValue.save_values_for_entities(
            cfield2, [gainax], date(year=2021, month=7, day=10),
        )
        old_count = HistoryLine.objects.count()

        clear_global_info()  # Current line is stored in global cache

        value1 = 'ABCD123'
        CustomFieldValue.save_values_for_entities(cfield1, [gainax], value1)
        CustomFieldValue.save_values_for_entities(
            cfield2, [gainax], date(year=2021, month=7, day=14),
        )
        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(gainax.id, hline.entity.id)
        self.assertEqual(FakeOrganisation, hline.entity_ctype.model_class())
        self.assertEqual(TYPE_CUSTOM_EDITION, hline.type)
        self.assertEqual(user, hline.entity_owner)
        self.assertListEqual(
            [
                [cfield1.id, value1],
                [cfield2.id, '2021-07-10', '2021-07-14'],
            ],
            hline.modifications,
        )

    def test_edition_customfield03(self):
        "Set value to empty => cf_value deleted (see save_values_for_entities())."
        user = self.user

        ct = ContentType.objects.get_for_model(FakeOrganisation)
        cfield = CustomField.objects.create(
            name='ID number', content_type=ct, field_type=CustomField.STR,
        )

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')

        old_value = 'To be removed'
        CustomFieldValue.save_values_for_entities(cfield, [gainax], old_value)
        old_count = HistoryLine.objects.count()

        clear_global_info()  # Current line is stored in global cache

        CustomFieldValue.save_values_for_entities(cfield, [gainax], '')
        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(gainax.id, hline.entity.id)
        self.assertEqual(FakeOrganisation, hline.entity_ctype.model_class())
        self.assertEqual(TYPE_CUSTOM_EDITION, hline.type)
        self.assertEqual(user, hline.entity_owner)
        self.assertListEqual(
            [[cfield.id, old_value, None]],
            hline.modifications,
        )
        self.assertEqual(
            self.FMT_3_VALUES(field=cfield.name, oldvalue=old_value, value=None),
            hline.get_verbose_modifications(user)[0],
        )

    def test_edition_customfield_enum(self):
        user = self.user

        cfield = CustomField.objects.create(
            name='Category',
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
            field_type=CustomField.ENUM,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        create_evalue(value='Plant')
        choice2 = create_evalue(value='Shop')
        choice3 = create_evalue(value='Studio')

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        old_count = HistoryLine.objects.count()

        CustomFieldValue.save_values_for_entities(cfield, [gainax], choice2.id)
        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline1 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(gainax.id, hline1.entity.id)
        self.assertEqual(FakeOrganisation, hline1.entity_ctype.model_class())
        self.assertEqual(TYPE_CUSTOM_EDITION, hline1.type)
        self.assertEqual(user, hline1.entity_owner)
        self.assertListEqual([[cfield.id, choice2.id]], hline1.modifications)
        self.assertEqual(
            self.FMT_2_VALUES(field=cfield.name, value=choice2.id),
            hline1.get_verbose_modifications(user)[0],
        )

        # Old & new values ---
        clear_global_info()  # Current line is stored in global cache
        CustomFieldValue.save_values_for_entities(cfield, [gainax], choice3.id)
        self.assertEqual(old_count + 2, HistoryLine.objects.count())

        hline2 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_CUSTOM_EDITION, hline2.type)
        self.assertListEqual(
            [[cfield.id, choice2.id, choice3.id]],
            hline2.modifications,
        )
        self.assertEqual(
            self.FMT_3_VALUES(field=cfield.name, oldvalue=choice2.id, value=choice3.id),
            hline2.get_verbose_modifications(user)[0],
        )

    def test_edition_customfield_multienum01(self):
        user = self.user

        cfield = CustomField.objects.create(
            name='Categories',
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
            field_type=CustomField.MULTI_ENUM,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        choice1 = create_evalue(value='Studio')
        choice2 = create_evalue(value='Animation')
        create_evalue(value='Food')

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        old_count = HistoryLine.objects.count()

        CustomFieldValue.save_values_for_entities(
            cfield, [gainax], [choice1.id, choice2.id],
        )
        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline1 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(gainax.id, hline1.entity.id)
        self.assertEqual(FakeOrganisation, hline1.entity_ctype.model_class())
        self.assertEqual(TYPE_CUSTOM_EDITION, hline1.type)
        self.assertEqual(user, hline1.entity_owner)
        self.assertListEqual(
            [[cfield.id, [], [choice1.id, choice2.id]]],
            hline1.modifications,
        )

        vmodifs1 = hline1.get_verbose_modifications(user)
        self.assertEqual(1, len(vmodifs1))
        self.assertEqual(
            f'Field “{cfield.name}” changed: [{choice1.id}, {choice2.id}] added.',
            vmodifs1[0],
        )

        # Remove values ---
        clear_global_info()  # Current line is stored in global cache
        CustomFieldValue.save_values_for_entities(
            cfield, [gainax], [choice2.id],  # Choice1 removed
        )
        self.assertEqual(old_count + 2, HistoryLine.objects.count())

        hline2 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_CUSTOM_EDITION, hline2.type)
        self.assertListEqual(
            [[cfield.id, [choice1.id], []]],
            hline2.modifications,
        )
        self.assertEqual(
            f'Field “{cfield.name}” changed: [{choice1.id}] removed.',
            hline2.get_verbose_modifications(user)[0],
        )

        # Add & remove at the same time ----
        clear_global_info()  # Current line is stored in global cache
        CustomFieldValue.save_values_for_entities(
            cfield, [gainax], [choice1.id],  # Choice1 added, choice2 removed
        )
        self.assertEqual(old_count + 3, HistoryLine.objects.count())

        hline3 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_CUSTOM_EDITION, hline3.type)
        self.assertListEqual(
            [[cfield.id, [choice2.id], [choice1.id]]],
            hline3.modifications,
        )
        self.assertEqual(
            f'Field “{cfield.name}” changed: [{choice2.id}] removed, [{choice1.id}] added.',
            hline3.get_verbose_modifications(user)[0],
        )

    def test_edition_customfield_multienum02(self):
        "Merge several lines with 2 CustomFields."
        user = self.user

        ct = ContentType.objects.get_for_model(FakeOrganisation)
        create_cfield = partial(
            CustomField.objects.create,
            content_type=ct, field_type=CustomField.MULTI_ENUM,
        )
        cfield1 = create_cfield(name='Categories')
        cfield2 = create_cfield(name='Theme')

        create_evalue = CustomFieldEnumValue.objects.create
        choice1 = create_evalue(value='Studio', custom_field=cfield1)
        create_evalue(value='Animation', custom_field=cfield1)
        choice2 = create_evalue(value='Planes', custom_field=cfield2)
        create_evalue(value='Nature', custom_field=cfield2)

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        old_count = HistoryLine.objects.count()

        save_values = CustomFieldValue.save_values_for_entities
        save_values(cfield1, [gainax], [choice1.id])
        save_values(cfield2, [gainax], [choice2.id])

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(gainax.id, hline.entity.id)
        self.assertEqual(FakeOrganisation, hline.entity_ctype.model_class())
        self.assertEqual(TYPE_CUSTOM_EDITION, hline.type)
        self.assertEqual(user, hline.entity_owner)
        self.assertListEqual(
            [
                [cfield1.id, [], [choice1.id]],
                [cfield2.id, [], [choice2.id]],
            ],
            hline.modifications,
        )

    # TODO: other CustomField types ?

    def test_deletion01(self):
        old_count = HistoryLine.objects.count()
        gainax = FakeOrganisation.objects.create(user=self.other_user, name='Gainax')
        entity_repr = str(gainax)

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        creation_line = HistoryLine.objects.get(entity=gainax)

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
        self.assertListEqual([], hline.modifications)
        self.assertBetweenDates(hline)

        creation_line = self.refresh(creation_line)
        self.assertIsNone(creation_line.entity)
        self.assertEqual(entity_repr, creation_line.entity_repr)

    def test_deletion02(self):
        "With auxiliary models."
        gainax = FakeOrganisation.objects.create(user=self.user, name='Gainax')
        FakeAddress.objects.create(entity=gainax, city='Tokyo')
        old_count = HistoryLine.objects.count()

        gainax.delete()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))
        self.assertEqual(TYPE_DELETION, hlines[-1].type)

    def test_trash(self):
        user = self.user
        gainax = self.refresh(
            FakeOrganisation.objects.create(user=user, name='Gainax')
        )
        old_count = HistoryLine.objects.count()

        gainax.trash()
        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(TYPE_TRASH,       hline.type)
        self.assertEqual(gainax.id,        hline.entity_id)
        self.assertEqual(FakeOrganisation, hline.entity_ctype.model_class())
        self.assertListEqual([True],       hline.modifications)
        self.assertBetweenDates(hline)
        self.assertListEqual(
            [_('Sent to the trash')], hline.get_verbose_modifications(user),
        )

    def test_restoration(self):
        user = self.user
        gainax = self.refresh(FakeOrganisation.objects.create(
            user=user, name='Gainax', is_deleted=True,
        ))
        old_count = HistoryLine.objects.count()

        gainax.restore()
        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(TYPE_TRASH, hline.type)
        self.assertListEqual([False], hline.modifications)
        self.assertListEqual(
            [_('Restored')], hline.get_verbose_modifications(user),
        )

    def test_related_edition01(self):
        "No HistoryConfigItem => no related line."
        user = self.user
        ghibli = self._build_organisation(user=user.id, name='Ghibli')

        first_name = 'Hayao'
        last_name = 'Miyazaki'
        hayao = self._build_contact(
            user=user.id, first_name=first_name, last_name=last_name,
        )

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_employed', 'is employed'),
            ('test-object_employed', 'employs'),
        )[0]
        Relation.objects.create(
            user=user, subject_entity=hayao, object_entity=ghibli, type=rtype,
        )

        old_count = HistoryLine.objects.count()
        description = 'A great animation movie maker'
        response = self.client.post(
            hayao.get_edit_absolute_url(),
            follow=True,
            data={
                'user':        user.id,
                'first_name':  first_name,
                'last_name':   last_name,
                'description': description,
            },
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
        ghibli = self.create_old(FakeOrganisation, user=user, name='Ghibli')

        first_name = 'Hayao'
        last_name  = 'Miyazaki'
        hayao = self._build_contact(
            user=user.id, first_name=first_name, last_name=last_name,
        )
        self.assertNotEqual(hayao.modified, ghibli.modified)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_employed', 'is employed'),
            ('test-object_employed', 'employs'),
        )[0]
        Relation.objects.create(
            user=user, subject_entity=hayao, object_entity=ghibli, type=rtype,
        )

        HistoryConfigItem.objects.create(relation_type=rtype)

        old_count = HistoryLine.objects.count()
        response = self.client.post(
            hayao.get_edit_absolute_url(),
            follow=True,
            data={
                'user':        user.id,
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
        self.assertEqual(str(ghibli),        hline.entity_repr)
        self.assertEqual(edition_hline.id,   hline.related_line.id)
        self.assertListEqual([], hline.modifications)
        self.assertBetweenDates(hline)
        self.assertEqual(self.refresh(hayao).modified, hline.date)

    def test_related_edition_m2m(self):
        user = self.user
        ghibli = self.create_old(FakeOrganisation, user=user, name='Ghibli')
        img = FakeImage.objects.create(user=user, name='Museum image')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_related_img', '(image) is used by'),
            ('test-object_related_img',  'has related image'),
        )[0]
        Relation.objects.create(
            user=user, subject_entity=img, object_entity=ghibli, type=rtype,
        )

        HistoryConfigItem.objects.create(relation_type=rtype)
        old_count = HistoryLine.objects.count()

        cat = FakeImageCategory.objects.first()
        img.categories.add(cat)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))

        edition_hline = hlines[-2]
        self.assertEqual(TYPE_EDITION, edition_hline.type)

        hline = hlines[-1]
        self.assertEqual(ghibli.id,          hline.entity.id)
        self.assertEqual(ghibli.entity_type, hline.entity_ctype)
        self.assertEqual(user,               hline.entity_owner)
        self.assertEqual(TYPE_RELATED,       hline.type)
        self.assertEqual(str(ghibli),        hline.entity_repr)
        self.assertEqual(edition_hline.id,   hline.related_line.id)
        self.assertListEqual([], hline.modifications)

    def test_related_edition_customfield(self):
        user = self.user

        ct = ContentType.objects.get_for_model(FakeContact)
        cfield = CustomField.objects.create(
            name='Hobbies', content_type=ct, field_type=CustomField.STR,
        )

        ghibli = FakeOrganisation.objects.create(user=user, name='Ghibli')
        hayao = FakeContact.objects.create(user=user, last_name='Miyazaki')

        rtype = self.get_object_or_fail(RelationType, pk=FAKE_REL_SUB_EMPLOYED_BY)
        Relation.objects.create(
            user=user, subject_entity=hayao, object_entity=ghibli, type=rtype,
        )

        HistoryConfigItem.objects.create(relation_type=rtype)
        old_count = HistoryLine.objects.count()

        CustomFieldValue.save_values_for_entities(cfield, [hayao], 'Planes')

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))

        edition_hline = hlines[-2]
        self.assertEqual(TYPE_CUSTOM_EDITION, edition_hline.type)

        hline = hlines[-1]
        self.assertEqual(ghibli.id,          hline.entity.id)
        self.assertEqual(ghibli.entity_type, hline.entity_ctype)
        self.assertEqual(user,               hline.entity_owner)
        self.assertEqual(TYPE_RELATED,       hline.type)
        self.assertEqual(str(ghibli),        hline.entity_repr)
        self.assertEqual(edition_hline.id,   hline.related_line.id)
        self.assertListEqual([], hline.modifications)

    def test_related_edition_customfield_multienum(self):
        user = self.user

        cfield = CustomField.objects.create(
            name='Categories',
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
            field_type=CustomField.MULTI_ENUM,
        )
        choice1 = CustomFieldEnumValue.objects.create(custom_field=cfield, value='Studio')

        ghibli = FakeOrganisation.objects.create(user=user, name='Ghibli')
        hayao = FakeContact.objects.create(user=user, last_name='Miyazaki')

        rtype = self.get_object_or_fail(RelationType, pk=FAKE_REL_SUB_EMPLOYED_BY)
        Relation.objects.create(
            user=user, subject_entity=hayao, object_entity=ghibli, type=rtype,
        )

        HistoryConfigItem.objects.create(relation_type=rtype)
        old_count = HistoryLine.objects.count()

        CustomFieldValue.save_values_for_entities(cfield, [hayao], [choice1.id])

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))

        edition_hline = hlines[-2]
        self.assertEqual(TYPE_CUSTOM_EDITION, edition_hline.type)

        hline = hlines[-1]
        self.assertEqual(ghibli.id,          hline.entity.id)
        self.assertEqual(ghibli.entity_type, hline.entity_ctype)
        self.assertEqual(user,               hline.entity_owner)
        self.assertEqual(TYPE_RELATED,       hline.type)
        self.assertEqual(str(ghibli),        hline.entity_repr)
        self.assertEqual(edition_hline.id,   hline.related_line.id)
        self.assertListEqual([], hline.modifications)

    def test_add_property01(self):
        user = self.user

        gainax = self.create_old(FakeOrganisation, user=user, name='Gainax')
        old_count = HistoryLine.objects.count()

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_make_animes', text='Make anime series',
        )
        prop = CremeProperty.objects.create(type=ptype, creme_entity=gainax)

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,     hline.entity.id)
        self.assertEqual(str(gainax),   hline.entity_repr)
        self.assertEqual(TYPE_PROP_ADD, hline.type)
        self.assertListEqual([ptype.id], hline.modifications)
        self.assertIs(hline.line_type.is_about_relation, False)
        self.assertGreater(hline.date, gainax.modified)

        msg = _('Add property “{}”').format
        self.assertListEqual([msg(ptype.text)], hline.get_verbose_modifications(user))

        expected = [msg(ptype.id)]
        prop.delete()
        ptype.delete()
        self.assertEqual(expected, self.refresh(hline).get_verbose_modifications(user))

    def test_delete_property01(self):
        user = self.user
        gainax = self.create_old(FakeOrganisation, user=user, name='Gainax')
        old_count = HistoryLine.objects.count()

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_make_animes', text='make animes',
        )
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
        self.assertListEqual([ptype.id],      hline.modifications)
        self.assertIs(hline.line_type.is_about_relation, False)
        self.assertGreater(hline.date, gainax.modified)

        ptype.text = ptype.text.title()
        ptype.save()
        self.assertListEqual(
            [_('Delete property “{}”').format(ptype.text)],
            hline.get_verbose_modifications(user),
        )

    def test_add_relation01(self):
        user = self.user

        # Ensure than relation is younger than entities
        nerv = self.create_old(FakeOrganisation, user=user, name='Nerv')
        rei = self.create_old(FakeContact, user=user, first_name='Rei', last_name='Ayanami')

        old_count = HistoryLine.objects.count()

        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_works4', 'is employed'),
            ('test-object_works4',  'employs'),
        )
        relation = Relation.objects.create(
            user=user, subject_entity=rei, object_entity=nerv, type=rtype,
        )
        relation = self.refresh(relation)  # Refresh to get the right modified value

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-2]
        self.assertEqual(rei.id,            hline.entity.id)
        self.assertEqual(str(rei),          hline.entity_repr)
        self.assertEqual(TYPE_RELATION,     hline.type)
        self.assertEqual(relation.created,  hline.date)
        self.assertListEqual([rtype.id], hline.modifications)
        self.assertIs(hline.line_type.is_about_relation, True)

        hline_sym = hlines[-1]
        self.assertEqual(nerv.id,           hline_sym.entity.id)
        self.assertEqual(str(nerv),         hline_sym.entity_repr)
        self.assertEqual(TYPE_SYM_RELATION, hline_sym.type)
        self.assertEqual(relation.created,  hline_sym.date)
        self.assertListEqual([srtype.id], hline_sym.modifications)
        self.assertIs(hline.line_type.is_about_relation, True)

        self.assertEqual(hline_sym.id, hline.related_line.id)
        self.assertEqual(hline.id,     hline_sym.related_line.id)

        msg = _('Add a relationship “{}”').format
        self.assertListEqual([msg(rtype.predicate)],  hline.get_verbose_modifications(user))
        self.assertListEqual([msg(srtype.predicate)], hline_sym.get_verbose_modifications(user))

        rtype_id = rtype.id
        relation.delete()
        rtype.delete()
        self.assertDoesNotExist(rtype)
        self.assertListEqual(
            [msg(rtype_id)], self.refresh(hline).get_verbose_modifications(user),
        )

    def test_add_relation02(self):
        "Create the relation using the 'object' relation type."
        user = self.user
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        rei  = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        olds_ids = [*HistoryLine.objects.values_list('id', flat=True)]

        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_works5', 'is employed'),
            ('test-object_works5',  'employs'),
        )
        Relation.objects.create(user=user, subject_entity=nerv, object_entity=rei, type=srtype)

        hlines = [*HistoryLine.objects.exclude(id__in=olds_ids).order_by('id')]
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
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        old_count = HistoryLine.objects.count()

        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_works4', 'is employed'),
            ('test-object_works4',  'employs'),
        )
        relation = Relation.objects.create(
            user=user, subject_entity=rei, object_entity=nerv, type=rtype,
        )

        hlines = self._get_hlines()
        self.assertEqual(old_count + 2, len(hlines))
        self.assertEqual(TYPE_RELATION,     hlines[-2].type)
        self.assertEqual(TYPE_SYM_RELATION, hlines[-1].type)

        relation.delete()
        hlines = self._get_hlines()
        self.assertEqual(old_count + 4, len(hlines))

        hline = hlines[-2]
        self.assertEqual(rei,               hline.entity.get_real_entity())
        self.assertEqual(str(rei),          hline.entity_repr)
        self.assertEqual(TYPE_RELATION_DEL, hline.type)
        self.assertListEqual([rtype.id], hline.modifications)
        self.assertIs(hline.line_type.is_about_relation, True)
        self.assertDatetimesAlmostEqual(now(), hline.date)

        hline_sym = hlines[-1]
        self.assertEqual(nerv,             hline_sym.entity.get_real_entity())
        self.assertEqual(str(nerv),        hline_sym.entity_repr)
        self.assertEqual(TYPE_SYM_REL_DEL, hline_sym.type)
        self.assertListEqual([srtype.id], hline_sym.modifications)
        self.assertIs(hline_sym.line_type.is_about_relation, True)

        rtype.predicate = rtype.predicate.title()
        rtype.save()
        self.assertListEqual(
            [_('Delete a relationship “{}”').format(rtype.predicate)],
            hline.get_verbose_modifications(user),
        )

    def test_auxiliary_creation(self):
        "Auxiliary: Address."
        user = self.user
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        old_count = HistoryLine.objects.count()

        city = 'Tokyo'
        response = self.client.post(
            reverse('creme_core__create_fake_address', args=(nerv.id,)),
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

    def test_auxiliary_edition01(self):
        "Address."
        country = 'Japan'
        old_city = 'MITAKA'
        gainax = self._build_organisation(user=self.other_user.id, name='Gainax')
        address = FakeAddress.objects.create(entity=gainax, country=country, city=old_city)

        old_count = HistoryLine.objects.count()
        city = old_city.title()
        department = 'Tokyo'
        response = self.client.post(
            address.get_edit_absolute_url(),
            data={
                'country':    country,
                'city':       city,
                'department': department,
            },
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
        self.assertListEqual(
            [
                [
                    ContentType.objects.get_for_model(address).id,
                    address.id,
                    str(address),
                ],
                ['city', old_city, city],
                ['department', department],
            ],
            hline.modifications,
        )

        vmodifs = hline.get_verbose_modifications(self.user)
        self.assertEqual(3, len(vmodifs))

        self.assertEqual(
            _('Edit <{type}>: “{value}”').format(type='Test address', value=address),
            vmodifs[0],
        )
        self.assertEqual(
            self.FMT_3_VALUES(field=_('City'), oldvalue=old_city, value=city),
            vmodifs[1],
        )
        self.assertEqual(
            self.FMT_2_VALUES(field=_('Department'), value=department),
            vmodifs[2],
        )

    def test_auxiliary_edition02(self):
        """Billing.Line
        - an auxiliary + CremeEntity at the same time
        - DecimalField
        - field with choices.
        """
        user = self.user
        invoice = FakeInvoice.objects.create(
            user=user, name='Invoice', expiration_date=date(year=2012, month=12, day=15),
        )
        old_count = HistoryLine.objects.count()
        pline = FakeInvoiceLine.objects.create(
            item='DeathNote', user=user,
            linked_invoice=invoice, quantity=Decimal('1'),
            # discount_unit=FAKE_AMOUNT_UNIT,
            discount_unit=FakeInvoiceLine.Discount.AMOUNT,
        )

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1,     len(hlines))
        self.assertEqual(TYPE_AUX_CREATION, hlines[-1].type)

        old_count += 1

        pline.quantity = Decimal('2')
        # pline.discount_unit = FAKE_PERCENT_UNIT
        pline.discount_unit = FakeInvoiceLine.Discount.PERCENT
        pline.save()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(TYPE_AUX_EDITION, hline.type)

        vmodifs = hline.get_verbose_modifications(user)
        self.assertEqual(3, len(vmodifs))
        self.assertIn(
            self.FMT_3_VALUES(field=_('Quantity'), oldvalue='1', value='2'),
            vmodifs[1],
        )
        self.assertIn(
            self.FMT_3_VALUES(
                field=_('Discount Unit'), oldvalue=_('Amount'), value=_('Percent'),
            ),
            vmodifs[2],
        )

    def test_auxiliary_edition_m2m01(self):
        cat1, cat2 = FakeTodoCategory.objects.order_by('id')[:2]

        gainax = FakeOrganisation.objects.create(user=self.other_user, name='Gainax')
        todo = FakeTodo.objects.create(title='New logo', creme_entity=gainax)
        old_count = HistoryLine.objects.count()

        gainax = self.refresh(gainax)
        todo.categories.set([cat1, cat2])
        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline1 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_AUX_EDITION, hline1.type)

        self.assertEqual(gainax.id,          hline1.entity.id)
        self.assertEqual(gainax.entity_type, hline1.entity_ctype)
        self.assertEqual(self.other_user,    hline1.entity_owner)
        self.assertListEqual(
            [
                [
                    ContentType.objects.get_for_model(todo).id,
                    todo.id,
                    str(todo),
                ],
                ['categories', [], [cat1.id, cat2.id]],
            ],
            hline1.modifications,
        )

        vmodifs1 = hline1.get_verbose_modifications(self.user)
        self.assertEqual(2, len(vmodifs1))
        self.assertEqual(
            _('Edit <{type}>: “{value}”').format(type='Test Todo', value=todo),
            vmodifs1[0],
        )
        self.assertIn(
            vmodifs1[1],
            (
                f'Field “{_("Categories")}” changed: [{cat1}, {cat2}] added.',
                f'Field “{_("Categories")}” changed: [{cat2}, {cat1}] added.',
            ),
        )

        # ---
        todo = self.refresh(todo)  # Reset cache
        todo.categories.set([cat1])

        hline2 = HistoryLine.objects.order_by('-id').first()
        self.assertNotEqual(hline1, hline2)
        self.assertEqual(TYPE_AUX_EDITION, hline2.type)
        self.assertListEqual(
            ['categories', [cat2.id], []],
            hline2.modifications[1],
        )
        self.assertListEqual(
            [
                _('Edit <{type}>: “{value}”').format(type='Test Todo', value=todo),
                f'Field “{_("Categories")}” changed: [{cat2}] removed.'
            ],
            hline2.get_verbose_modifications(self.user),
        )

    def test_auxiliary_edition_m2m02(self):
        "add()/remove() (not at the same time)."
        user = self.user
        cat = FakeTodoCategory.objects.first()

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        todo = FakeTodo.objects.create(title='New logo', creme_entity=gainax)

        # todo = self.refresh(todo)
        todo.categories.add(cat)

        hline1 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_AUX_EDITION, hline1.type)
        self.assertEqual(gainax.id, hline1.entity.id)
        self.assertListEqual(
            ['categories', [], [cat.id]],
            hline1.modifications[1],
        )

        # ---
        todo = self.refresh(todo)
        todo.categories.remove(cat)

        hline2 = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_AUX_EDITION, hline2.type)
        self.assertEqual(gainax.id, hline2.entity.id)
        self.assertListEqual(
            ['categories', [cat.id], []],
            hline2.modifications[1],
        )

    def test_auxiliary_edition_m2m03(self):
        "Set() which adds & removes at the same time (1 line, not 2)."
        user = self.user
        cat1, cat2, cat3 = FakeTodoCategory.objects.order_by('id')[:3]

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        todo = FakeTodo.objects.create(title='New logo', creme_entity=gainax)
        todo.categories.set([cat2, cat3])
        old_count = HistoryLine.objects.count()

        todo = self.refresh(todo)
        todo.categories.set([cat1, cat3])
        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_AUX_EDITION, hline.type)
        self.assertEqual(gainax.id, hline.entity.id)
        self.assertListEqual(
            [
                [
                    ContentType.objects.get_for_model(todo).id,
                    todo.id,
                    str(todo),
                ],
                ['categories', [cat2.id], [cat1.id]],
            ],
            hline.modifications,
        )
        self.assertEqual(
            f'Field “{_("Categories")}” changed: [{cat2}] removed, [{cat1}] added.',
            hline.get_verbose_modifications(user)[1],
        )

        # We re-add an element (don't do that...)
        todo.categories.add(cat2)
        self.assertListEqual(
            ['categories', [], [cat1.id]],
            self.refresh(hline).modifications[1],
        )

        # We re-remove an element (don't do that...)
        todo.categories.remove(cat1)
        self.assertListEqual(
            # NB: if your code produces this kind of empty line, change your code
            ['categories', [], []],
            self.refresh(hline).modifications[1],
        )

    def test_auxiliary_edition_m2m04(self):
        "clear()."
        user = self.user
        cat = FakeTodoCategory.objects.first()

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        todo = FakeTodo.objects.create(title='New logo', creme_entity=gainax)
        todo.categories.set([cat])
        old_count = HistoryLine.objects.count()

        todo = self.refresh(todo)
        todo.categories.clear()
        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_AUX_EDITION, hline.type)
        self.assertEqual(gainax.id, hline.entity.id)
        self.assertListEqual(
            ['categories', [cat.id], []],
            hline.modifications[1],
        )

    def test_auxiliary_edition_regular_n_m2m(self):
        user = self.user
        cat = FakeTodoCategory.objects.first()

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')

        old_title = 'new logo'
        todo = FakeTodo.objects.create(title=old_title, creme_entity=gainax)
        old_count = HistoryLine.objects.count()

        todo = self.refresh(todo)  # Reset cache
        todo.title = new_title = old_title.upper()
        todo.save()
        todo.categories.set([cat])
        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_AUX_EDITION, hline.type)
        self.assertEqual(gainax.id, hline.entity.id)
        self.assertListEqual(
            [
                ['title', old_title, new_title],
                ['categories', [], [cat.id]],
            ],
            hline.modifications[1:],
        )

    def test_auxiliary_edition_multi_save(self):
        user = self.user

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')

        old_title = 'new logo'
        todo = FakeTodo.objects.create(title=old_title, creme_entity=gainax)
        old_count = HistoryLine.objects.count()

        todo = self.refresh(todo)  # Reset cache
        todo.title = new_title = old_title.title()
        todo.save()

        todo.description = description = 'We should design a new logo'
        todo.save()
        self.assertEqual(old_count + 1, HistoryLine.objects.count())  # Not 2

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(TYPE_AUX_EDITION, hline.type)
        self.assertEqual(gainax.id, hline.entity.id)
        self.assertListEqual(
            [
                [
                    ContentType.objects.get_for_model(todo).id,
                    todo.id,
                    str(todo),
                ],
                ['title', old_title, new_title],
                ['description', description],
            ],
            hline.modifications,
        )

    def test_delete_auxiliary(self):
        "Auxiliary: Address."
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

        self.assertEqual(
            _('Delete <{type}>: “{value}”').format(type='Test address', value=address),
            vmodifs[0],
        )

    def test_multi_save01(self):
        old_last_name = 'Ayami'
        new_last_name = 'Ayanami'

        rei = FakeContact.objects.create(
            user=self.user, first_name='Rei', last_name=old_last_name,
        )
        self.assertEqual(1, HistoryLine.objects.filter(entity=rei.id).count())

        rei.last_name = new_last_name
        rei.save()

        hlines = [*HistoryLine.objects.filter(entity=rei.id).order_by('id')]
        self.assertEqual(1, len(hlines))
        self.assertEqual(TYPE_CREATION, hlines[0].type)

    def test_multi_save02(self):
        "Beware internal backup must be recreated after the save()."
        old_last_name = 'Ayami'
        new_last_name = 'Ayanami'

        old_first_name = 'Rey'
        new_first_name = 'Rei'

        rei = FakeContact.objects.create(
            user=self.user, first_name=old_first_name, last_name=old_last_name,
        )
        self.assertEqual(1, HistoryLine.objects.filter(entity=rei.id).count())

        rei = self.refresh(rei)  # Force internal backup, we can begin our edition stuffs

        rei.last_name = new_last_name
        rei.save()

        hlines = [*HistoryLine.objects.filter(entity=rei.id).order_by('id')]
        self.assertEqual(2, len(hlines))

        creation_hline = hlines[0]
        self.assertEqual(TYPE_CREATION, creation_hline.type)

        edition_hline01 = hlines[1]
        self.assertEqual(TYPE_EDITION, edition_hline01.type)
        self.assertListEqual(
            [['last_name', old_last_name, new_last_name]],
            edition_hline01.modifications,
        )

        rei.first_name = new_first_name
        rei.save()

        hlines = [*HistoryLine.objects.filter(entity=rei.id).order_by('id')]
        # self.assertEqual(3, len(hlines))
        self.assertEqual(2, len(hlines))
        self.assertEqual(creation_hline,  hlines[0])
        # self.assertEqual(edition_hline01, hlines[1])

        # edition_hline02 = hlines[2]
        edition_hline02 = hlines[1]
        self.assertEqual(TYPE_EDITION,       edition_hline02.type)
        self.assertEqual(edition_hline01.id, edition_hline02.id)
        self.assertListEqual(
            # [['first_name', old_first_name, new_first_name]],
            [
                ['last_name', old_last_name, new_last_name],
                ['first_name', old_first_name, new_first_name],
            ],
            edition_hline02.modifications,
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

        self.assertListEqual(
            [
                self.FMT_3_VALUES(
                    field=_('Name'), oldvalue='Nerv', value='NERV',
                ),
            ],
            hline.get_verbose_modifications(user),
        )

        fname = 'invalid'
        hline.value = hline.value.replace('name', fname)
        hline.save()
        hline = self.refresh(hline)  # Clean cache

        with self.assertNoException():
            vmodifs = hline.get_verbose_modifications(user)

        self.assertListEqual([self.FMT_1_VALUE(field=fname)], vmodifs)

    def test_disable01(self):
        "CremeEntity creation, edition & deletion."
        old_count = HistoryLine.objects.count()
        logo = FakeImage(user=self.user, name="nerv's logo")

        HistoryLine.disable(logo)
        logo.save()
        self.assertEqual(old_count, HistoryLine.objects.count())

        # Edition ---
        logo = self.refresh(logo)
        HistoryLine.disable(logo)

        logo.name = logo.name.title()
        logo.save()
        self.assertEqual(old_count, HistoryLine.objects.count())

        # Edition (M2M) ---
        logo.categories.add(FakeImageCategory.objects.first())
        self.assertEqual(old_count, HistoryLine.objects.count())

        # Deletion ---
        logo = self.refresh(logo)
        HistoryLine.disable(logo)

        logo.delete()
        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_disable02(self):
        "Relationship creation & deletion."
        user = self.user
        hayao = FakeContact.objects.create(
            user=user, first_name='Hayao', last_name='Miyazaki',
        )
        ghibli = FakeOrganisation.objects.create(user=user, name='Ghibli')
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_employed', 'is employed'),
            ('test-object_employed', 'employs'),
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
        "Property creation & deletion."
        user = self.user
        hayao = FakeContact.objects.create(
            user=user, first_name='Hayao', last_name='Miyazaki',
        )

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_make_animes', text='Make animes',
        )
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
        "Auxiliary creation, edition & deletion."
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
        hayao = FakeContact.objects.create(
            user=user, first_name='Hayao', last_name='Miyazaki',
        )
        ghibli = FakeOrganisation.objects.create(user=user, name='Ghibli')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_delline_works', 'is employed'),
            ('test-object_delline_works',  'employs'),
        )[0]
        Relation.objects.create(
            user=user, subject_entity=hayao, object_entity=ghibli, type=rtype,
        )

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

        ghibli_lines = [*ghibli_line_qs.all()]
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

        line_filter = HistoryLine.objects.filter
        line_filter(id=hline1.id).update(username=admin.username)
        line_filter(id=hline2.id).update(username=other_user.username)
        line_filter(id=hline3.id).update(username=user.username)

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

    def test_populate_related_lines01(self):
        user = self.user
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_contact = partial(FakeContact.objects.create, user=user)
        rei   = create_contact(first_name='Rei',   last_name='Ayanami')
        asuka = create_contact(first_name='Asuka', last_name='Langley')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_employs', 'employs'),
            ('test-object_employs',  'is employed'),
        )[0]
        create_rel = partial(Relation.objects.create, user=user, subject_entity=nerv, type=rtype)
        create_rel(object_entity=rei)
        create_rel(object_entity=asuka)

        hlines = [*HistoryLine.objects.filter(entity=nerv.id).order_by('id')]
        self.assertListEqual(
            [TYPE_CREATION, TYPE_RELATION, TYPE_RELATION],
            [hline.type for hline in hlines],
        )

        with self.assertNumQueries(1):
            HistoryLine.populate_related_lines(hlines)

        with self.assertNumQueries(0):
            rline1 = hlines[0].related_line
            rline2 = hlines[1].related_line
            rline3 = hlines[2].related_line

        self.assertIsNone(rline1)

        self.assertIsNotNone(rline2)
        self.assertEqual(TYPE_SYM_RELATION, rline2.type)
        self.assertEqual(rei.id,            rline2.entity_id)

        self.assertIsNotNone(rline3)
        self.assertEqual(TYPE_SYM_RELATION, rline3.type)
        self.assertEqual(asuka.id,          rline3.entity_id)

        # Avoid fetching lines when it's useless
        with self.assertNumQueries(0):
            HistoryLine.populate_related_lines(hlines)

    def test_populate_related_lines02(self):
        "Use lines passed as pool too."
        user = self.user
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_employs', 'employs'),
            ('test-object_employs',  'is employed'),
        )[0]
        Relation.objects.create(
            user=user, subject_entity=nerv, type=rtype, object_entity=rei,
        )

        hlines = [*reversed(HistoryLine.objects.order_by('-id')[:3])]
        self.assertListEqual(
            [TYPE_CREATION, TYPE_RELATION, TYPE_SYM_RELATION],
            [hline.type for hline in hlines],
        )

        with self.assertNumQueries(0):
            HistoryLine.populate_related_lines(hlines)

        with self.assertNumQueries(0):
            rline1 = hlines[0].related_line
            rline2 = hlines[1].related_line
            rline3 = hlines[2].related_line

        self.assertIsNone(rline1)
        self.assertEqual(hlines[2], rline2)
        self.assertEqual(hlines[1], rline3)
