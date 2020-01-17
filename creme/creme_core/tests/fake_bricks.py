# -*- coding: utf-8 -*-

from creme.creme_core.gui.bricks import Brick


class FakeAppPortalBrick(Brick):
    id_ = Brick.generate_id('creme_core', 'fake_app_portal')

    def detailview_display(self, context):
        return f'<div id="{self.id_}" class="brick"></div>'
