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

# Trigger ----------------------------------------------------------------------
# TODO: doc-strings
class WorkflowTrigger:
    type_id = ''
    verbose_name = '??'

    def __init__(self, **kwargs):
        pass

    @property
    def description(self) -> str:
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {'type': self.type_id}


# Sources ----------------------------------------------------------------------
# TODO: base class
# TODO: 'SourceDescriptor' ??
class SingleEntitySource:
    def __init__(self, *, id, model):
        self._id = id
        self._model = model

    @property
    def id(self):
        return self._id

    @property
    def model(self):
        return self._model

    @property
    def label(self):
        return self._model._meta.verbose_name

    # TODO: errors
    #  - key error
    #  - type error (assert type of extracted value)
    def extract(self, workflow_context: dict):
        return workflow_context[self._id]


# Action -----------------------------------------------------------------------
# TODO: doc-strings
class WorkflowAction:
    type_id = ''
    verbose_name = '??'

    def __init__(self, **kwargs):
        pass

    @property
    def description(self) -> str:
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {'type': self.type_id}


# Registry ---------------------------------------------------------------------
# TODO: static typing
# TODO: errors (empty id, duplicate, unknown id etc...)
# TODO: register filter (condition handler etc...) ?
class WorkflowRegistry:
    """TODO"""
    # TODO
    # class RegistrationError(Exception):
    #     pass

    def __init__(self):
        self._action_classes = {}
        self._trigger_classes = {}

    # Actions ---
    @property
    def action_classes(self):
        yield from self._action_classes.values()

    # TODO: errors
    def build_action(self, data):
        type_id = data['type']
        return self._action_classes[type_id](**data)

    # TODO: errors
    def register_actions(self, *action_classes):
        for action_class in action_classes:
            self._action_classes[action_class.type_id] = action_class

        return self

    # TODO: errors
    def unregister_actions(self, *action_classes):
        for action_class in action_classes:
            del self._action_classes[action_class.type_id]

        return self

    # Triggers ---
    @property
    def trigger_classes(self):
        yield from self._trigger_classes.values()

    def build_trigger(self, data):
        type_id = data['type']

        return self._trigger_classes[type_id](**data)

    # TODO: errors
    def register_triggers(self, *trigger_classes):
        for trigger_class in trigger_classes:
            self._trigger_classes[trigger_class.type_id] = trigger_class

        return self

    # TODO: errors
    def unregister_triggers(self, *trigger_classes):
        for trigger_class in trigger_classes:
            del self._trigger_classes[trigger_class.type_id]

        return self


workflow_registry = WorkflowRegistry()
