from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class CremeApiConfig(CremeAppConfig):
    default = True
    name = "creme.creme_api"
    verbose_name = _("Creme Api")
    dependencies = ["creme.creme_core"]

    def register_bricks(self, brick_registry):
        from .bricks import ApplicationsBrick

        brick_registry.register(ApplicationsBrick)

    def register_menu_entries(self, menu_registry):
        from creme.creme_config.menu import CremeConfigEntry, WorldConfigEntry

        from .menu import CremeApiEntry

        CremeConfigEntry.children_classes.insert(
            CremeConfigEntry.children_classes.index(WorldConfigEntry), CremeApiEntry
        )
