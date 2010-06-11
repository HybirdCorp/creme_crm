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

#from creme_core.models import CremeProperty, CremePropertyType
#from creme_core.models import Property_i18n


#def translate_property(property_id):
    #return CremePropertyLabel.objects.filter(id=property_id)[0].text

#def get_property_id_for_property_name(property_name):
    #return  Property_i18n.objects.filter(i18n_text=property_name)[0].property_label.id

#TODO: not used ???
#TODO: improve SQL ???
#def get_list_property_that_name_contains(name):
    #list = Property_i18n.objects.filter(i18n_text__contains=name)
    #pk_list = [item.property_label.id for item in list]
    #return pk_list
 