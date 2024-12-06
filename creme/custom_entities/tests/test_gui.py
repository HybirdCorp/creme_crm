from django.utils.translation import gettext as _

from creme.creme_core.gui.menu import (
    CreationEntry,
    ListviewEntry,
    menu_registry,
)

from ..models import CustomEntity1  # NOQA
from ..models import CustomEntity2  # NOQA
from ..models import CustomEntity13  # NOQA
from .base import CustomEntitiesBaseTestCase


class CustomEntityGuiTestCase(CustomEntitiesBaseTestCase):
    def test_list_entry(self):
        ce_type1 = self._enable_type(id=1, name='Training', plural_name='Trainings')
        ce_type2 = self._enable_type(id=2, name='Shop', plural_name='Shops', deleted=True)

        entry_classes = {
            entry_class.custom_id: entry_class
            for entry_class in menu_registry.entry_classes
            if issubclass(entry_class, ListviewEntry) and hasattr(entry_class, 'custom_id')
        }

        enabled_cls = entry_classes.get(1)
        self.assertIsNotNone(enabled_cls)
        self.assertEqual(CustomEntity1, enabled_cls.model)
        self.assertEqual('custom_entities-list1', enabled_cls.id)
        self.assertEqual(ce_type1.plural_name, enabled_cls().label)

        deleted_cls = entry_classes.get(2)
        self.assertIsNotNone(deleted_cls)
        self.assertEqual(CustomEntity2, deleted_cls.model)
        self.assertEqual('custom_entities-list2', deleted_cls.id)
        self.assertEqual(
            _('{model} [deleted]').format(model=ce_type2.plural_name),
            deleted_cls().label,
        )

        disabled_cls = entry_classes.get(13)
        self.assertIsNotNone(disabled_cls)
        self.assertEqual(CustomEntity13, disabled_cls.model)
        self.assertEqual('custom_entities-list13', disabled_cls.id)
        self.assertEqual('', disabled_cls().label)

    def test_creation_entry(self):
        ce_type1 = self._enable_type(id=1, name='Training', plural_name='Trainings')
        ce_type2 = self._enable_type(id=2, name='Shop', plural_name='Shops', deleted=True)

        entry_classes = {
            entry_class.custom_id: entry_class
            for entry_class in menu_registry.entry_classes
            if issubclass(entry_class, CreationEntry) and hasattr(entry_class, 'custom_id')
        }

        enabled_cls = entry_classes.get(1)
        self.assertIsNotNone(enabled_cls)
        self.assertEqual(CustomEntity1, enabled_cls.model)
        self.assertEqual('custom_entities-create1', enabled_cls.id)
        self.assertEqual(
            _('Create a entity «{model}»').format(model=ce_type1.name),
            enabled_cls().label,
        )

        deleted_cls = entry_classes.get(2)
        self.assertIsNotNone(deleted_cls)
        self.assertEqual(CustomEntity2, deleted_cls.model)
        self.assertEqual('custom_entities-create2', deleted_cls.id)
        self.assertEqual(
            _('Create a entity «{model}» [deleted]').format(model=ce_type2.name),
            deleted_cls().label,
        )

        disabled_cls = entry_classes.get(13)
        self.assertIsNotNone(disabled_cls)
        self.assertEqual(CustomEntity13, disabled_cls.model)
        self.assertEqual('custom_entities-create13', disabled_cls.id)
        self.assertEqual('', disabled_cls().label)
