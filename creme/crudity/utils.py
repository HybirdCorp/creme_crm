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

import base64
import struct
import uuid
import warnings
from typing import Tuple, Type

from django.db.models import Model

from creme.creme_core.models import SettingValue

from .setting_keys import sandbox_key


def is_sandbox_by_user() -> bool:
    return SettingValue.objects.get_4_key(sandbox_key, default=False).value


def strip_html(text: str) -> str:
    warnings.warn(
        'crudity.utils.strip_html() is deprecated ; '
        'use creme_core.utils.html.strip_html() instead.',
        DeprecationWarning,
    )

    from creme.creme_core.utils.html import strip_html
    return strip_html(text)


def generate_guid_for_field(urn: str,
                            model: Type[Model],
                            field_name: str) -> str:
    return '{%s}' % str(uuid.uuid5(
        uuid.NAMESPACE_X500,
        f'{urn}.{model._meta.object_name}.{field_name}'
    )).upper()


def decode_b64binary(blob_b64: bytes) -> Tuple[str, bytes]:
    """Decode base64binary encoded files
    (Usually found in xsd:base64Binary http://www.w3.org/TR/xmlschema-2/#base64Binary)
    @param blob_b64: <bytes> data encoded in base64.
    @return: A tuple (file_name, decoded_data) ; "file_name" is a str, "decoded_data" bytes.
    """
    blob_str = base64.decodebytes(blob_b64)
    blob_str_len = len(blob_str)

    header, filesize, filename_len, rest = struct.unpack(
        '16sII{}s'.format(blob_str_len - 16 - 2 * 4),
        blob_str,
    )
    filename_len *= 2

    header, filesize, filename_len, filename, blob = struct.unpack(
        '16sII{}s{}s'.format(filename_len, (blob_str_len - 16 - 2 * 4 - filename_len)),
        blob_str,
    )

    filename = ''.join(
        chr(i)
        for i in struct.unpack('{}h'.format(len(filename) // 2), filename)
        if i > 0
    )
    filename = str(filename.encode('utf8'))

    return filename, blob
