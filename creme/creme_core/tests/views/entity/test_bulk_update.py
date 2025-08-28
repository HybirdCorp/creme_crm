from datetime import date, timedelta
from decimal import Decimal
from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.forms import CharField, DateField
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

import creme.creme_config.forms.fields as config_fields
from creme.creme_core.gui import bulk_update
from creme.creme_core.models import (
    CustomField,
    CustomFieldBoolean,
    CustomFieldDateTime,
    CustomFieldEnum,
    CustomFieldEnumValue,
    CustomFieldFloat,
    CustomFieldInteger,
    CustomFieldMultiEnum,
    CustomFieldString,
    FakeActivity,
    FakeActivityType,
    FakeAddress,
    FakeContact,
    FakeDocument,
    FakeFolder,
    FakeImage,
    FakeImageCategory,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    FakePosition,
    FakeSector,
    FieldsConfig,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.utils.collections import LimitedList
from creme.creme_core.views.entity import BulkUpdate, InnerEdition


class _BulkEditTestCase(CremeTestCase):
    @staticmethod
    def get_cf_values(cf, entity):
        return cf.value_class.objects.get(custom_field=cf, entity=entity)

    @staticmethod
    def create_image(name, user, categories=()):
        image = FakeImage.objects.create(user=user, name=name)
        image.categories.set(categories)

        return image


class BulkUpdateTestCase(_BulkEditTestCase):
    def setUp(self):
        super().setUp()
        # TODO: deepcopy() in setUpClass() ?
        self._original_bulk_update_registry = BulkUpdate.bulk_update_registry

    def tearDown(self):
        super().tearDown()
        BulkUpdate.bulk_update_registry = self._original_bulk_update_registry

    def create_2_contacts_n_url(self,
                                user,
                                mario_kwargs=None,
                                luigi_kwargs=None,
                                field='first_name',
                                ):
        create_contact = partial(
            FakeContact.objects.create, user=user, last_name='Bros',
        )
        mario = create_contact(first_name='Mario', **(mario_kwargs or {}))
        luigi = create_contact(first_name='Luigi', **(luigi_kwargs or {}))

        return (
            mario,
            luigi,
            self.build_bulkupdate_uri(
                model=FakeContact, field=field, entities=(mario, luigi),
            ),
        )

    def test_not_registered_model(self):
        user = self.login_as_root_and_get()
        BulkUpdate.bulk_update_registry = registry = bulk_update.BulkUpdateRegistry()
        registry.register(FakeOrganisation)  # Not FakeContact

        self.assertGET404(
            self.build_bulkupdate_uri(model=FakeImage, entities=[user.linked_contact])
        )

    def test_no_editable_field(self):
        user = self.login_as_root_and_get()
        BulkUpdate.bulk_update_registry = registry = bulk_update.BulkUpdateRegistry()
        registry.register(FakeActivity).exclude(
            'user', 'description',
            'title', 'place', 'minutes', 'start', 'end', 'type',
        )

        activity = FakeActivity.objects.create(
            user=user, title='Meeting', type=FakeActivityType.objects.first(),
        )
        response = self.client.get(
            self.build_bulkupdate_uri(model=type(activity), entities=[activity])
        )
        self.assertContains(
            response, text='has not inner-editable field.', status_code=404,
        )

    def test_regular_field_invalid_field(self):
        self.login_as_root()
        self.assertContains(
            self.client.get(self.build_bulkupdate_uri(model=FakeContact, field='unknown')),
            'The cell "regular_field-unknown" is invalid',
            status_code=404, html=True,
        )

    def test_no_field_given(self):
        user = self.login_as_root_and_get()

        uri = self.build_bulkupdate_uri(model=FakeContact, entities=[user.linked_contact])
        response1 = self.assertGET200(uri)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context1 = response1.context
        self.assertEqual(_('Multiple update'),        context1.get('title'))
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))
        self.assertHTMLEqual(
            ngettext(
                '{count} «{model}» has been selected.',
                '{count} «{model}» have been selected.',
                1
            ).format(count=1, model='Test Contact'),
            context1.get('help_message'),
        )

        with self.assertNoException():
            fields = context1['form'].fields
            choices_f = fields['_bulk_fieldname']
            choices = choices_f.choices

        other_field = self.get_alone_element(
            name for name in fields.keys() if name != '_bulk_fieldname'
        )

        with self.assertNoException():
            FakeContact._meta.get_field(other_field)

        build_url = partial(self.build_bulkupdate_uri, model=FakeContact)
        self.assertInChoices(
            value=build_url(field='first_name'), label=_('First name'), choices=choices,
        )
        self.assertInChoices(
            value=build_url(field='user'),       label=_('Owner user'), choices=choices,
        )
        self.assertEqual(build_url(field=other_field), choices_f.initial)

    def test_regular_field_not_entity_model(self):
        self.login_as_root()
        self.assertGET409(self.build_bulkupdate_uri(model=FakeSector))
        self.assertGET409(self.build_bulkupdate_uri(model=FakeSector, field='title'))

    def test_regular_field_1_entity(self):
        user = self.login_as_root_and_get()

        mario = FakeContact.objects.create(user=user, first_name='Mario', last_name='Bros')
        build_url = partial(self.build_bulkupdate_uri, model=FakeContact)
        field_name = 'first_name'
        response1 = self.assertGET200(build_url(field=field_name, entities=[mario]))
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context1 = response1.context
        self.assertEqual(_('Multiple update'),        context1.get('title'))
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))
        self.assertHTMLEqual(
            ngettext(
                '{count} «{model}» has been selected.',
                '{count} «{model}» have been selected.',
                1
            ).format(
                count=1, model='Test Contact',
            ),
            context1.get('help_message'),
        )

        with self.assertNoException():
            form = context1['form']
            fields = form.fields
            choices_f = fields['_bulk_fieldname']
            choices = choices_f.choices
            edition_field = fields[field_name]

        self.assertIsInstance(edition_field, CharField)
        self.assertEqual(_('First name'), edition_field.label)
        self.assertFalse(edition_field.required)
        self.assertDictEqual({field_name: getattr(mario, field_name)}, form.initial)

        url = build_url(field=field_name)
        self.assertInChoices(value=url,                     label=_('First name'), choices=choices)
        self.assertInChoices(value=build_url(field='user'), label=_('Owner user'), choices=choices)
        self.assertEqual(url, choices_f.initial)

        # ---
        first_name = 'Marioooo'
        response2 = self.client.post(
            url,
            data={
                'entities': [mario.pk],
                field_name: first_name,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(first_name, self.refresh(mario).first_name)

        self.assertTemplateUsed(response2, 'creme_core/bulk-update-results.html')

        get_context2 = response2.context.get
        self.assertEqual(_('Multiple update'), get_context2('title'))
        self.assertEqual(1, get_context2('initial_count'))
        self.assertEqual(1, get_context2('success_count'))
        self.assertEqual(0, get_context2('forbidden_count'))

        errors = get_context2('errors')
        self.assertIsInstance(errors, LimitedList)
        self.assertEqual(0, len(errors))
        self.assertEqual(100, errors.max_size)

        self.assertContains(
            response2,
            ngettext(
                '%(counter)s entity has been successfully modified.',
                '%(counter)s entities have been successfully modified.',
                1,
            ) % {'counter': 1},
        )

    def test_regular_field_2_entities(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user, last_name='Bros')
        mario = create_contact(first_name='Mario')
        luigi = create_contact(first_name='Luigi')
        field_name = 'first_name'
        build_url = partial(self.build_bulkupdate_uri, model=FakeContact, field=field_name)
        entities = [mario, luigi]
        response1 = self.assertGET200(build_url(entities=entities))

        context1 = response1.context
        self.assertHTMLEqual(
            ngettext(
                '{count} «{model}» has been selected.',
                '{count} «{model}» have been selected.',
                2
            ).format(
                count=2, model='Test Contacts',
            ),
            context1.get('help_message'),
        )

        with self.assertNoException():
            form = context1['form']

        self.assertDictEqual({'first_name': 'Luigi'}, form.initial)

        # ---
        value = 'Peach'
        response2 = self.client.post(
            build_url(),
            data={
                'entities': [e.id for e in entities],
                field_name: value,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(value, self.refresh(mario).first_name)
        self.assertEqual(value, self.refresh(luigi).first_name)

        get_context2 = response2.context.get
        self.assertEqual(_('Multiple update'), get_context2('title'))
        self.assertEqual(2, get_context2('initial_count'))
        self.assertEqual(2, get_context2('success_count'))
        self.assertEqual(0, get_context2('forbidden_count'))

        self.assertContains(
            response2,
            ngettext(
                '%(counter)s entity has been successfully modified.',
                '%(counter)s entities have been successfully modified.',
                2,
            ) % {'counter': 2},
        )

    def test_regular_field_not_super_user01(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*')

        mario = FakeContact.objects.create(user=user, first_name='Mario', last_name='Bros')
        self.assertTrue(user.has_perm_to_change(mario))

        field_name = 'first_name'
        url = self.build_bulkupdate_uri(model=FakeContact, field=field_name)
        self.assertGET200(url)

        field_value = 'Marioooo'
        response = self.client.post(
            url,
            data={
                'entities': [mario.pk],
                field_name: field_value,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(field_value, getattr(self.refresh(mario), field_name))

    def test_regular_field_not_super_user02(self):
        "No entity is allowed to be changed."
        user = self.login_as_standard()

        old_first_name = 'Mario'
        mario = FakeContact.objects.create(
            user=self.get_root_user(),
            first_name=old_first_name,
            last_name='Bros',
        )
        self.assertFalse(user.has_perm_to_change(mario))

        field_name = 'first_name'
        url = self.build_bulkupdate_uri(model=type(mario), field=field_name)
        self.assertGET200(url)

        self.assertPOST403(
            url,
            data={
                'entities': [mario.pk],
                field_name: 'Marioooo',
            },
        )
        self.assertEqual(old_first_name, getattr(self.refresh(mario), field_name))

    def test_regular_field_fk(self):
        user = self.login_as_root_and_get()

        create_pos = FakePosition.objects.create
        unemployed   = create_pos(title='unemployed')
        plumber      = create_pos(title='plumber')
        ghost_hunter = create_pos(title='ghost hunter')

        field_name = 'position'
        mario, luigi, url = self.create_2_contacts_n_url(
            user=user,
            mario_kwargs={field_name: plumber},
            luigi_kwargs={field_name: ghost_hunter},
            field=field_name,
        )
        self.assertGET200(url)

        response = self.assertPOST200(
            url,
            data={
                'entities': [mario.id, luigi.id],
                field_name: unemployed.id,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(unemployed, getattr(self.refresh(mario), field_name))
        self.assertEqual(unemployed, getattr(self.refresh(luigi), field_name))

    def test_regular_field_ignore_missing(self):
        user = self.login_as_root_and_get()

        create_sector = FakeSector.objects.create
        plumbing = create_sector(title='Plumbing')
        games    = create_sector(title='Games')

        field_name = 'sector'
        create_contact = partial(FakeContact.objects.create, user=user, **{field_name: games})
        mario = create_contact(first_name='Mario', last_name='Bros')
        luigi = create_contact(first_name='Luigi', last_name='Bros')

        nintendo = FakeOrganisation.objects.create(
            user=user, name='Nintendo', **{field_name: games},
        )

        url = self.build_bulkupdate_uri(model=FakeContact, field=field_name)
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'entities': [mario.id, luigi.id, nintendo.id],
                field_name: plumbing.id,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(plumbing, getattr(self.refresh(mario), field_name))
        self.assertEqual(plumbing, getattr(self.refresh(luigi), field_name))
        # Missing id in Contact's table
        self.assertEqual(games, getattr(self.refresh(nintendo), field_name))

    def test_regular_field_not_editable(self):
        user = self.login_as_root_and_get()

        field_name1 = 'position'
        BulkUpdate.bulk_update_registry = registry = bulk_update.BulkUpdateRegistry()
        registry.register(FakeContact).exclude(field_name1)

        unemployed = FakePosition.objects.create(title='unemployed')
        mario, luigi, url = self.create_2_contacts_n_url(user=user, field=field_name1)
        self.assertPOST404(
            url,
            data={
                'entities': [mario.id, luigi.id],
                field_name1: unemployed.id,
            },
        )

        # Not editable field ---
        field_name2 = 'created'
        self.assertPOST404(
            self.build_bulkupdate_uri(
                model=FakeContact, field=field_name2, entities=(mario, luigi),
            ),
            data={
                'entities': [mario.id, luigi.id],
                field_name2: 'whatever',
            },
        )

    def test_regular_field_required_empty(self):
        user = self.login_as_root_and_get()

        field_name = 'last_name'
        mario, luigi, url = self.create_2_contacts_n_url(user=user, field=field_name)
        response = self.assertPOST200(
            url,
            data={
                'entities': [mario.id, luigi.id],
                field_name: '',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=field_name, errors=_('This field is required.'),
        )

    def test_regular_field_empty(self):
        user = self.login_as_root_and_get()

        field_name = 'description'
        mario, luigi, url = self.create_2_contacts_n_url(
            user=user,
            mario_kwargs={field_name: "Luigi's brother"},
            luigi_kwargs={field_name: "Mario's brother"},
            field=field_name,
        )
        response = self.client.post(
            url,
            data={
                'entities': [mario.id, luigi.id],
                field_name: '',
            },
        )
        self.assertNoFormError(response)
        self.assertEqual('', getattr(self.refresh(mario), field_name))
        self.assertEqual('', getattr(self.refresh(luigi), field_name))

    def test_regular_field_unique(self):
        user = self.login_as_root_and_get()

        BulkUpdate.bulk_update_registry = registry = bulk_update.BulkUpdateRegistry()
        registry.register(FakeActivity)

        atype = FakeActivityType.objects.first()
        activity = FakeActivity.objects.create(user=user, title='Comiket', type=atype)

        build_url = partial(self.build_bulkupdate_uri, model=FakeActivity)
        response1 = self.assertGET200(build_url(entities=[activity]))

        with self.assertNoException():
            choices = response1.context['form'].fields['_bulk_fieldname'].choices

        field_name = 'title'
        self.assertInChoices(value=build_url(field='user'), label=_('Owner user'), choices=choices)
        url = build_url(field=field_name)
        self.assertNotInChoices(value=url, choices=choices)

        self.assertGET404(url)

    def test_regular_field_ignore_forbidden_entity(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*')
        other_user = self.get_root_user()

        field_name = 'description'
        mario_desc = "Luigi's brother"
        create_bros = partial(FakeContact.objects.create, last_name='Bros')
        mario = create_bros(user=other_user, first_name='Mario', **{field_name: mario_desc})
        luigi = create_bros(user=user, first_name='Luigi', **{field_name: "Mario's brother"})
        toad  = create_bros(user=user, first_name='Toad', **{field_name: "Mario's friend"})

        response = self.client.post(
            self.build_bulkupdate_uri(model=FakeContact, field=field_name),
            data={
                'entities': [mario.id, luigi.id, toad.id],
                field_name: '',
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(mario_desc, getattr(self.refresh(mario), field_name))  # Not allowed
        self.assertEqual('',         getattr(self.refresh(luigi), field_name))
        self.assertEqual('',         getattr(self.refresh(toad),  field_name))

        get_context = response.context.get
        self.assertEqual(3, get_context('initial_count'))
        self.assertEqual(2, get_context('success_count'))
        self.assertEqual(1, get_context('forbidden_count'))
        self.assertFalse(get_context('errors'))

        self.assertContains(
            response,
            ngettext(
                '%(counter)s entity on %(initial_count)s has been successfully modified.',
                '%(counter)s entities on %(initial_count)s have been successfully modified.',
                2,
            ) % {'counter': 2, 'initial_count': 3},
        )
        self.assertContains(
            response,
            ngettext(
                '%(counter)s entity was not editable.',
                '%(counter)s entities were not editable.',
                1,
            ) % {'counter': 1},
        )

    def test_regular_field_date(self):
        user = self.login_as_root_and_get()

        field_name = 'birthday'
        mario, luigi, url = self.create_2_contacts_n_url(user=user, field=field_name)

        birthday = date(2000, 1, 31)
        response1 = self.assertPOST200(
            url,
            data={
                'entities': [mario.id, luigi.id],
                field_name: birthday.strftime('%d-%m-%y'),
            },
        )
        self.assertFormError(
            response1.context['form'],
            field=field_name, errors=_('Enter a valid date.'),
        )

        response2 = self.client.post(
            url,
            data={
                'entities': [mario.id, luigi.id],
                field_name: self.formfield_value_date(birthday),
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(birthday, getattr(self.refresh(mario), field_name))
        self.assertEqual(birthday, getattr(self.refresh(luigi), field_name))

    def test_regular_field_ignore_forbidden_field(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*')
        other_user = self.get_root_user()

        create_bros = partial(FakeContact.objects.create, last_name='Bros')
        mario = create_bros(user=other_user, first_name='Mario')
        luigi = create_bros(user=user,       first_name='Luigi')

        create_img = FakeImage.objects.create
        forbidden = create_img(user=other_user, name='forbidden')
        self.assertFalse(user.has_perm_to_view(forbidden))

        field_name = 'image'
        response = self.assertPOST200(
            self.build_bulkupdate_uri(model=FakeContact, field=field_name),
            data={
                'entities': [mario.id, luigi.id],
                field_name: forbidden.id,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=field_name,
            errors=_('You are not allowed to link this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=forbidden.id),
            ),
        )

    def test_regular_field_overrider(self):
        user = self.login_as_root_and_get()

        field_name = 'birthday'
        called_instances = []

        class DateDelayOverrider(bulk_update.FieldOverrider):
            field_names = [field_name]

            def formfield(self, instances, user, **kwargs):
                called_instances.append(instances)
                return DateField()

            def post_clean_instance(this, *, instance, value, form):
                setattr(instance, field_name, value + timedelta(days=1))

        BulkUpdate.bulk_update_registry = registry = bulk_update.BulkUpdateRegistry()
        registry.register(FakeContact).add_overriders(DateDelayOverrider)

        mario, luigi, url = self.create_2_contacts_n_url(user=user, field=field_name)
        response1 = self.assertGET200(url)
        formfield_name = f'override-{field_name}'

        with self.assertNoException():
            overridden_f = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(overridden_f, DateField)

        self.assertEqual(1, len(called_instances))
        self.assertCountEqual([mario, luigi], called_instances[0])

        # ---
        called_instances.clear()
        response2 = self.client.post(
            url,
            data={
                'entities': [mario.id, luigi.id],
                formfield_name: self.formfield_value_date(date(2000, 1, 31)),
            },
        )
        self.assertNoFormError(response2)

        self.assertEqual(3, len(called_instances))
        self.assertCountEqual([mario, luigi], called_instances[0])
        self.assertCountEqual([mario, luigi], called_instances[1])

        field_value = date(2000, 2, 1)
        self.assertEqual(field_value, getattr(self.refresh(mario), field_name))
        self.assertEqual(field_value, getattr(self.refresh(luigi), field_name))

    def test_regular_field_user(self):
        """Fix a bug with the field list when bulk editing user
        (i.e. a field of the parent class CremeEntity).
        """
        self.login_as_root()

        build_url = partial(self.build_bulkupdate_uri, model=FakeContact)
        url = build_url(field='user')
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['_bulk_fieldname'].choices

        self.assertInChoices(
            value=url, label=_('Owner user'), choices=choices,
        )
        self.assertInChoices(
            value=build_url(field='first_name'), label=_('First name'), choices=choices,
        )

    def test_regular_field_file01(self):
        "FileFields are excluded."
        user = self.login_as_root_and_get()

        BulkUpdate.bulk_update_registry = registry = bulk_update.BulkUpdateRegistry()
        registry.register(FakeDocument)

        doc = FakeDocument.objects.create(
            user=user, title='Japan map',
            linked_folder=FakeFolder.objects.create(user=user, title='Earth maps'),
        )
        build_uri = partial(self.build_bulkupdate_uri, model=type(doc))
        response = self.assertGET200(build_uri())

        with self.assertNoException():
            choices = response.context['form'].fields['_bulk_fieldname'].choices

        self.assertInChoices(value=build_uri(field='title'), label=_('Title'), choices=choices)

        uri = build_uri(field='filedata')
        self.assertNotInChoices(value=uri, choices=choices)
        self.assertGET404(uri)

    # TODO: if subfield are unleashed
    # def test_regular_field_file02(self):
    #     "FileFields are excluded (sub-field case)."
    #     user = self.login()
    #     bag = FakeFileBag.objects.create(user=user, name='Stuffes')
    #     response = self.assertGET200(self.build_bulkupdate_uri(model=type(bag), field='name'))
    #
    #     with self.assertNoException():
    #         field_urls = {
    #             f_url
    #             for f_url, label in response.context['form'].fields['_bulk_fieldname'].choices
    #         }
    #
    #     self.assertIn(
    #         reverse('creme_core__bulk_update', args=(bag.entity_type_id, 'name')),
    #         field_urls,
    #     )
    #     self.assertNotIn('file1', field_urls)

    def test_regular_field_many2many(self):
        user = self.login_as_root_and_get()

        categories = [FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')]

        image1 = self.create_image('image1', user, categories)
        image2 = self.create_image('image2', user, categories[:1])

        self.assertListEqual([*image1.categories.all()], categories)
        self.assertListEqual([*image2.categories.all()], categories[:1])

        m2m_name = 'categories'
        response = self.client.post(
            self.build_bulkupdate_uri(model=FakeImage, field=m2m_name),
            data={
                'entities': [image1.id, image2.id],
                m2m_name: [categories[0].pk, categories[2].pk],
            },
        )
        self.assertNoFormError(response)

        expected = [categories[0], categories[2]]
        self.assertListEqual([*getattr(image1, m2m_name).all()], expected)
        self.assertListEqual([*getattr(image2, m2m_name).all()], expected)

    def test_regular_field_many2many_invalid(self):
        user = self.login_as_root_and_get()

        categories = [FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')]

        m2m_name = 'categories'
        image1 = self.create_image('image1', user, categories)
        image2 = self.create_image('image2', user, categories[:1])

        self.assertListEqual([*getattr(image1, m2m_name).all()], categories)
        self.assertListEqual([*getattr(image2, m2m_name).all()], categories[:1])

        invalid_pk = (FakeImageCategory.objects.aggregate(Max('id'))['id__max'] or 0) + 1
        response = self.client.post(
            self.build_bulkupdate_uri(model=type(image1), field=m2m_name),
            data={
                'entities': [image1.id, image2.id],
                m2m_name: [categories[0].pk, invalid_pk],
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=m2m_name,
            errors=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': invalid_pk},
        )

        self.assertListEqual([*image1.categories.all()], categories)
        self.assertListEqual([*image2.categories.all()], categories[:1])

    def test_regular_field_subfield(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user, last_name='Bros')
        mario = create_contact(first_name='Mario')
        luigi = create_contact(first_name='Luigi')

        address1 = FakeAddress.objects.create(entity=mario, value='address 1')
        mario.address = address1
        mario.save()

        # GET (field given) ---
        self.assertGET404(self.build_bulkupdate_uri(
            field='address__city', model=FakeContact, entities=[mario, luigi],
        ))

    def test_regular_field_fields_config_hidden(self):
        self.login_as_root()

        hidden_fname = 'phone'
        hidden_fkname = 'image'
        # hidden_subfname = 'zipcode'  TODO

        create_fconf = FieldsConfig.objects.create
        create_fconf(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname, {FieldsConfig.HIDDEN: True}),
                (hidden_fkname, {FieldsConfig.HIDDEN: True}),
            ],
        )

        build_uri = partial(self.build_bulkupdate_uri, model=FakeContact)
        self.assertGET404(build_uri(field=hidden_fname))
        self.assertGET404(build_uri(field=hidden_fkname))
        # self.assertGET(404, build_uri(field='address__' + hidden_subfname))

    def test_regular_field_fields_config_required(self):
        self.login_as_root()

        model = FakeContact
        field_name1 = 'phone'
        url = self.build_bulkupdate_uri(model=model, field=field_name1)

        # ---
        response1 = self.assertGET200(url)

        with self.assertNoException():
            edition_field1 = response1.context['form'].fields[field_name1]

        self.assertFalse(edition_field1.required)

        # ---
        field_name2 = 'mobile'
        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[
                (field_name1, {FieldsConfig.REQUIRED: True}),
                (field_name2, {FieldsConfig.REQUIRED: True}),
            ],
        )
        response2 = self.assertGET200(url)

        with self.assertNoException():
            fields2 = response2.context['form'].fields
            edition_field2 = fields2[field_name1]

        self.assertTrue(edition_field2.required)
        self.assertNotIn(field_name2, fields2)

    def test_custom_field_error01(self):
        self.login_as_root()

        cell_key = 'custom_field-44500124'
        response = self.client.get(
            reverse(
                'creme_core__bulk_update',
                args=(
                    ContentType.objects.get_for_model(FakeContact).id,
                    cell_key,
                ),
            )
        )
        self.assertContains(
            response,
            f'The cell "{cell_key}" is invalid',
            status_code=404, html=True,
        )

    def test_custom_field_integer(self):
        user = self.login_as_root_and_get()

        cf_int = CustomField.objects.create(
            name='int', content_type=FakeContact, field_type=CustomField.INT,
        )
        mario, luigi, uri = self.create_2_contacts_n_url(user=user, field=cf_int)

        # GET ---
        response1 = self.assertGET200(uri)

        with self.assertNoException():
            choices = response1.context['form'].fields['_bulk_fieldname'].choices

        # TODO: improve assertInChoices for opt-groups
        cf_gname = _('Custom fields')
        url = self.build_bulkupdate_uri(model=FakeContact, field=cf_int)
        for group_label, group_choices in choices:
            if group_label == cf_gname:
                self.assertInChoices(value=url, label=cf_int.name, choices=group_choices)
                break
        else:
            self.fail(f'Group "{cf_gname}" not found')

        # POST ---
        response2 = self.client.post(
            uri,
            data={
                'entities': [mario.pk, luigi.pk],
                f'custom_field-{cf_int.id}': 10,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(10, self.get_cf_values(cf_int, self.refresh(mario)).value)
        self.assertEqual(10, self.get_cf_values(cf_int, self.refresh(luigi)).value)

        # POST (empty) ---
        response3 = self.client.post(
            uri,
            data={
                'field_value': '',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response3)

        DoesNotExist = CustomFieldInteger.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_int, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_int, self.refresh(luigi))

    def test_custom_field_decimal(self):
        user = self.login_as_root_and_get()

        cf_decimal = CustomField.objects.create(
            name='float', content_type=FakeContact,
            field_type=CustomField.FLOAT,
        )
        mario, luigi, url = self.create_2_contacts_n_url(user=user, field=cf_decimal)

        formfield_name = f'custom_field-{cf_decimal.id}'
        response1 = self.client.post(
            url,
            data={
                'entities': [mario.pk, luigi.pk],
                formfield_name: '10.2',
            },
        )
        self.assertNoFormError(response1)
        expected = Decimal('10.2')
        self.assertEqual(expected, self.get_cf_values(cf_decimal, self.refresh(mario)).value)
        self.assertEqual(expected, self.get_cf_values(cf_decimal, self.refresh(luigi)).value)

        # Empty ---
        response2 = self.client.post(
            url,
            data={
                'entities': [mario.pk, luigi.pk],
                formfield_name: '',
            },
        )
        self.assertNoFormError(response2)

        DoesNotExist = CustomFieldFloat.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_decimal, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_decimal, self.refresh(luigi))

    def test_custom_field_boolean(self):
        user = self.login_as_root_and_get()

        cf_bool = CustomField.objects.create(
            name='bool', content_type=FakeContact,
            field_type=CustomField.BOOL,
        )
        mario, luigi, url = self.create_2_contacts_n_url(user=user, field=cf_bool)

        # Bool
        formfield_name = f'custom_field-{cf_bool.id}'
        e_ids = [mario.pk, luigi.pk]
        response1 = self.client.post(
            url,
            data={
                'entities': e_ids,
                formfield_name: 'true',
            },
        )
        self.assertNoFormError(response1)
        self.assertEqual(True, self.get_cf_values(cf_bool, self.refresh(mario)).value)
        self.assertEqual(True, self.get_cf_values(cf_bool, self.refresh(luigi)).value)

        # Bool false
        response2 = self.client.post(
            url,
            data={
                'entities': e_ids,
                formfield_name: 'false',
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(False, self.get_cf_values(cf_bool, self.refresh(mario)).value)
        self.assertEqual(False, self.get_cf_values(cf_bool, self.refresh(luigi)).value)

        # Bool empty
        response3 = self.client.post(
            url,
            data={
                'entities': e_ids,
                formfield_name: 'unknown',
            },
        )
        self.assertNoFormError(response3)

        DoesNotExist = CustomFieldBoolean.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_bool, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_bool, self.refresh(luigi))

    def test_custom_field_string(self):
        user = self.login_as_root_and_get()

        cf_str = CustomField.objects.create(
            name='str', content_type=FakeContact, field_type=CustomField.STR,
        )
        mario, luigi, url = self.create_2_contacts_n_url(user=user, field=cf_str)

        # Str
        e_ids = [mario.pk, luigi.pk]
        formfield_name = f'custom_field-{cf_str.id}'
        field_value = 'my value'
        response1 = self.client.post(
            url,
            data={
                'entities': e_ids,
                formfield_name: field_value,
            },
        )
        self.assertNoFormError(response1)
        self.assertEqual(field_value, self.get_cf_values(cf_str, self.refresh(mario)).value)
        self.assertEqual(field_value, self.get_cf_values(cf_str, self.refresh(luigi)).value)

        # Str empty
        response2 = self.client.post(
            url,
            data={
                'entities': e_ids,
                formfield_name: '',
            },
        )
        self.assertNoFormError(response2)

        DoesNotExist = CustomFieldString.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_str, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_str, self.refresh(luigi))

    def test_custom_field_datetime(self):
        user = self.login_as_root_and_get()

        get_cf_values = self.get_cf_values
        cf_date = CustomField.objects.create(
            name='date', content_type=FakeContact, field_type=CustomField.DATETIME,
        )
        mario, luigi, url = self.create_2_contacts_n_url(user=user, field=cf_date)

        # Date
        e_ids = [mario.pk, luigi.pk]
        formfield_name = f'custom_field-{cf_date.id}'
        dt = self.create_datetime(2000, 1, 31)
        response1 = self.client.post(
            url,
            data={
                'entities': e_ids,
                formfield_name: self.formfield_value_datetime(dt),
            },
        )
        self.assertNoFormError(response1)

        self.assertEqual(dt, get_cf_values(cf_date, self.refresh(mario)).value)
        self.assertEqual(dt, get_cf_values(cf_date, self.refresh(luigi)).value)

        # Date empty
        response2 = self.client.post(
            url,
            data={
                'entities': e_ids,
                formfield_name: '',
            },
        )
        self.assertNoFormError(response2)

        DoesNotExist = CustomFieldDateTime.DoesNotExist
        self.assertRaises(DoesNotExist, get_cf_values, cf_date, self.refresh(mario))
        self.assertRaises(DoesNotExist, get_cf_values, cf_date, self.refresh(luigi))

    def test_custom_field_enum(self):
        user = self.login_as_root_and_get()
        get_cf_values = self.get_cf_values

        cf_enum = CustomField.objects.create(
            name='enum', content_type=FakeContact, field_type=CustomField.ENUM,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cf_enum)
        enum1 = create_evalue(value='Enum1')
        create_evalue(value='Enum2')

        mario, luigi, url = self.create_2_contacts_n_url(user=user, field=cf_enum)

        response1 = self.assertGET200(url)
        formfield_name = f'custom_field-{cf_enum.id}'

        with self.assertNoException():
            field = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(field, config_fields.CreatorCustomEnumerableChoiceField)
        self.assertEqual(user, field.user)

        # Enum
        e_ids = [mario.pk, luigi.pk]
        response2 = self.client.post(
            url,
            data={
                'entities': e_ids,
                formfield_name: enum1.id,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(enum1, get_cf_values(cf_enum, self.refresh(mario)).value)
        self.assertEqual(enum1, get_cf_values(cf_enum, self.refresh(luigi)).value)

        # Enum empty
        response3 = self.client.post(
            url,
            data={
                'entities': e_ids,
                formfield_name: '',
            },
        )
        self.assertNoFormError(response3)

        DoesNotExist = CustomFieldEnum.DoesNotExist
        self.assertRaises(DoesNotExist, get_cf_values, cf_enum, self.refresh(mario))
        self.assertRaises(DoesNotExist, get_cf_values, cf_enum, self.refresh(luigi))

    def test_custom_field_enum_multiple(self):
        user = self.login_as_root_and_get()
        get_cf_values = self.get_cf_values

        cf_multi_enum = CustomField.objects.create(
            name='multi_enum', content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
        )

        create_cfvalue = partial(
            CustomFieldEnumValue.objects.create, custom_field=cf_multi_enum,
        )
        m_enum1 = create_cfvalue(value='MEnum1')
        create_cfvalue(value='MEnum2')
        m_enum3 = create_cfvalue(value='MEnum3')

        mario, luigi, url = self.create_2_contacts_n_url(user=user, field=cf_multi_enum)
        self.assertGET200(url)

        # Multi-Enum
        e_ids = [mario.pk, luigi.pk]
        formfield_name = f'custom_field-{cf_multi_enum.id}'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'entities': e_ids,
                formfield_name: [m_enum1.id, m_enum3.id],
            },
        ))

        mario = self.refresh(mario)
        luigi = self.refresh(luigi)

        values_set = {
            *get_cf_values(cf_multi_enum, mario).value.values_list('pk', flat=True),
        }
        self.assertIn(m_enum1.id, values_set)
        self.assertIn(m_enum3.id, values_set)

        # Multi-Enum empty
        self.assertNoFormError(self.client.post(
            url,
            data={
                'entities': e_ids,
                formfield_name: [],
            },
        ))

        DoesNotExist = CustomFieldMultiEnum.DoesNotExist
        self.assertRaises(DoesNotExist, get_cf_values, cf_multi_enum, self.refresh(mario))
        self.assertRaises(DoesNotExist, get_cf_values, cf_multi_enum, self.refresh(luigi))

    def test_custom_field_deleted(self):
        user = self.login_as_root_and_get()

        cfield = CustomField.objects.create(
            name='int', content_type=FakeContact, field_type=CustomField.INT,
            is_deleted=True,
        )
        mario, luigi, url = self.create_2_contacts_n_url(user=user, field=cfield)
        self.assertGET404(url)

    def test_other_field_validation_error_1_entity(self):
        user = self.login_as_root_and_get()

        empty_user1 = self.create_user(
            username='empty1', first_name='', last_name='', email='',
        )
        empty_contact1 = FakeContact.objects.create(
            user=user, first_name='', last_name='', is_user=empty_user1,
        )

        field_name = 'last_name'
        response = self.assertPOST200(
            self.build_bulkupdate_uri(model=FakeContact, field=field_name),
            data={
                'entities': [empty_contact1.id],
                field_name: 'Bros',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_('This Contact is related to a user and must have a first name.'),
        )

    def test_other_field_validation_error_several_entities01(self):
        "First selected entities (used as initial) raises an error."
        user = self.login_as_root_and_get()

        def create_contact(related_user):
            return FakeContact.objects.create(
                user=user, is_user=related_user,
                first_name=related_user.first_name, last_name=related_user.last_name,
            )

        user_contact1 = create_contact(self.create_user(index=0))
        user_contact2 = create_contact(self.create_user(index=1))

        field_name = 'first_name'
        build_uri = partial(self.build_bulkupdate_uri, model=FakeContact, field=field_name)
        self.assertGET200(build_uri(entities=[user_contact1, user_contact2]))

        # ---
        response2 = self.assertPOST200(
            build_uri(),
            data={
                'entities': [user_contact1.id, user_contact2.id],
                field_name: '',
            },
        )
        self.assertFormError(
            response2.context['form'],
            field=None,
            errors=_('This Contact is related to a user and must have a first name.'),
        )

    def test_other_field_validation_error_several_entities02(self):
        "First selected entities (used as initial) does not raise an error."
        user = self.login_as_root_and_get()

        def create_user_contact(related_user):
            return FakeContact.objects.create(
                user=user, is_user=related_user,
                first_name=related_user.first_name, last_name=related_user.last_name,
            )

        user_contact1 = create_user_contact(self.create_user(index=0))
        user_contact2 = create_user_contact(self.create_user(index=1))

        contact3 = FakeContact.objects.create(
            user=user, first_name='Mario', last_name='Acme',
        )
        self.assertLess(contact3.last_name, user_contact1.last_name)
        self.assertLess(contact3.last_name, user_contact2.last_name)

        field_name = 'first_name'
        build_uri = partial(self.build_bulkupdate_uri, model=FakeContact, field=field_name)
        self.assertGET200(build_uri(entities=[user_contact1, user_contact2, contact3]))

        # ---
        response2 = self.client.post(
            build_uri(),
            data={
                'entities': [user_contact1.id, user_contact2.id, contact3.id],
                field_name: '',
            },
        )
        self.assertNoFormError(response2)

        get_context = response2.context.get
        self.assertEqual(3, get_context('initial_count'))
        self.assertEqual(1, get_context('success_count'))
        self.assertEqual(2, len(get_context('errors')))

        self.assertContains(
            response2,
            _('This Contact is related to a user and must have a first name.'),
            count=2,
        )


class InnerEditTestCase(_BulkEditTestCase):
    def setUp(self):
        super().setUp()
        self._original_bulk_update_registry = InnerEdition.bulk_update_registry

    def tearDown(self):
        super().tearDown()
        InnerEdition.bulk_update_registry = self._original_bulk_update_registry

    def create_contact(self, user):
        return FakeContact.objects.create(user=user, first_name='Mario', last_name='Bros')

    def create_orga(self, user):
        return FakeOrganisation.objects.create(user=user, name='Mushroom kingdom')

    def test_callback_url(self):
        user = self.login_as_root_and_get()

        mario = self.create_contact(user=user)
        cb_url = mario.get_lv_absolute_url()
        response = self.assertGET200(
            self.build_inneredit_uri(mario, 'first_name') + f'&callback_url={cb_url}'
        )
        self.assertEqual(
            '<a href="{url}">{label}</a>'.format(
                url=f'{mario.get_edit_absolute_url()}?callback_url={cb_url}',
                label=_('Full edition form'),
            ),
            response.context.get('help_message'),
        )

    def test_aux_entity(self):
        user = self.login_as_standard(allowed_apps=['creme_core'])
        self.add_credentials(user.role, all='!CHANGE')

        invoice = FakeInvoice.objects.create(user=user, name='Invoice#1')
        line = FakeInvoiceLine.objects.create(user=user, linked_invoice=invoice)
        response = self.client.get(self.build_inneredit_uri(line, 'item'))
        self.assertContains(
            response,
            text=_('You are not allowed to edit this entity'),
            status_code=403, html=True,
        )

    def test_permissions(self):
        user = self.login_as_standard(allowed_apps=['creme_core'])
        self.add_credentials(user.role, all='!CHANGE')

        mario = self.create_contact(user=user)
        self.assertGET403(self.build_inneredit_uri(mario, 'first_name'))

    def test_regular_field(self):
        user = self.login_as_root_and_get()

        mario = self.create_contact(user=user)
        self.assertGET404(self.build_inneredit_uri(mario, 'unknown'))

        field_name = 'first_name'
        url = self.build_inneredit_uri(mario, field_name)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        get_ctxt = response1.context.get
        self.assertEqual(_('Edit «{object}»').format(object=mario), get_ctxt('title'))
        self.assertEqual(_('Save the modifications'),               get_ctxt('submit_label'))
        self.assertIsNone(get_ctxt('help_message'))

        # ---
        first_name = 'Luigi'
        self.assertNoFormError(self.client.post(
            url, data={field_name: first_name},
        ))
        self.assertEqual(first_name, self.refresh(mario).first_name)

    def test_regular_field_validation(self):
        user = self.login_as_root_and_get()

        mario = self.create_contact(user=user)
        field_name = 'birthday'
        response = self.assertPOST200(
            self.build_inneredit_uri(mario, field_name),
            data={field_name: 'whatever'},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=field_name, errors=_('Enter a valid date.'),
        )

    def test_regular_field_not_allowed(self):
        "No permission."
        user = self.login_as_standard(
            creatable_models=[FakeContact],
            allowed_apps=['documents'],
        )
        self.add_credentials(user.role, all='!CHANGE')

        mario = self.create_contact(user=user)
        self.assertFalse(user.has_perm_to_change(mario))
        self.assertGET403(self.build_inneredit_uri(mario, 'first_name'))

    def test_regular_field_required(self):
        user = self.login_as_root_and_get()

        mario = self.create_contact(user=user)
        field_name = 'last_name'
        response = self.assertPOST200(
            self.build_inneredit_uri(mario, field_name),
            data={field_name: ''},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=field_name, errors=_('This field is required.'),
        )

    def test_regular_field_not_editable(self):
        user = self.login_as_root_and_get()

        mario = self.create_contact(user=user)
        self.assertFalse(mario._meta.get_field('is_user').editable)

        build_uri = self.build_inneredit_uri
        uri = build_uri(mario, 'is_user')
        self.assertGET404(uri)
        self.assertPOST404(uri, data={'is_user': self.create_user().id})

        # Fields without form-field
        self.assertGET404(build_uri(mario, 'id'))
        self.assertGET404(build_uri(mario, 'cremeentity_ptr'))

    def test_regular_field_fields_config_hidden(self):
        user = self.login_as_root_and_get()

        hidden_fname = 'phone'
        hidden_fkname = 'image'
        hidden_subfname = 'zipcode'

        create_fconf = FieldsConfig.objects.create
        create_fconf(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname, {FieldsConfig.HIDDEN: True}),
                (hidden_fkname, {FieldsConfig.HIDDEN: True}),
            ],
        )
        create_fconf(
            content_type=FakeAddress,
            descriptions=[(hidden_subfname, {FieldsConfig.HIDDEN: True})],
        )

        mario = self.create_contact(user=user)

        build_uri = partial(self.build_inneredit_uri, mario)
        self.assertGET404(build_uri(hidden_fname))
        self.assertGET404(build_uri(hidden_fkname))
        self.assertGET404(build_uri('address__' + hidden_subfname))

    def test_regular_field_fields_config_required01(self):
        user = self.login_as_root_and_get()

        field_name = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(field_name, {FieldsConfig.REQUIRED: True})],
        )

        mario = self.create_contact(user=user)
        uri = self.build_inneredit_uri(mario, field_name)
        response1 = self.assertGET200(uri)

        with self.assertNoException():
            edition_f = response1.context['form'].fields[field_name]

        self.assertIsInstance(edition_f, CharField)
        self.assertTrue(edition_f.required)

        # ---
        response2 = self.assertPOST200(uri, data={field_name: ''})
        self.assertFormError(
            response2.context['form'],
            field=field_name,
            errors=[
                _('This field is required.'),
                _('The field «{}» has been configured as required.').format(_('Phone')),
            ],
        )

    def test_regular_field_fields_config_required02(self):
        "The required field is not edited & is not filled."
        user = self.login_as_root_and_get()

        field_name1 = 'phone'
        field_name2 = 'mobile'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(field_name2, {FieldsConfig.REQUIRED: True})],
        )

        mario = self.create_contact(user=user)
        uri = self.build_inneredit_uri(mario, field_name1)
        response1 = self.assertGET200(uri)

        with self.assertNoException():
            fields = response1.context['form'].fields

        self.assertIn(field_name1, fields)

        field2 = fields.get(field_name2)
        # TODO?
        # self.assertIsInstance(field2, CharField)
        # self.assertTrue(field2.required)
        self.assertIsNone(field2)

        # ---
        response2 = self.assertPOST200(
            uri,
            data={
                field_name1: '123456',
                # field_name2: '',  # Not filled
            },
        )
        self.assertFormError(
            # TODO?
            # response2.context['form'], field_name2, _('This field is required.'),
            response2.context['form'],
            field=None,
            errors=_('The field «{}» has been configured as required.').format(_('Mobile')),
        )

        # TODO?
        # # ---
        # value2 = '8463469'
        # response3 = self.client.post(
        #     uri,
        #     data={
        #         field_name1: value1,
        #         field_name2: value2,
        #     },
        # )
        # self.assertNoFormError(response3)
        #
        # mario = self.refresh(mario)
        # self.assertEqual(value1, getattr(mario, field_name1))
        # self.assertEqual(value2, getattr(mario, field_name2))

    def test_regular_field_many2many(self):
        user = self.login_as_root_and_get()

        create_cat = FakeImageCategory.objects.create
        categories = [create_cat(name='A'), create_cat(name='B'), create_cat(name='C')]

        image = self.create_image('image', user, categories)
        image.categories.set([categories[1]])

        m2m_name = 'categories'
        uri = self.build_inneredit_uri(image, m2m_name)

        response1 = self.assertGET200(uri)

        with self.assertNoException():
            form1 = response1.context['form']
            edition_f = form1.fields[m2m_name]

        self.assertIsInstance(edition_f, config_fields.CreatorModelMultipleChoiceField)
        self.assertListEqual([categories[1]], form1.initial.get(m2m_name))

        # ---
        response2 = self.client.post(
            uri, data={m2m_name: [categories[0].pk, categories[2].pk]},
        )
        self.assertNoFormError(response2)

        image = self.refresh(image)
        self.assertListEqual([*image.categories.all()], [categories[0], categories[2]])

    def test_regular_field_many2many_invalid(self):
        user = self.login_as_root_and_get()

        create_cat = FakeImageCategory.objects.create
        categories = [create_cat(name='A'), create_cat(name='B'), create_cat(name='C')]

        image = self.create_image('image', user, categories)
        self.assertCountEqual(image.categories.all(), categories)

        invalid_pk = self.UNUSED_PK
        self.assertFalse(FakeImageCategory.objects.filter(id=invalid_pk))

        m2m_name = 'categories'
        uri = self.build_inneredit_uri(image, m2m_name)
        response = self.assertPOST200(
            uri, data={m2m_name: [categories[0].pk, invalid_pk]},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=m2m_name,
            errors=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': invalid_pk},
        )
        self.assertCountEqual(categories, self.refresh(image).categories.all())

    def test_regular_field_unique(self):
        user = self.login_as_root_and_get()

        InnerEdition.bulk_update_registry = registry = bulk_update.BulkUpdateRegistry()
        registry.register(FakeActivity)

        atype = FakeActivityType.objects.first()
        activity = FakeActivity.objects.create(user=user, title='Comiket', type=atype)

        field_name = 'title'
        uri = self.build_inneredit_uri(activity, field_name)
        self.assertGET200(uri)

        title = f'{activity.title} (edited)'
        response2 = self.client.post(uri, data={field_name: title})
        self.assertNoFormError(response2)
        self.assertEqual(title, self.refresh(activity).title)

    def test_regular_field_invalid_model(self):
        "Neither an entity & neither related to an entity."
        self.login_as_root()

        sector = FakeSector.objects.all()[0]
        response = self.client.get(self.build_inneredit_uri(sector, 'title'))
        self.assertContains(
            response,
            'This model is not a entity model: creme.creme_core.tests.fake_models.FakeSector',
            status_code=409,
        )

    def test_regular_field_overrider(self):
        user = self.login_as_root_and_get()

        field_name = 'last_name'

        class UpperOverrider(bulk_update.FieldOverrider):
            field_names = [field_name]

            def formfield(self, instances, user, **kwargs):
                return CharField()

            def post_clean_instance(this, *, instance, value, form):
                setattr(instance, field_name, value.upper())

        InnerEdition.bulk_update_registry = registry = bulk_update.BulkUpdateRegistry()
        registry.register(FakeContact).add_overriders(UpperOverrider)

        mario = self.create_contact(user=user)
        uri = self.build_inneredit_uri(mario, field_name)
        self.assertGET200(uri)

        self.assertNoFormError(
            self.client.post(uri, data={f'override-{field_name}': 'luigi'})
        )
        self.assertEqual('LUIGI', self.refresh(mario).last_name)

    def test_regular_field_overrider_validation_error(self):
        user = self.login_as_root_and_get()

        field_name = 'last_name'
        error_msg = 'Invalid name'

        class ForbiddenOverrider(bulk_update.FieldOverrider):
            field_names = [field_name]

            def formfield(self, instances, user, **kwargs):
                return CharField()

            def post_clean_instance(this, *, instance, value, form):
                raise ValidationError(error_msg)

        InnerEdition.bulk_update_registry = registry = bulk_update.BulkUpdateRegistry()
        registry.register(FakeContact).add_overriders(ForbiddenOverrider)

        mario = self.create_contact(user=user)

        formfield_name = f'override-{field_name}'
        response = self.assertPOST200(
            self.build_inneredit_uri(mario, 'last_name'),
            data={formfield_name: 'luigi'},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=formfield_name, errors=error_msg,
        )

    def test_regular_field_file01(self):
        user = self.login_as_root_and_get()

        InnerEdition.bulk_update_registry = registry = bulk_update.BulkUpdateRegistry()
        registry.register(FakeDocument)

        folder = FakeFolder.objects.create(user=user, title='Earth maps')
        doc = FakeDocument.objects.create(
            user=user, title='Japan map', linked_folder=folder,
        )

        uri = self.build_inneredit_uri(doc, 'filedata')
        self.assertGET200(uri)

        content = 'Yes I am the content (DocumentTestCase.test_createview)'
        file_obj = self.build_filedata(content, suffix=f'.{settings.ALLOWED_EXTENSIONS[0]}')
        response = self.client.post(uri, data={'filedata': file_obj})
        self.assertNoFormError(response)

        filedata = self.refresh(doc).filedata
        self.assertEqual(f'creme_core-tests/{file_obj.base_name}', filedata.name)

        with filedata.open('r') as f:
            self.assertEqual([content], f.readlines())

    # TODO: test FileField + blank=True (need a new fake CremeEntity)
    # def test_regular_field_file02(self):
    #     "Empty data."
    #     user = self.login()
    #
    #     InnerEdition.bulk_update_registry = registry = bulk_update._BulkUpdateRegistry()
    #     registry.register(FakeDocument)
    #
    #     file_path = self.create_uploaded_file(
    #         file_name='InnerEditTestCase_test_regular_field_file02.txt',
    #         dir_name='views',
    #     )
    #
    #     comp = FakeFileComponent.objects.create(filedata=file_path)
    #     bag = FakeFileBag.objects.create(user=user, name='Stuffes', file1=comp)
    #
    #     # url = self.build_inneredit_url(bag, 'file1__filedata')
    #     url = self.build_inneredit_uri(bag, 'file1__filedata')
    #     self.assertGET200(url)
    #
    #     response = self.client.post(
    #         url,
    #         data={
    #             'entities_lbl': [str(bag)],
    #             'field_value-clear': 'on',
    #             'field_value': b'',
    #         },
    #     )
    #     self.assertNoFormError(response)
    #     self.assertEqual('', self.refresh(comp).filedata.name)

    def test_custom_field01(self):
        user = self.login_as_root_and_get()
        mario = self.create_contact(user=user)
        old_created = mario.created - timedelta(days=1)
        type(mario).objects.filter(id=mario.id).update(
            created=old_created,
            modified=mario.modified - timedelta(days=1),
        )

        cfield = CustomField.objects.create(
            name='custom 1', content_type=mario.entity_type,
            field_type=CustomField.STR,
        )
        uri = self.build_inneredit_uri(mario, cfield)
        response1 = self.assertGET200(uri)

        formfield_name = f'custom_field-{cfield.id}'

        with self.assertNoException():
            field = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(field, CharField)

        value = 'hihi'
        response2 = self.client.post(uri, data={formfield_name: value})
        self.assertNoFormError(response2)

        mario = self.refresh(mario)
        self.assertEqual(value, self.get_cf_values(cfield, mario).value)
        self.assertEqual(old_created, mario.created)
        self.assertDatetimesAlmostEqual(now(), mario.modified)

    def test_custom_field02(self):
        user = self.login_as_root_and_get()
        mario = self.create_contact(user=user)
        cfield = CustomField.objects.create(
            name='custom 1', content_type=mario.entity_type,
            field_type=CustomField.ENUM,
        )
        uri = self.build_inneredit_uri(mario, cfield)
        response = self.assertGET200(uri)

        with self.assertNoException():
            field = response.context['form'].fields[f'custom_field-{cfield.id}']

        self.assertIsInstance(field, config_fields.CreatorCustomEnumerableChoiceField)
        self.assertEqual(user, field.user)

    def test_custom_field03(self):
        "Deleted CustomField => error."
        user = self.login_as_root_and_get()
        mario = self.create_contact(user=user)
        cfield = CustomField.objects.create(
            name='custom 1', content_type=mario.entity_type,
            field_type=CustomField.INT,
            is_deleted=True,
        )
        self.assertGET404(self.build_inneredit_uri(mario, cfield))

    def test_related_subfield(self):
        user = self.login_as_root_and_get()
        orga = self.create_orga(user=user)
        self.assertGET404(self.build_inneredit_uri(orga, 'address__city'))

    def test_related_field(self):
        user = self.login_as_root_and_get()
        orga = self.create_orga(user=user)
        orga.address = FakeAddress.objects.create(entity=orga, value='address 1')
        orga.save()

        self.assertGET404(self.build_inneredit_uri(orga, 'address'))

    def test_other_field_validation_error(self):
        user = self.login_as_root_and_get()
        empty_user = self.create_user(
            username='empty', first_name='', last_name='', email='',
        )
        empty_contact = FakeContact.objects.create(
            user=user, first_name='', last_name='', is_user=empty_user,
        )

        field_name = 'last_name'
        uri = self.build_inneredit_uri(empty_contact, field_name)
        self.assertGET200(uri)

        response2 = self.assertPOST200(uri, data={field_name: 'Bros'})
        self.assertFormError(
            response2.context['form'],
            field=None,
            errors=_('This Contact is related to a user and must have a first name.'),
        )

    def test_both_edited_field_and_field_validation_error(self):
        user = self.login_as_root_and_get()
        empty_user = self.create_user(
            username='empty', first_name='', last_name='', email='',
        )
        empty_contact = FakeContact.objects.create(
            user=user, first_name='', last_name='', is_user=empty_user,
        )

        field_name = 'last_name'
        uri = self.build_inneredit_uri(empty_contact, field_name)
        self.assertGET200(uri)

        response = self.assertPOST200(uri, data={field_name: ''})
        self.assertFormError(
            self.get_form_or_fail(response),
            field=field_name, errors=_('This field is required.'),
        )

    def test_multi_fields(self):
        "2 regular fields + 1 CustomField."
        user = self.login_as_root_and_get()

        mario = self.create_contact(user=user)

        cfield = CustomField.objects.create(
            content_type=mario.entity_type, name='Coins', field_type=CustomField.INT,
        )

        url = self.build_inneredit_uri(mario, 'first_name', 'phone', cfield)
        response1 = self.assertGET200(url)
        # TODO: template with no block?
        # self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        get_ctxt1 = response1.context.get
        self.assertEqual(_('Edit «{object}»').format(object=mario), get_ctxt1('title'))
        self.assertEqual(_('Save the modifications'),               get_ctxt1('submit_label'))

        # ---
        first_name = 'Luigi'
        phone = '123 456'
        coins = 569
        response = self.client.post(
            url,
            data={
                'first_name': first_name,
                'phone':      phone,
                f'custom_field-{cfield.id}': coins,
            },
        )
        self.assertNoFormError(response)

        mario = self.refresh(mario)
        self.assertEqual(first_name, mario.first_name)
        self.assertEqual(phone,      mario.phone)
        self.assertEqual(
            coins,
            cfield.value_class.objects.get(custom_field=cfield, entity=mario).value,
        )

    def test_multi_fields_errors01(self):
        user = self.login_as_root_and_get()

        mario = self.create_contact(user=user)
        self.assertGET404(self.build_inneredit_uri(mario))  # No field
        self.assertGET404(self.build_inneredit_uri(mario, 'unknown', 'phone'))  # Invalid field

    def test_multi_fields_errors02(self):
        "Hidden field given."
        user = self.login_as_root_and_get()

        mario = self.create_contact(user=user)
        hidden = 'phone'
        FieldsConfig.objects.create(
            content_type=mario.entity_type,
            descriptions=[(hidden, {FieldsConfig.HIDDEN: True})],
        )

        self.assertGET404(self.build_inneredit_uri(mario, 'first_name', hidden))
