# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.db.models.base import Model
from django.urls.base import reverse

from creme.creme_core.models.entity import CremeEntity
from creme.creme_core.utils.collections import InheritedDataChain


class UIAction:
    """An Instance of UIAction represent an action the user can do in the UI,
    like edit an entity, or merge to entities.

    Attributes:
        - id: Unique ID used to register & retrieve the UIAction (see ActionsRegistry) ;
            use generate_id() to build it.
        - model: Class inheriting djnago.db.model.Model ; indicates what kind of
            model is concerned by this UIAction.
        - type: Used by the GUI (ie: JavaScript) to use the good behaviour.
            The built-in type "redirect" can be to redirect the page to a new URL
            (it's to make download view too).
            Other existing types: "delete", "clone", "edit-selection"...
        - url_name: String to reverse() the URL to use (see @url).
        - label: String displayed to the user for this UIAction.
            Should be translatable (ie: ugettext_lazy) .
        - icon: Name of the icon used in the UI with our Icon system. Eg: "edit".
        - help_text: Should be translatable (ie: ugettext_lazy).
        - is_default: Boolean. True means the UIAction should be the one the user see first.
        - is_is_visible: Boolean. If False, the user should not see this action.
        - is_enabled: Boolean. If False, this UIAction cannot be activated by the user
            (not allowed, some business logic not OK...).
    """
    id = None
    model = None

    type = ''
    url_name = None

    label = ''
    icon = ''
    help_text = ''

    is_default = False
    is_visible = True
    is_enabled = True

    @staticmethod
    def generate_id(app_label, name):
        return '{}-{}'.format(app_label, name)

    def __init__(self, user, model=None, instance=None, **kwargs):
        self.user = user
        self.instance = instance

        if model is None and instance is not None:
            model = instance.__class__

        if model is not None:
            self.model = model

        assert self.model is not None

    def _get_options(self):
        return None

    def _get_data(self):
        return None

    @property
    def ctype(self):
        """Returns the ContentType corresponding to the model."""
        return ContentType.objects.get_for_model(self.model)

    @property
    def action_data(self):
        """Returns some JSONifiable data the UI will need."""
        options = self._get_options()
        data = self._get_data()
        action_data = None

        if options or data:
            action_data = {
                'options': options or {},
                'data': data or {},
            }

        return action_data

    @property
    def url(self):
        return reverse(self.url_name)


class EntityAction(UIAction):
    model = CremeEntity


class BulkAction(UIAction):
    """Specialization of UIAction which can operate on several instances at once.

    Attributes:
        - bulk_max_count: Maximum number of instances which is manage.
            None means <no limit>.
        - bulk_min_count: Minimum number of instances which is needed.
    """
    bulk_max_count = None
    bulk_min_count = 1


class BulkEntityAction(BulkAction):
    model = CremeEntity


class ActionRegistrationError(Exception):
    pass


class VoidAction:
    """Specific Action class used internally to remove an UIAction
    for a specific model.

    See ActionsRegistry.void_instance_actions() & void_bulk_actions().
    """
    pass


class ActionsChain(InheritedDataChain):
    """Collections of UIActions per model.

    Register & retrieve classes (inheriting UIAction) corresponding to a model.

    NOTICE: the inheritance of the model is respected. It means that if a
    class B inherits the class A, B get the actions registered for A & B.
    And you can override an UIAction of A with another UIAction for B.
    """
    def __init__(self, base_class=UIAction):
        """Constructor.

        @param base_class: Class inheriting UIAction. The classes registered
               must be sub-classes of this base class.
        """
        super().__init__(dict)
        self.base_class = base_class

    def _inherited_actions(self, model):
        result = {}

        for model_dict in self.chain(model):
            result.update(model_dict)

        return result

    def actions(self, model):
        """Get a list of UIAction classes corresponding to a model."""
        return [
            a for a in self._inherited_actions(model).values()
                if not issubclass(a, VoidAction)
        ]

    # TODO ?
    # def get_action(self, action_id, model):
    #     for model_dict in self.chain(model, parent_first=False):
    #         a = model_dict.get(action_id)
    #
    #         if a is not None:
    #             return a if not issubclass(a, VoidAction) else None

    def _register_action(self, action_class, action_id, model):
        registered = self[model].setdefault(action_id, action_class)

        if registered is not action_class:
            if issubclass(action_class, VoidAction):
                raise ActionRegistrationError(
                    "Unable to void action '{}'. "
                    "An action is already defined for model {}".format(action_id, model)
                )

            raise ActionRegistrationError("Duplicated action '{}' for model {}".format(action_id, model))

    def register_actions(self, *action_classes):
        """Register several UIAction classes.

        @param action_classes: Classes inheriting the base_class (see __init__).
        @raise: ActionRegistrationError (duplicate)
        """
        validate = self._validate_action_class
        register = self._register_action

        for action_class in action_classes:
            register(validate(action_class), action_class.id, action_class.model)

    def _validate_action_class(self, action_class):
        if not issubclass(action_class, self.base_class):
            raise ActionRegistrationError(
                '{} is not a <{}>'.format(action_class, self.base_class.__name__)
            )

        if getattr(action_class, 'model', None) is None:
            raise ActionRegistrationError(
                "Invalid action {}: 'model' attribute must be defined".format(action_class)
            )

        if not issubclass(action_class.model, Model):
            raise ActionRegistrationError(
                "Invalid action {}: {} is not a Django Model".format(action_class, action_class.model)
            )

        if getattr(action_class, 'id', None) is None:
            raise ActionRegistrationError(
                "Invalid action {}: 'id' attribute must be defined".format(action_class)
            )

        return action_class

    def void_actions(self, model, *action_classes):
        """Mask several inherited UIActions.

        If a model inherits some UIActions classes from one of its parent model,
        you can mask them (ie: the method action() will not return them).

        @param model: Class inheriting <django.db.model.Model>.
        @param action_classes: Classes inheriting the base_class (see __init__).
        """
        register = self._register_action

        for action_class in action_classes:
            # TODO ?
            # action_id = action_class if isinstance(action_class, str) else action_class.id
            register(VoidAction, action_id=action_class.id, model=model)


class ActionsRegistry:
    """Registry for UIAction with 2 groups of actions:
      - action which operate on 1 instance (called "instance action").
      - actions which operate on several instances (called "bulk actions").

    It is used in the list-view to build the 'actions' columns. In the header
    there is the menu for bulk actions, & in each line there is the menu for
    the instance actions.
    """
    __slots__ = (
        '_instance_action_classes',
        '_bulk_action_classes',
    )

    def __init__(self, instance_chain_class=ActionsChain, bulk_chain_class=ActionsChain):
        self._instance_action_classes = instance_chain_class(base_class=UIAction)
        self._bulk_action_classes = bulk_chain_class(base_class=BulkAction)

    # def is_registered_for_instance(self, model, action):
    #     return self.instance_action(model, action.id) is not None
    #
    # def is_registered_for_bulk(self, model, action):
    #     return self.bulk_action(model, action.id) is not None

    # TODO ? (return instance)
    # def instance_action(self, model, action_id):
    #     return self._instance_action_classes.get_action(action_id=action_id, model=model)
    #
    # def bulk_action(self, model, action_id):
    #     return self._bulk_action_classes.get_action(action_id=action_id, model=model)

    def instance_action_classes(self, model):
        """Get the list of the classes for instances actions registered for a model.
        NB: use the method instance_actions() if you want instances of UIActions
            (which can be used to build a UI, contrarily to the class).
        """
        return self._instance_action_classes.actions(model=model)

    def _instance_actions_kwargs(self, user, instance):
        return {
            'user': user,
            'model': instance.__class__,
            'instance': instance,
        }

    def instance_actions(self, user, instance):
        """Generator of instance actions.

        @param user: User which displays the UI (used for credentials)
        @param instance: Instance of a model.
        @return: Instance of UIActions corresponding to the action classes
                 registered for the instance's model (see
                 register_instance_actions()).
        """
        model = instance.__class__
        kwargs = self._instance_actions_kwargs(user=user, instance=instance)

        for action_class in self.instance_action_classes(model=model):
            yield action_class(**kwargs)

    def bulk_action_classes(self, model):
        """Get the list of the classes for bulk actions registered for a model.
        NB: use the method instance_actions() if you want instances of BulkActions
            (which can be used to build a UI, contrarily to the class).
        """
        return self._bulk_action_classes.actions(model=model)

    def _bulk_actions_kwargs(self, user, model):
        return {
            'user': user,
            'model': model,
        }

    def bulk_actions(self, user, model):
        """Generator of bulk actions.

        @param user: User which displays the UI (used for credentials)
        @param model: Class inheriting <django.db.model.Model>.
        @return: Instance of BulkActions corresponding to the action classes
                 registered for the given model (see
                 register_bulk_actions()).
        """
        ctxt = self._bulk_actions_kwargs(user=user, model=model)

        for action_class in self.bulk_action_classes(model):
            yield action_class(**ctxt)

    def register_instance_actions(self, *action_classes):
        """Register several instances actions.
        @param action_classes: Classes inheriting UIAction.
        """
        self._instance_action_classes.register_actions(*action_classes)

    def register_bulk_actions(self, *action_classes):
        """Register several bulk actions.
        @param action_classes: Classes inheriting BulkAction.
        """
        self._bulk_action_classes.register_actions(*action_classes)

    def void_instance_actions(self, model, *action_classes):
        """Mask several instance actions for a specific model.

        If a model inherits some UIActions classes from one of its parent model,
        you can mask them (ie: the method instance_actions() will not return
        instance of them).

        @param model: Class inheriting <django.db.model.Model>.
        @param action_classes: Classes inheriting UIAction.
        """
        self._instance_action_classes.void_actions(model, *action_classes)

    def void_bulk_actions(self, model, *action_classes):
        """Like void_instance_actions() but for bulk actions."""
        self._bulk_action_classes.void_actions(model, *action_classes)


actions_registry = ActionsRegistry()
