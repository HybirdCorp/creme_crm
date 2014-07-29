# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from creme.creme_core.forms.base import FieldBlockManager, CremeForm
from creme.creme_core.forms.widgets import Label

from creme.creme_config.models.setting import SettingValue, SettingKey

from ..models import CremeClient
from ..cipher import Cipher
from ..constants import (USER_MOBILE_SYNC_SERVER_URL, USER_MOBILE_SYNC_SERVER_DOMAIN,
                         USER_MOBILE_SYNC_SERVER_SSL, USER_MOBILE_SYNC_SERVER_LOGIN ,
                         USER_MOBILE_SYNC_SERVER_PWD,
                         MAPI_SERVER_URL, MAPI_DOMAIN, MAPI_SERVER_SSL,
                         COMMONS_SERVER_URL_CFG, USER_MOBILE_SYNC_ACTIVITIES, USER_MOBILE_SYNC_CONTACTS)


class UserSettingsConfigForm(CremeForm):
    help         =   CharField(   label=_(u"NB"),                  required=False, initial=_(u"Note that if you change your server URL or your login, synchronization will be reset. You will not loose all your synchronized contacts but there will be all added on the 'new' account at next synchronization."), widget=Label)
    url_examples   = ChoiceField( label=_(u"Server URL examples"), required=False, help_text=_(u"Some common configurations"), choices=chain((("", ""),), COMMONS_SERVER_URL_CFG), widget=Select(attrs={'onchange':'this.form.url.value=$(this).val();'}) )
    url            = URLField(    label=_(u"Server URL"),          required=False, help_text=_(u"Let empty to get the default configuration (currently '%s')."))
    domain         = CharField(   label=_(u"Domain"),              required=False, help_text=_(u"Let empty to get the default configuration (currently '%s')."))
    ssl            = ChoiceField( label=_(u"Is secure"),           required=False, help_text=_(u"Let default to get the default configuration  (currently '%s')."), choices=(('', _('Default')) ,('1', _('Yes')), ('0', _('No'))) )
    login          = CharField(   label=_(u"Login"),               required=False)
    password       = CharField(   label=_(u"Password"),            required=False, widget=PasswordInput)
    sync_calendars = ChoiceField( label=_(u"Synchronize activities (calendars)"), help_text=_(u"Choose if either you want to synchronize your activities in both way or not."), choices=(('0', _('No')), ('1', _('Yes'))))
    sync_contacts  = ChoiceField( label=_(u"Synchronize contacts"),               help_text=_(u"Choose if either you want to synchronize your contacts in both way or not."),   choices=(('0', _('No')), ('1', _('Yes'))))

    blocks = FieldBlockManager(#('general',    _(u'Generic information'),  '*'),
                               ('mobile_sync', _(u'Mobile synchronization configuration'),   ('url', 'url_examples', 'domain', 'ssl', 'login', 'password', 'help')),
                               ('what_sync', _(u'What to sync'),   ('sync_calendars', 'sync_contacts')),
                              )

    def __init__(self, user, *args, **kwargs):
        super(UserSettingsConfigForm, self).__init__(user, *args, **kwargs)
        self.user = user
        #user_id   = user.id

        fields    = self.fields
        sv_get    = SettingValue.objects.get
        sv_doesnotexist = SettingValue.DoesNotExist

        undefined = _(u"Undefined") #TODO: use cached_ugettext when it exists :)

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
            fields['password'].initial = Cipher.decrypt_from_db(sv_get(key__id=USER_MOBILE_SYNC_SERVER_PWD, user=user).value)
            fields['password'].widget.render_value = True
        except sv_doesnotexist:
            pass

        try:
            fields['sync_calendars'].initial = int(bool(sv_get(key__id=USER_MOBILE_SYNC_ACTIVITIES, user=user).value))
        except (sv_doesnotexist, ValueError):
            pass

        try:
            fields['sync_contacts'].initial = int(bool(sv_get(key__id=USER_MOBILE_SYNC_CONTACTS, user=user).value))
        except (sv_doesnotexist, ValueError):
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

    def _booleanify(self, value):
        try:
            return bool(int(value))
        except ValueError:
            pass

    def clean_ssl(self):
        return self._booleanify(self.cleaned_data['ssl'])

    def clean_sync_calendars(self):
        return self._booleanify(self.cleaned_data['sync_calendars'])

    def clean_sync_contacts(self):
        return self._booleanify(self.cleaned_data['sync_contacts'])

    def save(self):
#        super(UserSettingsConfigForm, self).save()

        user = self.user

        clean_get = self.cleaned_data.get

        sv_get_or_create = SettingValue.objects.get_or_create
        sv_filter        = SettingValue.objects.filter
        url_is_created   = False
        login_is_created = False

        url = clean_get('url')
        if url:
            user_url_cfg, url_is_created = sv_get_or_create(key_id=USER_MOBILE_SYNC_SERVER_URL, user=user)
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
            user_login_cfg, login_is_created = sv_get_or_create(key_id=USER_MOBILE_SYNC_SERVER_LOGIN, user=user)
            user_login_cfg.value = login
            user_login_cfg.save()
        else:
            sv_filter(key__id=USER_MOBILE_SYNC_SERVER_LOGIN, user=user).delete()

        user_sync_cal_cfg_sk = SettingKey.objects.get(pk=USER_MOBILE_SYNC_ACTIVITIES)
        user_sync_cal_cfg, is_created = sv_get_or_create(key=user_sync_cal_cfg_sk, user=user)
        user_sync_cal_cfg.value = clean_get('sync_calendars')
        user_sync_cal_cfg.save()

        user_sync_con_cfg_sk = SettingKey.objects.get(pk=USER_MOBILE_SYNC_CONTACTS)
        user_sync_con_cfg, is_created = sv_get_or_create(key=user_sync_con_cfg_sk, user=user)
        user_sync_con_cfg.value = clean_get('sync_contacts')
        user_sync_con_cfg.save()

        password = clean_get('password')
        if password:
            user_password_cfg, is_created = sv_get_or_create(key_id=USER_MOBILE_SYNC_SERVER_PWD, user=user)
#            user_password_cfg.value = password
            user_password_cfg.value = Cipher.encrypt_for_db(password)
            user_password_cfg.save()
        else:
            sv_filter(key__id=USER_MOBILE_SYNC_SERVER_PWD, user=user).delete()

        if url_is_created or login_is_created:
            try:
                as_client = CremeClient.objects.get(user=user)
            except CremeClient.DoesNotExist:
                pass
            else:
                as_client.purge()#NB: If server_url or login have changed, we reset all mapping & clientdef



