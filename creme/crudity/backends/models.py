# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
import logging
import re

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db.models.fields import FieldDoesNotExist, TextField, BooleanField
from django.db.models.fields.files import FileField
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.db.utils import IntegrityError
from django.template.context import Context
from django.utils.translation import ugettext_lazy as _

from creme_config.models.setting import SettingValue

from creme_core.utils.dates import get_dt_from_str
from creme_core.utils.meta import is_date_field
from creme_core.views.file_handling import handle_uploaded_file

from crudity.constants import SETTING_CRUDITY_SANDBOX_BY_USER
from crudity.exceptions import ImproperlyConfiguredBackend
from crudity.models.history import History
from media_managers.models.image import Image


class CrudityBackend(object):
    model = None

    password     = u""  #Password to check permission
    in_sandbox   = True #Show in sandbox (if False can be shown only in history & the creation will be automatic)
    body_map     = {}   #Mapping email body's key <==> model's key, value in the dict is the default value
    limit_froms  = ()   #If "recipient" doesn't the backend policy
    subject      = u""  #Matched subject
    blocks       = ()   #Blocks classes
    buttons      = None #An (mutable) iterable of buttons

    def __init__(self, config, *args, **kwargs):
        config_get = config.get

        self.password    = config_get('password')    or self.password
        self.limit_froms = config_get('limit_froms') or self.limit_froms
        in_sandbox = config_get('in_sandbox')
        if in_sandbox is not None:
            self.in_sandbox  = in_sandbox
        self.body_map    = config_get('body_map')    or self.body_map
        self.subject     = CrudityBackend.normalize_subject(config_get('subject') or self.subject)
        self.source         = config_get('source')
        self.verbose_source = config_get('verbose_source')
        self.verbose_method = config_get('verbose_method')
        self._sandbox_by_user = None
        self._check_configuration()
#        self.body_map.update({'password': self.password})

    @property
    def is_configured(self):
        return all([self.subject, self.body_map, self.model])

    def _check_configuration(self):
        """Check if declared fields exists in the model
        TODO: Check the requirement, default value ?
        """
        if self.is_configured:
            model = self.model
            for field_name in self.body_map.iterkeys():
                try:
                    model._meta.get_field(field_name)
                except FieldDoesNotExist, e:
                    for field in model._meta.fields:
                        if field.get_attname() == field_name:
                            break
                    else:
                        raise ImproperlyConfiguredBackend(e)

    def _get_is_sandbox_by_user(self):
        if self._sandbox_by_user is None:
            self._sandbox_by_user = SettingValue.objects.get(key=SETTING_CRUDITY_SANDBOX_BY_USER, user=None).value
        return self._sandbox_by_user

    def _set_is_sandbox_by_user(self, value):
        self._sandbox_by_user = value

    is_sandbox_by_user = property(_get_is_sandbox_by_user, _set_is_sandbox_by_user);del _get_is_sandbox_by_user, _set_is_sandbox_by_user

    @staticmethod
    def normalize_subject(subject):
        """Normalize the subject for an easier retrieve by the input"""
        return re.sub('\s', '', subject or "").upper()

    def create(self, action):
        return self._create_instance_n_history(action.get_data(), action.user, action.source, action.action)

    def _create_instance_before_save(self, instance, data):
        """Called before the instance is saved"""
        return instance

    def _create_instance_after_save(self, instance, data):
        """Called after the instance was saved
        @returns a boolean to check if a re-save is needed
        """
        model_get_field = self.model._meta.get_field
        need_new_save = False

        for field_name, field_value in data.iteritems():
            try:
                field = model_get_field(field_name)
            except FieldDoesNotExist, e:
                continue

            if issubclass(field.__class__, ManyToManyField):
                setattr(instance, field_name, field.rel.to._default_manager.filter(pk__in=field_value.split()))

        return need_new_save

    def _create_instance_n_history(self, data, user=None, source="", action=""):
        instance = self.model()

        model_get_field = self.model._meta.get_field

        for field_name, field_value in data.items():
            try:
                field = model_get_field(field_name)
            except FieldDoesNotExist:
                #TODO: data.pop(field_name) when virtual fields are added in crudity, because for example user_id is not a "real field" (model._meta.get_field)
                continue

            if field_value is None:
                data[field_name] = field.to_python(None)
                continue

            if isinstance(field_value, basestring) and not isinstance(field_value, unicode):
                field_value = field_value.decode('utf8')

            if not isinstance(field, TextField) and isinstance(field_value, basestring):
                data[field_name] = field_value = field_value.replace('\n', ' ')

            if is_date_field(model_get_field(field_name)):
                data[field_name] = field_value = get_dt_from_str(field_value.strip())

            elif isinstance(field, BooleanField) and isinstance(field_value, basestring):
                data[field_name] = field_value = field.to_python(field_value.strip()[0:1].lower()) #Trick to obtain 't'/'f' or '1'/'0'

            elif isinstance(field, ForeignKey) and issubclass(field.rel.to, Image):
                filename, blob = field_value#should be pre-processed by the input
                upload_path = field.rel.to._meta.get_field('image').upload_to.split('/')#TODO: 'image' bof bof...

                if user is None:
                    shift_user_id = data.get('user_id')
                    if shift_user_id is None:
                        try:
                            shift_user_id = User.objects.filter(is_superuser=True)#Not as the default value of data.get because a query is always done even the default value is not necessary
                        except User.DoesNotExist:
                            continue#There is really nothing we can do
                else:
                    shift_user_id = user.id

                img_entity = Image()
                img_entity.image = handle_uploaded_file(ContentFile(blob), path=upload_path, name=filename)
                img_entity.user_id  = shift_user_id
                img_entity.save()
                setattr(instance, field_name, img_entity)
                data.pop(field_name)
                continue

            elif issubclass(field.__class__, FileField):
                filename, blob = field_value#should be pre-processed by the input
                upload_path = field.upload_to.split('/')
                setattr(instance, field_name, handle_uploaded_file(ContentFile(blob), path=upload_path, name=filename))
                data.pop(field_name)
                continue

            data[field_name] = field.to_python(field_value)

        instance.__dict__.update(data)#TODO: Improve this when virtual fields will be added

        is_created = True
        try:
            self._create_instance_before_save(instance, data)
            instance.save()
            need_new_save = self._create_instance_after_save(instance, data)
            if need_new_save:
                instance.save()
            history = History()
            history.entity = instance
            history.action = "create"
            history.source = source
            history.user = user
            history.description = _(u"Creation of %(entity)s") % {'entity': instance}
            history.save()
        except IntegrityError, e:
            logging.error(e)
            is_created = False

        return is_created, instance

    def add_buttons(self, *buttons):
        if self.buttons is None:
            self.buttons = []
        self.buttons.extend(buttons)

    def get_rendered_buttons(self):
        return [button.render(Context({'backend': self})) for button in self.buttons if self.is_configured]

