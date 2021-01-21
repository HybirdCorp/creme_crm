# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2021 Hybird
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
from typing import Type

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class Replacer:
    type_id: str = 'OVERRIDE'

    def __init__(self, *, model_field):
        self.model_field = model_field

    def as_dict(self) -> dict:
        field = self.model_field

        return {
            'ctype': ContentType.objects.get_for_model(field.model).natural_key(),
            'field': field.name,
        }

    @classmethod
    def from_dict(cls, d: dict):
        raise NotImplementedError

    def get_value(self):
        raise NotImplementedError


class ReplacersRegistry:
    __slots__ = ('_replacer_classes', )

    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._replacer_classes = {}

    def __call__(self, cls: Type[Replacer]):
        if self._replacer_classes.setdefault(cls.type_id, cls) is not cls:
            raise self.RegistrationError(f'Duplicated Replacer id: {cls.type_id}')

        return cls

    # TODO ?
    # def __getitem__(self, type_id):
    #     return self._replacer_classes[type_id]

    def serialize(self, replacers):
        return [
            [r.type_id, r.as_dict()] for r in replacers
        ]

    def deserialize(self, data):
        assert isinstance(data, list)
        replacers = []

        for replacer_data in data:
            assert isinstance(replacer_data, list)
            assert len(replacer_data) == 2

            type_id, instance_data = replacer_data
            assert isinstance(type_id, str)
            assert isinstance(instance_data, dict)

            replacers.append(self._replacer_classes[type_id].from_dict(instance_data))

        return replacers


REPLACERS_MAP = ReplacersRegistry()


@REPLACERS_MAP
class FixedValueReplacer(Replacer):
    type_id = 'fixed_value'

    def __init__(self, *, model_field, value=None):
        super().__init__(model_field=model_field)
        self._fixed_value = value

    def __str__(self):
        value = self._fixed_value
        rel_field = self.model_field

        if value:
            return _('In «{model} - {field}», replace by «{new}»').format(
                model=rel_field.model._meta.verbose_name,
                field=rel_field.verbose_name,
                new=value,
            )

        msg = (
            _('Remove from «{model} - {field}»')
            if rel_field.many_to_many else
            _('Empty «{model} - {field}»')
        )

        return msg.format(
            model=rel_field.model._meta.verbose_name,
            field=rel_field.verbose_name,
        )

    def as_dict(self):
        d = super().as_dict()

        value = self._fixed_value
        if value is not None:
            d['pk'] = value.pk

        return d

    @classmethod
    def from_dict(cls, d):
        ctype = ContentType.objects.get_by_natural_key(*d['ctype'])
        fk = ctype.model_class()._meta.get_field(d['field'])
        pk = d.get('pk')

        if pk is None:
            value = None
        else:
            model = fk.remote_field.model
            try:
                value = model._default_manager.get(pk=pk)
            except model.DoesNotExist:
                logger.exception('Error in FixedValueReplacer.from_dict()')
                value = None

        return cls(model_field=fk, value=value)

    def get_value(self):
        return self._fixed_value


@REPLACERS_MAP
class SETReplacer(Replacer):
    type_id = 'SET'

    def __str__(self):
        fk = self.model_field

        return _('In «{model} - {field}», replace by a fallback value').format(
            model=fk.model._meta.verbose_name,
            field=fk.verbose_name,
        )

    @classmethod
    def from_dict(cls, d):
        # TODO: factorise
        ctype = ContentType.objects.get_by_natural_key(*d['ctype'])
        fk = ctype.model_class()._meta.get_field(d['field'])

        return cls(model_field=fk)

    def get_value(self):
        captured_value = None

        # NB: we get the value passed to SET()
        class CapturingValueCollector:
            def add_field_update(self, field, value, objs):
                nonlocal captured_value
                captured_value = value

        self.model_field.remote_field.on_delete(
            collector=CapturingValueCollector(),
            field=None,
            sub_objs=None,
            using=None,
        )

        return captured_value
