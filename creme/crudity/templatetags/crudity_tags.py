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
from django import template
from django.template.defaultfilters import truncatewords

register = template.Library()

@register.filter(name="truncate")
def truncate(word, truncate_at):
    words = truncatewords(word, truncate_at)
    word = unicode(word)
    truncated = word[:truncate_at]
    if len(words.split()) == 1 and not len(truncated) == len(word):
        words = u"%s..." % truncated
    return words
