from django.conf import settings

from creme.creme_core.models.base import MinionModel

__all__: tuple[str, ...]

if not settings.TESTS_ON:
    __all__ = ()
else:
    from django.db import models
    from django.urls import reverse
    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.models import CremeEntity, FakeContact
    from creme.creme_core.models import fields as core_fields

    __all__ = ('FakeReportsColorCategory', 'FakeReportsFolder', 'FakeReportsDocument', 'Guild')

    class FakeReportsFolder(CremeEntity):
        title = models.CharField(_('Title'), max_length=100, unique=True)
        parent = models.ForeignKey(
            'self',
            verbose_name=_('Parent folder'), on_delete=models.PROTECT, null=True,
        )

        allowed_related = CremeEntity.allowed_related | {'fakereportsdocument'}

        class Meta:
            app_label = 'reports'
            verbose_name = 'Test (reports) Folder'
            verbose_name_plural = 'Test (reports) Folders'
            ordering = ('title',)

        def __str__(self):
            return self.title

        def get_absolute_url(self):
            return reverse('reports__view_fake_folder', args=(self.id,))

    class FakeReportsColorCategory(MinionModel):
        title = models.CharField(_('Title'), max_length=100)
        color = core_fields.ColorField(default=core_fields.ColorField.random)

        class Meta:
            app_label = 'reports'
            verbose_name = 'Test (reports) Color Category'
            verbose_name_plural = 'Test (reports) Color Categories'
            ordering = ('title',)

        def __str__(self):
            return self.title

    class FakeReportsDocument(CremeEntity):
        title = models.CharField(_('Title'), max_length=100)
        # filedata = models.FileField(_('File'), max_length=500, upload_to='documents')
        linked_folder = models.ForeignKey(
            FakeReportsFolder, verbose_name=_('Folder'), on_delete=models.PROTECT,
        )

        category = models.ForeignKey(
            FakeReportsColorCategory,
            verbose_name=_('Category'), null=True, on_delete=models.PROTECT,
        )

        class Meta:
            app_label = 'reports'
            verbose_name = 'Test (reports) Document'
            verbose_name_plural = 'Test (reports) Documents'
            ordering = ('title',)

        def __str__(self):
            return self.title

        # def get_absolute_url(self):
        # def get_edit_absolute_url(self):

        @staticmethod
        def get_lv_absolute_url():
            return reverse('reports__list_fake_documents')

    class Guild(CremeEntity):
        name = models.CharField(_('Name'), max_length=100)
        members = models.ManyToManyField(FakeContact, verbose_name=_('Members'))

        class Meta:
            app_label = 'reports'
            verbose_name = 'Book'
            verbose_name_plural = 'Books'
            ordering = ('name',)

        def __str__(self):
            return self.name
