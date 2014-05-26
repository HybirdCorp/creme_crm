# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.db import transaction, IntegrityError


logger = logging.getLogger(__name__)


def generate_string_id_and_save(model, objects, prefix):
    if not objects:
        return

    assert not prefix[-1].isdigit()

    #id_list = model.objects.filter(id__startswith=prefix).values_list('id', flat=True)
    prefix_len = len(prefix)
    #TODO: query with regex instead ?
    id_list = [int(suffix)
                    for suffix in (id_str[prefix_len:]
                                        for id_str in model.objects
                                                           .filter(id__startswith=prefix)
                                                           .values_list('id', flat=True)
                                  )
                        if suffix.isdigit()
              ]
    #TODO: do-able in SQL ????
    #TODO: would it be cool to fill the 'holes' in id ranges ???
    #index = max(int(string[prefix_len:]) for string in id_list) if id_list else 0
    index = max(id_list) if id_list else 0
    last_exception = None

    #We use transaction because the IntegrityError aborts the current transaction on PGSQL
    with transaction.commit_manually():
        try:
            for obj in objects:
                for i in xrange(1000): #avoid infinite loop
                    sid = transaction.savepoint()
                    index += 1
                    obj.id = prefix + str(index)

                    try:
                        obj.save(force_insert=True)
                    except IntegrityError as e: #an object with this id already exists
                        #TODO: indeed it can be raise if the given object if badly build.... --> improve this (detect the guilty column)???
                        logger.debug('generate_string_id_and_save(): id "%s" already exists ? (%s)', obj.id, e)
                        last_exception = e
                        obj.pk = None

                        transaction.savepoint_rollback(sid)
                    else:
                        transaction.savepoint_commit(sid)
                        break
                else:
                    raise last_exception #use transaction to delete saved objects ????
        except Exception:
            transaction.rollback()
            #logger.exception('generate_string_id_and_save') #we noticed that it breaks rollback feature...
            raise
        else:
            transaction.commit()
