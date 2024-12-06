from functools import partial

from django.forms import CharField
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.bricks import PropertiesBrick
from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.gui.bricks import Brick
from creme.creme_core.models import CustomEntity1  # NOQA
from creme.creme_core.models import CustomEntity2  # NOQA
from creme.creme_core.models import CustomEntityType, HeaderFilter

from ..base import CremeTestCase
# from .base import ButtonTestCaseMixin
from .base import BrickTestCaseMixin


class CustomEntityTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_detail(self):
        user = self.login_as_root_and_get()
        type_name = 'Training'
        CustomEntityType.objects.create(number=1, name=type_name)

        ent = CustomEntity1.objects.create(user=user, name='Training 01')

        url = ent.get_absolute_url()
        self.assertEqual(
            reverse('creme_core__view_custom_entity', args=(1, ent.id,)),
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
        self.assertEqual(f'{type_name} : {ent.name}', title_node.text.strip())

    def test_detail__other_type(self):
        user = self.login_as_root_and_get()
        type_name = 'Store'
        CustomEntityType.objects.create(number=2, name=type_name)

        ent = CustomEntity2.objects.create(user=user, name='Store 01')

        url = ent.get_absolute_url()
        self.assertEqual(
            reverse('creme_core__view_custom_entity', args=(2, ent.id,)),
            url,
        )

        response = self.assertGET200(url)

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=Brick.GENERIC_HAT_BRICK_ID,
        )
        title_node = self.get_html_node_or_fail(brick_node, ".//div[@class='bar-title']/h1")
        self.assertEqual(f'{type_name} : {ent.name}', title_node.text.strip())

    def test_detail__disabled_type(self):
        user = self.login_as_root_and_get()
        # CustomEntityType.objects.create(...)  # NOPE

        ent = CustomEntity1.objects.create(user=user, name='Store 01')
        self.assertGET404(ent.get_absolute_url())

    # TODO: customfields
    def test_creation(self):
        user = self.login_as_root_and_get()
        item = CustomEntityType.objects.create(number=1, name='Shop')

        # TODO: get_create_absolute_url()
        url = reverse('creme_core__create_custom_entity', args=(1,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add.html')

        self.assertEqual(
            _('Create a «{custom_model}»').format(custom_model=item.name),
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
        self.get_object_or_fail(CustomEntity1, user=user, name=name)

    def test_edition(self):
        user = self.login_as_root_and_get()
        CustomEntityType.objects.create(number=1, name='Shop')
        entity = CustomEntity1.objects.create(user=user, name='Acme')

        url = entity.get_edit_absolute_url()
        self.assertEqual(
            reverse('creme_core__edit_custom_entity', args=(1, entity.id,)),
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

    def test_list(self):
        user = self.login_as_root_and_get()
        CustomEntityType.objects.create(number=1, name='Shop')

        HeaderFilter.objects.create_if_needed(
            pk='creme_core-hf_custom_entity_1',
            name='Shop view', model=CustomEntity1, is_custom=False,
            # cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )

        create_entity = partial(CustomEntity1.objects.create, user=user)
        entity1 = create_entity(name='Happy fruits & vegetables')
        entity2 = create_entity(name='Mega bicycles')

        url = CustomEntity1.get_lv_absolute_url()
        self.assertEqual(reverse('creme_core__list_custom_entities', args=(1,)), url)
        response = self.assertGET200(url)

        with self.assertNoException():
            page = response.context['page_obj']

        self.assertEqual(2, page.paginator.count)

        entities_set = {*page.object_list}
        self.assertIn(entity1, entities_set)
        self.assertIn(entity2, entities_set)

    # TODO: deletion
