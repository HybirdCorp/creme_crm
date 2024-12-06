from functools import partial

from django.urls import reverse

from creme.creme_core.models import MenuConfigItem

from .base import CustomEntitiesBaseTestCase


class CustomEntityConfigTestCase(CustomEntitiesBaseTestCase):
    def test_deletion__menu_items(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        ce_type1 = self._enable_type(id=1, name='Shop', deleted=True)
        self._enable_type(id=2, name='Laboratory')

        existing_mci = MenuConfigItem.objects.filter(parent=None).first()

        create_menu_item = partial(MenuConfigItem.objects.create, parent=existing_mci)
        custom_mci11 = create_menu_item(entry_id='custom_entities-list1',   order=1)
        custom_mci12 = create_menu_item(entry_id='custom_entities-create1', order=2)
        custom_mci21 = create_menu_item(entry_id='custom_entities-list2',   order=1)
        custom_mci22 = create_menu_item(entry_id='custom_entities-create2', order=2)

        self.assertPOST200(
            reverse('creme_config__delete_custom_entity_type'),
            data={'id': ce_type1.id},
        )

        ce_type1 = self.assertStillExists(ce_type1)
        self.assertFalse(ce_type1.enabled)
        self.assertFalse(ce_type1.deleted)

        self.assertDoesNotExist(custom_mci11)
        self.assertDoesNotExist(custom_mci12)
        self.assertStillExists(existing_mci)
        self.assertStillExists(custom_mci21)
        self.assertStillExists(custom_mci22)
