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
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.simplejson.encoder import JSONEncoder


def inner_popup(request, template, template_dict, context_instance, is_valid=True,
                html=None, callback_url='', reload=True, delegate_reload=False, *args, **kwargs):
    debug("Inner_popup for: %s", request.path)

    template_dict['hide_submit'] = True

    REQUEST = request.REQUEST
    persist = REQUEST.getlist('persist')
    tpl_persist = {}
    for persist_key in persist:
        tpl_persist[persist_key] = REQUEST.getlist(persist_key)

    template_dict['persisted'] = tpl_persist

    html = mark_safe(html) if html else render_to_string(template, template_dict, context_instance, *args, **kwargs)

    return HttpResponse(render_to_string('creme_core/generics/inner_popup.html',
                                         {
                                            'html':            html,
                                            'from_url':        request.path,
                                            'is_valid':        is_valid,
                                            'whoami':          request.REQUEST.get('whoami'),
                                            'callback_url':    callback_url,
                                            'reload':          JSONEncoder().encode(reload),
                                            'persisted':       tpl_persist,
                                            'delegate_reload': delegate_reload,
                                         },
                                         context_instance, *args, **kwargs
                                        ),
                        mimetype="text/html"
                       )
