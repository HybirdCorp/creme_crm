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

from logging import debug

from django.db import IntegrityError


def generate_string_id_and_save(model, objects, prefix):
    if not objects:
        return

    id_list = model.objects.filter(id__startswith=prefix).values_list('id', flat=True)
    prefix_len= len(prefix)
    #TODO: do-able in SQL ????
    #TODO: would it be cool to fill the 'holes' in id ranges ???
    index = max(int(string[prefix_len:]) for string in id_list) if id_list else 0

    last_exception = None

    for obj in objects:
        for i in xrange(1000): #avoid infinite loop.....
            index += 1
            obj.id = prefix + str(index)

            try:
                obj.save(force_insert=True)
            except IntegrityError, e:  #an object with this id already exists
                #TODO: indeed it can be raise if the given object if badly build.... --> improve this (detect the guilty column)???
                debug('gen_id_and_save(): id %s already exists ? (%s)', obj.id, e)
                last_exception = e
                obj.pk = None
            else:
                break
        else:
            raise last_exception #use transaction to delete saved objects ????
