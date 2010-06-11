# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.encoding import smart_str

from creme_core.models import RelationType, RelationPredicate_i18n


def translate_predicate(predicat_id):
    #TODO: use values_list()....
    return smart_str(RelationType.objects.get(id=predicat_id).predicate)

def get_predicat_id_for_predicat_name(predicat_name):
    #TODO: use values_list()....
    return RelationPredicate_i18n.objects.filter(text=predicat_name)[0].relation_type_id

#COMMENT2 le 25/04/2010
#def get_list_predicat_that_name_contains(name):
    ##TODO: use values_list()....
    #list = RelationPredicate_i18n.objects.filter(text__contains=name)
    #return [item.predicate.id for item in list]
