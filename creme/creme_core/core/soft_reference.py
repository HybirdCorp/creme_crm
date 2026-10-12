################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from collections.abc import Iterator
from typing import Self

from django.db.models import Model


class SoftReferenceCollector:
    """Base class for collectors of soft references which protect against deletion.

    A soft reference is a reference to an instance stored in the SQL DataBase
    which does not use the Foreign Keys of SQL. Typically it's a UUID-string
    stored in a CharField or in a JSONField (e.g. the conditions of filters like
    'The field "Status" is the instance with uuid="abcd1123-..."').

    We collect the soft references which prevent the deletion of a instance,
    like an attribute <on_delete=PROTECT> on a ForeigKey field.
    """
    # Unique string to identify the class inside the registry (see SoftReferenceRegistry).
    # As usual you should prefix this id by "my_app-".
    id: str = ''
    # Model of the instances which are collected by the class; the argument
    # 'instance' passed to the method 'collect()' should be an instance of this model.
    model: type[Model] = Model

    # TODO: instanceS?
    def collect(self, instance: Model) -> Iterator[Model]:
        """Yield instances containing a soft reference to the given instance."""
        raise NotImplementedError


class SoftReferenceRegistry:
    """Registry of SoftReferenceCollector classes.

    See CremeAppConfig.register_soft_collectors().
    """
    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    _collector_classes: dict[str, type[SoftReferenceCollector]]

    def __init__(self):
        self._collector_classes = {}

    @property
    def collector_classes(self) -> Iterator[type[SoftReferenceCollector]]:
        """Generator for all registered classes."""
        yield from self._collector_classes.values()

    def register(self, *collector_classes: type[SoftReferenceCollector]) -> Self:
        """Register several classes at once.
        @raise SoftReferenceRegistry.RegistrationError if:
               - Some IDs are empty.
               - Some IDs are duplicated.
        """
        collectors = self._collector_classes

        for cls in collector_classes:
            type_id = cls.id

            if not type_id:
                raise self.RegistrationError(
                    f"Collector class with empty id: {cls}",
                )

            if type_id in collectors:
                raise self.RegistrationError(
                    f"Collector class with duplicated id: {cls}",
                )

            collectors[type_id] = cls

        return self

    def unregister(self, collector_class: type[SoftReferenceCollector]) -> Self:
        """Unregister a class.
        @raise SoftReferenceRegistry.UnRegistrationError if the ID is not found.
        """
        if self._collector_classes.pop(collector_class.id, None) is None:
            raise self.UnRegistrationError(
                f'Invalid collector {collector_class} (already unregistered?)'
            )

        return self

    # TODO: instanceS?
    # TODO: limit?
    def collect(self, instance: Model) -> Iterator[Model]:
        """Yield all the instances containing at least one soft reference to the
        given instance.
        """
        for collector_cls in self._collector_classes.values():
            if issubclass(type(instance), collector_cls.model):
                yield from collector_cls().collect(instance=instance)


soft_reference_registry = SoftReferenceRegistry()
