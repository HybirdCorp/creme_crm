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

from django.forms.fields import ChoiceField, TypedChoiceField, CharField, URLField
from django.forms.widgets import PasswordInput, Select
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms.base import FieldBlockManager, CremeForm

from creme.creme_config.models.setting import SettingValue, SettingKey

from ..models import CremeClient
from ..cipher import Cipher
from ..constants import (USER_MOBILE_SYNC_SERVER_URL, USER_MOBILE_SYNC_SERVER_DOMAIN,
        USER_MOBILE_SYNC_SERVER_SSL, USER_MOBILE_SYNC_SERVER_LOGIN ,
        USER_MOBILE_SYNC_SERVER_PWD, USER_MOBILE_SYNC_ACTIVITIES, USER_MOBILE_SYNC_CONTACTS,
        MAPI_SERVER_URL, MAPI_DOMAIN, MAPI_SERVER_SSL, COMMONS_SERVER_URL_CFG)


_choice_2_bool = lambda x: bool(int(x))
_BOOL_CHOICES  = ((0, _('No')), (1, _('Yes')))


class UserSettingsConfigForm(CremeForm):
    url            = URLField(label=_(u"Server URL"), required=False)
    url_examples   = ChoiceField(label=_(u"Server URL examples"), required=False,
                                 help_text=_(u"Some common configurations"),
                                 choices=chain((("", ""),), COMMONS_SERVER_URL_CFG),
                                 widget=Select(attrs={'onchange':'this.form.url.value=$(this).val();'}),
                                )
    domain         = CharField(label=_(u"Domain"), required=False)
    ssl            = ChoiceField(label=_(u"Is secure"), required=False,
                                 choices=(('', _('Default')), (1, _('Yes')), (0, _('No'))),
                                )
    login          = CharField(label=_(u"Login"), required=False)
    password       = CharField(label=_(u"Password"), required=False, widget=PasswordInput)
    sync_calendars = TypedChoiceField(label=_(u"Synchronize activities (calendars)"),
                                      help_text=_(u"Choose if either you want to synchronize your activities in both way or not."),
                                      choices=_BOOL_CHOICES, coerce=_choice_2_bool,
                                     )
    sync_contacts  = TypedChoiceField(label=_(u"Synchronize contacts"),
                                      help_text=_(u"Choose if either you want to synchronize your contacts in both way or not."),
                                      choices=_BOOL_CHOICES, coerce=_choice_2_bool,
                                     )

    blocks = FieldBlockManager(
        ('mobile_sync', _(u'Mobile synchronization configuration'), '*'),
        ('what_sync',   _(u'What to sync'), ('sync_calendars', 'sync_contacts')),
       )

    def __init__(self, *args, **kwargs):
        super(UserSettingsConfigForm, self).__init__(*args, **kwargs)
        user = self.user

        self._svalues_cache = svalues_cache = {}

        def get_svalue(key_id):
            sv = svalues_cache[key_id] = SettingValue.objects.get(key__id=key_id, user=user)
            return sv

        fields = self.fields
        sv_get = SettingValue.objects.get
        sv_doesnotexist = SettingValue.DoesNotExist

        let_empty_msg = ugettext(u"Let empty to get the default configuration (currently '%s').")

        url_field = fields['url']
        url_field.help_text = let_empty_msg % sv_get(key__id=MAPI_SERVER_URL).value
        try:
            url_field.initial = get_svalue(USER_MOBILE_SYNC_SERVER_URL).value
        except sv_doesnotexist:
            pass

        domain_field = fields['domain']
        domain_field.help_text = let_empty_msg % sv_get(key__id=MAPI_DOMAIN).value
        try:
            domain_field.initial = get_svalue(USER_MOBILE_SYNC_SERVER_DOMAIN).value
        except sv_doesnotexist:
            pass

        ssl_field = fields['ssl']
        ssl_field.help_text = ugettext(u"Let 'Default' to get the default configuration (currently '%s').") % (
                                    ugettext('Yes') if sv_get(key__id=MAPI_SERVER_SSL).value else ugettext('No')
                               )
        try:
            ssl_field.initial = int(get_svalue(USER_MOBILE_SYNC_SERVER_SSL).value)
        except sv_doesnotexist:
            pass

        #----------------------------------
        try:
            fields['login'].initial = get_svalue(USER_MOBILE_SYNC_SERVER_LOGIN).value
        except sv_doesnotexist:
            pass

        pwd_field = fields['password']
        try:
            pwd_field.initial = Cipher.decrypt_from_db(get_svalue(USER_MOBILE_SYNC_SERVER_PWD).value)
            pwd_field.widget.render_value = True
        except sv_doesnotexist:
            pass

        try:
            fields['sync_calendars'].initial = int(get_svalue(USER_MOBILE_SYNC_ACTIVITIES).value)
        except sv_doesnotexist:
            pass

        try:
            fields['sync_contacts'].initial = int(get_svalue(USER_MOBILE_SYNC_CONTACTS).value)
        except sv_doesnotexist:
            pass

    def clean_ssl(self):
        try:
            return _choice_2_bool(self.cleaned_data['ssl'])
        except ValueError:
            pass

    def save(self):
        user = self.user
        clean_get = self.cleaned_data.get

        url_is_created   = False
        login_is_created = False

        def upgrade_svalue(key_id, value):
            svalue = self._svalues_cache.get(key_id)
            created = False

            if svalue is None:
                svalue = self._svalues_cache[key_id] \
                       = SettingValue.objects.create(key_id=key_id, user=user, value=value)
                created = True
            elif svalue.value != value:
                svalue.value = value
                svalue.save()

            return created

        def delete_svalue(key_id):
            svalue = self._svalues_cache.pop(key_id, None)

            if svalue is not None:
                svalue.delete()

        url = clean_get('url')
        if url:
            url_is_created = upgrade_svalue(USER_MOBILE_SYNC_SERVER_URL, url)
        else:
            delete_svalue(USER_MOBILE_SYNC_SERVER_URL)

        domain = clean_get('domain')
        if domain:
            upgrade_svalue(USER_MOBILE_SYNC_SERVER_DOMAIN, domain)
        else:
            delete_svalue(USER_MOBILE_SYNC_SERVER_DOMAIN)

        ssl = clean_get('ssl')
        if ssl is not None:
            upgrade_svalue(USER_MOBILE_SYNC_SERVER_SSL, ssl)
        else:
            delete_svalue(USER_MOBILE_SYNC_SERVER_SSL)

        login = clean_get('login')
        if login:
            login_is_created = upgrade_svalue(USER_MOBILE_SYNC_SERVER_LOGIN, login)
        else:
            delete_svalue(USER_MOBILE_SYNC_SERVER_LOGIN)

        upgrade_svalue(USER_MOBILE_SYNC_ACTIVITIES, clean_get('sync_calendars'))
        upgrade_svalue(USER_MOBILE_SYNC_CONTACTS,   clean_get('sync_contacts'))

        password = clean_get('password')
        if password:
            upgrade_svalue(USER_MOBILE_SYNC_SERVER_PWD, Cipher.encrypt_for_db(password))
        else:
            delete_svalue(USER_MOBILE_SYNC_SERVER_PWD)

        #TODO: test
        #TODO: add a true button to purge (ex: we could want to purge if the url is changed, or not)
        if url_is_created or login_is_created:
            try:
                as_client = CremeClient.objects.get(user=user)
            except CremeClient.DoesNotExist:
                pass
            else:
                as_client.purge()#NB: If server_url or login have changed, we reset all mapping & clientdef
