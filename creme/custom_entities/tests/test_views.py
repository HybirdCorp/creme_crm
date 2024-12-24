from functools import partial

from django.forms import CharField
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.bricks import PropertiesBrick
from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.creme_jobs import (
    mass_import_type,
    temp_files_cleaner_type,
)
from creme.creme_core.gui.bricks import Brick
from creme.creme_core.models import CustomEntityType, HeaderFilter, Job
from creme.creme_core.tests.views.base import (
    BrickTestCaseMixin,
    MassImportBaseTestCaseMixin,
)

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
        title_node = self.get_html_node_or_fail(bar_node, ".//div[@class='bar-title']/h1")
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
        title_node = self.get_html_node_or_fail(brick_node, ".//div[@class='bar-title']/h1")
        self.assertEqual(f'{type_name} : {entity.name}', title_node.text.strip())

    def test_detail__disabled_type(self):
        user = self.login_as_root_and_get()
        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        self.assertFalse(ce_type.enabled)

        entity = ce_type.entity_model.objects.create(user=user, name='Store 01')
        self.assertGET404(entity.get_absolute_url())

    def test_creation(self):
        user = self.login_as_root_and_get()
        ce_type1 = self._enable_type(id=1, name='Shop')
        ce_type2 = self._enable_type(id=2, name='Warehouse')

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

        # ---
        name = 'Acme'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user': user.id,
                'name': name,
            },
        ))
        self.get_object_or_fail(ce_type1.entity_model, user=user, name=name)

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
        user = self.login_as_root_and_get()
        ce_type = self._enable_type(id=1, name='Shop')
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
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user': user.id,
                'name': name,
            },
        ))
        self.assertEqual(name, self.refresh(entity).name)

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

        HeaderFilter.objects.create_if_needed(
            pk='creme_core-hf_custom_entity_1',
            name='Shop view', model=model, is_custom=False,
            # cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )

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

    # TODO: test custom fields?
    def test_mass_import(self):
        user = self.login_as_root_and_get()
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

        self.get_object_or_fail(Job, type_id=temp_files_cleaner_type.id)
