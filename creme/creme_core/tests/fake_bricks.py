from creme.creme_core.gui.bricks import Brick, SimpleBrick


class FakePortalBrick(Brick):
    id = Brick.generate_id('creme_core', 'fake_portal')

    def detailview_display(self, context):
        return f'<div id="brick-{self.id}" data-brick-id="{self.id}" class="brick"></div>'


class FakeAppPortalBrick(Brick):
    id = Brick.generate_id('creme_core', 'fake_app_portal')

    def detailview_display(self, context):
        return f'<div id="brick-{self.id}" data-brick-id="{self.id}" class="brick"></div>'


class FakeOrganisationBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'creme_core/bricks/generic/hat-bar.html'


class FakeOrganisationCardHatBrick(SimpleBrick):
    id = SimpleBrick._generate_hat_id('creme_core', 'fake_organisation_card')
    verbose_name = 'Card for FakeOrganisation'
    template_name = 'creme_core/bricks/base/hat-card.html'
