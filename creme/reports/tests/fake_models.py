# -*- coding: utf-8 -*-

from django.conf import settings

if not settings.TESTS_ON:
    __all__ = ()
else:
    from django.db.models import CharField, TextField, ForeignKey, ManyToManyField, PROTECT  # FileField
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.models import CremeEntity
    from creme.creme_core.tests.fake_models import FakeContact

    __all__ = ('FakeReportsFolder', 'FakeReportsDocument', 'Guild')


    class FakeReportsFolder(CremeEntity):
        title       = CharField(_(u'Title'), max_length=100, unique=True)
        description = TextField(_(u'Description'), null=True, blank=True)
        parent      = ForeignKey('self', verbose_name=_(u'Parent folder'),
                                 on_delete=PROTECT, null=True,
                                )

        allowed_related = CremeEntity.allowed_related | {'fakereportsdocument'}

        class Meta:
            app_label = 'reports'
            verbose_name = u'Test (reports) Folder'
            verbose_name_plural = u'Test (reports) Folders'
            ordering = ('title',)

        def __unicode__(self):
            return self.title

        def get_absolute_url(self):
            return "/reports/tests/folder/%s" % self.id


    class FakeReportsDocument(CremeEntity):
        title       = CharField(_(u'Title'), max_length=100)
        description = TextField(_(u'Description'), blank=True, null=True)
#        filedata    = FileField(_(u'File'), max_length=500, upload_to='upload/documents')
        folder      = ForeignKey(FakeReportsFolder, verbose_name=_(u'Folder'), on_delete=PROTECT)

        class Meta:
            app_label = 'reports'
            verbose_name = 'Test (reports) Document'
            verbose_name_plural = u'Test (reports) Documents'
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


    class Guild(CremeEntity):
        name    = CharField(_(u'Name'), max_length=100)
        members = ManyToManyField(FakeContact, verbose_name=_(u'Members'))

        class Meta:
            app_label = 'reports'
            verbose_name = 'Book'
            verbose_name_plural = u'Books'
            ordering = ('name',)

        def __unicode__(self):
            return self.name
