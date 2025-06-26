from django.conf import settings

__all__: tuple[str, ...]

if not settings.TESTS_ON:
    __all__ = ()
else:
    from django.db import models
    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.models import CremeEntity

    __all__ = ('FakeConfigEntity',)

    class FakeConfigEntity(CremeEntity):
        name = models.CharField(_('Name'), max_length=100)

        class Meta:
            app_label = 'creme_config'
            verbose_name = 'Test ConfigEntity'
            verbose_name_plural = 'Test ConfigEntities'
            ordering = ('name',)

        def __str__(self):
            return self.name
