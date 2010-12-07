# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.forms.fields import ChoiceField, CharField, URLField
from django.forms.widgets import PasswordInput
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.forms.base import FieldBlockManager


from creme_config.models.config_models import CremeKVConfig
from creme_config.constants import (USER_MOBILE_SYNC_SERVER_URL,
                                    USER_MOBILE_SYNC_SERVER_DOMAIN,
                                    USER_MOBILE_SYNC_SERVER_SSL,
                                    USER_MOBILE_SYNC_SERVER_LOGIN ,
                                    USER_MOBILE_SYNC_SERVER_PWD,
                                    MAPI_SERVER_URL,
                                    MAPI_DOMAIN,
                                    MAPI_SERVER_SSL)

from prefered_menu import PreferedMenuForm

class UserSettingsConfigForm(PreferedMenuForm):

    url      = URLField(    label=_(u"Server url"),   required=False, help_text=_(u"Let empty to get the default configuration (currently '%s')."))
    domain   = CharField(   label=_(u"Domain"),       required=False, help_text=_(u"Let empty to get the default configuration (currently '%s')."))
    ssl      = ChoiceField( label=_(u"Is secure"),    required=False, help_text=_(u"Let default to get the default configuration  (currently '%s')."), choices=(('', _('Default')) ,('1', _('Yes')), ('0', _('No'))) )
    login    = CharField(   label=_(u"Login"),        required=False)
    password = CharField(   label=_(u"Password"),     required=False, widget=PasswordInput)

    blocks = FieldBlockManager(('general',    _(u'Generic information'),  '*'),
                               ('mobile_sync', _(u'Mobile synchronisation configuration'),   ('url', 'domain', 'ssl', 'login', 'password')),
                              )

    def __init__(self, user, *args, **kwargs):
        super(UserSettingsConfigForm, self).__init__(user, *args, **kwargs)

        user_id = user.id
        fields = self.fields
        ckv_get = CremeKVConfig.objects.get

        try:
            fields['url'].initial = ckv_get(pk=USER_MOBILE_SYNC_SERVER_URL % user_id).value
        except CremeKVConfig.DoesNotExist:
            pass

        try:
            fields['domain'].initial = ckv_get(pk=USER_MOBILE_SYNC_SERVER_DOMAIN % user_id).value
        except CremeKVConfig.DoesNotExist:
            pass

        try:
            fields['ssl'].initial = ckv_get(pk=USER_MOBILE_SYNC_SERVER_SSL % user_id).value
        except CremeKVConfig.DoesNotExist:
            pass

        try:
            fields['login'].initial = ckv_get(pk=USER_MOBILE_SYNC_SERVER_LOGIN % user_id).value
        except CremeKVConfig.DoesNotExist:
            pass

        try:
            fields['password'].initial = ckv_get(pk=USER_MOBILE_SYNC_SERVER_PWD % user_id).value
        except CremeKVConfig.DoesNotExist:
            pass

        try:
            fields['url'].help_text %= ckv_get(pk=MAPI_SERVER_URL).value
        except CremeKVConfig.DoesNotExist:
            pass

        try:
            fields['domain'].help_text %= ckv_get(pk=MAPI_DOMAIN).value
        except CremeKVConfig.DoesNotExist:
            pass

        try:
            fields['ssl'].help_text %= ugettext(_('Yes') if bool(ckv_get(pk=MAPI_SERVER_SSL).value) else _('No'))
        except CremeKVConfig.DoesNotExist:
            pass

    def save(self):
        super(UserSettingsConfigForm, self).save()

        user_id = self.user.id

        clean_get = self.cleaned_data.get

        ckv_get_or_create = CremeKVConfig.objects.get_or_create

        url = clean_get('url')
        if url:
            user_url_cfg, is_created = ckv_get_or_create(pk=USER_MOBILE_SYNC_SERVER_URL % user_id)
            user_url_cfg.value = url
            user_url_cfg.save()

        domain = clean_get('domain')
        if domain:
            user_domain_cfg, is_created = ckv_get_or_create(pk=USER_MOBILE_SYNC_SERVER_DOMAIN % user_id)
            user_domain_cfg.value = domain
            user_domain_cfg.save()

        ssl = clean_get('ssl')
        if ssl:
            user_ssl_cfg, is_created = ckv_get_or_create(pk=USER_MOBILE_SYNC_SERVER_SSL % user_id)
            user_ssl_cfg.value = ssl
            user_ssl_cfg.save()

        login = clean_get('login')
        if login:
            user_login_cfg, is_created = ckv_get_or_create(pk=USER_MOBILE_SYNC_SERVER_LOGIN % user_id)
            user_login_cfg.value = login
            user_login_cfg.save()

        password = clean_get('password')
        if password:
            user_password_cfg, is_created = ckv_get_or_create(pk=USER_MOBILE_SYNC_SERVER_PWD % user_id)
            user_password_cfg.value = password
            user_password_cfg.save()#TODO: Needs to be crypted ?



