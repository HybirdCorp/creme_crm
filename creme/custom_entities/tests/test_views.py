from functools import partial
from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.forms import CharField
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.bricks import PropertiesBrick
from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegularField,
)
from creme.creme_core.creme_jobs import (
    batch_process_type,
    mass_import_type,
    temp_files_cleaner_type,
)
from creme.creme_core.gui.bricks import Brick
from creme.creme_core.gui.custom_form import (
    CustomFormDescriptor,
    FieldGroup,
    FieldGroupList,
)
from creme.creme_core.models import (
    CustomEntityType,
    CustomField,
    CustomFormConfigItem,
    EntityJobResult,
    FakeContact,
    HeaderFilter,
    Job,
)
from creme.creme_core.tests import fake_custom_forms
from creme.creme_core.tests.views.base import (
    BrickTestCaseMixin,
    MassImportBaseTestCaseMixin,
)

from .. import custom_forms
from .base import CustomEntitiesBaseTestCase


class CustomEntityViewsTestCase(BrickTestCaseMixin,
                                MassImportBaseTestCaseMixin,
                                CustomEntitiesBaseTestCase):
    def test_detail(self):
        user = self.login_as_root_and_get()
        type_name = 'Training'
        ce_type = self._enable_type(id=1, name=type_name)
        entity = ce_type.entity_model.objects.create(user=user, name='Training 01')

        url = entity.get_absolute_url()
        self.assertEqual(
            reverse('custom_entities__view_custom_entity', args=(1, entity.id,)),
            url,
        )

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/view_entity.html')

        # -----
        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, brick=PropertiesBrick)
        self.get_brick_node(tree, brick=MODELBRICK_ID)

        # TODO: test icon
        bar_node = self.get_brick_node(tree, brick=Brick.GENERIC_HAT_BRICK_ID)
        # title_node = self.get_html_node_or_fail(bar_node, ".//div[@class='bar-title']/h1")
        title_node = self.get_html_node_or_fail(bar_node, ".//h1[@class='bar-title']")
        self.assertEqual(f'{type_name} : {entity.name}', title_node.text.strip())

    def test_detail__other_type(self):
        user = self.login_as_root_and_get()
        type_name = 'Store'
        ce_type = self._enable_type(id=2, name=type_name)

        entity = ce_type.entity_model.objects.create(user=user, name='Store 01')

        url = entity.get_absolute_url()
        self.assertEqual(
            reverse('custom_entities__view_custom_entity', args=(2, entity.id,)),
            url,
        )

        response = self.assertGET200(url)

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=Brick.GENERIC_HAT_BRICK_ID,
        )
        # title_node = self.get_html_node_or_fail(brick_node, ".//div[@class='bar-title']/h1")
        title_node = self.get_html_node_or_fail(brick_node, ".//h1[@class='bar-title']")
        self.assertEqual(f'{type_name} : {entity.name}', title_node.text.strip())

    def test_detail__disabled_type(self):
        user = self.login_as_root_and_get()
        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        self.assertFalse(ce_type.enabled)

        entity = ce_type.entity_model.objects.create(user=user, name='Store 01')
        self.assertGET404(entity.get_absolute_url())

    def test_creation(self):
        descriptor = custom_forms.creation_descriptors.get(1)
        self.assertIsInstance(descriptor, CustomFormDescriptor)
        self.assertEqual('custom_entities-creation1', descriptor.id)
        self.assertEqual(_('Creation form'),          descriptor.verbose_name)

        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=descriptor.id, role=None, superuser=False,
        )

        user = self.login_as_root_and_get()
        ce_type1 = self._enable_type(id=1, name='Shop')
        ce_type2 = self._enable_type(id=2, name='Warehouse')

        model = ce_type1.entity_model

        create_cf = partial(CustomField.objects.create, content_type=model)
        cf1 = create_cf(field_type=CustomField.STR, name='Punchline')
        cf2 = create_cf(field_type=CustomField.INT, name='Size (m2)')

        cfci.store_groups(
            FieldGroupList(
                model=model,
                cell_registry=descriptor.build_cell_registry(),
                groups=[
                    FieldGroup(
                        name='My fields',
                        cells=[
                            *(
                                EntityCellRegularField.build(model=model, name=name)
                                for name in ('user', 'name', 'description')
                            ),
                            EntityCellCustomField(cf1),
                            # EntityCellCustomField(cf2),  # NOPE
                        ],
                    ),
                ],
            )
        )
        cfci.save()

        # GET ---
        url = ce_type1.entity_model.get_create_absolute_url()
        self.assertEqual(
            reverse('custom_entities__create_custom_entity', args=(1,)),
            url,
        )
        self.assertEqual(
            reverse('custom_entities__create_custom_entity', args=(2,)),
            ce_type2.entity_model.get_create_absolute_url(),
        )

        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add.html')

        self.assertEqual(
            _('Create a «{custom_model}»').format(custom_model=ce_type1.name),
            response1.context.get('title'),
        )
        self.assertEqual(_('Save the entity'), response1.context.get('submit_label'))

        with self.assertNoException():
            name_f = response1.context['form'].fields['name']
        self.assertIsInstance(name_f, CharField)

        # POST ---
        name = 'Acme'
        description = 'Sells stuffs'
        punchline = 'Best stuffs in the universe!'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user': user.id,
                'name': name,
                'description': description,

                f'custom_field-{cf1.id}': punchline,
                f'custom_field-{cf2.id}': 30,
            },
        ))

        instance = self.get_object_or_fail(ce_type1.entity_model, user=user, name=name)
        self.assertEqual(description, instance.description)
        self.assertEqual(
            punchline,
            cf1.value_class.objects.get(custom_field=cf1, entity=instance).value,
        )
        # self.assertEqual(
        #     30, cf2.value_class.objects.get(custom_field=cf2, entity=instance).value,
        # )
        self.assertFalse(cf2.value_class.objects.filter(custom_field=cf2, entity=instance))

    def test_creation__deleted_type(self):
        self.login_as_root()
        ce_type = self._enable_type(id=1, name='Shop', deleted=True)

        response = self.client.get(ce_type.entity_model.get_create_absolute_url())
        self.assertContains(
            response,
            _('You are not allowed to create: {}').format(
                _('{custom_model} [deleted]').format(custom_model=ce_type.name)
            ),
            status_code=403,
            html=True,
        )

    def test_edition(self):
        descriptor = custom_forms.edition_descriptors.get(1)
        self.assertIsInstance(descriptor, CustomFormDescriptor)
        self.assertEqual('custom_entities-edition1', descriptor.id)
        self.assertEqual(_('Edition form'),          descriptor.verbose_name)

        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=descriptor.id, role=None, superuser=False,
        )

        ce_type = self._enable_type(id=1, name='Shop')
        model = ce_type.entity_model

        create_cf = partial(CustomField.objects.create, content_type=model)
        cf1 = create_cf(field_type=CustomField.STR, name='Punchline')
        cf2 = create_cf(field_type=CustomField.INT, name='Size (m2)')

        cfci.store_groups(
            FieldGroupList(
                model=model,
                cell_registry=descriptor.build_cell_registry(),
                groups=[
                    FieldGroup(
                        name='My fields',
                        cells=[
                            *(
                                EntityCellRegularField.build(model=model, name=name)
                                for name in ('user', 'name', 'description')
                            ),
                            EntityCellCustomField(cf1),
                            # EntityCellCustomField(cf2),  # NOPE
                        ],
                    ),
                ],
            )
        )
        cfci.save()

        user = self.login_as_root_and_get()
        entity = ce_type.entity_model.objects.create(user=user, name='Acme')

        url = entity.get_edit_absolute_url()
        self.assertEqual(
            reverse('custom_entities__edit_custom_entity', args=(1, entity.id,)),
            url,
        )

        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit.html')

        self.assertEqual(
            _('Edit «{object}»').format(object=entity.name),
            response1.context.get('title'),
        )
        self.assertEqual(_('Save the modifications'), response1.context.get('submit_label'))

        with self.assertNoException():
            form = response1.context['form']
        self.assertEqual(entity.name, form.initial.get('name'))

        # ---
        name = 'Acme inc'
        description = 'Sells stuffs'
        punchline = 'Best stuffs in the universe!'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user': user.id,
                'name': name,
                'description': description,

                f'custom_field-{cf1.id}': punchline,
                f'custom_field-{cf2.id}': 30,
            },
        ))

        entity = self.refresh(entity)
        self.assertEqual(name,        entity.name)
        self.assertEqual(description, entity.description)

        self.assertEqual(
            punchline,
            cf1.value_class.objects.get(custom_field=cf1, entity=entity).value,
        )
        # self.assertEqual(
        #     30, cf2.value_class.objects.get(custom_field=cf2, entity=entity).value,
        # )
        self.assertFalse(cf2.value_class.objects.filter(custom_field=cf2, entity=entity))

    def test_edition__deleted_type(self):
        user = self.login_as_root_and_get()
        ce_type = self._enable_type(id=1, name='Shop', deleted=True)
        entity = ce_type.entity_model.objects.create(user=user, name='Acme')
        self.assertGET403(entity.get_edit_absolute_url())

    def test_list(self):
        user = self.login_as_root_and_get()

        plural_name = 'Shops'
        ce_type = self._enable_type(id=1, name='Shop', plural_name=plural_name)
        model = ce_type.entity_model

        HeaderFilter.objects.proxy(
            id='creme_core-hf_custom_entity_1',
            name='Shop view', model=model, is_custom=False,
            cells=[(EntityCellRegularField, 'name')],
        ).get_or_create()

        create_entity = partial(model.objects.create, user=user)
        entity1 = create_entity(name='Happy fruits & vegetables')
        entity2 = create_entity(name='Mega bicycles')

        url = model.get_lv_absolute_url()
        self.assertEqual(reverse('custom_entities__list_custom_entities', args=(1,)), url)
        context = self.assertGET200(url).context

        with self.assertNoException():
            page  = context['page_obj']
            title = context['list_title']

        self.assertEqual(2, page.paginator.count)

        entities_set = {*page.object_list}
        self.assertIn(entity1, entities_set)
        self.assertIn(entity2, entities_set)

        self.assertEqual(_('List of {models}').format(models=plural_name), title)

    def test_deletion(self):
        user = self.login_as_root_and_get()
        ce_type = self._enable_type(id=1, name='Shop')
        entity = ce_type.entity_model.objects.create(user=user, name='Acme')

        url = reverse('creme_core__delete_entity', args=(entity.id,))
        self.assertGET405(url)
        self.assertRedirects(self.client.post(url), entity.get_lv_absolute_url())

        with self.assertNoException():
            entity = self.refresh(entity)

        self.assertIs(entity.is_deleted, True)

    # TODO: test custom fields?
    def test_cloning(self):
        user = self.login_as_root_and_get()
        ce_type = self._enable_type(id=1, name='Shop')
        model = ce_type.entity_model
        entity = model.objects.create(user=user, name='Acme')
        self.assertEqual(1, model.objects.count())

        self.assertPOST200(
            reverse('creme_core__clone_entity'),
            data={'id': entity.id}, follow=True,
        )
        instances = model.objects.order_by('id')
        self.assertEqual(2, len(instances))
        self.assertEqual(entity.name, instances[1].name)

    def test_cloning__deleted_type(self):
        user = self.login_as_root_and_get()
        ce_type = self._enable_type(id=1, name='Shop', deleted=True)
        model = ce_type.entity_model
        entity = model.objects.create(user=user, name='Acme')
        self.assertPOST403(
            reverse('creme_core__clone_entity'),
            data={'id': entity.id}, follow=True,
        )

    def test_inner_edition(self):
        user = self.login_as_root_and_get()

        ce_type = self._enable_type(id=1, name='Shop', plural_name='Shops')
        instance = ce_type.entity_model.objects.create(user=user, name='Toyzzz')

        field_name = 'name'
        url = self.build_inneredit_uri(instance, field_name)
        self.assertGET200(url)

        # POST ---
        value = 'Super Toyz'
        self.assertNoFormError(self.client.post(url, data={field_name: value}))
        self.assertEqual(value, self.refresh(instance).name)

    # TODO: test custom fields?
    def test_mass_import(self):
        user = self.login_as_root_and_get()

        # ---
        contact_doc = self._build_csv_doc(lines=[['Rei', 'Ayanami']], user=user)
        contact_response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                'step': 1,
                'document': contact_doc.id,
                'user': user.id,
                # 'has_header': ...,

                'first_name_colselect': 1,
                'last_name_colselect': 2,

                'civility_colselect': 0,
                'description_colselect': 0,
                'phone_colselect': 0,
                'mobile_colselect': 0,
                'position_colselect': 0,
                'sector_colselect': 0,
                'email_colselect': 0,
                'url_site_colselect': 0,
                'birthday_colselect': 0,
                'image_colselect': 0,

                'is_a_nerd_colselect': 0,
                'loves_comics_colselect': 0,
                'languages_colselect': 0,
                'preferred_countries_colselect': 0,

                # 'property_types',
                # 'fixed_relations',
                # 'dyn_relations',

                'address_value_colselect': 0,
                'address_zipcode_colselect': 0,
                'address_city_colselect': 0,
                'address_department_colselect': 0,
                'address_country_colselect': 0,
            },
        )
        self.assertNoFormError(contact_response)
        contact_job = self._get_job(contact_response)

        # ----

        ce_type = self._enable_type(id=1, name='Shop', plural_name='Shops')
        model = ce_type.entity_model
        lines = [
            ['Video g@mezzz',   'For hardcore gamers & n00b too'],
            ['Pencils palooza', 'For artists'],
        ]

        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(model)
        response1 = self.assertGET200(url)
        self.assertEqual(
            _('Import «{model}» from data file').format(model=ce_type.plural_name),
            response1.context.get('title'),
        )

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                'step':     0,
                'document': doc.id,
                # has_header
            },
        ))

        # ---
        response3 = self.client.post(
            url,
            follow=True,
            data={
                'step': 1,
                'document': doc.id,
                'user': user.id,
                # 'has_header': ...,

                'name_colselect': 1,
                'description_colselect': 2,

                # 'property_types',
                # 'fixed_relations',
                # 'dyn_relations',
            },
        )
        self.assertNoFormError(response3)

        job = self._execute_job(response3)
        self.assertListEqual(
            [_('Import «{model}» from {doc}').format(model=ce_type.name, doc=doc)],
            mass_import_type.get_description(job),
        )

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))

        shop1 = model.objects.get(name=lines[0][0])
        self.assertEqual(lines[0][1], shop1.description)

        shop2 = model.objects.get(name=lines[1][0])
        self.assertEqual(lines[1][1], shop2.description)

        # Type deletion ---
        shop1.delete()
        shop2.delete()

        ce_type.deleted = True
        ce_type.save()

        self.assertPOST200(
            reverse('creme_config__delete_custom_entity_type'),
            data={'id': ce_type.id},
        )
        self.assertDoesNotExist(job)
        self.assertDoesNotExist(results[0])

        self.assertStillExists(contact_job)
        self.get_object_or_fail(Job, type_id=temp_files_cleaner_type.id)

    def test_batch_process(self):
        user = self.login_as_root_and_get()

        ce_type = self._enable_type(id=1, name='Shop', plural_name='Shops')
        model = ce_type.entity_model

        create_entity = partial(model.objects.create, user=user)
        entity1 = create_entity(name='Happy fruits')
        entity2 = create_entity(name='Mega bicycles')

        get_ct = ContentType.objects.get_for_model
        contact_response = self.client.post(
            reverse('creme_core__batch_process', args=(get_ct(FakeContact).id,)),
            follow=True,
            data={
                'actions': json_dump([{
                    'name': 'last_name',
                    'operator': 'upper',
                    'value': '',
                }]),
            },
        )
        self.assertNoFormError(contact_response)
        contact_job = self._get_job(contact_response)

        url = reverse('creme_core__batch_process', args=(get_ct(model).id,))
        self.assertGET200(url)

        response2 = self.client.post(
            url,
            follow=True,
            data={
                'actions': json_dump([{
                    'name': 'name',
                    'operator': 'upper',
                    'value': '',
                }]),
            },
        )
        self.assertNoFormError(response2)

        job = self._get_job(response2)
        batch_process_type.execute(job)
        self.assertEqual('HAPPY FRUITS',  self.refresh(entity1).name)
        self.assertEqual('MEGA BICYCLES', self.refresh(entity2).name)

        # Type deletion ---
        entity1.delete()
        entity2.delete()

        ce_type.deleted = True
        ce_type.save()

        self.assertPOST200(
            reverse('creme_config__delete_custom_entity_type'),
            data={'id': ce_type.id},
        )
        self.assertDoesNotExist(job)
        self.assertFalse(EntityJobResult.objects.filter(job=job))

        self.assertStillExists(contact_job)
        self.get_object_or_fail(Job, type_id=temp_files_cleaner_type.id)

    def test_custom_form_config(self):
        self.login_as_root()

        ce_type = self._enable_type(id=1, name='Shop', plural_name='Shops')
        descriptor = custom_forms.creation_descriptors.get(ce_type.id)
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=custom_forms.creation_descriptors.get(ce_type.id).id,
            role=None, superuser=False,
        )
        self.assertGET200(
            reverse('creme_config__create_custom_form', args=(descriptor.id,))
        )
        self.assertGET200(
            reverse('creme_config__add_custom_form_group', args=(cfci.id,))
        )
        self.assertGET200(
            reverse('creme_config__edit_custom_form_group', args=(cfci.id, 0))
        )

    def test_custom_form_config__disabled_type(self):
        self.login_as_root()

        # ce_type = self._enable_type(id=1, ...)
        descriptor = custom_forms.creation_descriptors.get(1)
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=descriptor.id, role=None, superuser=False,
        )
        self.assertGET409(
            reverse('creme_config__create_custom_form', args=(descriptor.id,))
        )
        self.assertGET409(
            reverse('creme_config__add_custom_form_group', args=(cfci.id,))
        )
        self.assertGET409(
            reverse('creme_config__edit_custom_form_group', args=(cfci.id, 0))
        )

    def test_custom_form_config__deletion(self):
        """Default Custom forms are reset, other are deleted."""
        self.login_as_root()
        role = self.create_role()

        ce_type = self._enable_type(id=1, name='Shop', deleted=True)
        model = ce_type.entity_model

        # Should be reset ---
        creation_descriptor = custom_forms.creation_descriptors.get(ce_type.id)
        creation_cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=creation_descriptor.id, role=None, superuser=False,
        )
        creation_groups = creation_cfci.json_groups  # we capture the initial data...
        creation_cfci.store_groups(
            FieldGroupList(
                model=model,
                cell_registry=creation_descriptor.build_cell_registry(),
                groups=[FieldGroup(
                    name='My creation fields',
                    cells=[
                        EntityCellRegularField.build(model=model, name=name)
                        for name in ('user', 'name')
                    ],
                )],
            )
        )
        creation_cfci.save()  # ...then save different new data

        edition_descriptor = custom_forms.edition_descriptors.get(ce_type.id)
        edition_cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=edition_descriptor.id, role=None, superuser=False,
        )
        edition_groups = edition_cfci.json_groups
        edition_cfci.store_groups(
            FieldGroupList(
                model=model,
                cell_registry=creation_descriptor.build_cell_registry(),
                groups=[FieldGroup(
                    name='My edition fields',
                    cells=[
                        EntityCellRegularField.build(model=model, name=name)
                        for name in ('user', 'description', 'name')
                    ],
                )],
            )
        )
        edition_cfci.save()

        # Should be deleted ---
        create_cfci = CustomFormConfigItem.objects.create_if_needed
        creation_cfci_4_super = create_cfci(descriptor=creation_descriptor, role='superuser')
        creation_cfci_4_role  = create_cfci(descriptor=creation_descriptor, role=role)
        edition_cfci_4_super  = create_cfci(descriptor=edition_descriptor, role='superuser')

        # Should not be modified or deleted ---
        orga_desc = fake_custom_forms.FAKEORGANISATION_CREATION_CFORM
        orga_cfci = self.get_object_or_fail(
            CustomFormConfigItem, descriptor_id=orga_desc.id, role=None, superuser=False,
        )
        orga_cfci.store_groups(
            FieldGroupList(
                model=orga_desc.model,
                cell_registry=creation_descriptor.build_cell_registry(),
                groups=[FieldGroup(
                    name='My own config',
                    cells=[
                        EntityCellRegularField.build(model=orga_desc.model, name=name)
                        for name in ('user', 'name')
                    ],
                )],
            )
        )
        orga_cfci.save()
        orga_cfci_groups = orga_cfci.json_groups

        orga_cfci_for_role = create_cfci(
            descriptor=fake_custom_forms.FAKEORGANISATION_CREATION_CFORM, role=role,
        )

        # ---
        self.assertPOST200(
            reverse('creme_config__delete_custom_entity_type'),
            data={'id': ce_type.id},
        )

        ce_type = self.assertStillExists(ce_type)
        self.assertFalse(ce_type.enabled)
        self.assertFalse(ce_type.deleted)

        creation_cfci = self.assertStillExists(creation_cfci)
        self.assertListEqual(
            creation_groups, self.refresh(creation_cfci).groups_as_dicts(),
        )

        edition_cfci = self.assertStillExists(edition_cfci)
        self.assertListEqual(
            edition_groups, self.refresh(edition_cfci).groups_as_dicts(),
        )

        self.assertDoesNotExist(creation_cfci_4_super)
        self.assertDoesNotExist(creation_cfci_4_role)
        self.assertDoesNotExist(edition_cfci_4_super)

        self.assertListEqual(orga_cfci_groups, self.refresh(orga_cfci).json_groups)
        self.assertStillExists(orga_cfci_for_role)
