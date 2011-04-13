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
from itertools import chain

from django.forms.fields import ChoiceField, CharField, URLField
from django.forms.widgets import PasswordInput, Select
from django.utils.translation import ugettext_lazy as _, ugettext
from creme_config.models.setting import SettingValue

from creme_core.forms.base import FieldBlockManager, CremeForm


from activesync.constants import (USER_MOBILE_SYNC_SERVER_URL,
                                    USER_MOBILE_SYNC_SERVER_DOMAIN,
                                    USER_MOBILE_SYNC_SERVER_SSL,
                                    USER_MOBILE_SYNC_SERVER_LOGIN ,
                                    USER_MOBILE_SYNC_SERVER_PWD,
                                    MAPI_SERVER_URL,
                                    MAPI_DOMAIN,
                                    MAPI_SERVER_SSL,
                                    COMMONS_SERVER_URL_CFG)


class UserSettingsConfigForm(CremeForm):

    url_examples = ChoiceField( label=_(u"Server url examples"), required=False, help_text=_(u"Some common configurations"), choices=chain((("", ""),), COMMONS_SERVER_URL_CFG), widget=Select(attrs={'onchange':'this.form.url.value=$(this).val();'}) )
    url          = URLField(    label=_(u"Server url"),          required=False, help_text=_(u"Let empty to get the default configuration (currently '%s')."))
    domain       = CharField(   label=_(u"Domain"),              required=False, help_text=_(u"Let empty to get the default configuration (currently '%s')."))
    ssl          = ChoiceField( label=_(u"Is secure"),           required=False, help_text=_(u"Let default to get the default configuration  (currently '%s')."), choices=(('', _('Default')) ,('1', _('Yes')), ('0', _('No'))) )
    login        = CharField(   label=_(u"Login"),               required=False)
    password     = CharField(   label=_(u"Password"),            required=False, widget=PasswordInput)

    blocks = FieldBlockManager(#('general',    _(u'Generic information'),  '*'),
                               ('mobile_sync', _(u'Mobile synchronization configuration'),   ('url', 'url_examples', 'domain', 'ssl', 'login', 'password')),
                              )

    def __init__(self, user, *args, **kwargs):
        super(UserSettingsConfigForm, self).__init__(user, *args, **kwargs)
        self.user = user
        user_id   = user.id
        
        fields    = self.fields
        sv_get    = SettingValue.objects.get
        sv_doesnotexist = SettingValue.DoesNotExist

        undefined = _(u"Undefined")

        try:
            fields['url'].initial = sv_get(key__id=USER_MOBILE_SYNC_SERVER_URL, user=user).value
        except sv_doesnotexist:
            pass

        try:
            fields['domain'].initial = sv_get(key__id=USER_MOBILE_SYNC_SERVER_DOMAIN, user=user).value
        except sv_doesnotexist:
            pass

        try:
            fields['ssl'].initial = int(sv_get(key__id=USER_MOBILE_SYNC_SERVER_SSL, user=user).value)
        except (sv_doesnotexist, ValueError):
            pass

        try:
            fields['login'].initial = sv_get(key__id=USER_MOBILE_SYNC_SERVER_LOGIN, user=user).value
        except sv_doesnotexist:
            pass

        try:
            fields['password'].initial = sv_get(key__id=USER_MOBILE_SYNC_SERVER_PWD, user=user).value
        except sv_doesnotexist:
            pass

        try:
            fields['url'].help_text %= sv_get(key__id=MAPI_SERVER_URL).value
        except sv_doesnotexist:
            fields['url'].help_text %= undefined

        try:
            fields['domain'].help_text %= sv_get(key__id=MAPI_DOMAIN).value
        except sv_doesnotexist:
            fields['domain'].help_text %= undefined

        try:
            fields['ssl'].help_text %= ugettext(_('Yes') if sv_get(key__id=MAPI_SERVER_SSL) else _('No'))
        except sv_doesnotexist:
            fields['ssl'].help_text %= undefined

    def clean_ssl(self):
        try:
            return bool(int(self.cleaned_data['ssl']))
        except ValueError:
            pass

    def save(self):
#        super(UserSettingsConfigForm, self).save()

        user = self.user
        user_id = self.user.id

        clean_get = self.cleaned_data.get

        sv_get_or_create = SettingValue.objects.get_or_create
        sv_filter        = SettingValue.objects.filter

        url = clean_get('url')
        if url:
            user_url_cfg, is_created = sv_get_or_create(key_id=USER_MOBILE_SYNC_SERVER_URL, user=user)
            user_url_cfg.value = url
            user_url_cfg.save()
        else:
            sv_filter(key__id=USER_MOBILE_SYNC_SERVER_URL, user=user).delete()

        domain = clean_get('domain')
        if domain:
            user_domain_cfg, is_created = sv_get_or_create(key_id=USER_MOBILE_SYNC_SERVER_DOMAIN, user=user)
            user_domain_cfg.value = domain
            user_domain_cfg.save()
        else:
            sv_filter(key__id=USER_MOBILE_SYNC_SERVER_DOMAIN, user=user).delete()


        ssl = clean_get('ssl')
        if ssl:
            user_ssl_cfg, is_created = sv_get_or_create(key_id=USER_MOBILE_SYNC_SERVER_SSL, user=user)
            user_ssl_cfg.value = ssl
            user_ssl_cfg.save()
        else:
            sv_filter(key__id=USER_MOBILE_SYNC_SERVER_SSL, user=user).delete()

        login = clean_get('login')
        if login:
            user_login_cfg, is_created = sv_get_or_create(key_id=USER_MOBILE_SYNC_SERVER_LOGIN, user=user)
            user_login_cfg.value = login
            user_login_cfg.save()
        else:
            sv_filter(key__id=USER_MOBILE_SYNC_SERVER_LOGIN, user=user).delete()

        password = clean_get('password')
        if password:
            user_password_cfg, is_created = sv_get_or_create(key_id=USER_MOBILE_SYNC_SERVER_PWD, user=user)
            user_password_cfg.value = password
            user_password_cfg.save()#TODO: Needs to be crypted ?
        else:
            sv_filter(key__id=USER_MOBILE_SYNC_SERVER_PWD, user=user).delete()



