from functools import partial
from itertools import chain

import django.forms.fields as form_fields
from django.core.exceptions import ValidationError
from django.test.utils import override_settings
from django.utils.translation import gettext as _

from creme.creme_config.forms.fields import CreatorEnumerableModelChoiceField
from creme.creme_core.core import entity_cell
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegularField,
    EntityCellVolatile,
)
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.gui.bulk_update import BulkUpdateRegistry, FieldOverrider
from creme.creme_core.models import (
    CustomField,
    FakeActivity,
    FakeActivityType,
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeImage,
    FakeOrganisation,
    FakeSector,
    FieldsConfig,
    Language,
)

from ..base import CremeTestCase


class BulkUpdateRegistryTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.bulk_update_registry = BulkUpdateRegistry()
        self.maxDiff = None

    def test_register(self):
        registry = self.bulk_update_registry
        self.assertIsNone(registry.config(FakeContact))
        self.assertIsNone(registry.config(FakeOrganisation))

        registry.register(FakeContact)
        self.assertIsInstance(registry.config(FakeContact), registry._ModelConfig)
        self.assertIsNone(registry.config(FakeOrganisation))

        with self.assertNoException():
            registry.register(FakeOrganisation)

        with self.assertRaises(registry.Error):
            registry.register(FakeContact)

    def test_is_regular_field_updatable(self):
        is_updatable = partial(
            self.bulk_update_registry
                .register(FakeOrganisation)
                .exclude('email')
                .is_regular_field_updatable,
            model=FakeOrganisation,
        )
        get_field = FakeOrganisation._meta.get_field

        self.assertTrue(is_updatable(field=get_field('name')))
        self.assertTrue(is_updatable(field=get_field('phone')))
        self.assertTrue(is_updatable(field=get_field('sector')))

        self.assertFalse(is_updatable(field=get_field('id')))
        self.assertFalse(is_updatable(field=get_field('cremeentity_ptr')))
        self.assertFalse(is_updatable(field=get_field('created')))  # Editable = False
        self.assertFalse(is_updatable(field=get_field('address')))  # Editable = False
        self.assertFalse(is_updatable(field=get_field('email')))  # Excluded field

    def test_is_regular_field_updatable_inheritance(self):
        is_updatable = partial(
            self.bulk_update_registry
                .register(FakeContact)
                .is_regular_field_updatable,
            model=FakeContact,
        )
        get_field = FakeContact._meta.get_field

        self.assertTrue(is_updatable(field=get_field('first_name')))
        self.assertTrue(is_updatable(field=get_field('last_name')))
        self.assertFalse(is_updatable(field=get_field('address')))

        # Automatically inherited from CremeEntity excluded fields (editable = false)
        self.assertFalse(is_updatable(field=get_field('modified')))
        self.assertFalse(is_updatable(field=get_field('is_deleted')))

    def test_is_regular_field_updatable_unique01(self):
        is_updatable = partial(
            self.bulk_update_registry
                .register(FakeActivity)
                .is_regular_field_updatable,
            model=FakeActivity,
        )
        title_f = FakeActivity._meta.get_field('title')

        # NB: 'title' is a unique field which means we should avoid to edit
        #     several entities at once.
        self.assertTrue(is_updatable(field=title_f, exclude_unique=False))
        self.assertFalse(is_updatable(field=title_f))

    def test_is_regular_field_updatable_unique02(self):
        "FileFields are considered unique."
        is_updatable = partial(
            self.bulk_update_registry
                .register(FakeDocument)
                .is_regular_field_updatable,
            model=FakeDocument,
        )
        filedata_f = FakeDocument._meta.get_field('filedata')

        self.assertTrue(is_updatable(field=filedata_f, exclude_unique=False))
        self.assertFalse(is_updatable(field=filedata_f, exclude_unique=True))

    def test_is_regular_field_updatable_many2many(self):
        self.assertTrue(
            self.bulk_update_registry.register(FakeImage).is_regular_field_updatable(
                model=FakeImage,
                field=FakeImage._meta.get_field('categories'),
            )
        )

    def test_overriders(self):
        config = self.bulk_update_registry.register(FakeOrganisation)
        self.assertDictEqual({}, config.overrider_classes)

        class ImageOverrider(FieldOverrider):
            field_names = ['image']

        class CapitalOverrider(FieldOverrider):
            field_names = ['capital', 'legal_form']

        with self.assertNoException():
            config.exclude(
                'sector',  # Causes no problem
            ).add_overriders(
                ImageOverrider, CapitalOverrider,
            )

        self.assertDictEqual(
            {
                'image': ImageOverrider,
                'capital': CapitalOverrider,
                'legal_form': CapitalOverrider,
            },
            config.overrider_classes,
        )

    def test_overriders_duplicate01(self):
        "Field overridden several times => error."
        registry = self.bulk_update_registry
        overridden = 'image'

        class ImageOverrider(FieldOverrider):
            field_names = [overridden]

        class SectorOverrider(FieldOverrider):
            field_names = ['sector', overridden]

        config = registry.register(FakeOrganisation)

        with self.assertRaises(registry.Error) as cm:
            config.add_overriders(ImageOverrider, SectorOverrider)

        self.assertEqual(
            f'The field "{overridden}" cannot be overridden several times.',
            str(cm.exception),
        )

    def test_overriders_duplicate02(self):
        "Field overridden several times => error."
        registry = self.bulk_update_registry
        overridden = 'image'

        class ImageOverrider(FieldOverrider):
            field_names = [overridden]

        class SectorOverrider(FieldOverrider):
            field_names = ['sector', overridden]

        config = registry.register(FakeOrganisation)
        config.add_overriders(ImageOverrider)

        with self.assertRaises(registry.Error) as cm:
            config.add_overriders(SectorOverrider)

        self.assertEqual(
            f'The field "{overridden}" cannot be overridden several times.',
            str(cm.exception),
        )

    def test_overriders_excluded01(self):
        "Field excluded + overridden => error."
        registry = self.bulk_update_registry
        overridden = 'image'

        class ImageOverrider(FieldOverrider):
            field_names = [overridden]

        config = registry.register(FakeOrganisation).exclude(overridden)

        with self.assertRaises(registry.Error) as cm:
            config.add_overriders(ImageOverrider)

        self.assertEqual(
            f'The field "{overridden}" cannot be excluded & overridden at the same time.',
            str(cm.exception),
        )

    def test_overriders_excluded02(self):
        "Field excluded + overridden => error (exclude() is called after) ."
        registry = self.bulk_update_registry
        overridden = 'image'

        class ImageOverrider(FieldOverrider):
            field_names = [overridden]

        config = registry.register(FakeOrganisation).add_overriders(ImageOverrider)

        with self.assertRaises(registry.Error) as cm:
            config.exclude(overridden)

        self.assertEqual(
            f'The field "{overridden}" cannot be excluded & overridden at the same time.',
            str(cm.exception),
        )

    def test_regular_fields(self):
        fields = {
            field.name: field
            for field in chain(
                FakeContact._meta.fields,
                FakeContact._meta.many_to_many,
            )
            if field.editable and not field.unique
        }
        self.assertIn('first_name', fields)
        self.assertIn('last_name',  fields)
        self.assertIn('sector',     fields)
        self.assertIn('languages',  fields)  # M2M

        self.assertNotIn('id',              fields)  # Unique
        self.assertNotIn('cremeentity_ptr', fields)  # Unique
        self.assertNotIn('is_user',         fields)  # Not editable

        registry = self.bulk_update_registry
        registry.register(FakeContact)

        self.assertCountEqual(
            fields.values(),
            [*registry.config(FakeContact).regular_fields(exclude_unique=True)],
        )

        registry.config(FakeContact).exclude('sector')
        del fields['sector']
        self.assertCountEqual(
            fields.values(),
            [*registry.config(FakeContact).regular_fields(exclude_unique=True)],
        )

        # ---
        registry.register(FakeActivity)
        get_field = FakeActivity._meta.get_field
        self.assertCountEqual(
            [
                get_field(fname) for fname in
                [
                    # 'cremeentity_ptr',
                    # 'id',
                    'user',
                    'description',

                    # 'title',  Unique
                    'place',
                    'minutes',
                    'start',
                    'end',
                    'type',
                ]
            ],
            registry.config(FakeActivity).regular_fields(),
        )

    def test_regular_fields_include_unique(self):
        get_field = FakeActivity._meta.get_field
        self.assertCountEqual(
            [
                get_field(fname) for fname in
                [
                    # 'cremeentity_ptr',
                    # 'id',
                    'user',
                    'description',

                    'title',
                    'place',
                    'minutes',
                    'start',
                    'end',
                    'type',
                ]
            ],
            self.bulk_update_registry.register(FakeActivity)
                                     .regular_fields(exclude_unique=False),
        )

    def test_custom_fields(self):
        registry = self.bulk_update_registry
        registry.register(FakeContact)

        cf_1 = CustomField.objects.create(
            name='A', content_type=FakeContact, field_type=CustomField.STR,
        )

        self.assertCountEqual(
            [cf_1], [*registry.config(FakeContact).custom_fields],
        )

    def test_custom_fields_deleted(self):
        registry = self.bulk_update_registry
        registry.register(FakeContact)

        create_cf = partial(CustomField.objects.create, content_type=FakeContact)
        cf_1 = create_cf(name='A', field_type=CustomField.STR)
        cf_2 = create_cf(name='C', field_type=CustomField.BOOL)
        cf_3 = create_cf(name='DELETED', field_type=CustomField.INT, is_deleted=True)

        config = registry.config(FakeContact)
        self.assertTrue(config.is_custom_field_updatable(cf_1))
        self.assertTrue(config.is_custom_field_updatable(cf_2))
        self.assertFalse(config.is_custom_field_updatable(cf_3))
        self.assertCountEqual(
            [cf_1, cf_2],
            [*config.custom_fields],
        )

# NB: these 2 tests make some other test cases crash. Example:
#     Problem with entity deletion: (1146, "Table '....creme_core_subcontact' doesn't exist")
# We comment them because entity inheritance is not recommended anyway
# TODO: uncomment them with a true SubContact model ??
#    def test_innerforms_inherit01(self):
#        "Inheritance : registering parent first"
#        bulk_update_registry = self.bulk_update_registry
#        is_bulk_updatable = bulk_update_registry.is_updatable
#        status = bulk_update_registry.status
#
#        class SubContact(Contact):
#            pass
#
#        class _ContactInnerEditForm(BulkDefaultEditForm):
#            pass
#
#        class _SubContactInnerEdit(BulkDefaultEditForm):
#            pass
#
#        bulk_update_registry.register(Contact, exclude=['position'],
#                                      innerforms={'first_name': _ContactInnerEditForm,
#                                                  'last_name':  _ContactInnerEditForm,
#                                                 }
#                                     )
#        bulk_update_registry.register(SubContact, exclude=['position'],
#                                      innerforms={'birthday':  _SubContactInnerEdit,
#                                                  'last_name': _SubContactInnerEdit,
#                                                 }
#                                     )
#
#        self.assertFalse(is_bulk_updatable(model=Contact,    field_name='position'))
#        self.assertFalse(is_bulk_updatable(model=SubContact, field_name='position'))
#        self.assertIsNone(status(Contact).get_form('position'))
#        self.assertIsNone(status(SubContact).get_form('position'))
#
#        # subclass inherits inner forms from base class
#        self.assertTrue(is_bulk_updatable(model=Contact,    field_name='first_name'))
#        self.assertTrue(is_bulk_updatable(model=SubContact, field_name='first_name'))
#        self.assertEqual(_ContactInnerEditForm, status(Contact).get_form('first_name'))
#        self.assertEqual(_ContactInnerEditForm, status(SubContact).get_form('first_name'))
#
#        # base class ignore changes of inner form made for subclass
#        self.assertTrue(is_bulk_updatable(model=Contact, field_name='birthday'))
#        self.assertTrue(is_bulk_updatable(model=SubContact, field_name='birthday'))
#        self.assertIsNone(status(Contact).get_form('birthday'))
#        self.assertEqual(_SubContactInnerEdit, status(SubContact).get_form('birthday'))
#
#        # subclass force bulk form for field
#        self.assertTrue(is_bulk_updatable(model=Contact, field_name='last_name'))
#        self.assertTrue(is_bulk_updatable(model=SubContact, field_name='last_name'))
#        self.assertEqual(_ContactInnerEditForm, status(Contact).get_form('last_name'))
#        self.assertEqual(_SubContactInnerEdit, status(SubContact).get_form('last_name'))
#
#    def test_innerforms_inherit02(self):
#        "Inheritance : registering child first"
#        bulk_update_registry = self.bulk_update_registry
#        is_bulk_updatable = bulk_update_registry.is_updatable
#
#       class SubContact(Contact):
#            pass
#
#        class _ContactInnerEditForm(BulkDefaultEditForm):
#            pass
#
#        class _SubContactInnerEdit(BulkDefaultEditForm):
#            pass
#
#        bulk_update_registry.register(SubContact,
#                                      innerforms={'first_name': _SubContactInnerEdit,
#                                                  'last_name':  _SubContactInnerEdit,
#                                                 }
#                                     )
#        bulk_update_registry.register(Contact, exclude=['position'],
#                                      innerforms={'birthday':  _ContactInnerEditForm,
#                                                  'last_name': _ContactInnerEditForm,
#                                                 }
#                                     )
#
#        self.assertFalse(is_bulk_updatable(model=Contact,    field_name='position'))
#        self.assertFalse(is_bulk_updatable(model=SubContact, field_name='position'))
#
#        status = bulk_update_registry.status
#        self.assertTrue(is_bulk_updatable(model=SubContact, field_name='birthday'))
#        self.assertEqual(_ContactInnerEditForm, status(Contact).get_form('birthday'))
#        self.assertEqual(_ContactInnerEditForm, status(SubContact).get_form('birthday'))
#
#        self.assertIsNone(bulk_update_registry.status(Contact).get_form('first_name'))
#        self.assertEqual(_SubContactInnerEdit, status(SubContact).get_form('first_name'))
#
#        self.assertEqual(_ContactInnerEditForm, status(Contact).get_form('last_name'))
#        self.assertEqual(_SubContactInnerEdit,  status(SubContact).get_form('last_name'))

    def test_inner_uri01(self):
        "Regular field."
        user = self.get_root_user()
        model = FakeContact
        instance = model.objects.create(
            user=user, first_name='Guybrush', last_name='Threepwood',
        )

        registry = self.bulk_update_registry
        fname1 = 'first_name'
        cell1 = entity_cell.EntityCellRegularField.build(model=model, name=fname1)
        self.assertIsNone(registry.inner_uri(instance=instance, cells=[cell1]))

        # ---
        registry.register(FakeContact)
        self.assertEqual(
            self.build_inneredit_uri(instance, fname1),
            registry.inner_uri(instance=instance, cells=[cell1]),
        )

        # ---
        fname2 = 'last_name'
        cell2 = entity_cell.EntityCellRegularField.build(model=model, name=fname2)
        self.assertEqual(
            self.build_inneredit_uri(instance, fname2),
            registry.inner_uri(instance=instance, cells=[cell2]),
        )

        # ---
        self.assertEqual(
            self.build_inneredit_uri(instance, fname1, fname2),
            registry.inner_uri(instance=instance, cells=[cell1, cell2]),
        )

    def test_inner_uri02(self):
        "Not inner-editable field."
        user = self.get_root_user()
        model = FakeContact
        fname = 'first_name'

        registry = self.bulk_update_registry
        registry.register(model).exclude(fname)

        instance = model.objects.create(
            user=user, first_name='Guybrush', last_name='Threepwood',
        )
        cell = entity_cell.EntityCellRegularField.build(model=model, name=fname)
        self.assertIsNone(registry.inner_uri(instance=instance, cells=[cell]))

    def test_inner_uri03(self):
        "Custom field."
        user = self.get_root_user()
        model = FakeContact

        registry = self.bulk_update_registry
        registry.register(model)

        cfield = CustomField.objects.create(
            name='A', content_type=model, field_type=CustomField.STR,
        )

        instance = model.objects.create(
            user=user, first_name='Guybrush', last_name='Threepwood',
        )
        # cell = entity_cell.EntityCellCustomField.build(model=model, customfield_id=cfield.id)
        cell = entity_cell.EntityCellCustomField.build(model=model, name=str(cfield.id))
        self.assertEqual(
            self.build_inneredit_uri(instance, cfield),
            registry.inner_uri(instance=instance, cells=[cell]),
        )

    def test_build_form_class_model_not_registered(self):
        registry = self.bulk_update_registry
        # registry.register(FakeOrganisation) NOPE

        with self.assertRaises(registry.Error) as cm:
            registry.build_form_class(
                model=FakeOrganisation,
                cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
            )

        self.assertEqual(
            'The model "FakeOrganisation" is not registered for inner-edition.',
            str(cm.exception),
        )

        # ---
        registry.register(FakeContact)

        with self.assertRaises(registry.Error):
            registry.build_form_class(
                model=FakeOrganisation,
                cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
            )

    def test_build_form_class_no_cell(self):
        registry = self.bulk_update_registry
        registry.register(FakeOrganisation)

        with self.assertRaises(registry.Error) as cm:
            registry.build_form_class(FakeOrganisation, cells=[])

        self.assertEqual(
            'Empty list of field/custom-field.',
            str(cm.exception),
        )

    def test_build_form_class_not_editable_cell_type(self):
        model = FakeOrganisation
        registry = self.bulk_update_registry
        registry.register(model)

        class MyEntityCellVolatile(EntityCellVolatile):
            title = 'Test volatile'

        with self.assertRaises(registry.Error) as cm:
            registry.build_form_class(
                model=model, cells=[MyEntityCellVolatile(model=model)],
            )

        self.assertEqual(
            f'The cell "{MyEntityCellVolatile.title}" is not editable',
            str(cm.exception),
        )

    def test_build_form_class_1_regular_field(self):
        registry = self.bulk_update_registry
        registry.register(FakeOrganisation)

        field_name = 'name'
        form_cls = registry.build_form_class(
            FakeOrganisation,
            [EntityCellRegularField.build(FakeOrganisation, field_name)],
        )
        self.assertIsNotNone(form_cls)
        self.assertIsSubclass(form_cls, CremeModelForm)

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        # GET
        with self.assertNoException():
            form1 = form_cls(user=user, instance=orga)

        fields1 = form1.fields
        self.assertCountEqual([field_name], fields1.keys())
        self.assertIsInstance(fields1[field_name], form_fields.CharField)
        self.assertDictEqual({field_name: orga.name}, form1.initial)

        # POST
        name = f'{orga.name} (edited)'

        with self.assertNoException():
            form2 = form_cls(user=user, instance=orga, data={field_name: name})

        self.assertFalse(form2.errors)

        form2.save()
        self.assertEqual(name, self.refresh(orga).name)

    def test_build_form_class_2_regular_fields(self):
        registry = self.bulk_update_registry
        registry.register(FakeOrganisation)

        field_name1 = 'name'
        field_name2 = 'email'
        form_cls = registry.build_form_class(
            model=FakeOrganisation,
            cells=[
                EntityCellRegularField.build(FakeOrganisation, field_name1),
                EntityCellRegularField.build(FakeOrganisation, field_name2),
            ],
        )

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        # GET
        with self.assertNoException():
            form1 = form_cls(user=user, instance=orga)

        fields1 = form1.fields
        self.assertListEqual([field_name1, field_name2], [*fields1.keys()])
        self.assertIsInstance(fields1[field_name1], form_fields.CharField)
        self.assertIsInstance(fields1[field_name2], form_fields.EmailField)
        self.assertDictEqual(
            {field_name1: orga.name, field_name2: ''},
            form1.initial,
        )

        # POST (error)
        name = f'{orga.name} (edited)'

        with self.assertNoException():
            form2 = form_cls(
                user=user, instance=orga,
                data={field_name1: name, field_name2: 'invalid_email'},
            )

        self.assertFormInstanceErrors(
            form2,
            (field_name2, _('Enter a valid email address.')),
        )

        # POST (OK)
        email = 'contact@nrev.jp'

        with self.assertNoException():
            form3 = form_cls(
                user=user, instance=orga,
                data={field_name1: name, field_name2: email},
            )

        self.assertFalse(form3.errors)

        form3.save()
        orga = self.refresh(orga)
        self.assertEqual(name,  orga.name)
        self.assertEqual(email, orga.email)

    def test_build_form_class_not_editable_field(self):
        registry = self.bulk_update_registry
        registry.register(FakeOrganisation)

        def assertFieldRejected(field_name):
            with self.assertRaises(registry.Error) as cm:
                registry.build_form_class(
                    FakeOrganisation,
                    [EntityCellRegularField.build(FakeOrganisation, field_name)],
                )

            self.assertEqual(
                _(
                    'The field «{}» is not editable (it may have been hidden).'
                ).format(FakeOrganisation._meta.get_field(field_name).verbose_name),
                str(cm.exception),
            )

        # assertFieldRejected('id')  # TODO: test not viewable but editable?
        # assertFieldRejected('cremeentity_ptr')
        assertFieldRejected('created')
        assertFieldRejected('address')

    def test_build_form_class_excluded_field(self):
        field_name = 'email'
        registry = self.bulk_update_registry
        registry.register(FakeOrganisation).exclude(field_name)

        with self.assertRaises(registry.Error) as cm:
            registry.build_form_class(
                FakeOrganisation,
                [EntityCellRegularField.build(FakeOrganisation, field_name)],
            )

        self.assertEqual(
            _(
                'The field «{}» is not editable (it may have been hidden).'
            ).format(_('Email address')),
            str(cm.exception),
        )

    def test_build_form_class_hidden_field(self):
        model = FakeOrganisation
        field_name = 'capital'
        registry = self.bulk_update_registry
        registry.register(model)

        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[(field_name, {FieldsConfig.HIDDEN: True})],
        )

        with self.assertRaises(registry.Error) as cm:
            registry.build_form_class(
                model,
                [EntityCellRegularField.build(model, field_name)],
            )

        self.assertEqual(
            _(
                'The field «{}» is not editable (it may have been hidden).'
            ).format(_('{} [hidden]').format(_('Capital'))),
            str(cm.exception),
        )

    def test_build_form_class_unique_regular_field(self):
        "<FakeActivity.title> is unique."
        registry = self.bulk_update_registry
        registry.register(FakeActivity)

        field_name = 'title'
        form_cls = registry.build_form_class(
            FakeActivity,
            [EntityCellRegularField.build(FakeActivity, field_name)],
        )
        user = self.get_root_user()
        atype = FakeActivityType.objects.first()
        create_activity = partial(FakeActivity.objects.create, user=user, type=atype)
        activity1 = create_activity(title='Meeting #1')
        activity2 = create_activity(title='Meeting #2')

        # POST (error)
        with self.assertNoException():
            form2 = form_cls(
                user=user, instance=activity1,
                data={field_name: activity2.title},
            )

        self.assertFormInstanceErrors(
            form2,
            (
                field_name,
                _('%(model_name)s with this %(field_label)s already exists.') % {
                    'model_name': 'Test Activity',
                    'field_label': _('Title'),
                },
            ),
        )

        # POST (OK)
        title = f'{activity1.title} (edited)'

        with self.assertNoException():
            form3 = form_cls(
                user=user, instance=activity1,
                data={field_name: title},
            )

        self.assertFalse(form3.errors)

        form3.save()
        self.assertEqual(title, self.refresh(activity1).title)

    def test_build_form_class_1_custom_field(self):
        registry = self.bulk_update_registry
        registry.register(FakeOrganisation)

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        cfield = CustomField.objects.create(
            content_type=orga.entity_type, name='Ammo', field_type=CustomField.INT,
        )
        value = 1000
        cfield.value_class.objects.create(custom_field=cfield, entity=orga, value=value)

        form_cls = registry.build_form_class(
            FakeOrganisation, cells=[EntityCellCustomField(cfield)],
        )
        self.assertIsNotNone(form_cls)

        # GET
        with self.assertNoException():
            form1 = form_cls(user=user, instance=orga)

        fields1 = form1.fields
        formfield_id = f'custom_field-{cfield.id}'
        self.assertCountEqual([formfield_id], fields1.keys())

        formfield = fields1[formfield_id]
        self.assertIsInstance(formfield, form_fields.IntegerField)
        self.assertEqual(value, formfield.initial)

        # POST
        value += 358

        with self.assertNoException():
            form2 = form_cls(user=user, instance=orga, data={formfield_id: value})

        self.assertFalse(form2.errors)

        form2.save()
        self.assertEqual(
            value,
            cfield.value_class.objects.get(custom_field=cfield, entity=orga).value,
        )

    def test_build_form_class_deleted_custom_field(self):
        registry = self.bulk_update_registry
        registry.register(FakeOrganisation)

        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='NERV')
        cfield = CustomField.objects.create(
            content_type=orga.entity_type, name='Ammo', field_type=CustomField.INT,
            is_deleted=True,
        )

        with self.assertRaises(registry.Error) as cm:
            registry.build_form_class(
                FakeOrganisation, cells=[EntityCellCustomField(cfield)],
            )

        self.assertEqual(
            f'The field "{cfield.name}" is deleted',
            str(cm.exception),
        )

    def test_build_form_class_overriders01(self):
        registry = self.bulk_update_registry
        overridden1 = 'image'
        overridden2 = 'capital'

        a_lot_str = 'A lot'
        a_lot = 100000

        passed_instances = []

        class ImageOverrider(FieldOverrider):
            field_names = [overridden1]

            def formfield(self, instances, user, **kwargs):
                passed_instances.append(instances)

                return form_fields.IntegerField(required=False)

            def post_clean_instance(this, *, instance, value, form):
                instance.image_id = value

        class CapitalOverrider(FieldOverrider):
            field_names = [overridden2]

            def formfield(self, instances, user, **kwargs):
                # TODO: always required = False ????
                return form_fields.CharField(required=False, initial=instances[0].capital)

            def post_clean_instance(this, *, instance, value, form):
                if value == a_lot_str:
                    instance.capital = a_lot

        class AddressFormOverrider(FieldOverrider):
            field_names = ['address']

        registry.register(FakeOrganisation).add_overriders(
            ImageOverrider, CapitalOverrider, AddressFormOverrider,
        )

        field_name = 'name'
        form_cls = registry.build_form_class(
            model=FakeOrganisation,
            cells=[
                EntityCellRegularField.build(FakeOrganisation, field_name),
                EntityCellRegularField.build(FakeOrganisation, overridden1),
                EntityCellRegularField.build(FakeOrganisation, overridden2),
            ],
        )

        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='NERV', capital=236)

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='Img#1')
        create_img(name='Img#2')

        # GET ---
        with self.assertNoException():
            form1 = form_cls(user=user, instance=orga1)

        fields1 = form1.fields
        form_field_name1 = f'override-{overridden1}'
        form_field_name2 = f'override-{overridden2}'
        self.assertListEqual(
            [field_name, form_field_name1, form_field_name2],
            [*fields1.keys()],
        )
        self.assertIsInstance(fields1[field_name], form_fields.CharField)

        ov_field1 = fields1[form_field_name1]
        self.assertIsInstance(ov_field1, form_fields.IntegerField)
        self.assertIsNone(ov_field1.initial)

        ov_field2 = fields1[form_field_name2]
        self.assertIsInstance(ov_field2, form_fields.CharField)
        self.assertEqual(orga1.capital, ov_field2.initial)

        self.assertEqual(1, len(passed_instances))
        self.assertListEqual([orga1], passed_instances[0])
        passed_instances.clear()

        # POST (error + instances) ---
        name = f'{orga1.name} (edited)'
        orga2 = create_orga(name='Seele')

        with self.assertNoException():
            form2 = form_cls(
                user=user, instance=orga1, instances=[orga1, orga2],
                data={
                    field_name: name,
                    form_field_name1: 'not_an_int',
                },
            )

        self.assertFormInstanceErrors(
            form2,
            (form_field_name1, _('Enter a whole number.')),
        )

        self.assertEqual(1, len(passed_instances))
        self.assertListEqual([orga1, orga2], passed_instances[0])
        passed_instances.clear()

        # POST (OK) ---
        with self.assertNoException():
            form3 = form_cls(
                user=user, instance=orga1,
                data={
                    field_name: name,
                    form_field_name1: img1.id,
                    form_field_name2: a_lot_str,
                },
            )

        self.assertFalse(form3.errors)

        form3.save()
        orga1 = self.refresh(orga1)
        self.assertEqual(img1.id, orga1.image_id)
        self.assertEqual(a_lot,   orga1.capital)

    def test_build_form_class_overriders02(self):
        "Override several fields at once."
        registry = self.bulk_update_registry
        overridden1 = 'url_site'
        overridden2 = 'email'

        class DetailsOverrider(FieldOverrider):
            field_names = [overridden1, overridden2]

            def formfield(self, instances, user, **kwargs):
                return form_fields.CharField(required=False)

            def post_clean_instance(this, *, instance, value, form):
                instance.url_site = f'https://{value}'
                instance.email = f'contact@{value}'

        registry.register(FakeOrganisation).add_overriders(DetailsOverrider)

        field_name = 'name'
        form_cls = registry.build_form_class(
            model=FakeOrganisation,
            cells=[
                EntityCellRegularField.build(FakeOrganisation, field_name),
                EntityCellRegularField.build(FakeOrganisation, overridden1),
                # A 2nd field of the same group is requested
                EntityCellRegularField.build(FakeOrganisation, overridden2),
            ],
        )

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='NERV', capital=236)

        # GET
        with self.assertNoException():
            form1 = form_cls(user=user, instance=orga)

        fields1 = form1.fields
        form_field_name = f'override-{overridden1}'
        self.assertListEqual([field_name, form_field_name], [*fields1.keys()])

        # POST (OK)
        with self.assertNoException():
            form3 = form_cls(
                user=user, instance=orga,
                data={
                    field_name: orga.name.title(),
                    form_field_name: 'nerv.jp',
                },
            )

        self.assertFalse(form3.errors)

        form3.save()
        orga = self.refresh(orga)
        self.assertEqual('https://nerv.jp', orga.url_site)
        self.assertEqual('contact@nerv.jp', orga.email)

    def test_build_form_class_overriders03(self):
        "Errors are wrapped with good field name."
        registry = self.bulk_update_registry
        overridden = 'email'
        error_msg = 'Nope'

        class EmailOverrider(FieldOverrider):
            field_names = [overridden]

            def formfield(self, instances, user, **kwargs):
                return form_fields.CharField(required=False)

            def post_clean_instance(this, *, instance, value, form):
                raise ValidationError(error_msg)

        registry.register(FakeOrganisation).add_overriders(EmailOverrider)

        field_name = 'name'
        form_cls = registry.build_form_class(
            model=FakeOrganisation,
            cells=[
                EntityCellRegularField.build(FakeOrganisation, field_name),
                EntityCellRegularField.build(FakeOrganisation, overridden),
            ],
        )

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='NERV', capital=236)

        form_field_name = f'override-{overridden}'

        with self.assertNoException():
            form = form_cls(
                user=user, instance=orga,
                data={
                    field_name: orga.name.title(),
                    form_field_name: 'nerv.jp',
                },
            )

        self.assertFormInstanceErrors(
            form, (form_field_name, error_msg),
        )

    def test_build_form_class_overriders__post_save_instance(self):
        registry = self.bulk_update_registry
        overridden = 'languages'

        class LanguageField(form_fields.CharField):
            def clean(this, value):
                lname = super().clean(value=value)

                # NB: a real field would check errors better...
                return [Language.objects.get(name=lname)]

        class LanguagesOverrider(FieldOverrider):
            field_names = [overridden]

            def formfield(self, instances, user, **kwargs):
                return LanguageField(required=False)

            def post_save_instance(self, *, instance, value, form):
                instance.languages.set(value)

        registry.register(FakeContact).add_overriders(LanguagesOverrider)

        form_cls = registry.build_form_class(
            model=FakeContact,
            cells=[EntityCellRegularField.build(FakeContact, overridden)],
        )

        user = self.get_root_user()
        contact = FakeContact.objects.create(
            user=user, first_name='Asa', last_name='Asada',
        )
        klingon = Language.objects.create(name='Klingon')

        # GET ---
        with self.assertNoException():
            form1 = form_cls(user=user, instance=contact)

        fields1 = form1.fields
        form_field_name = f'override-{overridden}'
        self.assertListEqual([form_field_name], [*fields1.keys()])

        # POST ---
        with self.assertNoException():
            form2 = form_cls(
                user=user, instance=contact,
                data={form_field_name: klingon.name},
            )

        self.assertFalse(form2.errors)

        form2.save()
        self.assertListEqual([klingon], [*self.refresh(contact).languages.all()])

    def test_build_form_class_fk(self):
        model = FakeContact
        registry = self.bulk_update_registry
        registry.register(model)

        field_name = 'civility'
        self.assertFalse(model._meta.get_field(field_name).remote_field.limit_choices_to)

        form_cls = registry.build_form_class(
            model=model, cells=[EntityCellRegularField.build(model, field_name)],
        )
        self.assertIsNotNone(form_cls)
        self.assertIsSubclass(form_cls, CremeModelForm)

        user = self.get_root_user()
        civ1, civ2 = FakeCivility.objects.all()[:2]
        contact = FakeContact.objects.create(
            user=user, first_name='Asa', last_name='Asada', civility=civ1,
        )

        # GET ---
        with self.assertNoException():
            form1 = form_cls(user=user, instance=contact)

        fields1 = form1.fields
        self.assertCountEqual([field_name], fields1.keys())
        self.assertIsInstance(fields1[field_name], CreatorEnumerableModelChoiceField)
        self.assertDictEqual({field_name: civ1.id}, form1.initial)

        # POST ---
        with self.assertNoException():
            form2 = form_cls(user=user, instance=contact, data={field_name: civ2.id})

        self.assertFalse(form2.errors)

        form2.save()
        self.assertEqual(civ2, getattr(self.refresh(contact), field_name))

    @override_settings(FORM_ENUMERABLE_LIMIT=100)
    def test_build_form_class_fk_limit_choices(self):
        "limit_choices_to: callable yielding Q."
        user = self.get_root_user()

        model = FakeContact
        registry = self.bulk_update_registry
        registry.register(model)

        field_name = 'sector'
        # NB: limit_choices_to=lambda: ~Q(title='[INVALID]')
        self.assertTrue(callable(model._meta.get_field(field_name).remote_field.limit_choices_to))

        form_cls = registry.build_form_class(
            model=model, cells=[EntityCellRegularField.build(model, field_name)],
        )
        self.assertIsNotNone(form_cls)

        contact = FakeContact.objects.create(first_name='A', last_name='B', user=user)

        with self.assertNoException():
            form_field = form_cls(user=user, instance=contact).fields[field_name]
            choices = [(c.value, c.label) for c in form_field.choices]

        expected = [
            ('', form_field.empty_label),
            *FakeSector.objects.exclude(title='[INVALID]').values_list('pk', 'title'),
        ]

        self.assertEqual(expected, choices)

    def test_build_form_class_fk_sub_field(self):
        model = FakeContact
        registry = self.bulk_update_registry
        registry.register(model)

        with self.assertRaises(registry.Error) as cm:
            registry.build_form_class(
                model=model, cells=[EntityCellRegularField.build(model, 'sector__title')],
            )

        self.assertEqual(
            _(
                'The field «{}» is not editable (it seems to be a sub-field).'
            ).format(_('Line of business') + ' - ' + _('Title')),
            str(cm.exception),
        )

        # ---
        with self.assertRaises(registry.Error):
            registry.build_form_class(
                model=model, cells=[EntityCellRegularField.build(model, 'address__city')],
            )
