# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from creme.creme_core.gui.field_printers import simple_print_html
from creme.creme_core.utils.media import creme_media_themed_url


def print_phone(entity, fval, user, field):  # TODO: rename  print_phone_html ?
    if not fval:
        return simple_print_html(entity, fval, user, field)

# #    return """%(number)s&nbsp;<a onclick="creme.cti.phoneCall('%(url)s', '%(number)s', %(id)s);"><img width="18px" height="18px" src="%(img)s" alt="%(label)s"/></a>""" % {
#     return """%(number)s&nbsp;<a onclick="creme.cti.phoneCall('%(external_url)s', %(creme_url)s', '%(number)s', %(id)s);"><img width="18px" height="18px" src="%(img)s" alt="%(label)s"/></a>""" % {
    return """%(number)s&nbsp;<a onclick="creme.cti.phoneCall('%(external_url)s', '%(creme_url)s', '%(number)s', %(id)s);"><img class="text_icon" src="%(img)s" alt="%(label)s"/></a>""" % {
#            'url':    settings.ABCTI_URL,
            'external_url': settings.ABCTI_URL,
            'creme_url':    reverse('cti__create_phonecall_as_caller'),
            'number': fval,
            'id':     entity.id,
            'label':  _(u'Call'),
            'img':    creme_media_themed_url('images/phone_22.png'),
        }
