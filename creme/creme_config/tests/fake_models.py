# -*- coding: utf-8 -*-

from django.conf import settings

if not settings.TESTS_ON:
    __all__ = ()
else:
    from django.db import models
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.models import CremeEntity

    __all__ = ('FakeConfigEntity',)

    class FakeConfigEntity(CremeEntity):
        name = models.CharField(_(u'Name'), max_length=100)

        class Meta:
            app_label = 'creme_config'
            manager_inheritance_from_future = True
            verbose_name = u'Test ConfigEntity'
            verbose_name_plural = u'Test ConfigEntities'
            ordering = ('name',)

        def __unicode__(self):
            return self.name
