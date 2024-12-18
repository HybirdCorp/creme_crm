from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_config.bricks import CustomEntitiesBrick
from creme.creme_core.bricks import PropertiesBrick
from creme.creme_core.buttons import Restrict2SuperusersButton
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import (
    BrickDetailviewLocation,
    ButtonMenuItem,
    CustomEntityType,
    CustomField,
    EntityFilter,
    FakeContact,
    HeaderFilter,
    HistoryLine,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class CustomEntityConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    def _enable_type(self, id, name, plural_name=None):
        ce_type = self.get_object_or_fail(CustomEntityType, id=id)
        ce_type.enabled = True
        ce_type.name = name
        ce_type.plural_name = plural_name or f'{name}s'
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
        #     [ce_type1.name, ce_type2.name],
        #     [
        #         n.text
        #         for n in brick_node.findall('.//td[@class="cfields-config-name"]')
        #     ],
        # )

    def test_creation(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        self.assertFalse(CustomEntityType.objects.filter(enabled=True))

        name = 'Training'
        plural_name = 'Trainings'

        # Should not cause a uniqueness error (not enabled)
        ce_type2 = self.get_object_or_fail(CustomEntityType, id=3)
        ce_type2.name = name
        ce_type2.save()

        # GET ---
        url = reverse('creme_config__create_custom_entity_type')
        context = self.assertGET200(url).context
        self.assertEqual(_('New custom type of entity'), context.get('title'))
        self.assertEqual(CustomEntityType.save_label,    context.get('submit_label'))

        # POST ---
        self.assertNoFormError(self.client.post(
            url, data={'name': name, 'plural_name': plural_name},
        ))

        ce_type = self.get_alone_element(CustomEntityType.objects.filter(enabled=True))
        self.assertEqual(1,           ce_type.id)
        self.assertEqual(name,        ce_type.name)
        self.assertEqual(plural_name, ce_type.plural_name)

        hfilter = self.get_object_or_fail(
            HeaderFilter,
            entity_type=ContentType.objects.get_for_model(ce_type.entity_model),
        )
        self.assertEqual(_('{model} view').format(model=name), hfilter.name)
        self.assertEqual('creme_core-hf_custom_entity_1',      hfilter.pk)
        self.assertFalse(hfilter.is_custom)
        self.assertListEqual(
            [EntityCellRegularField.build(ce_type.entity_model, 'name')],
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

        name = 'Country'
        plural_name = 'Countries'
        ce_type1 = self._enable_type(id=1, name='House')
        ce_type2 = self._enable_type(id=2, name='Building')

        # Should not cause an uniqueness error (not enabled)
        ce_type3 = self.get_object_or_fail(CustomEntityType, id=3)
        ce_type3.name = name
        ce_type3.save()

        url = reverse('creme_config__edit_custom_entity_type', args=(ce_type1.id,))

        # GET ---
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Edit «{object}»').format(object=ce_type1.name), context1.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))

        # POST ---
        self.assertNoFormError(self.client.post(
            url, data={'name': name, 'plural_name': plural_name},
        ))
        ce_type1 = self.refresh(ce_type1)
        self.assertEqual(1,           ce_type1.id)
        self.assertEqual(name,        ce_type1.name)
        self.assertEqual(plural_name, ce_type1.plural_name)
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

    # NB: MenuConfigItem are tested in 'custom_entities'
    def test_deletion__no_related_entity(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        name = 'Building'
        ce_type = self._enable_type(id=1, name=name)
        model = ce_type.entity_model
        self.assertFalse(ce_type.deleted)

        existing_hf = HeaderFilter.objects.first()
        custom_hf = HeaderFilter.objects.create_if_needed(
            pk='creme_core-hf_customentity1', name='Building view',
            model=model,
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )

        existing_efilter = EntityFilter.objects.first()
        custom_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-customentity01', name='Towers', model=model, is_custom=True,
            # conditions=[...],
        )

        create_cf = partial(CustomField.objects.create, field_type=CustomField.STR)
        contact_cfield = create_cf(content_type=FakeContact, name='Size')
        custom_cfield  = create_cf(content_type=model,       name='Color')

        existing_bmi = ButtonMenuItem.objects.first()
        custom_bmi = ButtonMenuItem.objects.create_if_needed(
            model=model, button=Restrict2SuperusersButton, order=1024,
        )

        existing_bdl = BrickDetailviewLocation.objects.first()
        custom_bdl = BrickDetailviewLocation.objects.create_if_needed(
            brick=PropertiesBrick, order=1, zone=BrickDetailviewLocation.LEFT, model=model,
        )

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

        self.assertDoesNotExist(custom_hf)
        self.assertStillExists(existing_hf)

        self.assertDoesNotExist(custom_efilter)
        self.assertStillExists(existing_efilter)

        self.assertDoesNotExist(custom_cfield)
        self.assertStillExists(contact_cfield)

        self.assertDoesNotExist(custom_bmi)
        self.assertStillExists(existing_bmi)

        self.assertDoesNotExist(custom_bdl)
        self.assertStillExists(existing_bdl)

        # POST (invalid) ---
        self.assertPOST404(url, data=data)

    def test_deletion__related_entities(self):
        user = self.login_as_standard(admin_4_apps=['creme_core'])

        name = 'Building'
        ce_type = self._enable_type(id=1, name=name)
        self.assertFalse(ce_type.deleted)

        ce_type.entity_model.objects.create(user=user, name='Happy fruits & vegetables')

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

    def test_deletion__history(self):
        user = self.login_as_standard(admin_4_apps=['creme_core'])

        ce_type1 = self._enable_type(id=1, name='Shop')
        ce_type2 = self._enable_type(id=2, name='Lab')

        entity1 = ce_type1.entity_model.objects.create(user=user, name='Happy fruits')
        entity2 = ce_type2.entity_model.objects.create(user=user, name='Happy vegetables')

        entity1.delete()

        def count_lines(ctype):
            return HistoryLine.objects.filter(entity_ctype=ctype).count()

        self.assertEqual(2, count_lines(entity1.entity_type))
        self.assertEqual(1, count_lines(entity2.entity_type))

        ce_type1.deleted = True
        ce_type1.save()

        self.assertPOST200(
            reverse('creme_config__delete_custom_entity_type'),
            data={'id': ce_type1.id},
        )

        ce_type1 = self.assertStillExists(ce_type1)
        self.assertFalse(ce_type1.enabled)
        self.assertFalse(ce_type1.deleted)

        self.assertFalse(count_lines(entity1.entity_type))
        self.assertEqual(1, count_lines(entity2.entity_type))

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