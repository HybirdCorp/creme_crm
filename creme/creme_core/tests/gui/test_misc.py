# from functools import partial
# from time import sleep
#
# from django.contrib.sessions.models import Session
# from django.test.utils import override_settings
from django.apps import apps

from creme.creme_core.forms import CremeEntityQuickForm, CremeModelForm
from creme.creme_core.gui.fields_config import FieldsConfigRegistry
from creme.creme_core.gui.icons import Icon, IconRegistry
# from creme.creme_core.gui.last_viewed import LastViewedItem
from creme.creme_core.gui.mass_import import FormRegistry
from creme.creme_core.gui.merge import _MergeFormRegistry
from creme.creme_core.gui.quick_forms import QuickFormRegistry
from creme.creme_core.gui.statistics import StatisticRegistry
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (  # CremeEntity
    FakeContact,
    FakeEmailCampaign,
    FakeImage,
    FakeInvoice,
    FakeOrganisation,
    FakeTicket,
)

from ..base import CremeTestCase, skipIfNotInstalled
from ..fake_forms import (
    FakeContactQuickForm,
    FakeOrganisationQuickForm,
    get_csv_form_builder,
    get_merge_form_builder,
)


class GuiTestCase(CremeTestCase):
    # @override_settings(MAX_LAST_ITEMS=5)
    # def test_last_viewed_items(self):
    #     self.login_as_root()
    #     user = self.get_root_user()
    #
    #     class FakeRequest:
    #         def __init__(this):
    #             user_id = str(user.id)
    #             this.session = self.get_alone_element(
    #                 d
    #                 for d in (s.get_decoded() for s in Session.objects.all())
    #                 if d.get('_auth_user_id') == user_id
    #             )
    #
    #     def get_items():
    #         return LastViewedItem.get_all(FakeRequest())
    #
    #     self.assertEqual(0, len(LastViewedItem.get_all(FakeRequest())))
    #
    #     create_contact = partial(FakeContact.objects.create, user=user)
    #     contact01 = create_contact(first_name='Casca',    last_name='Mylove')
    #     contact02 = create_contact(first_name='Puck',     last_name='Elfman')
    #     contact03 = create_contact(first_name='Judo',     last_name='Doe')
    #     contact04 = create_contact(first_name='Griffith', last_name='Femto')
    #
    #     self.assertGET200(contact01.get_absolute_url())
    #     items = get_items()
    #     self.assertEqual(1, len(items))
    #     self.assertEqual(contact01.pk, items[0].pk)
    #
    #     # ---
    #     self.assertGET200(contact02.get_absolute_url())
    #     self.assertGET200(contact03.get_absolute_url())
    #     self.assertGET200(contact04.get_absolute_url())
    #     items = get_items()
    #     self.assertEqual(4, len(items))
    #     self.assertListEqual(
    #         [contact04.pk, contact03.pk, contact02.pk, contact01.pk],
    #         [i.pk for i in items],
    #     )
    #
    #     # ---
    #     sleep(1)
    #     contact01.last_name = 'ILoveYou'
    #     contact01.save()
    #     self.assertGET200(FakeContact.get_lv_absolute_url())
    #     old_item = get_items()[-1]
    #     self.assertEqual(contact01.pk,   old_item.pk)
    #     self.assertEqual(str(contact01), old_item.name)
    #
    #     # ---
    #     self.assertGET200(contact02.get_absolute_url())
    #     self.assertListEqual(
    #         [contact02.pk, contact04.pk, contact03.pk, contact01.pk],
    #         [i.pk for i in get_items()],
    #     )
    #
    #     # ---
    #     contact03.delete()
    #     self.assertFalse(CremeEntity.objects.filter(pk=contact03.id))
    #     self.assertGET200(FakeContact.get_lv_absolute_url())
    #     items = get_items()
    #     self.assertListEqual(
    #         [contact02.pk, contact04.pk, contact01.pk],
    #         [i.pk for i in items],
    #     )
    #
    #     # ---
    #     contact04.trash()
    #     self.assertGET200(FakeContact.get_lv_absolute_url())
    #     self.assertListEqual(
    #         [contact02.pk, contact01.pk],
    #         [i.pk for i in get_items()],
    #     )
    #
    #     # ---
    #     with override_settings(MAX_LAST_ITEMS=1):
    #         self.assertGET200(FakeContact.get_lv_absolute_url())
    #
    #     self.assertListEqual([contact02.pk], [i.pk for i in get_items()])

    def test_statistics(self):
        user = self.get_root_user()

        registry = StatisticRegistry()

        s_id = 'persons-contacts'
        label = 'Contacts'
        fmt = 'There are {} Contacts'.format
        registry.register(s_id, label, lambda: [fmt(FakeContact.objects.count())])

        stat = self.get_alone_element(registry)
        self.assertEqual(s_id,  stat.id)
        self.assertEqual(label, stat.label)
        self.assertListEqual([fmt(FakeContact.objects.count())], stat.retrieve())
        self.assertEqual('', stat.perm)

        FakeContact.objects.create(user=user, first_name='Koyomi', last_name='Araragi')
        self.assertListEqual([fmt(FakeContact.objects.count())], stat.retrieve())

    def test_statistics__priority(self):
        id1 = 'persons-contacts'
        perm = 'creme_core'
        id2 = 'persons-organisations'
        id3 = 'creme_core-images'
        registry = StatisticRegistry(
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

    def test_statistics__priority_none(self):
        "Priority None/not None"
        id1 = 'persons-contacts'
        id2 = 'persons-organisations'
        id3 = 'creme_core-images'
        id4 = 'billing-invoices'
        id5 = 'emails-campaigns'
        registry = StatisticRegistry(
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

    def test_statistics__duplicated_id04(self):
        id1 = 'persons-contacts'
        id2 = 'persons-organisations'
        registry = StatisticRegistry(
        ).register(
            id1, 'Contacts', lambda: [FakeContact.objects.count()], priority=2,
        ).register(
            id2, 'Organisations', lambda: [FakeOrganisation.objects.count()], priority=1,
        )

        with self.assertRaises(ValueError):
            registry.register(id1, 'Images', lambda: FakeImage.objects.count())

    def test_statistics__change_priority(self):
        id1 = 'persons-contacts'
        id2 = 'persons-organisations'
        id3 = 'creme_core-images'
        registry = StatisticRegistry(
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

    def test_statistics__remove(self):
        id1 = 'persons-contacts'
        id2 = 'persons-organisations'
        id3 = 'creme_core-images'
        registry = StatisticRegistry(
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

    def test_icon_registry__get_4_model(self):
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

    def test_icon_registry__get_4_instance(self):
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

    def test_quickforms__registry__register(self):
        registry = QuickFormRegistry()

        self.assertFalse([*registry.models])
        self.assertIsNone(registry.get_form_class(FakeContact))

        registry.register(
            FakeContact, FakeContactQuickForm,
        ).register(
            FakeOrganisation, FakeOrganisationQuickForm,
        )
        self.assertIs(FakeContactQuickForm,      registry.get_form_class(FakeContact))
        self.assertIs(FakeOrganisationQuickForm, registry.get_form_class(FakeOrganisation))

        self.assertCountEqual([FakeContact, FakeOrganisation], registry.models)

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

    def test_quickforms__registry__unregister(self):
        registry = QuickFormRegistry()

        with self.assertRaises(registry.UnRegistrationError) as cm:
            registry.unregister(FakeContact)

        self.assertEqual(
            "No Quick Form is registered for the model "
            "<class 'creme.creme_core.tests.fake_models.FakeContact'>",
            str(cm.exception),
        )

        # ---
        registry.register(FakeContact, FakeContactQuickForm)
        with self.assertNoException():
            registry.unregister(FakeContact)

        self.assertIsNone(registry.get_form_class(FakeContact))

    def test_fields_config_registry(self):
        registry = FieldsConfigRegistry()
        self.assertIs(registry.is_model_registered(FakeContact), False)

        registry.register_models(
            FakeContact, FakeOrganisation,
        ).register_models(FakeImage)

        self.assertCountEqual(
            [FakeContact, FakeOrganisation, FakeImage],
            registry.models,
        )
        self.assertIs(registry.is_model_registered(FakeContact), True)

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.documents')
    def test_fields_config_registry__get_needing_apps(self):
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

    def test_viewtag(self):
        self.assertListEqual(
            [ViewTag.HTML_DETAIL], [*ViewTag.smart_generator(ViewTag.HTML_DETAIL)],
        )
        self.assertListEqual(
            [ViewTag.HTML_LIST], [*ViewTag.smart_generator(ViewTag.HTML_LIST)],
        )

        self.assertListEqual(
            [ViewTag.HTML_DETAIL, ViewTag.HTML_LIST],
            [*ViewTag.smart_generator([ViewTag.HTML_DETAIL, ViewTag.HTML_LIST])],
        )

        with self.assertRaises(TypeError):
            [*ViewTag.smart_generator(['foobar', 2])]  # NOQA

        self.assertListEqual(
            [ViewTag.HTML_DETAIL, ViewTag.HTML_LIST, ViewTag.HTML_FORM],
            [*ViewTag.smart_generator('html*')],
        )
        self.assertListEqual(
            [ViewTag.TEXT_PLAIN],
            [*ViewTag.smart_generator('text*')],
        )
        self.assertListEqual(
            [ViewTag.HTML_DETAIL, ViewTag.HTML_LIST, ViewTag.HTML_FORM, ViewTag.TEXT_PLAIN],
            [*ViewTag.smart_generator('*')],
        )
        with self.assertRaises(ValueError):
            [*ViewTag.smart_generator('unknown')]  # NOQA

    def test_mass_import_registry__regsiter(self):
        registry = FormRegistry()

        self.assertNotIn(FakeContact,      registry)
        self.assertNotIn(FakeOrganisation, registry)
        self.assertNotIn(FakeTicket,       registry)

        # ---
        with self.assertRaises(KeyError) as cm_absent:
            registry[FakeContact]  # NOQA
        self.assertEqual(
            "<class 'creme.creme_core.tests.fake_models.FakeContact'>",
            str(cm_absent.exception),
        )

        # ---
        registry.register(FakeContact, get_csv_form_builder).register(FakeTicket)
        self.assertIn(FakeContact, registry)
        self.assertNotIn(FakeOrganisation, registry)
        self.assertIn(FakeTicket, registry)

        with self.assertNoException():
            contact_builder = registry[FakeContact]
        self.assertIs(get_csv_form_builder, contact_builder)

        with self.assertNoException():
            ticket_builder = registry[FakeTicket]
        self.assertIsNone(ticket_builder)

        with self.assertRaises(KeyError):
            registry[FakeOrganisation]  # NOQA

        # ---
        with self.assertRaises(registry.RegistrationError) as cm_dup:
            registry.register(FakeContact)

        self.assertEqual(
            "Model <class 'creme.creme_core.tests.fake_models.FakeContact'> "
            "already registered for mass-import",
            str(cm_dup.exception),
        )

    def test_mass_import_registry__unregister(self):
        registry = FormRegistry().register(FakeContact)

        registry.unregister(FakeContact)
        self.assertNotIn(FakeContact, registry)

        # ---
        with self.assertRaises(registry.UnRegistrationError) as cm:
            registry.unregister(FakeContact)

        self.assertEqual(
            "Invalid model (already unregistered?): "
            "<class 'creme.creme_core.tests.fake_models.FakeContact'>",
            str(cm.exception),
        )

    def test_merge_form_registry__regsiter(self):
        registry = _MergeFormRegistry()
        self.assertListEqual([], [*registry.models])
        self.assertIsNone(registry.get(FakeContact))
        self.assertIsNone(registry.get(FakeOrganisation))

        self.assertNotIn(FakeContact, registry)
        self.assertNotIn(FakeOrganisation, registry)

        # ---
        registry.register(FakeContact, get_merge_form_builder)
        self.assertListEqual([FakeContact], [*registry.models])
        self.assertIs(registry.get(FakeContact), get_merge_form_builder)
        self.assertIsNone(registry.get(FakeOrganisation))

        self.assertIn(FakeContact, registry)
        self.assertNotIn(FakeOrganisation, registry)

        # ---
        with self.assertRaises(registry.RegistrationError) as cm:
            registry.register(FakeContact, get_merge_form_builder)

        self.assertEqual(
            f'Model {FakeContact} is already registered',
            str(cm.exception),
        )

    def test_merge_form_registry__unregister(self):
        registry = _MergeFormRegistry().register(
            FakeContact, get_merge_form_builder,
        ).register(
            FakeOrganisation, get_merge_form_builder,
        )

        registry.unregister(FakeContact)
        self.assertNotIn(FakeContact, registry)
        self.assertIn(FakeOrganisation, registry)

        # ---
        with self.assertRaises(registry.UnRegistrationError) as cm:
            registry.unregister(FakeContact)

        self.assertEqual(
            f'Invalid model {FakeContact} (already registered?)',
            str(cm.exception),
        )
