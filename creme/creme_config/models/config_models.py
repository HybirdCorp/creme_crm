# -*- coding: utf-8 -*-

#from logging import debug

from django.db.models import Model, CharField, ForeignKey, BooleanField
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User


class CremeConfigDescKey(Model):
    name              = CharField(max_length=100, blank=False, null=False)
    desc              = CharField(max_length=100, blank=True, null=True)
    default_value     = CharField(max_length=100, blank=False, null=False)
    is_multiple_value = BooleanField(blank=True, default=False)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = "creme_config"


class GeneralConfig(Model):
    key    = ForeignKey(CremeConfigDescKey, verbose_name=_(u'Key'))
    value  = CharField(max_length=100, blank=False, null=False)
    user   = ForeignKey(User, blank=True, null=True)
    module = CharField(max_length=100, blank=False, null=False)

    def __unicode__(self):
        return force_unicode(self.key)

    class Meta:
        app_label = "creme_config"


class CremeKVConfig(Model):
    id    = CharField(primary_key=True, max_length=100, blank=False, null=False)
    value  = CharField(max_length=100, blank=False, null=False)

    @staticmethod
    def get_int_value(key):
        item = CremeKVConfig.objects.get(id=key)
        return int (item.value)

    class Meta:
        app_label = "creme_config"



#class UserSettings(Model):
    #user = ForeignKey(User, unique=True)

    #class Meta:
        #app_label = "creme_config"
