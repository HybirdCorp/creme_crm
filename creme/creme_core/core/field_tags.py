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

from enum import Enum


class FieldTag(Enum):
    CLONABLE = 'clonable'
    VIEWABLE = 'viewable'
    ENUMERABLE = 'enumerable'
    OPTIONAL = 'optional'

    @classmethod
    def is_valid(cls, value):
        try:
            cls(value)
        except ValueError:
            return False

        return True

    def __str__(self):
        return self.value


class InvalidFieldTag(Exception):
    pass


def _add_tags_to_fields():
    """Hook Django models.Field to add a tag system.
    DO NOT CALL THIS METHOD, CREME DOES IT FOR YOU !!
    """
    from django.db.models import (
        AutoField,
        Field,
        ForeignKey,
        ManyToManyField,
        OneToOneField,
        UUIDField,
    )

    def _set_tags(self, **kwargs):
        # for tag_name in ('clonable', 'viewable', 'enumerable', 'optional'):
        for tag in FieldTag:
            tag_name = tag.value
            value = kwargs.pop(tag_name, None)
            if value is not None:
                setattr(self, f'_cremetag_{tag_name}', value)

        if kwargs:
            raise InvalidFieldTag(f'Unknown tag(s) : {kwargs.keys()}')

        return self

    # def _get_tag(self, tag_name):
    def _get_tag(self, tag):
        tag_name = tag.value if isinstance(tag, FieldTag) else tag
        try:
            return getattr(self, f'_cremetag_{tag_name}')
        except AttributeError as e:
            raise InvalidFieldTag(f'Unknown tag : {tag_name}') from e

    Field.set_tags = _set_tags
    Field.get_tag  = _get_tag

    # FieldTag.VIEWABLE
    Field._cremetag_viewable = True
    AutoField._cremetag_viewable = False
    OneToOneField._cremetag_viewable = False

    # FieldTag.CLONABLE
    Field._cremetag_clonable = True
    AutoField._cremetag_clonable = False
    OneToOneField._cremetag_clonable = False
    UUIDField._cremetag_clonable = False

    # FieldTag.ENUMERABLE
    Field._cremetag_enumerable = False
    ForeignKey._cremetag_enumerable = True
    ManyToManyField._cremetag_enumerable = True
    OneToOneField._cremetag_enumerable = False

    # FieldTag.OPTIONAL
    Field._cremetag_optional = False
