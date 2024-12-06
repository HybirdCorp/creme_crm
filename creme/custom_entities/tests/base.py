from creme.creme_core.models import CustomEntityType
from creme.creme_core.tests.base import CremeTestCase


class CustomEntitiesBaseTestCase(CremeTestCase):
    def _enable_type(self, id, name, plural_name=None, deleted=False):
        ce_type = self.get_object_or_fail(CustomEntityType, id=id)
        ce_type.enabled = True
        ce_type.name = name
        ce_type.plural_name = plural_name or f'{name}s'
        ce_type.deleted = deleted
        ce_type.save()

        return ce_type
