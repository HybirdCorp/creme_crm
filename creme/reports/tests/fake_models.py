# -*- coding: utf-8 -*-

from django.conf import settings

if not settings.TESTS_ON:
    __all__ = ()
else:
    from django.db.models import CharField, TextField, ForeignKey, PROTECT #FileField
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.models import CremeEntity


    class FakeFolder(CremeEntity):
        title         = CharField(_(u'Title'), max_length=100, unique=True)
        description   = TextField(_(u'Description'), null=True, blank=True)

        allowed_related = CremeEntity.allowed_related | {'fakedocument'}

        class Meta:
            app_label = 'reports'
            verbose_name = u'Test Folder'
            verbose_name_plural = u'Test Folders'
            ordering = ('title',)

        def __unicode__(self):
            return self.title

        def get_absolute_url(self):
            return "/reports/tests/folder/%s" % self.id


    class FakeDocument(CremeEntity):
        title       = CharField(_(u'Title'), max_length=100)
        description = TextField(_(u'Description'), blank=True, null=True)
#        filedata    = FileField(_(u'File'), max_length=500, upload_to='upload/documents')
        folder      = ForeignKey(FakeFolder, verbose_name=_(u'Folder'), on_delete=PROTECT)


        class Meta:
            app_label = 'reports'
            verbose_name = 'Test Document'
            verbose_name_plural = u'Test Documents'
            ordering = ('title',)

        def __unicode__(self):
            return self.title

#        def get_absolute_url(self):
#            return "/documents/document/%s" % self.id
#    
#        def get_edit_absolute_url(self):
#            return "/documents/document/edit/%s" % self.id

        @staticmethod
        def get_lv_absolute_url():
            return '/reports/tests/documents'
