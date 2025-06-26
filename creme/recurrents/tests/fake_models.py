from django.conf import settings

__all__: tuple[str, ...]

if not settings.TESTS_ON:
    __all__ = ()
else:
    from django.db import models
    # from django.urls import reverse
    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.models import CremeEntity

    __all__ = ('FakeRecurrentDoc', 'FakeRecurrentTemplate')

    class FakeRecurrentDoc(CremeEntity):
        title = models.CharField(_('Title'), max_length=50, unique=True)

        class Meta:
            app_label = 'recurrents'
            verbose_name = 'Test Recurrent Document'
            verbose_name_plural = 'Test Recurrent Documents'
            ordering = ('title',)

        def __str__(self):
            return self.title

        # def get_absolute_url(self):
        #     return reverse('reports__view_fake_folder', args=(self.id,))

    class FakeRecurrentTemplate(CremeEntity):
        title = models.CharField(_('Title'), max_length=50, unique=True)

        class Meta:
            app_label = 'recurrents'
            verbose_name = 'Test Recurrent Template'
            verbose_name_plural = 'Test Recurrent Templates'
            ordering = ('title',)

        def __str__(self):
            return self.title

        # def get_absolute_url(self):
        #     return reverse('reports__view_fake_folder', args=(self.id,))
