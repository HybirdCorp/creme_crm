# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from typing import (
    TYPE_CHECKING,
    Any,
    Collection,
    Dict,
    Optional,
    Sequence,
    Tuple,
    Type,
)

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db.models import (
    BooleanField,
    DateField,
    DateTimeField,
    FileField,
    ForeignKey,
    ManyToManyField,
    TextField,
)
from django.db.transaction import atomic
from django.utils.translation import gettext as _

from creme.creme_core.models import CremeEntity
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.utils.dates import date_from_str, dt_from_str
from creme.creme_core.views.file_handling import handle_uploaded_file
# TODO: improve the crudity_registry in order to manage FK to other entity types
#      => use test-models
from creme.documents import get_document_model, get_folder_model

from ..bricks import BaseWaitingActionsBrick, WaitingActionsBrick
from ..exceptions import ImproperlyConfiguredBackend
from ..models import History, WaitingAction

if TYPE_CHECKING:
    from ..inputs.base import CrudityInput

logger = logging.getLogger(__name__)

Folder = get_folder_model()
Document = get_document_model()


class CrudityBackend:
    # model = None
    model: Type[CremeEntity]     # OVERRIDE THIS IN on your own backend.

    # These ones are set by the registry.dispatch()
    fetcher_name: str = ''  # Name of the fetcher (eg: 'emails')
    # TODO: useless with 'crud_input' attribute ?
    input_name: str = ''  # Name of the CrudityInput (eg: 'raw')

    password: str = ''   # Password to check permission

    # Show in sandbox (if False can be shown only in history & the creation will be automatic)
    in_sandbox: bool = True

    # Mapping email/sms/... body's key <==> model's key, value in the dict is the default value
    body_map: Dict[str, Any] = {}

    limit_froms: Collection[str] = ()  # If not empty, it lists the allowed senders.
    subject: str = ''  # Matched subject

    brick_classes: Sequence[Type[BaseWaitingActionsBrick]] = (WaitingActionsBrick,)

    def __init__(self,
                 config: Dict[str, Any],
                 crud_input: Optional['CrudityInput'] = None,
                 *args, **kwargs):
        config_get = config.get
        self.crud_input = crud_input

        # TODO: validate types of data in config...
        self.password    = config_get('password')    or self.password
        self.limit_froms = config_get('limit_froms') or self.limit_froms

        in_sandbox = config_get('in_sandbox')
        if in_sandbox is not None:
            self.in_sandbox = in_sandbox

        self.body_map = config_get('body_map') or self.body_map
        self.subject = CrudityBackend.normalize_subject(config_get('subject') or self.subject)

        self.source         = config_get('source')
        self.verbose_source = config_get('verbose_source')
        self.verbose_method = config_get('verbose_method')

        # self._sandbox_by_user: Optional[bool] = None
        self._check_configuration()

    @property
    def is_configured(self) -> bool:
        return bool(self.subject and self.body_map and self.model)

    def _check_configuration(self) -> None:
        """Check if declared fields exists in the model
        TODO: Check the requirement, default value ?
        """
        if self.is_configured:
            model = self.model  # TODO: alias _meta
            for field_name in self.body_map:
                try:
                    model._meta.get_field(field_name)
                except FieldDoesNotExist as e:
                    for field in model._meta.fields:  # TODO: any()
                        if field.get_attname() == field_name:
                            break
                    else:
                        raise ImproperlyConfiguredBackend(e) from e

    @staticmethod
    def normalize_subject(subject: str) -> str:
        """Normalize the subject for an easier retrieve by the input."""
        return re.sub(r'\s', '', subject or '').upper()

    def create(self, action: WaitingAction) -> Tuple[bool, CremeEntity]:
        return self._create_instance_n_history(
            action.data, action.user, action.source, action.action,
        )

    def _create_instance_before_save(
            self,
            instance: CremeEntity,
            data: Dict[str, Any]) -> CremeEntity:
        """Called before the instance is saved"""
        return instance

    def _create_instance_after_save(self, instance: CremeEntity, data: Dict[str, Any]) -> bool:
        """Called after the instance was saved
        @returns a boolean to check if a re-save is needed
        """
        model_get_field = self.model._meta.get_field
        need_new_save = False

        for field_name, field_value in data.items():
            try:
                field = model_get_field(field_name)
            except FieldDoesNotExist:
                continue

            # TODO: isinstance(field, ManyToManyField) ...
            if issubclass(field.__class__, ManyToManyField):
                getattr(instance, field_name).set(
                    field.remote_field.model._default_manager.filter(pk__in=field_value.split())
                )

        return need_new_save

    def _create_instance_n_history(self,
                                   data: Dict[str, Any],
                                   user=None,
                                   source: str = '',
                                   action='') -> Tuple[bool, CremeEntity]:  # TODO: remove 'action'
        is_created = True
        instance = self.model()
        model_get_field = self.model._meta.get_field

        try:
            with atomic():
                field_value: Any
                # NB: we build a list to modify "data"
                for field_name, field_value in [*data.items()]:
                    try:
                        field = model_get_field(field_name)
                    except FieldDoesNotExist:
                        # TODO: data.pop(field_name) when virtual fields are added in crudity,
                        #       because for example user_id is not a "real field"
                        #       (model._meta.get_field)
                        continue

                    # TODO: exclude not editable fields ??

                    if field_value is None:
                        data[field_name] = field.to_python(None)
                        continue

                    if not isinstance(field, TextField) and isinstance(field_value, str):
                        data[field_name] = field_value = field_value.replace('\n', ' ')

                    if isinstance(field, DateTimeField):
                        data[field_name] = field_value = dt_from_str(field_value.strip())
                    elif isinstance(field, DateField):
                        data[field_name] = field_value = date_from_str(field_value.strip())

                    elif isinstance(field, BooleanField) and isinstance(field_value, str):
                        # NB: trick to obtain 't'/'f' or '1'/'0'
                        data[field_name] = field_value = field.to_python(
                            field_value.strip()[0:1].lower()
                        )

                    elif (
                        isinstance(field, ForeignKey)
                        and issubclass(field.remote_field.model, Document)
                    ):
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
                            filedata=handle_uploaded_file(
                                ContentFile(blob), path=upload_path, name=filename,
                            ),
                            linked_folder=Folder.objects.get_or_create(
                                title=_('External data'),
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

                    # TODO: why not isinstance(field, FileField) ??
                    elif issubclass(field.__class__, FileField):
                        filename, blob = field_value  # Should be pre-processed by the input
                        upload_path = field.upload_to.split('/')
                        setattr(
                            instance,
                            field_name,
                            handle_uploaded_file(
                                ContentFile(blob), path=upload_path, name=filename,
                            ),
                        )
                        data.pop(field_name)
                        continue

                    data[field_name] = field.to_python(field_value)
                    # TODO (instead of for ..: setattr()... ??
                    # setattr(instance, field_name, field.to_python(field_value))

                instance.__dict__.update(data)
                # TODO: (but fix bug with ManyToManyField)
                #     for k, v in data.iteritems():
                #         setattr(instance, k, v)

                self._create_instance_before_save(instance, data)
                instance.save()
                need_new_save = self._create_instance_after_save(instance, data)
                if need_new_save:
                    instance.save()

                history = History()  # TODO: History.objects.create(entity=instance [...])
                history.entity = instance
                history.action = 'create'
                history.source = source
                history.user = user
                history.description = _('Creation of {entity}').format(entity=instance)
                history.save()
        except IntegrityError as e:
            logger.error(
                '_create_instance_n_history() : error when try to create instance [%s]',
                e,
            )
            is_created = False

        return is_created, instance

    def get_id(self) -> str:
        subject = self.subject

        return (
            self.fetcher_name
            if subject == '*' else
            f'{self.fetcher_name}|{self.input_name}|{self.subject}'
        )
