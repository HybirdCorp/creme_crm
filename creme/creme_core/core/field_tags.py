# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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


class InvalidFieldTag(Exception):
    pass


def _add_tags_to_fields():
    """Hook Django models.Field to add a tag system.
    DO NOT CALL THIS METHOD, CREME DO IT FOR YOU !!
    """
    from django.db.models import Field, AutoField, OneToOneField, ForeignKey
    from django.contrib.contenttypes.models import ContentType

    def _set_tags(self, **kwargs):
        for tag_name in ('clonable', 'viewable', 'enumerable'):
            value = kwargs.pop(tag_name, None)
            if value is not None:
                setattr(self, '_cremetag_%s' % tag_name, value)

        if kwargs:
            raise InvalidFieldTag('Unknown tag(s) : %s' % kwargs.keys())

        return self

    def _get_tag(self, tag_name):
        try:
            return getattr(self, '_cremetag_%s' % tag_name)
        except AttributeError:
            raise InvalidFieldTag('Unknown tag : %s' % tag_name)

    Field.set_tags = _set_tags
    Field.get_tag  = _get_tag

    #viewable
    Field._cremetag_viewable = True
    AutoField._cremetag_viewable = False
    OneToOneField._cremetag_viewable = False

    #clonable
    Field._cremetag_clonable = True
    AutoField._cremetag_clonable = False
    OneToOneField._cremetag_clonable = False

    #enumerable
    Field._cremetag_enumerable = False
    ForeignKey._cremetag_enumerable = True
    OneToOneField._cremetag_enumerable = False

    #TODO: could become useless with HeaderFilter refactoring, that ignores
    #      by default the sub fields of FK. (to be continued...)
    #ContentType hooking
    #get_ct_field = ContentType._meta.get_field_by_name
    get_ct_field = ContentType._meta.get_field
    for fname in ('name', 'app_label', 'model'):
        #get_ct_field(fname)[0].set_tags(viewable=False)
        get_ct_field(fname).set_tags(viewable=False)
