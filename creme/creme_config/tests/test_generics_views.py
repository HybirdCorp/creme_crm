from functools import partial

from django.apps import apps
from django.db.models.deletion import PROTECT, SET_NULL
from django.forms import CharField
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from parameterized import parameterized

from creme.creme_core.creme_jobs import deletor_type
from creme.creme_core.forms.widgets import Label
from creme.creme_core.models import (
    DeletionCommand,
    FakeActivity,
    FakeActivityType,
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeDocumentCategory,
    FakeFolder,
    FakeFolderCategory,
    FakeImageCategory,
    FakeIngredient,
    FakeLegalForm,
    FakeOrganisation,
    FakePosition,
    FakeProduct,
    FakeProductType,
    FakeSector,
    FakeSkill,
    FakeTicket,
    FakeTicketPriority,
    FakeTicketStatus,
    FakeTraining,
    FieldsConfig,
    Job,
    JobResult,
)
from creme.creme_core.models.history import TYPE_EDITION, HistoryLine
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_bricks import FakeAppPortalBrick
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.translation import smart_model_verbose_name

from ..bricks import GenericModelBrick, PropertyTypesBrick, SettingsBrick


class GenericModelConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.get_root_user()

    def setUp(self):
        super().setUp()
        self.login_as_root()

    def assertReplacersEqual(self, expected, dcom):
        # NB: works well on for FixedValueReplacer ??
        self.assertListEqual(
            expected,
            [
                (r.type_id, r.model_field.model, r.model_field.name, r.get_value())
                for r in dcom.replacers
            ],
        )

    @staticmethod
    def _build_finish_deletor_url(job):
        return reverse('creme_config__finish_deletor', args=(job.id,))

    def test_portals(self):
        response = self.assertGET200(
            reverse('creme_config__app_portal', args=('creme_core',))
        )
        self.assertTemplateUsed(response, 'creme_config/generics/app-portal.html')

        self.assertGET404(
            reverse('creme_config__app_portal', args=('unexistingapp',))
        )

        response = self.assertGET200(
            reverse('creme_config__model_portal', args=('creme_core', 'fake_civility'))
        )
        self.assertTemplateUsed(response, 'creme_config/generics/model-portal.html')

        self.assertGET404(
            reverse('creme_config__model_portal', args=('creme_core', 'unexistingmodel'))
        )

        if apps.is_installed('creme.persons'):
            self.assertGET200(
                reverse('creme_config__app_portal', args=('persons',))
            )
            self.assertGET200(
                reverse('creme_config__model_portal', args=('persons', 'civility'))
            )
            self.assertGET404(
                reverse('creme_config__model_portal', args=('persons', 'unexistingmodel'))
            )

    def test_creation(self):
        count = FakeCivility.objects.count()

        url = reverse('creme_config__create_instance', args=('creme_core', 'fake_civility'))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/add-popup.html')

        context = response.context
        self.assertEqual(_('Create'), context.get('title'))
        self.assertEqual(_('Save'),   context.get('submit_label'))

        title = 'Generalissime'
        shortcut = 'G.'
        self.assertNoFormError(
            self.client.post(url, data={'title': title, 'shortcut': shortcut})
        )
        self.assertEqual(count + 1, FakeCivility.objects.count())

        civility = self.get_object_or_fail(FakeCivility, title=title)
        self.assertEqual(shortcut, civility.shortcut)

        now_value = now()
        self.assertDatetimesAlmostEqual(civility.created, now_value)
        self.assertDatetimesAlmostEqual(civility.modified, now_value)

    def test_creation__order(self):
        count = FakeSector.objects.count()

        url = reverse('creme_config__create_instance', args=('creme_core', 'fake_sector'))
        context = self.assertGET200(url).context
        self.assertEqual(_('Create a sector'), context.get('title'))
        self.assertEqual(_('Save the sector'), context.get('submit_label'))

        title = 'Music'
        self.assertNoFormError(self.client.post(url, data={'title': title}))
        self.assertEqual(count + 1, FakeSector.objects.count())

        sector = self.get_object_or_fail(FakeSector, title=title, is_custom=True)
        self.assertEqual(count + 1, sector.order)  # order is set to max

        title = 'Music & movie'
        self.client.post(url, data={'title': title})
        sector = self.get_object_or_fail(FakeSector, title=title)
        self.assertEqual(count + 2, sector.order)  # order is set to max

    def test_creation__disabled(self):
        "Disabled creation (see creme.creme_core.apps.CremeCoreConfig.register_creme_config())."
        self.assertGET409(
            reverse(
                'creme_config__create_instance',
                args=('creme_core', 'fake_position'),
            )
        )

    def test_creation__custom_url(self):
        "Not vanilla-URL (see creme.creme_core.apps.CremeCoreConfig.register_creme_config())."
        self.assertGET409(
            reverse(
                'creme_config__create_instance',
                args=('creme_core', 'fake_legalform'),
            )
        )

    def assertWidgetResponse(self, response, instance):
        self.assertDictEqual(
            {
                'added': [[instance.id, str(instance)]],
                'value': instance.id
            },
            response.json(),
        )

    def test_creation_from_widget(self):
        count = FakeCivility.objects.count()

        url = reverse(
            'creme_config__create_instance_from_widget',
            args=('creme_core', 'fake_civility'),
        )
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/add-popup.html')

        context = response.context
        self.assertEqual(_('Create'), context.get('title'))
        self.assertEqual(_('Save'), context.get('submit_label'))

        # ---
        title = 'Generalissime'
        shortcut = 'G.'
        response = self.client.post(url, data={'title': title, 'shortcut': shortcut})
        self.assertNoFormError(response)
        self.assertEqual(count + 1, FakeCivility.objects.count())

        civility = self.get_object_or_fail(FakeCivility, title=title)
        self.assertEqual(shortcut, civility.shortcut)
        self.assertWidgetResponse(response, civility)

    def test_creation_from_widget__order(self):
        count = FakeSector.objects.count()

        url = reverse(
            'creme_config__create_instance_from_widget',
            args=('creme_core', 'fake_sector'),
        )
        context = self.assertGET200(url).context

        self.assertEqual(_('Create a sector'), context.get('title'))
        self.assertEqual(_('Save the sector'), context.get('submit_label'))

        # ---
        title = 'Music'
        response = self.client.post(url, data={'title': title})
        self.assertNoFormError(response)
        self.assertEqual(count + 1, FakeSector.objects.count())

        sector = self.get_object_or_fail(FakeSector, title=title, is_custom=True)
        self.assertEqual(count + 1, sector.order)  # order is set to max
        self.assertWidgetResponse(response, sector)

        title = 'Music & movie'
        response = self.client.post(url, data={'title': title})
        sector = self.get_object_or_fail(FakeSector, title=title)
        self.assertEqual(count + 2, sector.order)  # order is set to max
        self.assertWidgetResponse(response, sector)

    def test_edition(self):
        title = 'herr'
        shortcut = 'H.'
        civ = FakeCivility.objects.create(title=title, shortcut=shortcut)

        old_date = self.create_datetime(year=2020, month=1, day=1)
        FakeCivility.objects.filter(id=civ.id).update(created=old_date, modified=old_date)

        url = reverse(
            'creme_config__edit_instance',
            args=('creme_core', 'fake_civility', civ.id,),
        )
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/edit-popup.html')
        self.assertEqual(
            _('Edit «{object}»').format(object=civ),
            response.context.get('title'),
        )

        title = title.title()
        self.assertNoFormError(self.client.post(
            url, data={'title': title, 'shortcut': shortcut},
        ))

        civ = self.refresh(civ)
        self.assertEqual(title,    civ.title)
        self.assertEqual(shortcut, civ.shortcut)
        self.assertEqual(old_date, civ.created)
        self.assertDatetimesAlmostEqual(civ.modified, now())

    def test_edition__order_no_changed(self):
        count = FakeSector.objects.count()
        sector = FakeSector.objects.create(title='music', order=count + 1)

        url = reverse(
            'creme_config__edit_instance',
            args=('creme_core', 'fake_sector', sector.id,),
        )
        self.assertGET200(url)

        title = sector.title.title()
        self.assertNoFormError(self.client.post(url, data={'title': title}))

        new_sector = self.refresh(sector)
        self.assertEqual(title,        new_sector.title)
        self.assertEqual(sector.order, new_sector.order)

    def test_edition__disabled(self):
        "Edition disabled (see creme.creme_core.apps.CremeCoreConfig.register_creme_config())."
        lf = FakeLegalForm.objects.create(title='Foundation')
        self.assertGET409(
            reverse(
                'creme_config__edit_instance',
                args=('creme_core', 'fake_legalform', lf.id,)
            )
        )

    def test_edition__custom_url(self):
        "Not vanilla-URL (see creme.creme_core.apps.CremeCoreConfig.register_creme_config())."
        position = FakePosition.objects.first()

        self.assertGET409(
            reverse(
                'creme_config__edit_instance',
                args=('creme_core', 'fake_position', position.id),
            )
        )

    def test_delete01(self):
        "SET_NULL."
        self.assertIsNone(DeletionCommand.objects.first())

        pos2del = FakePosition.objects.create(title='Kunoichi')
        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_position', pos2del.pk),
        )
        fname = 'replace_creme_core__fakecontact_position'

        # No related entity ---
        response = self.assertGET200(url)

        context = response.context
        self.assertEqual(
            _('Replace & delete «{object}»').format(object=pos2del),
            context.get('title'),
        )

        with self.assertNoException():
            replace_field = context['form'].fields[fname]

        self.assertIsInstance(replace_field, CharField)
        self.assertIsInstance(replace_field.widget, Label)
        self.assertEqual(
            '{} - {}'.format('Test Contact', _('Position')),
            replace_field.label,
        )
        self.assertEqual(
            _('OK: no instance of «{model}» have to be updated.').format(
                model=smart_model_verbose_name(model=FakeContact, count=0),
            ),
            replace_field.initial,
        )

        # One related entity ---
        create_contact = partial(FakeContact.objects.create, user=self.user, position=pos2del)
        contact1 = create_contact(last_name='Hattori', first_name='Tomoe')

        response = self.assertGET200(url)
        self.assertEqual(
            ngettext(
                'BEWARE: {count} instance of «{model}» uses «{instance}» & '
                'will be updated (the field will be emptied).',
                'BEWARE: {count} instances of «{model}» use «{instance}» & '
                'will be updated (the field will be emptied).',
                1
            ).format(
                count=1,
                model=smart_model_verbose_name(model=FakeContact, count=1),
                instance=pos2del,
            ),
            self.get_form_or_fail(response).fields[fname].initial
        )

        # Two related entity ---
        contact2 = create_contact(last_name='Hattori', first_name='Hanzo')

        response = self.assertGET200(url)
        self.assertEqual(
            ngettext(
                'BEWARE: {count} instance of «{model}» uses «{instance}» & '
                'will be updated (the field will be emptied).',
                'BEWARE: {count} instances of «{model}» use «{instance}» & '
                'will be updated (the field will be emptied).',
                2
            ).format(
                count=2,
                model=smart_model_verbose_name(model=FakeContact, count=2),
                instance=pos2del,
            ),
            self.get_form_or_fail(response).fields[fname].initial,
        )

        # POST ---
        response = self.assertPOST200(url)
        self.assertNoFormError(response)
        self.assertStillExists(pos2del)

        dcom = self.get_deletion_command_or_fail(FakePosition)
        self.assertEqual(pos2del,       dcom.instance_to_delete)
        self.assertEqual(pos2del.title, dcom.deleted_repr)
        self.assertReplacersEqual(
            [('fixed_value', FakeContact, 'position', None)],
            dcom,
        )
        self.assertEqual(2, dcom.total_count)
        self.assertEqual(0, dcom.updated_count)

        job = dcom.job
        self.assertEqual(deletor_type.id, job.type_id)
        self.assertEqual(self.user, job.user)
        self.assertListEqual(
            [
                _('Deleting «{object}» ({model})').format(
                    object=pos2del.title, model='Test People position',
                ),
                _('Empty «{model} - {field}»').format(
                    model='Test Contact',
                    field=_('Position'),
                ),
            ],
            deletor_type.get_description(job),
        )

        deletor_type.execute(job)
        self.assertDoesNotExist(pos2del)
        self.assertIsNone(self.refresh(contact1).position)
        self.assertIsNone(self.refresh(contact2).position)

    def test_delete02(self):
        "CREME_REPLACE_NULL."
        self.assertIsNone(DeletionCommand.objects.first())

        civ1    = FakeCivility.objects.first()
        civ2del = FakeCivility.objects.create(title='Kun')
        contact = FakeContact.objects.create(
            user=self.user, civility=civ2del,
            last_name='Hattori', first_name='Hanzo',
        )

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_civility', civ2del.pk),
        )
        response = self.assertGET200(url)

        context = response.context
        self.assertEqual(
            _('Replace & delete «{object}»').format(object=civ2del),
            context.get('title'),
        )

        with self.assertNoException():
            replace_field = context['form'].fields['replace_creme_core__fakecontact_civility']
            choices = [*replace_field.choices]

        self.assertEqual(
            '{} - {}'.format('Test Contact', _('Civility')),
            replace_field.label,
        )

        self.assertInChoices(value='',      label='---------', choices=choices)
        self.assertInChoices(value=civ1.id, label=str(civ1),   choices=choices)
        self.assertNotInChoices(value=civ2del.id, choices=choices)

        response = self.client.post(url)
        self.assertNoFormError(response)
        self.assertStillExists(civ2del)

        dcom = self.get_deletion_command_or_fail(FakeCivility)
        self.assertEqual(str(civ2del.id), dcom.pk_to_delete)
        self.assertReplacersEqual(
            [('fixed_value', FakeContact, 'civility', None)],
            dcom,
        )
        self.assertEqual(1, dcom.total_count)

        job = dcom.job
        self.assertEqual(deletor_type.id, job.type_id)
        self.assertEqual(self.user, job.user)

        deletor_type.execute(job)
        self.assertDoesNotExist(civ2del)
        self.assertIsNone(self.refresh(contact).civility)

        job.delete()
        self.assertDoesNotExist(dcom)

    def test_delete03(self):
        "Not custom instance."
        sector = FakeSector.objects.create(title='Music', is_custom=False)
        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_sector', sector.pk),
        )
        self.assertGET409(url)
        self.assertPOST409(url)
        self.assertStillExists(sector)

    def test_delete04(self):
        "Several fields + replacement + limit_choices + CREME_REPLACE."
        create_sector = FakeSector.objects.create
        sector1 = create_sector(title='Bo')
        sector2 = create_sector(title='Blade')
        sector3 = create_sector(title='Sai')
        sector4 = create_sector(title='[INVALID]')  # Should not be proposed for Contacts
        sector2del = create_sector(title='Gun')

        create_contact = partial(FakeContact.objects.create, user=self.user, last_name='Turtle')
        contact1 = create_contact(first_name='Donatello', sector=sector1)
        contact2 = create_contact(first_name='Leonardo',  sector=sector2del)

        create_orga = partial(FakeOrganisation.objects.create, user=self.user)
        orga1 = create_orga(name='Turtles',   sector=sector1)
        orga2 = create_orga(name='Foot clan', sector=sector2del)

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_sector', sector2del.pk),
        )
        response = self.assertGET200(url)

        fname1 = 'replace_creme_core__fakecontact_sector'
        fname2 = 'replace_creme_core__fakeorganisation_sector'

        with self.assertNoException():
            fields = response.context['form'].fields
            replace_field1 = fields[fname1]
            replace_field2 = fields[fname2]
            choices1 = [*replace_field1.choices]
            choices2 = [*replace_field2.choices]

        self.assertInChoices(value='',         label='---------',  choices=choices1)
        self.assertInChoices(value=sector1.id, label=str(sector1), choices=choices1)
        self.assertInChoices(value=sector2.id, label=str(sector2), choices=choices1)
        self.assertInChoices(value=sector3.id, label=str(sector3), choices=choices1)
        self.assertNotInChoices(value=sector2del.id, choices=choices1)
        self.assertNotInChoices(value=sector4.id,    choices=choices1)

        self.assertNotInChoices(value='', choices=choices2)
        self.assertInChoices(value=sector1.id, label=str(sector1), choices=choices2)
        self.assertInChoices(value=sector4.id, label=str(sector4), choices=choices2)
        self.assertNotInChoices(value=sector2del.id, choices=choices2)

        response = self.assertPOST200(
            url,
            data={
                fname1: sector2.id,
                fname2: sector3.id,
            },
        )
        self.assertNoFormError(response)
        self.assertStillExists(sector2del)

        job = self.get_object_or_fail(Job, type_id=deletor_type.id)
        dcom = self.get_object_or_fail(DeletionCommand, job=job)
        self.assertEqual(2, dcom.total_count)

        deletor_type.execute(job)
        self.assertDoesNotExist(sector2del)

        self.assertEqual(sector1.id, self.refresh(contact1).sector_id)
        self.assertEqual(sector2.id, self.refresh(contact2).sector_id)
        self.assertEqual(sector1.id, self.refresh(orga1).sector_id)
        self.assertEqual(sector3.id, self.refresh(orga2).sector_id)

    def test_delete05(self):
        "CASCADE."
        create_prod_type = FakeProductType.objects.create
        prodtype1    = create_prod_type(name='Weapon')
        prodtype2del = create_prod_type(name='Duplicated weapon')

        create_product = partial(FakeProduct.objects.create, user=self.user)
        prod1 = create_product(name='Katana', type=prodtype1)

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_product_type', prodtype2del.id),
        )

        # No entity will be deleted ---
        response = self.assertGET200(url)

        fname = 'replace_creme_core__fakeproduct_type'
        with self.assertNoException():
            replace_field = response.context['form'].fields[fname]

        self.assertIsInstance(replace_field, CharField)
        self.assertIsInstance(replace_field.widget, Label)
        self.assertEqual(
            '{} - {}'.format('Test Product', _('Type')),
            replace_field.label,
        )
        self.assertEqual(
            _('OK: no instance of «{model}» have to be deleted.').format(
                model=smart_model_verbose_name(model=FakeProduct, count=0),
            ),
            replace_field.initial,
        )

        # One entity will be deleted ---
        prod2 = create_product(name='Shovel', type=prodtype2del)
        response = self.assertGET200(url)
        self.assertEqual(
            ngettext(
                'BEWARE: {count} instance of «{model}» will be deleted.',
                'BEWARE: {count} instances of «{model}» will be deleted.',
                1
            ).format(
                count=1,
                model=smart_model_verbose_name(model=FakeProduct, count=1),
            ),
            self.get_form_or_fail(response).fields[fname].initial,
        )

        # Several entities will be deleted ---
        prod3 = create_product(name='Screw driver', type=prodtype2del)
        response = self.assertGET200(url)
        self.assertEqual(
            ngettext(
                'BEWARE: {count} instance of «{model}» will be deleted.',
                'BEWARE: {count} instances of «{model}» will be deleted.',
                2
            ).format(
                count=2,
                model=smart_model_verbose_name(model=FakeProduct, count=2),
            ),
            self.get_form_or_fail(response).fields[fname].initial,
        )

        # POST ---
        response = self.assertPOST200(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeProductType)
        self.assertEqual(str(prodtype2del.id), dcom.pk_to_delete)
        self.assertEqual([], dcom.replacers)

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(prodtype2del)

        self.assertStillExists(prod1)
        self.assertDoesNotExist(prod2)
        self.assertDoesNotExist(prod3)

    def test_delete06(self):
        "PROTECT + no related entity."
        self.assertIs(
            FakeActivity._meta.get_field('type').remote_field.on_delete,
            PROTECT
        )

        atype = FakeActivityType.objects.first()
        atype2del = FakeActivityType.objects.create(name='Show')

        FakeActivity.objects.create(user=self.user, title='Comiket', type=atype)

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_activity_type', atype2del.id),
        )
        response = self.assertGET200(url)

        fname = 'replace_creme_core__fakeactivity_type'
        with self.assertNoException():
            replace_field = response.context['form'].fields[fname]

        self.assertIsInstance(replace_field, CharField)
        self.assertIsInstance(replace_field.widget, Label)
        message = _(
            'OK: there is no related instance of «{model}», the deletion can be done.'
        ).format(model=smart_model_verbose_name(model=FakeActivity, count=0))
        self.assertEqual(message, replace_field.initial)

        response = self.assertPOST200(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeActivityType)
        self.assertEqual(str(atype2del.id), dcom.pk_to_delete)
        self.assertEqual([], dcom.replacers)

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(atype2del)

    def test_delete07(self):
        "PROTECT + related entity."
        atype = FakeActivityType.objects.create(name='Show')
        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_activity_type', atype.id),
        )
        fname = 'replace_creme_core__fakeactivity_type'

        # One related entity ---
        FakeActivity.objects.create(user=self.user, title='Comiket', type=atype)

        response = self.assertGET200(url)
        with self.assertNoException():
            replace_field = response.context['form'].fields[fname]

        self.assertIsInstance(replace_field, CharField)
        self.assertIsInstance(replace_field.widget, Label)
        self.assertEqual(
            ngettext(
                'ERROR: {count} instance of «{model}» uses «{instance}» '
                'so the deletion is not possible.',
                'ERROR: {count} instances of «{model}» use «{instance}» '
                'so the deletion is not possible.',
                1
            ).format(
                count=1,
                model=smart_model_verbose_name(model=FakeActivity, count=1),
                instance=atype,
            ),
            replace_field.initial,
        )

        # Two related entities ---
        FakeActivity.objects.create(user=self.user, title='Comicon', type=atype)

        response = self.assertGET200(url)
        self.assertEqual(
            ngettext(
                'ERROR: {count} instance of «{model}» uses «{instance}» '
                'so the deletion is not possible.',
                'ERROR: {count} instances of «{model}» use «{instance}» '
                'so the deletion is not possible.',
                2
            ).format(
                count=2,
                model=smart_model_verbose_name(model=FakeActivity, count=2),
                instance=atype,
            ),
            self.get_form_or_fail(response).fields[fname].initial
        )

        response = self.assertPOST200(url)
        self.assertFormError(
            self.get_form_or_fail(response),
            field=fname, errors=_('Deletion is not possible.'),
        )

    def test_delete08(self):
        "SET_DEFAULT."
        default_status = FakeTicketStatus.objects.get(id=1)
        status2del = FakeTicketStatus.objects.create(name='Duplicated')
        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_ticket_status', status2del.id),
        )
        fname = 'replace_creme_core__faketicket_status'

        # No related entity ---
        response = self.assertGET200(url)
        with self.assertNoException():
            replace_field = response.context['form'].fields[fname]

        self.assertIsInstance(replace_field, CharField)
        self.assertIsInstance(replace_field.widget, Label)
        self.assertEqual(
            _('OK: no instance of «{model}» have to be updated.').format(
                model=smart_model_verbose_name(model=FakeTicket, count=0),
            ),
            replace_field.initial,
        )

        # One related entity ---
        create_ticket = partial(FakeTicket.objects.create, user=self.user)
        ticket1 = create_ticket(title='Bug #1', status=status2del)

        response = self.assertGET200(url)
        self.assertEqual(
            ngettext(
                'BEWARE: {count} instance of «{model}» uses «{instance}» & '
                'will be updated (the field will be set to «{fallback}»).',
                'BEWARE: {count} instances of «{model}» use «{instance}» & '
                'will be updated (the field will be set to «{fallback}»).',
                1
            ).format(
                count=1,
                model=smart_model_verbose_name(model=FakeTicket, count=1),
                instance=status2del,
                fallback=default_status,
            ),
            self.get_form_or_fail(response).fields[fname].initial,
        )

        # Two related entity ---
        create_ticket(title='Bug #2', status=status2del)

        response = self.assertGET200(url)
        self.assertEqual(
            ngettext(
                'BEWARE: {count} instance of «{model}» uses «{instance}» & '
                'will be updated (the field will be set to «{fallback}»).',
                'BEWARE: {count} instances of «{model}» use «{instance}» & '
                'will be updated (the field will be set to «{fallback}»).',
                2
            ).format(
                count=2,
                model=smart_model_verbose_name(model=FakeTicket, count=2),
                instance=status2del,
                fallback=default_status,
            ),
            self.get_form_or_fail(response).fields[fname].initial,
        )

        # POST ---
        response = self.assertPOST200(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeTicketStatus)
        self.assertReplacersEqual(
            [('fixed_value', FakeTicket, 'status', default_status)],
            dcom,
        )

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(status2del)
        self.assertEqual(default_status, self.refresh(ticket1).status)

        hline = HistoryLine.objects.filter(entity=ticket1.id).order_by('-id').first()
        self.assertIsNotNone(hline)
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertListEqual(
            [['status_id', status2del.id, default_status.id]],
            hline.modifications,
        )

    def test_delete09(self):
        "SET."
        prio2del = FakeTicketPriority.objects.create(name='Not so important')
        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_ticket_priority', prio2del.id),
        )
        fname = 'replace_creme_core__faketicket_priority'

        # No related entity ----
        response = self.assertGET200(url)
        with self.assertNoException():
            replace_field = response.context['form'].fields[fname]

        self.assertIsInstance(replace_field, CharField)
        self.assertIsInstance(replace_field.widget, Label)
        self.assertEqual(
            _('OK: no instance of «{model}» have to be updated.').format(
                model=smart_model_verbose_name(model=FakeTicket, count=0),
            ),
            replace_field.initial,
        )

        # One related entity ----
        create_ticket = partial(FakeTicket.objects.create, user=self.user)
        ticket1 = create_ticket(title='Bug #1', priority=prio2del)

        response = self.assertGET200(url)
        self.assertEqual(
            ngettext(
                'BEWARE: {count} instance of «{model}» uses «{instance}» & '
                'will be updated (the field will be set to the fallback value).',
                'BEWARE: {count} instances of «{model}» use «{instance}» & '
                'will be updated (the field will be set to the fallback value).',
                1
            ).format(
                count=1,
                model=smart_model_verbose_name(model=FakeTicket, count=1),
                instance=prio2del,
            ),
            self.get_form_or_fail(response).fields[fname].initial,
        )

        # One related entity ----
        ticket2 = create_ticket(title='Bug #2', priority=prio2del)

        response = self.assertGET200(url)
        self.assertEqual(
            ngettext(
                'BEWARE: {count} instance of «{model}» uses «{instance}» & '
                'will be updated (the field will be set to the fallback value).',
                'BEWARE: {count} instances of «{model}» use «{instance}» & '
                'will be updated (the field will be set to the fallback value).',
                2
            ).format(
                count=2,
                model=smart_model_verbose_name(model=FakeTicket, count=2),
                instance=prio2del,
            ),
            self.get_form_or_fail(response).fields[fname].initial,
        )

        # POST ---
        response = self.assertPOST200(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeTicketPriority)
        replacer = self.get_alone_element(dcom.replacers)
        self.assertEqual('SET', replacer.type_id)
        self.assertEqual(FakeTicket, replacer.model_field.model)
        self.assertEqual('priority', replacer.model_field.name)

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(prio2del)

        fallback_priority = self.refresh(ticket1).priority
        self.assertIsNotNone(fallback_priority)
        self.assertEqual('Deleted', fallback_priority.name)

        self.assertEqual(fallback_priority, self.refresh(ticket2).priority)

        hline = HistoryLine.objects.filter(entity=ticket2.id).order_by('-id').first()
        self.assertIsNotNone(hline)
        self.assertEqual(TYPE_EDITION, hline.type)
        self.assertListEqual(
            [['priority_id', prio2del.id, fallback_priority.id]],
            hline.modifications,
        )

    def test_delete10(self):
        "Deleted model get a M2M fiel (bugfix)."
        create_skill = FakeSkill.objects.create
        skill1 = create_skill(name='Python')
        skill2 = create_skill(name='Algorithm')

        training1 = FakeTraining.objects.create(name='Python for beginners')
        training1.skills.set([skill1, skill2])

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_training', training1.id),
        )

        # GET ---
        response1 = self.assertGET200(url)
        with self.assertNoException():
            fields = response1.context['form'].fields

        self.assertFalse(fields)

        # POST ---
        self.assertNoFormError(self.client.post(url))

        dcom = self.get_deletion_command_or_fail(FakeTraining)
        self.assertFalse(dcom.replacers)

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(training1)
        self.assertStillExists(skill1)

    def test_delete_m2m_01(self):
        "Does not replace."
        folder = FakeFolder.objects.create(user=self.user, title='Pictures')

        create_cat = FakeDocumentCategory.objects.create
        cat1    = create_cat(name='Pictures')
        cat2    = create_cat(name='Music')
        cat3    = create_cat(name='Video')
        cat2del = create_cat(name='Pix')

        doc = FakeDocument.objects.create(
            user=self.user, title='Pix1', linked_folder=folder,
        )
        doc.categories.set([cat2del, cat3])

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_documentcat', cat2del.id),
        )

        # GET ---
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            replace_field = fields['replace_creme_core__fakedocument_categories']
            choices = [*replace_field.choices]

        self.assertEqual(
            '{} - {}'.format('Test Document', _('Categories')),
            replace_field.label,
        )

        self.assertFalse(replace_field.required)

        self.assertInChoices(value='',      label='---------', choices=choices)
        self.assertInChoices(value=cat1.id, label=str(cat1),   choices=choices)
        self.assertInChoices(value=cat2.id, label=str(cat2),   choices=choices)
        self.assertNotInChoices(value=cat2del.id, choices=choices)

        self.assertEqual(1, len(fields), fields)

        # POST ---
        response = self.client.post(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeDocumentCategory)
        self.assertEqual(str(cat2del.id), dcom.pk_to_delete)
        self.assertReplacersEqual([], dcom)
        self.assertEqual(1, dcom.total_count)

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(cat2del)
        self.assertListEqual([cat3], [*doc.categories.all()])

    def test_delete_m2m_02(self):
        "Replace."
        folder = FakeFolder.objects.create(user=self.user, title='Pictures')

        create_cat = FakeDocumentCategory.objects.create
        cat1    = create_cat(name='Pictures')
        cat2    = create_cat(name='Music')
        cat2del = create_cat(name='Pix')

        create_doc = partial(FakeDocument.objects.create, user=self.user, linked_folder=folder)
        doc1 = create_doc(title='Summer pix')
        doc1.categories.set([cat2del, cat2])

        doc2 = create_doc(title='X-mas pix')
        # After replacement, "cat1" should not be duplicated
        doc2.categories.set([cat2del, cat1])

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('creme_core', 'fake_documentcat', cat2del.id),
            ),
            data={
                'replace_creme_core__fakedocument_categories': cat1.id,
            },
        )
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeDocumentCategory)
        self.assertReplacersEqual(
            [('fixed_value', FakeDocument, 'categories', cat1)],
            dcom,
        )
        self.assertEqual(2, dcom.total_count)

        job = dcom.job
        self.assertEqual(deletor_type.id, job.type_id)
        self.assertEqual(self.user, job.user)

        deletor_type.execute(job)
        self.assertDoesNotExist(cat2del)
        self.assertCountEqual([cat1, cat2], [*doc1.categories.all()])
        self.assertListEqual([cat1], [*doc2.categories.all()])

    def test_delete_m2m_03(self):
        "Not blank."
        create_ing = FakeIngredient.objects.create
        ing1    = create_ing(name='Courgette')
        ing2    = create_ing(name='Onion')
        ing2del = create_ing(name='Zucchini')

        response = self.assertGET200(
            reverse(
                'creme_config__delete_instance',
                args=('creme_core', 'fake_ingredient', ing2del.id),
            )
        )

        with self.assertNoException():
            fields = response.context['form'].fields
            replace_field = fields['replace_creme_core__fakerecipe_ingredients']
            choices = [*replace_field.choices]

        self.assertTrue(replace_field.required)
        self.assertInChoices(value=ing1.id, label=str(ing1), choices=choices)
        self.assertInChoices(value=ing2.id, label=str(ing2), choices=choices)
        self.assertNotInChoices(value=ing2del.id, choices=choices)
        self.assertNotInChoices(value='',         choices=choices)

    def test_delete_hidden_related(self):
        "ForeignKey(..., related_name='+', ...) => use the field anyway."
        self.assertIsNone(DeletionCommand.objects.first())

        lform     = FakeLegalForm.objects.create(title='Ninja clan[OK]')
        lform2del = FakeLegalForm.objects.create(title='Ninja army[OK]')

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_legalform', lform2del.id),
        )
        response = self.assertGET200(url)

        with self.assertNoException():
            replace_field = response.context['form'].fields[
                'replace_creme_core__fakeorganisation_legal_form'
            ]
            choices = [*replace_field.choices]

        self.assertEqual(
            '{} - {}'.format('Test Organisation', _('Legal form')),
            replace_field.label
        )

        self.assertInChoices(value='',       label='---------', choices=choices)
        self.assertInChoices(value=lform.id, label=str(lform),  choices=choices)
        self.assertNotInChoices(value=lform2del.id, choices=choices)

    def test_delete_hiddenfields01(self):
        "SET_NULL."
        self.assertIs(
            FakeContact._meta.get_field('position').remote_field.on_delete,
            SET_NULL
        )

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('position', {FieldsConfig.HIDDEN: True})],
        )

        pos2del = FakePosition.objects.create(title='Kunoichi')
        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_position', pos2del.pk),
        )

        # GET ---
        response = self.assertGET200(url)
        self.assertNotIn(
            'replace_creme_core__fakecontact_position',
            self.get_form_or_fail(response).fields,
        )

        # POST ---
        response = self.assertPOST200(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakePosition)
        self.assertEqual(str(pos2del.id), dcom.pk_to_delete)
        self.assertReplacersEqual(
            [('fixed_value', FakeContact, 'position', None)],
            dcom,
        )

        self.assertListEqual(
            [
                _('Deleting «{object}» ({model})').format(
                    object=pos2del.title, model='Test People position',
                ),
                # NB: hidden
                # _('Empty «{model} - {field}»').format(
                #        model='Test Contact',
                #        field=_('Position'),
                # ),
            ],
            deletor_type.get_description(dcom.job),
        )

    def test_delete_hiddenfields02(self):
        "SET."
        FieldsConfig.objects.create(
            content_type=FakeTicket,
            descriptions=[('priority', {FieldsConfig.HIDDEN: True})],
        )

        prio2del = FakeTicketPriority.objects.create(name='Not so important')
        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_ticket_priority', prio2del.id),
        )

        # GET ---
        response = self.assertGET200(url)
        self.assertNotIn(
            'replace_creme_core__faketicket_priority',
            self.get_form_or_fail(response).fields,
        )

        # POST ---
        response = self.assertPOST200(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeTicketPriority)
        self.assertFalse(dcom.replacers)

    def test_delete_hiddenfields03(self):
        "SET_DEFAULT."
        FieldsConfig.objects.create(
            content_type=FakeTicket,
            descriptions=[('status', {FieldsConfig.HIDDEN: True})],
        )

        status2del = FakeTicketStatus.objects.create(name='Duplicated')
        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_ticket_status', status2del.id),
        )

        # GET ---
        response = self.assertGET200(url)
        self.assertNotIn(
            'replace_creme_core__faketicket_status',
            self.get_form_or_fail(response).fields,
        )

        # POST ---
        response = self.assertPOST200(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeTicketStatus)
        self.assertReplacersEqual(
            [('fixed_value', FakeTicket, 'status', FakeTicketStatus.objects.get(id=1))],
            dcom,
        )

    def test_delete_hiddenfields04(self):
        "CASCADE."
        FieldsConfig.objects.create(
            content_type=FakeProduct,
            descriptions=[('type', {FieldsConfig.HIDDEN: True})],
        )

        create_prod_type = FakeProductType.objects.create
        prodtype2del = create_prod_type(name='Duplicated weapon')

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_product_type', prodtype2del.id),
        )
        fname = 'replace_creme_core__fakeproduct_type'

        # No related entity ---
        response = self.assertGET200(url)
        self.assertNotIn(fname, self.get_form_or_fail(response).fields)

        # One related entity ---
        FakeProduct.objects.create(user=self.user, name='Shovel', type=prodtype2del)
        response = self.assertGET200(url)

        with self.assertNoException():
            replace_field = response.context['form'].fields[fname]

        self.assertEqual(
            ngettext(
                'BEWARE: {count} instance of «{model}» will be deleted.',
                'BEWARE: {count} instances of «{model}» will be deleted.',
                1
            ).format(
                count=1,
                model=smart_model_verbose_name(model=FakeProduct, count=1),
            ),
            replace_field.initial,
        )

        # POST ---
        response = self.assertPOST200(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeProductType)
        self.assertFalse(dcom.replacers)

    def test_delete_hiddenfields05(self):
        "PROTECT + no related entity."
        FieldsConfig.objects.create(
            content_type=FakeActivity,
            descriptions=[('type', {FieldsConfig.HIDDEN: True})],
        )

        atype2del = FakeActivityType.objects.create(name='Show')
        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_activity_type', atype2del.id),
        )

        # GET ---
        response = self.assertGET200(url)
        self.assertNotIn(
            'replace_creme_core__fakeactivity_type',
            self.get_form_or_fail(response).fields,
        )

        # POST ---
        response = self.assertPOST200(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeActivityType)
        self.assertFalse(dcom.replacers)

    def test_delete_hiddenfields06(self):
        "PROTECT + related entity."
        FieldsConfig.objects.create(
            content_type=FakeActivity,
            descriptions=[('type', {FieldsConfig.HIDDEN: True})],
        )

        atype2del = FakeActivityType.objects.create(name='Show')
        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_activity_type', atype2del.id),
        )
        fname = 'replace_creme_core__fakeactivity_type'

        FakeActivity.objects.create(user=self.user, title='Comiket', type=atype2del)

        # GET ---
        response1 = self.assertGET200(url)

        with self.assertNoException():
            replace_field = response1.context['form'].fields[fname]

        self.assertEqual(
            ngettext(
                'ERROR: {count} instance of «{model}» uses «{instance}» so '
                'the deletion is not possible.',
                'ERROR: {count} instances of «{model}» use «{instance}» so '
                'the deletion is not possible.',
                1
            ).format(
                count=1,
                model=smart_model_verbose_name(model=FakeActivity, count=1),
                instance=atype2del,
            ),
            replace_field.initial,
        )

        # POST ---
        response2 = self.assertPOST200(url)
        self.assertFormError(
            response2.context['form'],
            field=fname, errors=_('Deletion is not possible.'),
        )

    def test_delete_hiddenfields07(self):
        "CREME_REPLACE_NULL."
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('civility', {FieldsConfig.HIDDEN: True})],
        )

        civ2del = FakeCivility.objects.create(title='Kun')
        FakeContact.objects.create(
            user=self.user, civility=civ2del,
            last_name='Hattori', first_name='Hanzo',
        )

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_civility', civ2del.pk),
        )

        # GET ---
        response = self.assertGET200(url)
        self.assertNotIn(
            'replace_creme_core__fakecontact_civility',
            self.get_form_or_fail(response).fields,
        )

        # POST ---
        response = self.assertPOST200(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeCivility)
        self.assertReplacersEqual(
            [('fixed_value', FakeContact, 'civility', None)],
            dcom,
        )

    def test_delete_hiddenfields08(self):
        "CREME_REPLACE + no related entity."
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[('sector', {FieldsConfig.HIDDEN: True})],
        )

        create_sector = FakeSector.objects.create
        sector1    = create_sector(title='Bo')
        sector2del = create_sector(title='Gun')

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_sector', sector2del.pk),
        )

        fname1 = 'replace_creme_core__fakecontact_sector'
        fname2 = 'replace_creme_core__fakeorganisation_sector'

        # GET ---
        response = self.assertGET200(url)

        fields = response.context['form'].fields
        self.assertIn(fname1, fields)
        self.assertNotIn(fname2, fields)

        # POST ---
        response = self.assertPOST200(url, data={fname1: sector1.id})
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeSector)
        self.assertReplacersEqual(
            [('fixed_value', FakeContact, 'sector', sector1)],
            dcom,
        )

    def test_delete_hiddenfields09(self):
        "CREME_REPLACE + some related entity."
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[('sector', {FieldsConfig.HIDDEN: True})],
        )

        create_sector = FakeSector.objects.create
        sector1    = create_sector(title='Bo')
        sector2del = create_sector(title='Gun')

        FakeOrganisation.objects.create(user=self.user, name='Turtles', sector=sector2del)

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_sector', sector2del.pk),
        )

        fname1 = 'replace_creme_core__fakecontact_sector'
        fname2 = 'replace_creme_core__fakeorganisation_sector'

        # GET ---
        response = self.assertGET200(url)

        fields = response.context['form'].fields
        self.assertIn(fname1, fields)

        with self.assertNoException():
            replace_field = fields[fname2]
            choices = [*replace_field.choices]

        self.assertTrue(replace_field.required)

        self.assertNotInChoices(value='', choices=choices)
        self.assertInChoices(value=sector1.id, label=str(sector1), choices=choices)
        self.assertNotInChoices(value=sector2del.id, choices=choices)

        # POST ---
        response = self.client.post(
            url,
            data={
                fname1: sector1.id,
                fname2: sector1.id,
            },
        )
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeSector)
        self.assertReplacersEqual(
            [
                ('fixed_value', FakeContact,      'sector', sector1),
                ('fixed_value', FakeOrganisation, 'sector', sector1),
            ],
            dcom,
        )

    def test_delete_hidden_m2m(self):
        FieldsConfig.objects.create(
            content_type=FakeDocument,
            descriptions=[('categories', {FieldsConfig.HIDDEN: True})],
        )

        folder = FakeFolder.objects.create(user=self.user, title='Pictures')
        cat2del = FakeDocumentCategory.objects.create(name='Pix')

        doc = FakeDocument.objects.create(
            user=self.user, title='Pix1', linked_folder=folder,
        )
        doc.categories.set([cat2del])

        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_documentcat', cat2del.id),
        )

        # GET ---
        response = self.assertGET200(url)

        self.assertNotIn(
            'replace_creme_core__fakedocument_categories',
            self.get_form_or_fail(response).fields,
        )

        # POST ---
        response = self.client.post(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(FakeDocumentCategory)
        self.assertReplacersEqual([], dcom)

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(cat2del)
        self.assertFalse(doc.categories.all())

    def test_delete_uniqueness(self):
        self.assertFalse(DeletionCommand.objects.first())

        job = Job.objects.create(type_id=deletor_type.id, user=self.user)
        self.assertEqual(Job.STATUS_WAIT, job.status)

        pos2del1 = FakePosition.objects.create(title='Kunoichi')
        dcom = DeletionCommand.objects.create(
            content_type=FakePosition,
            job=job,
            pk_to_delete=str(pos2del1.pk),
            deleted_repr=str(pos2del1),
        )

        pos2del2 = FakePosition.objects.create(title='Ronin')
        url = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fake_position', pos2del2.pk),
        )

        msg = _(
            'A deletion process for an instance of «{model}» already exists.'
        ).format(model='Test People position')
        self.assertContains(self.client.get(url), msg, status_code=409)

        # ---
        job.status = Job.STATUS_ERROR
        job.save()
        self.assertContains(self.client.get(url), msg, status_code=409)

        # ---
        job.status = Job.STATUS_OK
        job.save()
        response = self.assertGET200(url)
        self.assertIn('form', response.context)
        self.assertDoesNotExist(job)
        self.assertDoesNotExist(dcom)

    def test_finish_deletor01(self):
        job = Job.objects.create(
            type_id=deletor_type.id,
            user=self.user,
            status=Job.STATUS_OK,
        )

        pos2del1 = FakePosition.objects.create(title='Kunoichi')
        dcom = DeletionCommand.objects.create(
            content_type=FakePosition,
            job=job,
            pk_to_delete=str(pos2del1.pk),
            deleted_repr=str(pos2del1),
        )

        url = self._build_finish_deletor_url(job)
        self.assertGET405(url)
        self.assertPOST200(url)

        self.assertDoesNotExist(job)
        self.assertDoesNotExist(dcom)

    def test_finish_deletor02(self):
        "Other user's job."
        job = Job.objects.create(
            type_id=deletor_type.id,
            user=self.create_user(0),
            status=Job.STATUS_OK,
        )

        self.assertPOST403(self._build_finish_deletor_url(job))

    def test_finish_deletor03(self):
        "Job not finished."
        job = Job.objects.create(
            type_id=deletor_type.id,
            user=self.user,
            status=Job.STATUS_WAIT,
        )

        self.assertPOST409(self._build_finish_deletor_url(job))

    def test_finish_deletor04(self):
        "Job with errors (no message)."
        job = Job.objects.create(
            type_id=deletor_type.id,
            user=self.user,
            status=Job.STATUS_OK,
        )
        JobResult.objects.create(job=job)

        self.assertContains(
            self.client.post(self._build_finish_deletor_url(job)),
            _('Error. Please contact your administrator.'),
            status_code=409,
        )

    def test_finish_deletor05(self):
        "Job with errors (message)."
        job = Job.objects.create(
            type_id=deletor_type.id,
            user=self.user,
            status=Job.STATUS_OK,
        )
        messages = ['Dependencies error.', '3 Contacts']
        JobResult.objects.create(job=job, messages=messages)

        response = self.client.post(self._build_finish_deletor_url(job))
        self.assertContains(response, messages[0], status_code=409)
        self.assertContains(response, messages[1], status_code=409)

    def test_finish_deletor06(self):
        "Not deletor job."
        from creme.creme_core.creme_jobs.reminder import reminder_type

        job = Job.objects.create(
            type_id=reminder_type.id,
            user=self.user,
            status=Job.STATUS_OK,
        )

        self.assertPOST404(self._build_finish_deletor_url(job))

    def test_delete_customisation01(self):
        "Deletion disabled (see creme.creme_core.apps.CremeCoreConfig.register_creme_config())."
        fc = FakeFolderCategory.objects.create(name='PDFs')
        self.assertGET409(
            reverse(
                'creme_config__delete_instance',
                args=('creme_core', 'fake_foldercat', fc.id,)
            )
        )

    def test_delete_customisation02(self):
        "Not vanilla-URL (see creme.creme_core.apps.CremeCoreConfig.register_creme_config())."
        img_cat = FakeImageCategory.objects.first()

        self.assertGET409(
            reverse(
                'creme_config__delete_instance',
                args=('creme_core', 'fake_img_cat', img_cat.id),
            )
        )

    def test_reload_model_brick(self):
        response = self.assertGET200(
            reverse(
                'creme_config__reload_model_brick',
                args=('creme_core', 'fake_civility'),
            )
        )

        results = response.json()
        self.assertIsList(results, length=1)

        result = results[0]
        self.assertIsList(result, length=2)

        brick_id = GenericModelBrick.id
        self.assertEqual(brick_id, result[0])
        self.get_brick_node(self.get_html_tree(result[1]), brick_id)

    def test_reload_app_bricks01(self):
        url = reverse('creme_config__reload_app_bricks', args=('creme_core',))
        self.assertGET404(url)
        self.assertGET404(url, data={'brick_id': PropertyTypesBrick.id})

        response = self.assertGET200(url, data={'brick_id': SettingsBrick.id})

        results = response.json()
        self.assertIsList(results, length=1)

        result = results[0]
        self.assertIsList(result, length=2)

        brick_id = SettingsBrick.id
        self.assertEqual(brick_id, result[0])
        self.get_brick_node(self.get_html_tree(result[1]), brick_id)

    def test_reload_app_bricks02(self):
        response = self.assertGET200(
            reverse('creme_config__reload_app_bricks', args=('creme_core',)),
            data={'brick_id': FakeAppPortalBrick.id},
        )

        results = response.json()
        self.assertIsList(results, length=1)

        result = results[0]
        self.assertIsList(result, length=2)

        brick_id = FakeAppPortalBrick.id
        self.assertEqual(brick_id, result[0])
        self.get_brick_node(self.get_html_tree(result[1]), brick_id)

    @parameterized.expand([
        (2, 2, [
            (1, 'Music'), (2, 'Movie'), (3, 'Book'), (4, 'Web'),
        ]),
        (1, 4, [
            (1, 'Movie'), (2, 'Book'), (3, 'Web'), (4, 'Music'),
        ]),
        (4, 1, [
            (1, 'Web'), (2, 'Music'), (3, 'Movie'), (4, 'Book'),
        ]),
        (2, 3, [
            (1, 'Music'), (2, 'Book'), (3, 'Movie'), (4, 'Web'),
        ]),
    ])
    def test_reorder(self, target_order, next_order, expected):
        FakeSector.objects.all().delete()

        create_sector = FakeSector.objects.create
        create_sector(title='Music', order=1)
        create_sector(title='Movie', order=2)
        create_sector(title='Book',  order=3)
        create_sector(title='Web',   order=4)

        target = FakeSector.objects.get(order=target_order)

        url = reverse(
            'creme_config__reorder_instance',
            args=('creme_core', 'fake_sector', target.id),
        )
        data = {'target': next_order}

        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertListEqual(
            expected,
            list(FakeSector.objects.order_by('order').values_list(
                'order', 'title'
            ))
        )
