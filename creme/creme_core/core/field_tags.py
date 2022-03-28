# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2009-2022 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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
