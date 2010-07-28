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

from django.db.models import Q

def get_q_from_dict(dict, is_or=False):
    """
        @Returns: A Q instance from {'attr1':'val1', 'attr2':'val2',...}
        If is_or returns Q(attr1=val1) | Q(attr2=val2)
        else returns Q(attr1=val1) & Q(attr2=val2)
        Tip : Add ~ in the attr negate the Q
            Example :
                d = {'~attr1':'val1', 'attr2':'val2',...}
                returns ~Q(attr1=val1) & Q(attr2=val2)
    """
    q = Q()
    for k, v in dict.items():
        k = str(k)
        unused, is_not, req = k.rpartition("~")
        if bool(is_not):
          sub_q = ~Q(**{req:v})
        else:
          sub_q = Q(**{req:v})

        if is_or:
            q |= sub_q
        else:
            q &= sub_q

    return q