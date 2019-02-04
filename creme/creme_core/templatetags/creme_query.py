# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2019  Hybird
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

from django.template import Library

from ..auth.entity_credentials import EntityCredentials
from ..models import CremeEntity
from ..utils.queries import QSerializer

register = Library()
__serializer = QSerializer()


@register.simple_tag
def query_entities_count(ctype, user):
    """Returns the number of viewable entities with a specific type, in a fast way.

    @param ctype: A ContentType instance (related to a CremeEntity model).
    @param user: (Creme)User instance.
    @return: Integer.
        {% load creme_ctype creme_query %}

        {% ctype_for_swappable 'PERSONS_CONTACT_MODEL' as contact_ctype %}
        {% query_entities_count ctype=contact_ctype user=user as contacts_count %}
        <p>Number of Contact(s): {{contacts_count}}</p>
    """
    model = ctype.model_class()
    assert issubclass(model, CremeEntity)

    # TODO: factorise (with views.generic.listview)
    return EntityCredentials.filter_entities(
                    user,
                    CremeEntity.objects.filter(
                         is_deleted=False,
                         entity_type=ctype,
                        ),
                    as_model=model,
                ).count()


@register.filter()
def query_serialize(q):
    return __serializer.dumps(q)
