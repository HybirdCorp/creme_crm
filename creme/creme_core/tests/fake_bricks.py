from creme.creme_core.gui.bricks import Brick


class FakeAppPortalBrick(Brick):
    id = Brick.generate_id('creme_core', 'fake_app_portal')

    def detailview_display(self, context):
        return f'<div id="{self.id}" class="brick"></div>'
