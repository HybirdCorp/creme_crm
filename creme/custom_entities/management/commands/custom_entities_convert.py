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

import os
import unicodedata
from collections.abc import Iterator
from random import randint
from re import sub as re_sub

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import CommandError
from django.core.management.templates import TemplateCommand

import creme
from creme.creme_core.core.value_maker import (
    DateMaker,
    DateTimeMaker,
    NoneMaker,
)
from creme.creme_core.models import (
    CustomEntityType,
    CustomField,
    CustomFieldEnumValue,
)


# TODO: in core.utils ??
def snake_casify(value):
    """
    Convert a string (e.g. a label filled by a user) into a valid Python variable name.
    >> snake_casify("Saveur du café")
    saveur_du_cafe
    """
    value = (
        unicodedata.normalize('NFKD', value)
        .encode('ascii', 'ignore')
        .decode('ascii')
    )
    # \w => alphanumerics & _
    # \s => whitespace characters
    value = re_sub(r'[^\w\s-]', '', value.lower())
    value = re_sub(r'[-\s]+', '_', value).strip('_')

    if not value:
        value = f'placeholder{randint(0, 1024)}'
    elif value[0].isdigit():
        value = f'a_{value}'

    return value


# TODO: in core.utils ??
def camel_casify(value):
    """
    Convert a string (e.g. a label filled by a user) into a valid Python type name.
    >> camel_casify("Saveur du café")
    SaveurDuCafe
    """
    value = (
        unicodedata.normalize('NFKD', value)
        .encode('ascii', 'ignore')
        .decode('ascii')
    )
    # \w => alphanumerics & _
    # \s => whitespace characters
    value = re_sub(r'[^\w\s-]', '', value.title())
    value = re_sub(r'[-\s]+', '', value)

    if not value:
        value = f'PlaceHolder{randint(0, 1024)}'
    elif value[0].isdigit():
        value = f'A{value}'

    return value


class MinionInfo:
    """Information to build a MinionModel class."""
    def __init__(self, cfield):
        name = cfield.name
        self.name = camel_casify(name)
        self.snake_name = snake_casify(name)
        self.verbose_name = name
        self.instances_info = [
            {
                'name': enum_value.value.replace('"', r'\"'),
                'uuid': str(enum_value.uuid)
            }
            for enum_value in CustomFieldEnumValue.objects.filter(
                custom_field=cfield,
            )
        ]


class FieldConverter:
    """Information to build a regular model field corresponding to a specific
    type of CustomField.
    """
    cls_name: str = 'models.Field'
    default_attrs = {}
    # Note: 'from django.db import models' is already imported
    default_imports: list[str] = []

    def __init__(self, cfield):
        self._cfield = cfield
        self._name = snake_casify(cfield.name)
        self._minion = None
        self._extra_imports: list[str] = []

        maker = cfield.default_value_maker
        self._default_value = (
            None if isinstance(maker, NoneMaker) else self._build_default_value(maker)
        )

    def _build_default_value(self, maker):
        return repr(maker.make())

    def cls_attributes(self) -> dict:
        """Attributes of the regular field declaration.
        e.g {'max_length': 100}
        """
        cfield = self._cfield
        attrs = {
            'verbose_name': f'_("{cfield.name}")',
            **self.default_attrs,
        }

        if cfield.is_required:
            attrs['required'] = 'True'

        description = cfield.description
        if description:
            description = description.replace('"', r'\"')
            attrs['help_text'] = f'_("{description}")'

        defval = self._default_value
        if defval is not None:
            attrs['default'] = defval

        return attrs

    @property
    def name(self):
        "Name of the field in the model-class declaration."
        return self._name

    @property
    def minion(self) -> MinionInfo | None:
        "Related MinionModel if the field is ForeignKey/ManyToManyField"
        return self._minion

    @property
    def imports(self) -> Iterator[str]:
        yield from self.default_imports
        yield from self._extra_imports


class IntegerFieldConverter(FieldConverter):
    cls_name = 'models.IntegerField'


class DecimalFieldConverter(FieldConverter):
    cls_name = 'models.DecimalField'
    default_attrs = {'max_digits': 12, 'decimal_places': 2}

    def _build_default_value(self, maker):
        self._extra_imports.append('from decimal import Decimal')

        return super()._build_default_value(maker=maker)


class BooleanFieldConverter(FieldConverter):
    cls_name = 'models.BooleanField'
    default_attrs = {'default': False}


class StringFieldConverter(FieldConverter):
    cls_name = 'models.CharField'
    default_attrs = {'max_length': 100}


class TextFieldConverter(FieldConverter):
    cls_name = 'models.TextField'


class URLFieldConverter(FieldConverter):
    cls_name = 'CremeURLField'
    default_attrs = {'max_length': 200}
    default_imports = ['from creme.creme_core.models.fields import CremeURLField']


class DateFieldConverter(FieldConverter):
    cls_name = 'models.DateField'

    def _build_default_value(self, maker):
        assert isinstance(maker, DateMaker)
        if maker._date is None:
            self._extra_imports.append('import datetime')
            return 'datetime.date.today'

        return super()._build_default_value(maker=maker)


class DateTimeFieldConverter(FieldConverter):
    cls_name = 'models.DateTimeField'

    def _build_default_value(self, maker):
        assert isinstance(maker, DateTimeMaker)
        if maker._dt is None:
            self._extra_imports.append('from django.utils.timezone import now')
            return 'now'

        return super()._build_default_value(maker=maker)


class _BaseEnumFieldConverter(FieldConverter):
    def __init__(self, cfield):
        super().__init__(cfield=cfield)
        self._minion = MinionInfo(cfield)

    def cls_attributes(self):
        return {
            'to': self._minion.name,  # Dict keeps orders => this attribute will be first
            **super().cls_attributes(),
        }


class EnumFieldConverter(_BaseEnumFieldConverter):
    cls_name = 'models.ForeignKey'
    default_attrs = {'on_delete': 'CREME_REPLACE'}
    default_imports = ['from creme.creme_core.models import CREME_REPLACE']


class MultiEnumFieldConverter(_BaseEnumFieldConverter):
    cls_name = 'models.ManyToManyField'


FIELD_CONVERTERS = {
    CustomField.INT:        IntegerFieldConverter,
    CustomField.FLOAT:      DecimalFieldConverter,
    CustomField.BOOL:       BooleanFieldConverter,
    CustomField.STR:        StringFieldConverter,
    CustomField.TEXT:       TextFieldConverter,
    CustomField.URL:        URLFieldConverter,
    CustomField.DATE:       DateFieldConverter,
    CustomField.DATETIME:   DateTimeFieldConverter,
    CustomField.ENUM:       EnumFieldConverter,
    CustomField.MULTI_ENUM: MultiEnumFieldConverter,
}


# ---
class Command(TemplateCommand):
    help = (
        'Create an app (in the current directory) containing a CremeEntity model '
        'corresponding to a CustomEntity. This code can be used to convert a '
        'prototype made with a CustomEntity into a "real" app. '
        'NB #1: the generated code is not made to convert data of existing instances of entity. '
        'NB #2: the generated code is not complete; you should probably rename some models '
        '(which have been named from labels), complete unit tests, improve the '
        'script "populate.py" (see TODOs), then generate initial migration, locale.'
    )

    def add_arguments(self, parser):
        add_arg = parser.add_argument
        add_arg(
            '-i', '--id',
            action='store', dest='type_id', type=int,
            help='ID of the model to convert; use the "--list" argument to see available IDs.',
        )
        add_arg(
            '-l', '--list',
            action='store_true', dest='list_mode', default=False,
            help='Only display the available custom entity models to convert '
                 '[default: %(default)s]',
        )

    def _get_custom_types(self):
        return CustomEntityType.objects.filter(enabled=True).order_by('id')

    def handle(self, **options):
        # verbosity = options.get('verbosity')  TODO

        if options.get('list_mode'):
            ce_types = self._get_custom_types()

            if not ce_types:
                self.stdout.write('There is no enabled custom entity model.')
            else:
                for ce_type in ce_types:
                    self.stdout.write(f' - id={ce_type.id}: name="{ce_type.name}"')
        else:  # Creation mode
            ce_type_id = options.get('type_id')
            if ce_type_id is None:
                raise CommandError(
                    'The argument "--id" is required when "--list" is not used.'
                )

            try:
                ce_type = self._get_custom_types().get(id=ce_type_id)
            except CustomEntityType.DoesNotExist as e:
                raise CommandError(
                    'The ID is invalid. Hint: use "--list" to see valid IDs.'
                ) from e

            snake_case_entity_model_name = snake_casify(ce_type.name)

            field_converters = [
                FIELD_CONVERTERS[cfield.field_type](cfield=cfield)
                for cfield in CustomField.objects.filter(
                    content_type=ContentType.objects.get_for_model(ce_type.entity_model),
                )
            ]
            field_imports = {
                extra_import for fc in field_converters for extra_import in fc.imports
            }

            super().handle(
                app_or_project='app',
                name=f'{snake_case_entity_model_name}s',
                target=None,  # TODO?
                extensions=['py'],  # TODO: class attribute?
                files=[],
                template=os.path.join(
                    creme.__path__[0], 'custom_entities', 'conf', 'app_template',
                ),

                ce_type=ce_type,
                entity_model_name=camel_casify(ce_type.name),
                snake_case_entity_model_name=snake_case_entity_model_name,
                field_imports=sorted(field_imports),
                fields=field_converters,
                has_minions=any(fc.minion is not None for fc in field_converters),
                **options
            )
