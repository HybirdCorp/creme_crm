from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class CremeApiConfig(CremeAppConfig):
    default = True
    name = 'creme.creme_api'
    verbose_name = _('Creme Api')
    dependencies = ["creme.creme_core"]

    def register_creme_config(self, config_registry):
        from creme.creme_api import models

        from .forms import ApplicationForm

        register_model = config_registry.register_model
        register_model(models.Application, 'application').creation(
            form_class=ApplicationForm,
        ).edition(
            form_class=ApplicationForm,
        )

    def register_bricks(self, brick_registry):
        from .bricks import ApplicationsBrick
        brick_registry.register(ApplicationsBrick)
