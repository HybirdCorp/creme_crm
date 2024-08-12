from creme.creme_core.gui.bricks import InstanceBrick, brick_registry
from creme.creme_core.models import InstanceBrickConfigItem
from creme.creme_core.tests.base import CremeTestCase


class TransferInstanceBrick(InstanceBrick):
    id = InstanceBrickConfigItem.generate_base_id('creme_config', 'test_transfer')

    # NB: would be in __init__() in classical cases...
    verbose_name = 'Instance brick for transfer'

    def detailview_display(self, context):
        return (
            f'<table id="{self.id}">'
            f'<thead><tr>{self.config_item.entity}</tr></thead>'
            f'</table>'
        )

    def home_display(self, context):
        return self.detailview_display(context)


class TransferBaseTestCase(CremeTestCase):
    VERSION = '1.6'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        brick_registry.register_4_instance(TransferInstanceBrick)
