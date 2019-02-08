# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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


register = Library()


# @register.filter(name='is_custom')
@register.filter(name='config_is_custom')
def is_custom(obj):
    return getattr(obj, 'is_custom', True)


@register.simple_tag
def config_model_creation_url(model_config, user):
    return model_config.creator.get_url(user=user)


@register.simple_tag
def config_model_edition_url(model_config, instance, user):
    return model_config.editor.get_url(instance=instance, user=user)
