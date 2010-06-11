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

from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.utils.simplejson.encoder import JSONEncoder

def inner_popup(request, template, template_dict, context_instance, is_valid=True, html=None, callback_url='', reload=True, delegate_reload=False, *args, **kwargs):
    debug("###___ inner_popup ___###")

    template_dict.update({'hide_submit': True})

    if not html:
        html = render_to_string(template, template_dict, context_instance, *args, **kwargs)
    else:
        html = mark_safe(html)

    enc = JSONEncoder()

    inner_popup_html = render_to_string('creme_core/generics/inner_popup.html',
                                        {
                                            'html':     html,
                                            'from_url': request.path,
                                            'is_valid': is_valid,
                                            'whoami':   request.REQUEST.get('whoami'),
                                            'callback_url' : callback_url,
                                            'reload' : enc.encode(reload),
                                            'delegate_reload': delegate_reload
                                        },
                                        context_instance, *args, **kwargs)

    return HttpResponse(inner_popup_html, mimetype = "text/html")
