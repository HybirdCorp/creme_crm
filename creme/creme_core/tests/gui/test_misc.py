# -*- coding: utf-8 -*-

try:
    from functools import partial
    from time import sleep

    from django.apps import apps
    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.sessions.models import Session
    from django.db import models
    from django.test import override_settings
    from django.utils.formats import date_format, number_format
    from django.utils.html import escape
    from django.utils.timezone import localtime
    from django.utils.translation import gettext as _, pgettext

    from ..base import CremeTestCase, skipIfNotInstalled
    from ..fake_constants import FAKE_PERCENT_UNIT, FAKE_DISCOUNT_UNIT
    from ..fake_forms import FakeContactQuickForm, FakeOrganisationQuickForm
    from ..fake_models import (
        FakeContact, FakeOrganisation, FakePosition,
        FakeImage, FakeImageCategory,
        FakeEmailCampaign, FakeMailingList,
        FakeInvoice, FakeInvoiceLine,
    )

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.forms import CremeModelForm, CremeEntityQuickForm  # CremeModelWithUserForm
    from creme.creme_core.gui.button_menu import Button, ButtonsRegistry
    from creme.creme_core.gui.fields_config import FieldsConfigRegistry
    from creme.creme_core.gui.field_printers import (
        _FieldPrintersRegistry,
        FKPrinter,
        simple_print_html,
    )
    from creme.creme_core.gui.icons import Icon, IconRegistry
    from creme.creme_core.gui.last_viewed import LastViewedItem
    from creme.creme_core.gui.quick_forms import QuickFormsRegistry
    from creme.creme_core.gui.statistics import _StatisticsRegistry
    from creme.creme_core.models import CremeEntity, SetCredentials, Language
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class GuiTestCase(CremeTestCase):
    def test_last_viewed_items(self):
        settings.MAX_LAST_ITEMS = 5
        user = self.login()

        class FakeRequest:
            def __init__(this):
                user_id = str(user.id)
                sessions = [d for d in (s.get_decoded() for s in Session.objects.all())
                                if d.get('_auth_user_id') == user_id
                           ]
                self.assertEqual(1, len(sessions))
                this.session = sessions[0]

        def get_items():
            return LastViewedItem.get_all(FakeRequest())

        self.assertEqual(0, len(LastViewedItem.get_all(FakeRequest())))

        create_contact = partial(FakeContact.objects.create, user=self.user)
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
        self.assertGET200(FakeContact.get_lv_absolute_url())
        old_item = get_items()[-1]
        self.assertEqual(contact01.pk,       old_item.pk)
        self.assertEqual(str(contact01), old_item.name)

        self.assertGET200(contact02.get_absolute_url())
        self.assertEqual([contact02.pk, contact04.pk, contact03.pk, contact01.pk],
                         [i.pk for i in get_items()]
                        )

        contact03.delete()
        self.assertFalse(CremeEntity.objects.filter(pk=contact03.id))
        self.assertGET200(FakeContact.get_lv_absolute_url())
        items = get_items()
        self.assertEqual([contact02.pk, contact04.pk, contact01.pk],
                         [i.pk for i in items]
                        )

        contact04.trash()
        self.assertGET200(FakeContact.get_lv_absolute_url())
        self.assertEqual([contact02.pk, contact01.pk],
                         [i.pk for i in get_items()]
                        )

        settings.MAX_LAST_ITEMS = 1
        self.assertGET200(FakeContact.get_lv_absolute_url())
        self.assertEqual([contact02.pk], [i.pk for i in get_items()])

    def test_field_printers01(self):
        "Register by field types, different outputs..."
        user = self.create_user()

        print_charfield_html_args = []
        print_integerfield_html_args = []

        def print_charfield_html(entity, fval, user, field):
            print_charfield_html_args.append((entity, fval, user, field))
            return f'<span>{fval}</span>'

        def print_charfield_csv(entity, fval, user, field):
            return f'«{fval}»'

        def print_integerfield_html(entity, fval, user, field):
            print_integerfield_html_args.append((entity, fval, user, field))
            return f'<span data-type="integer">{fval}</span>'

        registry = _FieldPrintersRegistry()\
                       .register(models.CharField,    print_charfield_html) \
                       .register(models.CharField,    print_charfield_csv, output='csv') \
                       .register(models.IntegerField, print_integerfield_html, output='html')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='NERV', capital=1234)
        orga2 = create_orga(name='Seele')

        get_html_val = registry.get_html_field_value
        get_field = FakeOrganisation._meta.get_field

        self.assertEqual('<span>NERV</span>', get_html_val(orga1, 'name', user))
        self.assertEqual([(orga1, orga1.name, user, get_field('name'))],
                         print_charfield_html_args
                        )

        self.assertEqual('<span>Seele</span>', get_html_val(orga2, 'name', user))
        self.assertEqual('«NERV»', registry.get_csv_field_value(orga1, 'name', user))

        self.assertEqual('<span data-type="integer">1234</span>',
                         get_html_val(orga1, 'capital', user)
                        )
        self.assertEqual([(orga1, orga1.capital, user, get_field('capital'))],
                         print_integerfield_html_args
                        )

    def test_field_printers02(self):
        "ForeignKey."
        user = self.create_user()

        print_foreignkey_html = FKPrinter(none_printer=FKPrinter.print_fk_null_html,
                                          default_printer=simple_print_html,
                                         )
        print_foreignkey_html.register(CremeEntity, FKPrinter.print_fk_entity_html)

        field_printers_registry = _FieldPrintersRegistry()
        field_printers_registry.register(models.ForeignKey, print_foreignkey_html)

        get_html_val = field_printers_registry.get_html_field_value
        get_csv_val  = field_printers_registry.get_csv_field_value

        create_cat = FakeImageCategory.objects.create
        cat1 = create_cat(name='Photo of contact')
        cat2 = create_cat(name='Photo of product')

        img = FakeImage.objects.create(name="Casca's face", user=user, description="Casca's selfie")
        img.categories.set([cat1, cat2])

        create_contact = partial(FakeContact.objects.create, user=user)
        casca = create_contact(
            first_name='Casca', last_name='Mylove',
            position=FakePosition.objects.create(title='Warrior<script>'),
            image=img,
        )
        judo = create_contact(first_name='Judo', last_name='Doe')

        escaped_title = 'Warrior&lt;script&gt;'

        self.assertEqual(casca.last_name,      get_html_val(casca, 'last_name',       user))
        self.assertEqual(casca.last_name,      get_csv_val(casca,  'last_name',       user))

        self.assertEqual(casca.first_name,     get_html_val(casca, 'first_name',      user))
        self.assertEqual(escaped_title,        get_html_val(casca, 'position',        user))

        self.assertEqual(escaped_title,        get_html_val(casca, 'position__title', user))
        self.assertEqual(casca.position.title, get_csv_val(casca,  'position__title', user))

        # FK: with & without customised null_label
        self.assertEqual('', get_html_val(judo, 'position', user))
        self.assertEqual('', get_csv_val(judo,  'position', user))
        self.assertEqual('<em>{}</em>'.format(pgettext('persons-is_user', 'None')),
                         get_html_val(casca, 'is_user', user)
                        )
        self.assertEqual('', get_csv_val(casca, 'is_user', user))  # Null_label not used in CSV backend

        self.assertEqual(f'<a href="{img.get_absolute_url()}">{escape(img)}</a>',
                         get_html_val(casca, 'image', user)
                        )
        self.assertEqual(str(casca.image), get_csv_val(casca, 'image', user))

        self.assertEqual('<p>Casca&#39;s selfie</p>',
                         get_html_val(casca, 'image__description', user)
                        )
        self.assertEqual(casca.image.description,
                         get_csv_val(casca, 'image__description', user)
                        )

        date_str = date_format(localtime(casca.created), 'DATETIME_FORMAT')
        self.assertEqual(date_str, get_html_val(casca, 'created', user))
        self.assertEqual(date_str, get_csv_val(casca,  'created', user))

        self.assertEqual(f'<ul><li>{cat1.name}</li><li>{cat2.name}</li></ul>',
                         get_html_val(casca, 'image__categories', user)
                        )
        self.assertEqual(f'{cat1.name}/{cat2.name}',
                         get_csv_val(casca, 'image__categories', user)
                        )
        # TODO: test ImageField

        self.assertEqual('', get_html_val(judo, 'position__title',    user))
        self.assertEqual('', get_html_val(judo, 'image',              user))
        self.assertEqual('', get_html_val(judo, 'image__description', user))
        self.assertEqual('', get_html_val(judo, 'image__categories',  user))

        self.assertEqual(str(user), get_html_val(casca, 'image__user', user))                # depth = 2
        self.assertEqual(user.username, get_html_val(casca, 'image__user__username', user))  # depth = 3

    def test_field_printers03(self):
        "ManyToMany (simple model)."
        user = self.create_user()
        field_printers_registry = _FieldPrintersRegistry()

        create_lang = Language.objects.create
        lang1 = create_lang(name='Klingon')
        lang2 = create_lang(name='Namek')

        goku = FakeContact.objects.create(user=user, first_name='Goku', last_name='Son')
        goku.languages.set([lang1, lang2])

        get_html_val = field_printers_registry.get_html_field_value
        result_fmt = '<ul><li>{}</li><li>{}</li></ul>'.format
        self.assertEqual(result_fmt(lang1, lang2),
                         get_html_val(goku, 'languages', user)
                        )
        self.assertEqual(result_fmt(lang1.name, lang2.name),
                         get_html_val(goku,  'languages__name', user)
                        )

        get_csv_val = field_printers_registry.get_csv_field_value
        self.assertEqual(f'{lang1}/{lang2}',
                         get_csv_val(goku, 'languages', user)
                        )
        self.assertEqual(f'{lang1.name}/{lang2.name}',
                         get_csv_val(goku, 'languages__name', user)
                        )

    def test_field_printers04(self):
        "ManyToMany (CremeEntity)."
        user = self.login(is_superuser=False)
        self.role.exportable_ctypes.set([ContentType.objects.get_for_model(FakeEmailCampaign)])
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        field_printers_registry = _FieldPrintersRegistry()

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        camp1 = create_camp(name='Camp#1')
        camp2 = create_camp(name='Camp#2')
        create_camp(name='Camp#3')

        create_ml = partial(FakeMailingList.objects.create, user=user)
        ml1 = create_ml(name='ML#1')
        ml2 = create_ml(name='ML#2')
        ml3 = create_ml(name='ML#3', user=self.other_user)
        camp1.mailing_lists.set([ml1, ml2])
        camp2.mailing_lists.set([ml3])

        get_html_val = field_printers_registry.get_html_field_value
        get_csv_val  = field_printers_registry.get_csv_field_value
        self.assertEqual(f'<ul>'
                            f'<li><a target="_blank" href="{ml1.get_absolute_url()}">{ml1}</a></li>'
                            f'<li><a target="_blank" href="{ml2.get_absolute_url()}">{ml2}</a></li>'
                         f'</ul>',
                         get_html_val(camp1, 'mailing_lists', user)
                        )
        self.assertEqual(f'<ul>'
                            f'<li>{ml1.name}</li>'
                            f'<li>{ml2.name}</li>'
                         f'</ul>',
                         get_html_val(camp1, 'mailing_lists__name', user)
                        )

        csv_value = f'{ml1}/{ml2}'
        self.assertEqual(csv_value, get_csv_val(camp1, 'mailing_lists', user))
        self.assertEqual(csv_value, get_csv_val(camp1, 'mailing_lists__name', user))

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        html_value = f'<ul><li>{HIDDEN_VALUE}</li></ul>'
        self.assertEqual(html_value, get_html_val(camp2, 'mailing_lists', user))
        self.assertEqual(html_value, get_html_val(camp2, 'mailing_lists__name', user))

        self.assertEqual(HIDDEN_VALUE, get_csv_val(camp2, 'mailing_lists', user))
        self.assertEqual(HIDDEN_VALUE, get_csv_val(camp2, 'mailing_lists__name', user))

    def test_field_printers05(self):
        "Credentials."
        user = self.login(is_superuser=False, allowed_apps=['creme_core'])
        self.role.exportable_ctypes.set([ContentType.objects.get_for_model(FakeContact)])
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        field_printers_registry = _FieldPrintersRegistry()

        create_img = FakeImage.objects.create
        casca_face = create_img(name='Casca face', user=self.other_user, description="Casca's selfie")
        judo_face  = create_img(name='Judo face',  user=user,            description="Judo's selfie")
        self.assertTrue(user.has_perm_to_view(judo_face))
        self.assertFalse(user.has_perm_to_view(casca_face))

        create_contact = partial(FakeContact.objects.create, user=user)
        casca = create_contact(first_name='Casca', last_name='Mylove', image=casca_face)
        judo  = create_contact(first_name='Judo',  last_name='Doe',    image=judo_face)

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual(f'<a href="{judo_face.get_absolute_url()}">{judo_face}</a>',
                         get_html_val(judo, 'image', user)
                        )
        self.assertEqual('<p>Judo&#39;s selfie</p>',
                         get_html_val(judo, 'image__description', user)
                        )

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image', user))
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image__description', user))
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image__categories', user))

        get_csv_val = field_printers_registry.get_csv_field_value
        self.assertEqual(HIDDEN_VALUE, get_csv_val(casca, 'image', user))
        self.assertEqual(HIDDEN_VALUE, get_csv_val(casca, 'image__description', user))
        self.assertEqual(HIDDEN_VALUE, get_csv_val(casca, 'image__categories', user))

    def test_field_printers06(self):
        "Boolean Field."
        user = self.create_user()
        field_printers_registry = _FieldPrintersRegistry()

        create_contact = partial(FakeContact.objects.create, user=user)
        casca = create_contact(first_name='Casca', last_name='Mylove', is_a_nerd=False)
        judo  = create_contact(first_name='Judo',  last_name='Doe',    is_a_nerd=True)

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual('<input type="checkbox" disabled/>' + _('No'),
                         get_html_val(casca, 'is_a_nerd', user)
                        )
        self.assertEqual('<input type="checkbox" checked disabled/>' + _('Yes'),
                         get_html_val(judo, 'is_a_nerd', user)
                        )

        get_csv_val = field_printers_registry.get_csv_field_value
        self.assertEqual(_('No'),  get_csv_val(casca, 'is_a_nerd', user))
        self.assertEqual(_('Yes'), get_csv_val(judo, 'is_a_nerd', user))

    def test_field_printers07(self):
        "Numerics Field."
        user = self.create_user()
        field_printers_registry = _FieldPrintersRegistry()

        # Integer
        capital = 12345

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Hawk', capital=capital)
        orga2 = create_orga(name='God hand')

        get_csv_val = field_printers_registry.get_csv_field_value
        self.assertEqual(str(capital), get_csv_val(orga1, 'capital', user))
        self.assertEqual('',           get_csv_val(orga2, 'capital', user))

        # Decimal & integer with choices
        invoice = FakeInvoice.objects.create(user=user, name='Swords & shields')

        create_line = partial(FakeInvoiceLine.objects.create, user=user, linked_invoice=invoice)
        line1 = create_line(item='Swords',  quantity='3.00', unit_price='125.6', discount_unit=FAKE_PERCENT_UNIT)
        line2 = create_line(item='Shields', quantity='2.00', unit_price='53.4',  discount_unit=None)

        dec_format = partial(number_format, use_l10n=True)
        self.assertEqual(dec_format('3.00'),  get_csv_val(line1, 'quantity',   user))
        self.assertEqual(dec_format('125.6'), get_csv_val(line1, 'unit_price', user))
        self.assertEqual(FAKE_DISCOUNT_UNIT[FAKE_PERCENT_UNIT],
                         get_csv_val(line1, 'discount_unit', user)
                        )
        self.assertEqual('', get_csv_val(line2, 'discount_unit', user))

    @override_settings(URLIZE_TARGET_BLANK=False)
    def test_field_printers08(self):
        "Test TexField: link => no target."
        user = self.create_user()
        field_printers_registry = _FieldPrintersRegistry()

        hawk = FakeOrganisation.objects.create(
            user=user, name='Hawk',
            description='A powerful army.\nOfficial site: www.hawk-troop.org',
        )

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual(
            '<p>A powerful army.<br>Official site: <a href="http://www.hawk-troop.org">www.hawk-troop.org</a></p>',
            get_html_val(hawk, 'description', user)
        )

    @override_settings(URLIZE_TARGET_BLANK=True)
    def test_field_printers09(self):
        "Test TexField: link => target='_blank'."
        user = self.create_user()
        field_printers_registry = _FieldPrintersRegistry()

        hawk = FakeOrganisation.objects.create(user=user, name='Hawk',
                                               description='A powerful army.\nOfficial site: www.hawk-troop.org'
                                              )

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual(
            '<p>A powerful army.<br>'
            'Official site: '
            '<a target="_blank" rel="noopener noreferrer" href="http://www.hawk-troop.org">www.hawk-troop.org</a>'
            '</p>',
            get_html_val(hawk, 'description', user)
        )

    def test_statistics01(self):
        user = self.create_user()

        registry = _StatisticsRegistry()

        s_id = 'persons-contacts'
        label = 'Contacts'
        fmt = 'There are {} Contacts'.format
        registry.register(s_id, label, lambda: [fmt(FakeContact.objects.count())])

        stats = [*registry]
        self.assertEqual(1, len(stats))

        stat = stats[0]
        self.assertEqual(s_id,  stat.id)
        self.assertEqual(label, stat.label)
        self.assertEqual([fmt(FakeContact.objects.count())], stat.retrieve())
        self.assertEqual('', stat.perm)

        FakeContact.objects.create(user=user, first_name='Koyomi', last_name='Araragi')
        self.assertEqual([fmt(FakeContact.objects.count())], stat.retrieve())

    def test_statistics02(self):
        "Priority"
        id1 = 'persons-contacts'
        perm = 'creme_core'
        id2 = 'persons-organisations'
        id3 = 'creme_core-images'
        registry = _StatisticsRegistry() \
                    .register(id1, 'Contacts',      lambda: [FakeContact.objects.count()],      priority=2, perm=perm) \
                    .register(id2, 'Organisations', lambda: [FakeOrganisation.objects.count()], priority=1) \
                    .register(id3, 'Images',        lambda: [FakeImage.objects.count()],        priority=3)

        stats = [*registry]
        self.assertEqual(id2, stats[0].id)
        self.assertEqual(id1, stats[1].id)
        self.assertEqual(id3, stats[2].id)

        self.assertEqual(perm, stats[1].perm)

    def test_statistics03(self):
        "Priority None/not None"
        id1 = 'persons-contacts'
        id2 = 'persons-organisations'
        id3 = 'creme_core-images'
        id4 = 'billing-invoices'
        id5 = 'emails-campaigns'
        registry = _StatisticsRegistry() \
                    .register(id1, 'Contacts',      lambda: [FakeContact.objects.count()]) \
                    .register(id2, 'Organisations', lambda: [FakeOrganisation.objects.count()], priority=3) \
                    .register(id3, 'Images',        lambda: [FakeImage.objects.count()],        priority=2) \
                    .register(id4, 'Invoices',      lambda: [FakeInvoice.objects.count()]) \
                    .register(id5, 'Campaigns',     lambda: [FakeInvoice.objects.count()],      priority=0)

        stats = [*registry]
        self.assertEqual(id5, stats[0].id)
        self.assertEqual(id1, stats[1].id)
        self.assertEqual(id3, stats[2].id)
        self.assertEqual(id2, stats[3].id)
        self.assertEqual(id4, stats[4].id)

    def test_statistics04(self):
        "Duplicated ID."
        id1 = 'persons-contacts'
        id2 = 'persons-organisations'
        registry = _StatisticsRegistry() \
                    .register(id1, 'Contacts',      lambda: [FakeContact.objects.count()],      priority=2) \
                    .register(id2, 'Organisations', lambda: [FakeOrganisation.objects.count()], priority=1) \

        with self.assertRaises(ValueError):
            registry.register(id1, 'Images', lambda: FakeImage.objects.count())

    def test_statistics_changepriority(self):
        id1 = 'persons-contacts'
        id2 = 'persons-organisations'
        id3 = 'creme_core-images'
        registry = _StatisticsRegistry() \
                    .register(id1, 'Contacts',      lambda: [FakeContact.objects.count()],      priority=3) \
                    .register(id2, 'Organisations', lambda: [FakeOrganisation.objects.count()], priority=6) \
                    .register(id3, 'Images',        lambda: [FakeImage.objects.count()],        priority=9)

        registry.change_priority(1, id2, id3)

        stats = [*registry]
        self.assertEqual(id2, stats[0].id)
        self.assertEqual(id3, stats[1].id)
        self.assertEqual(id1, stats[2].id)

    def test_statistics_remove(self):
        id1 = 'persons-contacts'
        id2 = 'persons-organisations'
        id3 = 'creme_core-images'
        registry = _StatisticsRegistry() \
                    .register(id1, 'Contacts',      lambda: [FakeContact.objects.count()],      priority=3) \
                    .register(id2, 'Organisations', lambda: [FakeOrganisation.objects.count()], priority=6) \
                    .register(id3, 'Images',        lambda: [FakeImage.objects.count()],        priority=9)

        registry.remove('invalid_id', id3, id1)

        stats = [*registry]
        self.assertEqual(1,   len(stats))
        self.assertEqual(id2, stats[0].id)

    def test_icon_registry01(self):
        "get_4_model()"
        icon_reg = IconRegistry()
        icon_reg.register(FakeContact,      'images/contact_%(size)s.png')
        icon_reg.register(FakeOrganisation, 'images/organisation_%(size)s.png')

        icon1 = icon_reg.get_4_model(model=FakeContact, theme='icecream', size_px=22)
        self.assertIsInstance(icon1, Icon)
        self.assertIn('icecream/images/contact_22', icon1.url)
        self.assertEqual('Test Contact',           icon1.label)

        icon2 = icon_reg.get_4_model(model=FakeOrganisation, theme='chantilly', size_px=48)
        self.assertIn('chantilly/images/organisation_48', icon2.url)
        self.assertEqual('Test Organisation',            icon2.label)

        # Bad size
        icon3 = icon_reg.get_4_model(model=FakeContact, theme='icecream', size_px=1024)
        self.assertIsInstance(icon3, Icon)
        self.assertIn('', icon3.url)

        # Model not registered
        icon4 = icon_reg.get_4_model(model=FakeImage, theme='icecream', size_px=22)
        self.assertIsInstance(icon4, Icon)
        self.assertIn('', icon4.url)

    def test_icon_registry02(self):
        "get_4_instance()"
        icon_reg = IconRegistry()
        icon_reg.register(FakeContact,      'images/contact_%(size)s.png')
        icon_reg.register(FakeOrganisation, 'images/organisation_%(size)s.png')

        phone_label = 'Contact with phone'
        email_label = 'Contact with email'

        icon_reg.register_4_instance(
            FakeContact,
            lambda instance: ('phone', phone_label) if instance.phone else ('email', email_label)
        )

        c = FakeContact(first_name='Casca', last_name='Mylove')
        icon1 = icon_reg.get_4_instance(instance=c, theme='icecream', size_px=22)
        self.assertIsInstance(icon1, Icon)
        self.assertIn('icecream/images/email_22', icon1.url)
        self.assertEqual(email_label,             icon1.label)

        c.phone = '123456'
        icon2 = icon_reg.get_4_instance(instance=c, theme='icecream', size_px=22)
        self.assertIn('icecream/images/phone_22', icon2.url)
        self.assertEqual(phone_label,             icon2.label)

        o = FakeOrganisation(name='Midland')
        icon3 = icon_reg.get_4_instance(instance=o, theme='icecream', size_px=22)
        self.assertIn('icecream/images/organisation_22', icon3.url)
        self.assertEqual('Test Organisation',           icon3.label)

    def test_button_registry01(self):
        class TestButton1(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry_1')

        class TestButton2(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry_2')

            def ok_4_display(self, entity):
                return False

        class TestButton3(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry_3')

        class TestButton4(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry_4')

        registry = ButtonsRegistry()
        registry.register(TestButton1, TestButton2, TestButton3, TestButton4)

        class DuplicatedTestButton(Button):
            id_ = TestButton1.id_

        with self.assertRaises(ButtonsRegistry.RegistrationError):
            registry.register(DuplicatedTestButton)

        get = registry.get_button
        self.assertIsInstance(get(TestButton1.id_), TestButton1)
        self.assertIsInstance(get(TestButton2.id_), TestButton2)
        self.assertIsNone(get(Button.generate_id('creme_core', 'test_button_registry_invalid')))

        c = FakeContact(first_name='Casca', last_name='Mylove')
        buttons = [
            *registry.get_buttons([TestButton3.id_,
                                   TestButton2.id_,  # No because ok_4_display() returns False
                                   'test_button_registry_invalid',
                                   TestButton1.id_,
                                  ],
                                  entity=c,
                                 ),
        ]
        self.assertIsInstance(buttons, list)
        self.assertEqual(2, len(buttons))
        self.assertIsInstance(buttons[0], TestButton3)
        self.assertIsInstance(buttons[1], TestButton1)

        all_button_items = [*registry]
        self.assertEqual(4, len(all_button_items))

        button_item = all_button_items[0]
        self.assertIsInstance(button_item[1], Button)
        self.assertEqual(button_item[0], button_item[1].id_)

    def test_button_registry02(self):
        "Duplicated ID."
        class TestButton1(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry_1')

        class TestButton2(TestButton1):
            # id_ = Button.generate_id('creme_core', 'test_button_registry_2') NOPE
            pass

        registry = ButtonsRegistry()

        with self.assertRaises(ButtonsRegistry.RegistrationError) as cm:
            registry.register(TestButton1, TestButton2)

        self.assertEqual(
            f"Duplicated button's ID (or button registered twice) : {TestButton1.id_}",
            str(cm.exception)
        )

    def test_button_registry03(self):
        "Empty ID."
        class TestButton(Button):
            # id_ = Button.generate_id('creme_core', 'test_button_registry') # NOPE
            pass

        registry = ButtonsRegistry()

        with self.assertRaises(ButtonsRegistry.RegistrationError) as cm:
            registry.register(TestButton)

        self.assertEqual(
            f'Button class with empty id_: {TestButton}',
            str(cm.exception)
        )

    def test_quickforms_registry01(self):
        "Registration."
        registry = QuickFormsRegistry()

        self.assertFalse([*registry.iter_models()])
        self.assertFalse([*registry.models])
        self.assertIsNone(registry.get_form(FakeContact))
        self.assertIsNone(registry.get_form_class(FakeContact))

        registry.register(FakeContact,      FakeContactQuickForm) \
                .register(FakeOrganisation, FakeOrganisationQuickForm)
        self.assertIs(FakeContactQuickForm,      registry.get_form(FakeContact))
        self.assertIs(FakeOrganisationQuickForm, registry.get_form(FakeOrganisation))
        self.assertIs(FakeContactQuickForm,      registry.get_form_class(FakeContact))
        self.assertIs(FakeOrganisationQuickForm, registry.get_form_class(FakeOrganisation))

        self.assertSetEqual({FakeContact, FakeOrganisation},
                            {*registry.iter_models()}
                           )
        self.assertSetEqual({FakeContact, FakeOrganisation},
                            {*registry.models}
                           )

        # ---
        class OtherContactQuickForm(CremeEntityQuickForm):
            class Meta:
                model = FakeContact
                fields = ('user', 'last_name', 'first_name')

        with self.assertRaises(registry.RegistrationError):
            registry.register(FakeContact, OtherContactQuickForm)

        # ---
        class CampaignQuickForm(CremeModelForm):  # does not inherit CremeEntityQuickForm
            class Meta:
                model = FakeEmailCampaign
                fields = ('user', 'name')

        with self.assertRaises(registry.RegistrationError):
            registry.register(FakeEmailCampaign, CampaignQuickForm)

    def test_quickforms_registry02(self):
        "Un-registration."
        registry = QuickFormsRegistry()

        with self.assertRaises(registry.RegistrationError):
            registry.unregister(FakeContact)

        registry.register(FakeContact, FakeContactQuickForm)
        with self.assertNoException():
            registry.unregister(FakeContact)

        self.assertIsNone(registry.get_form(FakeContact))
        self.assertIsNone(registry.get_form_class(FakeContact))

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.documents')
    def test_fields_config_registry(self):
        from creme.documents.models import Document
        from creme.persons.models import Contact

        registry = FieldsConfigRegistry()
        self.assertFalse([*registry.get_needing_apps(Contact, 'phone')])

        registry.register_needed_fields('documents', Contact, 'phone', 'mobile') \
                .register_needed_fields('persons', Document, 'categories')
        self.assertListEqual(
            [apps.get_app_config('documents')],
            [*registry.get_needing_apps(Contact, 'phone')]
        )
        self.assertListEqual(
            [apps.get_app_config('documents')],
            [*registry.get_needing_apps(Contact, 'mobile')]
        )
        self.assertFalse([*registry.get_needing_apps(Contact, 'fax')])
        self.assertListEqual(
            [apps.get_app_config('persons')],
            [*registry.get_needing_apps(Document, 'categories')]
        )
