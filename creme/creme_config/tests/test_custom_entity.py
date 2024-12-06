from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_config.bricks import CustomEntitiesBrick
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import CustomEntity1  # NOQA
from creme.creme_core.models import CustomEntityType, HeaderFilter
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class CustomEntityConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    def _enable_type(self, id, name):
        ce_type = self.get_object_or_fail(CustomEntityType, id=id)
        ce_type.enabled = True
        ce_type.name = name
        ce_type.save()

        return ce_type

    def test_portal(self):
        self.login_as_root()

        self._enable_type(id=1, name='Training')
        self._enable_type(id=2, name='Shop')

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

        self.assertFalse(CustomEntityType.objects.filter(enabled=True))

        # GET ---
        url = reverse('creme_config__create_custom_entity_type')
        context = self.assertGET200(url).context
        self.assertEqual(_('New custom type of entity'), context.get('title'))
        self.assertEqual(CustomEntityType.save_label,    context.get('submit_label'))

        # POST ---
        name = 'Training'
        self.assertNoFormError(self.client.post(url, data={'name': name}))

        ce_type = self.get_alone_element(CustomEntityType.objects.filter(enabled=True))
        self.assertEqual(1,    ce_type.id)
        self.assertEqual(name, ce_type.name)

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

        # Uniqueness ---
        response3 = self.assertPOST200(url, data={'name': name})
        self.assertFormError(
            response3.context['form'],
            field='name',
            errors=_('There is already a type with this name.'),
        )

    def test_creation__no_available(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        CustomEntityType.objects.update(enabled=True)
        self.assertContains(
            self.client.get(reverse('creme_config__create_custom_entity_type')),
            _('You have reached the maximum number of custom types.'),
            status_code=409,
            html=True,
        )

    def test_edition(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        old_count = HeaderFilter.objects.count()

        ce_type1 = self._enable_type(id=1, name='Building')
        ce_type2 = self._enable_type(id=2, name='Country')

        url = reverse('creme_config__edit_custom_entity_type', args=(ce_type1.id,))

        # GET ---
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Edit «{object}»').format(object=ce_type1.name), context1.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))

        # POST ---
        name = 'House'
        self.assertNoFormError(self.client.post(url, data={'name': name}))
        ce_type1 = self.refresh(ce_type1)
        self.assertEqual(1,    ce_type1.id)
        self.assertEqual(name, ce_type1.name)
        self.assertTrue(ce_type1.enabled)

        # No HeaderFilter is created
        self.assertEqual(old_count, HeaderFilter.objects.count())

        # Uniqueness ---
        response3 = self.assertPOST200(url, data={'name': ce_type2.name})
        self.assertFormError(
            response3.context['form'],
            field='name',
            errors=_('There is already a type with this name.'),
        )

    def test_edition__disabled(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        ce_type = CustomEntityType.objects.first()
        self.assertFalse(ce_type.enabled)
        self.assertContains(
            self.client.get(
                reverse('creme_config__edit_custom_entity_type', args=(ce_type.id,))
            ),
            _('This custom type does not exist anymore.'),
            status_code=409,
            html=True,
        )

    def test_edition__deleted(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        ce_type = self._enable_type(id=1, name='Shop')
        ce_type.deleted = True
        ce_type.save()

        self.assertContains(
            self.client.get(
                reverse('creme_config__edit_custom_entity_type', args=(ce_type.id,))
            ),
            _('This custom type cannot be edited because it is going to be deleted.'),
            status_code=409,
            html=True,
        )

    def test_deletion__no_related(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        name = 'Building'
        ce_type = self._enable_type(id=1, name=name)
        self.assertFalse(ce_type.deleted)

        url = reverse('creme_config__delete_custom_entity_type')
        data = {'id': ce_type.id}
        self.assertGET405(url, data=data)

        # POST ---
        self.assertPOST200(url, data=data)
        ce_type = self.assertStillExists(ce_type)
        self.assertEqual(1,    ce_type.id)  # No change
        self.assertEqual(name, ce_type.name)  # No change
        self.assertTrue(ce_type.enabled)
        self.assertTrue(ce_type.deleted)

        # POST (definitive) ---
        self.assertPOST200(url, data=data)
        ce_type = self.assertStillExists(ce_type)
        self.assertFalse(ce_type.enabled)
        self.assertFalse(ce_type.deleted)

        # TODO: related filters, customfields etc...

        # POST (invalid) ---
        self.assertPOST404(url, data=data)

    def test_deletion__related(self):
        user = self.login_as_standard(admin_4_apps=['creme_core'])

        name = 'Building'
        ce_type = self._enable_type(id=1, name=name)
        self.assertFalse(ce_type.deleted)

        CustomEntity1.objects.create(user=user, name='Happy fruits & vegetables')

        self.assertContains(
            self.client.post(
                reverse('creme_config__delete_custom_entity_type'),
                data={'id': ce_type.id},
            ),
            ngettext(
                'This custom type cannot be deleted because {count} entity uses it.',
                'This custom type cannot be deleted because {count} entities use it.',
                1
            ).format(count=1),
            status_code=409,
            html=True,
        )
        self.assertStillExists(ce_type)

    def test_restore(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        ce_type = self._enable_type(id=1, name='Building')
        ce_type.deleted = True
        ce_type.save()

        url = reverse('creme_config__restore_custom_entity_type')
        data = {'id': ce_type.id}
        self.assertGET405(url, data=data)

        # POST ---
        self.assertPOST200(url, data=data)
        ce_type = self.assertStillExists(ce_type)
        self.assertTrue(ce_type.enabled)
        self.assertFalse(ce_type.deleted)

        # POST (invalid) ---
        self.assertPOST404(url, data=data)
