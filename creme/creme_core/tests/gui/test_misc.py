# -*- coding: utf-8 -*-

from functools import partial
from time import sleep

from django.apps import apps
from django.contrib.sessions.models import Session
from django.test.utils import override_settings

from creme.creme_core.forms import CremeEntityQuickForm, CremeModelForm
from creme.creme_core.gui.button_menu import Button, ButtonsRegistry
from creme.creme_core.gui.fields_config import FieldsConfigRegistry
from creme.creme_core.gui.icons import Icon, IconRegistry
from creme.creme_core.gui.last_viewed import LastViewedItem
from creme.creme_core.gui.quick_forms import QuickFormsRegistry
from creme.creme_core.gui.statistics import _StatisticsRegistry
from creme.creme_core.models import (
    CremeEntity,
    FakeContact,
    FakeEmailCampaign,
    FakeImage,
    FakeInvoice,
    FakeOrganisation,
)

from ..base import CremeTestCase, skipIfNotInstalled
from ..fake_forms import FakeContactQuickForm, FakeOrganisationQuickForm


class GuiTestCase(CremeTestCase):
    @override_settings(MAX_LAST_ITEMS=5)
    def test_last_viewed_items(self):
        user = self.login()

        class FakeRequest:
            def __init__(this):
                user_id = str(user.id)
                sessions = [
                    d
                    for d in (s.get_decoded() for s in Session.objects.all())
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
        self.assertListEqual(
            [contact04.pk, contact03.pk, contact02.pk, contact01.pk],
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
        self.assertListEqual(
            [contact02.pk, contact04.pk, contact03.pk, contact01.pk],
            [i.pk for i in get_items()],
        )

        contact03.delete()
        self.assertFalse(CremeEntity.objects.filter(pk=contact03.id))
        self.assertGET200(FakeContact.get_lv_absolute_url())
        items = get_items()
        self.assertListEqual(
            [contact02.pk, contact04.pk, contact01.pk],
            [i.pk for i in items],
        )

        contact04.trash()
        self.assertGET200(FakeContact.get_lv_absolute_url())
        self.assertListEqual(
            [contact02.pk, contact01.pk],
            [i.pk for i in get_items()],
        )

        # ---
        with override_settings(MAX_LAST_ITEMS=1):
            self.assertGET200(FakeContact.get_lv_absolute_url())

        self.assertListEqual([contact02.pk], [i.pk for i in get_items()])

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
        self.assertListEqual([fmt(FakeContact.objects.count())], stat.retrieve())
        self.assertEqual('', stat.perm)

        FakeContact.objects.create(user=user, first_name='Koyomi', last_name='Araragi')
        self.assertListEqual([fmt(FakeContact.objects.count())], stat.retrieve())

    def test_statistics02(self):
        "Priority."
        id1 = 'persons-contacts'
        perm = 'creme_core'
        id2 = 'persons-organisations'
        id3 = 'creme_core-images'
        registry = _StatisticsRegistry(
        ).register(
            id1, 'Contacts', lambda: [FakeContact.objects.count()], priority=2, perm=perm,
        ).register(
            id2, 'Organisations', lambda: [FakeOrganisation.objects.count()], priority=1,
        ).register(
            id3, 'Images', lambda: [FakeImage.objects.count()], priority=3,
        )

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
        registry = _StatisticsRegistry(
        ).register(
            id1, 'Contacts', lambda: [FakeContact.objects.count()]
        ).register(
            id2, 'Organisations', lambda: [FakeOrganisation.objects.count()], priority=3
        ).register(
            id3, 'Images', lambda: [FakeImage.objects.count()], priority=2
        ).register(
            id4, 'Invoices', lambda: [FakeInvoice.objects.count()]
        ).register(
            id5, 'Campaigns', lambda: [FakeInvoice.objects.count()], priority=0
        )

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
        registry = _StatisticsRegistry(
        ).register(
            id1, 'Contacts', lambda: [FakeContact.objects.count()], priority=2,
        ).register(
            id2, 'Organisations', lambda: [FakeOrganisation.objects.count()], priority=1,
        )

        with self.assertRaises(ValueError):
            registry.register(id1, 'Images', lambda: FakeImage.objects.count())

    def test_statistics_changepriority(self):
        id1 = 'persons-contacts'
        id2 = 'persons-organisations'
        id3 = 'creme_core-images'
        registry = _StatisticsRegistry(
        ).register(
            id1, 'Contacts', lambda: [FakeContact.objects.count()], priority=3,
        ).register(
            id2, 'Organisations', lambda: [FakeOrganisation.objects.count()], priority=6,
        ).register(
            id3, 'Images', lambda: [FakeImage.objects.count()], priority=9,
        )

        registry.change_priority(1, id2, id3)

        stats = [*registry]
        self.assertEqual(id2, stats[0].id)
        self.assertEqual(id3, stats[1].id)
        self.assertEqual(id1, stats[2].id)

    def test_statistics_remove(self):
        id1 = 'persons-contacts'
        id2 = 'persons-organisations'
        id3 = 'creme_core-images'
        registry = _StatisticsRegistry(
        ).register(
            id1, 'Contacts', lambda: [FakeContact.objects.count()], priority=3,
        ).register(
            id2, 'Organisations', lambda: [FakeOrganisation.objects.count()], priority=6,
        ).register(
            id3, 'Images', lambda: [FakeImage.objects.count()], priority=9,
        )

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
        self.assertEqual('Test Contact', icon1.label)

        icon2 = icon_reg.get_4_model(model=FakeOrganisation, theme='chantilly', size_px=48)
        self.assertIn('chantilly/images/organisation_48', icon2.url)
        self.assertEqual('Test Organisation', icon2.label)

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
        self.assertEqual(email_label, icon1.label)

        c.phone = '123456'
        icon2 = icon_reg.get_4_instance(instance=c, theme='icecream', size_px=22)
        self.assertIn('icecream/images/phone_22', icon2.url)
        self.assertEqual(phone_label,             icon2.label)

        o = FakeOrganisation(name='Midland')
        icon3 = icon_reg.get_4_instance(instance=o, theme='icecream', size_px=22)
        self.assertIn('icecream/images/organisation_22', icon3.url)
        self.assertEqual('Test Organisation', icon3.label)

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
            *registry.get_buttons(
                [
                    TestButton3.id_,
                    TestButton2.id_,  # No because ok_4_display() returns False
                    'test_button_registry_invalid',
                    TestButton1.id_,
                ],
                entity=c,
            ),
        ]
        self.assertIsList(buttons, length=2)
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

    def test_button_registry04(self):
        "Permissions."
        basic_user = self.login(
            is_superuser=False,
            allowed_apps=['creme_core', 'persons'],
            creatable_models=[FakeContact],
        )
        basic_ctxt = {'user': basic_user}
        super_ctxt = {'user': self.other_user}

        class TestButton01(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry04_01')
            permissions = 'creme_core'

        has_perm1 = TestButton01().has_perm
        self.assertIs(has_perm1(super_ctxt),  True)
        self.assertIs(has_perm1(basic_ctxt), True)

        # Other app ---
        class TestButton02(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry04_02')
            permissions = 'documents'

        has_perm2 = TestButton02().has_perm
        self.assertIs(has_perm2(super_ctxt),  True)
        self.assertIs(has_perm2(basic_ctxt), False)

        # Creation permission ---
        class TestButton03(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry04_03')
            permissions = 'creme_core.add_fakecontact'

        class TestButton04(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry04_04')
            permissions = 'creme_core.add_fakeorganisation'

        self.assertTrue(TestButton03().has_perm(basic_ctxt))
        self.assertFalse(TestButton04().has_perm(basic_ctxt))

        # Several permissions ---
        class TestButton05(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry04_05')
            permissions = ['persons', 'creme_core.add_fakecontact']

        class TestButton06(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry04_06')
            permissions = ['persons', 'creme_core.add_fakeorganisation']

        self.assertTrue(TestButton05().has_perm(basic_ctxt))
        self.assertFalse(TestButton06().has_perm(basic_ctxt))

        # Check by registry ---
        with self.assertNoException():
            registry = ButtonsRegistry().register(
                TestButton01, TestButton03, TestButton05,
            )

        class TestButton07(Button):
            id_ = Button.generate_id('creme_core', 'test_button_registry04_07')
            permission = 'persons'  # <== Old attribute

        with self.assertRaises(ButtonsRegistry.RegistrationError) as cm:
            registry.register(TestButton07)

        self.assertEqual(
            f'Button class with old attribute "permission" '
            f'(use "permissions" instead): {TestButton07}',
            str(cm.exception)
        )

    def test_quickforms_registry01(self):
        "Registration."
        registry = QuickFormsRegistry()

        # self.assertFalse([*registry.iter_models()])
        self.assertFalse([*registry.models])
        # self.assertIsNone(registry.get_form(FakeContact))
        self.assertIsNone(registry.get_form_class(FakeContact))

        registry.register(
            FakeContact, FakeContactQuickForm,
        ).register(
            FakeOrganisation, FakeOrganisationQuickForm,
        )
        # self.assertIs(FakeContactQuickForm,      registry.get_form(FakeContact))
        # self.assertIs(FakeOrganisationQuickForm, registry.get_form(FakeOrganisation))
        self.assertIs(FakeContactQuickForm,      registry.get_form_class(FakeContact))
        self.assertIs(FakeOrganisationQuickForm, registry.get_form_class(FakeOrganisation))

        # self.assertSetEqual(
        #     {FakeContact, FakeOrganisation},
        #     {*registry.iter_models()}
        # )
        self.assertSetEqual(
            {FakeContact, FakeOrganisation},
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

        # self.assertIsNone(registry.get_form(FakeContact))
        self.assertIsNone(registry.get_form_class(FakeContact))

    def test_fields_config_registry01(self):
        registry = FieldsConfigRegistry()
        self.assertIs(registry.is_model_registered(FakeContact), False)

        registry.register_models(
            FakeContact, FakeOrganisation,
        ).register_models(FakeImage)

        self.assertSetEqual(
            {FakeContact, FakeOrganisation, FakeImage},
            set(registry.models),
        )
        self.assertIs(registry.is_model_registered(FakeContact), True)

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.documents')
    def test_fields_config_registry02(self):
        from creme.documents.models import Document
        from creme.persons.models import Contact

        registry = FieldsConfigRegistry()
        self.assertFalse([*registry.get_needing_apps(Contact, 'phone')])

        registry.register_needed_fields('documents', Contact, 'phone', 'mobile') \
                .register_needed_fields('persons', Document, 'categories')
        self.assertListEqual(
            [apps.get_app_config('documents')],
            [*registry.get_needing_apps(Contact, 'phone')],
        )
        self.assertListEqual(
            [apps.get_app_config('documents')],
            [*registry.get_needing_apps(Contact, 'mobile')],
        )
        self.assertFalse([*registry.get_needing_apps(Contact, 'fax')])
        self.assertListEqual(
            [apps.get_app_config('persons')],
            [*registry.get_needing_apps(Document, 'categories')],
        )
