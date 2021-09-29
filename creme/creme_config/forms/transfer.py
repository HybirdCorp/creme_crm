# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2021  Hybird
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
from collections import defaultdict
from json import loads as json_load

from django.db.transaction import atomic
from django.forms import FileField, ValidationError
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm, FieldBlockManager

from ..core.importers import IMPORTERS

logger = logging.getLogger(__name__)


class ImportForm(CremeForm):
    config = FileField(
        label=_('Configuration file'),
        help_text=_(
            'A JSON file created with the export button '
            '(generally in another Creme instance).'
        ),
        # max_length=
    )

    error_messages = {
        'invalid_json':    _('File content is not valid JSON.'),
        'invalid_data':    _('File content is not valid (%(error)s).'),
        'invalid_version': _('The file has an unsupported version.'),
    }

    blocks = FieldBlockManager({
        'id': 'general', 'label': _('Configuration file'), 'fields': '*',
    })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._importers = IMPORTERS.build_importers()

    def clean_config(self):
        config = self.cleaned_data['config']

        try:
            deserialized_data = json_load('\n'.join(line.decode() for line in config))
        except Exception as e:
            logger.warning('ImportForm: invalid JSON (%s)', e)
            raise ValidationError(
                self.error_messages['invalid_json'], code='invalid_json',
            )
        else:
            if not isinstance(deserialized_data, dict):
                raise ValidationError(
                    self.error_messages['invalid_data'],
                    params={'error': gettext('main content must be a dictionary')},
                    code='invalid_data',
                )

            # see ..views.transfer.ConfigExport
            if deserialized_data.get('version') != '1.2':
                raise ValidationError(
                    self.error_messages['invalid_version'], code='invalid_version',
                )

            validated_data = defaultdict(set)

            try:
                for importer in self._importers:
                    importer.validate(
                        deserialized_data=deserialized_data,
                        validated_data=validated_data,
                    )
            except ValidationError:
                raise
            except Exception as e:
                logger.exception('Error in ImportForm.clean_config()')
                raise ValidationError(
                    self.error_messages['invalid_data'],
                    params={'error': e}, code='invalid_data',
                )

        return config

    @atomic
    def save(self):
        try:
            for importer in self._importers:
                importer.save()
        except Exception:
            logger.exception('error when saving imported data.')
            raise
