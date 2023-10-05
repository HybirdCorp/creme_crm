from creme.creme_core.gui.bricks import Brick, SimpleBrick


class FakeAppPortalBrick(Brick):
    id_ = Brick.generate_id('creme_core', 'fake_app_portal')

    def detailview_display(self, context):
        return f'<div id="{self.id_}" class="brick"></div>'


class FakeOrganisationBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'creme_core/bricks/generic/hat-bar.html'


class FakeOrganisationCardHatBrick(SimpleBrick):
    id_ = SimpleBrick._generate_hat_id('creme_core', 'fake_organisation_card')
    verbose_name = 'Card for FakeOrganisation'
    template_name = 'creme_core/bricks/base/hat-card.html'
