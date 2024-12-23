from functools import partial

from django.forms import CharField
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.bricks import PropertiesBrick
from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.gui.bricks import Brick
from creme.creme_core.models import CustomEntityType, HeaderFilter
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from .base import CustomEntitiesBaseTestCase


class CustomEntityViewsTestCase(BrickTestCaseMixin, CustomEntitiesBaseTestCase):
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

        response = self.client.get(entity.get_edit_absolute_url())
        self.assertContains(
            response,
            _('You cannot edit this entity because the custom type is deleted.'),
            status_code=409,
            html=True,
        )

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
