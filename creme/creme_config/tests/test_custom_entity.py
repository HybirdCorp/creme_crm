from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_config.bricks import CustomEntitiesBrick
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import CustomEntity1  # NOQA
from creme.creme_core.models import CustomEntityType, HeaderFilter
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class CustomEntityConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_portal(self):
        self.login_as_root()

        create_item = CustomEntityType.objects.create
        create_item(number=1, name='Training')
        create_item(number=2, name='Shop')

        response = self.assertGET200(reverse('creme_config__custom_entity_types'))
        self.assertTemplateUsed(response, 'creme_config/portals/custom-entity.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=CustomEntitiesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Type of entity',
            plural_title='{count} Types of entity',
        )
        # TODO: complete test
        # self.assertCountEqual(
        #     [cfield1.name, cfield2.name, cfield3.name],
        #     [
        #         n.text
        #         for n in brick_node.findall('.//td[@class="cfields-config-name"]')
        #     ],
        # )

    def test_creation(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        url = reverse('creme_config__create_custom_entity_type')
        context = self.assertGET200(url).context
        self.assertEqual(_('New custom type of entity'), context.get('title'))
        self.assertEqual(CustomEntityType.save_label,    context.get('submit_label'))

        self.assertFalse(CustomEntityType.objects.all())

        name = 'Training'
        self.assertNoFormError(self.client.post(url, data={'name': name}))

        custom_type = self.get_alone_element(CustomEntityType.objects.all())
        self.assertEqual(1,    custom_type.number)
        self.assertEqual(name, custom_type.name)

        hfilter = self.get_object_or_fail(
            HeaderFilter,
            entity_type=ContentType.objects.get_for_model(CustomEntity1),
        )
        self.assertEqual(_('{model} view').format(model=name), hfilter.name)
        self.assertEqual('creme_core-hf_custom_entity_1',      hfilter.pk)
        self.assertFalse(hfilter.is_custom)
        self.assertListEqual(
            [EntityCellRegularField.build(CustomEntity1, 'name')],
            hfilter.cells,
        )

    def test_edition(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        old_count = HeaderFilter.objects.count()

        item = CustomEntityType.objects.create(number=1, name='Building')
        url = reverse('creme_config__edit_custom_entity_type', args=(item.id,))

        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Edit «{object}»').format(object=item.name), context1.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))

        # ---
        name = 'House'
        self.assertNoFormError(self.client.post(url, data={'name': name}))
        item = self.refresh(item)
        self.assertEqual(1,    item.number)
        self.assertEqual(name, item.name)

        # No HeaderFilter is created
        self.assertEqual(old_count, HeaderFilter.objects.count())

    # TODO: edition + uniqueness
    # TODO: deletion
