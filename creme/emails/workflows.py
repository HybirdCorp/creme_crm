################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.workflow import WorkflowAction


# TODO: register
class EmailSendingAction(WorkflowAction):
    type_id = 'emails-email_sending'
    verbose_name = _('Sending an email')

    # # TODO: docstring
    # def __init__(self, *,
    #              entity_source: WorkflowActionSource,
    #              ptype: str | CremePropertyType,  # TODO: accept UUID?
    #              ):
    #     self._entity_source = entity_source
    #     if isinstance(ptype, str):
    #         self._ptype_uuid = ptype
    #         self._ptype = None
    #     else:
    #         assert isinstance(ptype, CremePropertyType)
    #         self._ptype_uuid = str(ptype.uuid)
    #         self._ptype = ptype
    #
    # @classmethod
    # def config_form_class(cls):
    #     from creme.creme_core.forms.workflows import PropertyAddingActionForm
    #     return PropertyAddingActionForm
    #
    # @property
    # def entity_source(self) -> WorkflowActionSource:
    #     return self._entity_source
    #
    # # TODO: manage errors (CremePropertyType does not exist anymore)
    # @property
    # def property_type(self) -> CremePropertyType:
    #     ptype = self._ptype
    #     if ptype is None:
    #         self._ptype = ptype = CremePropertyType.objects.get(uuid=self._ptype_uuid)
    #
    #     return ptype
    #
    # # TODO: do nothing (log?) if invalid ptype
    # def execute(self, context):
    #     entity = self._entity_source.extract(context)
    #     if entity is not None:
    #         CremeProperty.objects.safe_create(
    #             creme_entity=entity, type=self.property_type,
    #         )
    #
    # def to_dict(self) -> dict:
    #     d = super().to_dict()
    #     d['entity'] = self._entity_source.to_dict()
    #     d['ptype'] = self._ptype_uuid
    #
    #     return d
    #
    # @classmethod
    # def from_dict(cls, data: dict, registry):
    #     # TODO: error
    #     return cls(
    #         entity_source=registry.build_action_source(data['entity']),
    #         ptype=data['ptype'],
    #     )
    #
    # def render(self, user) -> str:
    #     source = self._entity_source
    #
    #     return mark_safe(
    #         _('Adding the property «{property}» to: {source}').format(
    #             property=self.property_type.text,
    #             source=source.render(user=user, mode=source.HTML),
    #         )
    #     )
