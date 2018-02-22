# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db.models import (FieldDoesNotExist, TextField, BooleanField,
        DateField, DateTimeField, FileField, ForeignKey, ManyToManyField)
from django.db.transaction import atomic
# from django.template.context import Context
from django.utils.translation import ugettext as _

from creme.creme_core.models import SettingValue
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.utils.dates import dt_from_str, date_from_str
from creme.creme_core.views.file_handling import handle_uploaded_file

# TODO: improve the crudity_registry in order to manage FK to other entity types => use test-models
# from creme.media_managers.models import Image
from creme.documents import get_document_model, get_folder_model

from ..models import History
from ..constants import SETTING_CRUDITY_SANDBOX_BY_USER
from ..exceptions import ImproperlyConfiguredBackend


logger = logging.getLogger(__name__)

Folder = get_folder_model()
Document = get_document_model()


class CrudityBackend(object):
    model = None     # Class inheriting CremeEntity. OVERRIDE THIS IN on your own backend.

    # These ones are set by the registry.dispatch()
    fetcher_name = ''  # Name of the fetcher (eg: 'emails')
    input_name   = ''  # Name of the CrudityInput (eg: 'raw')  # TODO: useless with 'crud_input' attribute ?

    password    = u''   # Password to check permission
    in_sandbox  = True  # Show in sandbox (if False can be shown only in history & the creation will be automatic)
    body_map    = {}    # Mapping email body's key <==> model's key, value in the dict is the default value
    limit_froms = ()    # If "recipient" doesn't the backend policy
    subject     = u''   # Matched subject
    blocks      = ()    # Blocks classes  # TODO: rename 'bricks'

    def __init__(self, config, crud_input=None, *args, **kwargs):
        config_get = config.get
        self.crud_input = crud_input

        self.password    = config_get('password')    or self.password
        self.limit_froms = config_get('limit_froms') or self.limit_froms

        in_sandbox = config_get('in_sandbox')
        if in_sandbox is not None:
            self.in_sandbox = in_sandbox

        self.body_map = config_get('body_map') or self.body_map
        self.subject  = CrudityBackend.normalize_subject(config_get('subject') or self.subject)

        self.source         = config_get('source')
        self.verbose_source = config_get('verbose_source')
        self.verbose_method = config_get('verbose_method')

        self._sandbox_by_user = None
        self._check_configuration()
        self.buttons = []  # TODO: deprecate in 1.8

    @property
    def is_configured(self):
        return all([self.subject, self.body_map, self.model])
        # TODO ? return bool(self.subject and self.body_map and self.model)

    def _check_configuration(self):
        """Check if declared fields exists in the model
        TODO: Check the requirement, default value ?
        """
        if self.is_configured:
            model = self.model  # TODO: alias _meta
            for field_name in self.body_map.iterkeys():
                try:
                    model._meta.get_field(field_name)
                except FieldDoesNotExist as e:
                    for field in model._meta.fields:  # TODO: any()
                        if field.get_attname() == field_name:
                            break
                    else:
                        raise ImproperlyConfiguredBackend(e)

    # TODO: factorise with CrudityQuerysetBrick.is_sandbox_by_user ?
    @property
    def is_sandbox_by_user(self):
        if self._sandbox_by_user is None:
            # self._sandbox_by_user = SettingValue.objects.get(key_id=SETTING_CRUDITY_SANDBOX_BY_USER, user=None).value
            self._sandbox_by_user = SettingValue.objects.get(key_id=SETTING_CRUDITY_SANDBOX_BY_USER).value

        return self._sandbox_by_user

    @is_sandbox_by_user.setter
    def is_sandbox_by_user(self, value):
        self._sandbox_by_user = value

    @staticmethod
    def normalize_subject(subject):
        """Normalize the subject for an easier retrieve by the input"""
        return re.sub('\s', '', subject or '').upper()

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
            except FieldDoesNotExist:
                continue

            if issubclass(field.__class__, ManyToManyField): #TODO: isinstance(field, ManyToManyField) ...
                setattr(instance, field_name, field.rel.to._default_manager.filter(pk__in=field_value.split()))

        return need_new_save

    def _create_instance_n_history(self, data, user=None, source="", action=""):  # TODO: remove 'action'
        is_created = True
        instance = self.model()
        model_get_field = self.model._meta.get_field

        try:
            with atomic():
                for field_name, field_value in data.items():
                    try:
                        field = model_get_field(field_name)
                    except FieldDoesNotExist:
                        # TODO: data.pop(field_name) when virtual fields are added in crudity,
                        #       because for example user_id is not a "real field" (model._meta.get_field)
                        continue

                    # TODO: exclude not editable fields ??

                    if field_value is None:
                        data[field_name] = field.to_python(None)
                        continue

                    if isinstance(field_value, basestring) and not isinstance(field_value, unicode):
                        field_value = field_value.decode('utf8')

                    if not isinstance(field, TextField) and isinstance(field_value, basestring):
                        data[field_name] = field_value = field_value.replace('\n', ' ')

                    if isinstance(field, DateTimeField):
                        data[field_name] = field_value = dt_from_str(field_value.strip())
                    elif isinstance(field, DateField):
                        data[field_name] = field_value = date_from_str(field_value.strip())

                    elif isinstance(field, BooleanField) and isinstance(field_value, basestring):
                        data[field_name] = field_value = field.to_python(field_value.strip()[0:1].lower()) #Trick to obtain 't'/'f' or '1'/'0'

                    elif isinstance(field, ForeignKey) and issubclass(field.rel.to, Document):
                        filename, blob = field_value  # Should be pre-processed by the input
                        upload_path = Document._meta.get_field('filedata').upload_to.split('/')

                        if user is None:
                            shift_user_id = data.get('user_id')
                            User = get_user_model()  # TODO: use first() instead
                            if shift_user_id is None:
                                try:
                                    # Not as the default value of data.get because a query is
                                    # always done even the default value is not necessary
                                    shift_user_id = User.objects.filter(is_superuser=True)[0].id
                                except IndexError:
                                    continue  # There is really nothing we can do
                        else:
                            shift_user_id = user.id

                        doc_entity = Document(
                                user_id=shift_user_id,
                                filedata=handle_uploaded_file(ContentFile(blob), path=upload_path, name=filename),
                                folder=Folder.objects.get_or_create(title=_('External data'),
                                                                    parent_folder=None,
                                                                    defaults={'user_id': shift_user_id},
                                                                   )[0],
                                description=_('Imported from external data.'),
                            )
                        assign_2_charfield(doc_entity, 'title', filename)
                        doc_entity.save()

                        setattr(instance, field_name, doc_entity)
                        data.pop(field_name)
                        continue

                    elif issubclass(field.__class__, FileField):  # TODO: why not isinstance(field, FileField) ??
                        filename, blob = field_value  # Should be pre-processed by the input
                        upload_path = field.upload_to.split('/')
                        setattr(instance, field_name, handle_uploaded_file(ContentFile(blob), path=upload_path, name=filename))
                        data.pop(field_name)
                        continue

                    data[field_name] = field.to_python(field_value)
                    #setattr(instance, field_name, field.to_python(field_value)) TODO (instead of for ..: setattr()... ??

                instance.__dict__.update(data)
                #for k, v in data.iteritems(): #TODO: (but fix bug with ManyToManyField)
                    #setattr(instance, k, v)

                self._create_instance_before_save(instance, data)
                instance.save()
                need_new_save = self._create_instance_after_save(instance, data)
                if need_new_save:
                    instance.save()

                history = History()  # TODO: History.objects.create(entity=intance [...])
                history.entity = instance
                history.action = 'create'
                history.source = source
                history.user = user
                history.description = _(u'Creation of %(entity)s') % {'entity': instance}
                history.save()
        except IntegrityError as e:
            logger.error('_create_instance_n_history() : error when try to create instance [%s]', e)
            is_created = False

        return is_created, instance

    def add_buttons(self, *buttons):  # TODO: deprecate in 1.8
        self.buttons.extend(buttons)

    def get_id(self):
        subject = self.subject
        return self.fetcher_name if subject == '*' else \
               '%s|%s|%s' % (self.fetcher_name, self.input_name, self.subject)

    def get_rendered_buttons(self):  # TODO: deprecate in 1.8
        return [button.render({'backend': self})
                    for button in self.buttons if self.is_configured
               ]
