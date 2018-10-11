# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from itertools import chain
from json import dumps as json_dump
import warnings

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


def inner_popup(request, template, template_dict, is_valid=True, html=None,
                callback_url='', reload=True, delegate_reload=False, *args, **kwargs):
    warnings.warn('creme_core.views.generic.popup.inner_popup() is deprecated ; '
                  'use a class-based view & InnerPopupMixin instead.',
                  DeprecationWarning
                 )

    template_dict['is_inner_popup'] = True

    GET = request.GET
    POST = request.POST

    tpl_persist = {persist_key: POST.getlist(persist_key) + GET.getlist(persist_key)
                        for persist_key in chain(POST.getlist('persist'),
                                                 GET.getlist('persist'),
                                                )
                  }
    template_dict['persisted'] = tpl_persist
    html = mark_safe(html) if html else render_to_string(template, template_dict, request=request, *args, **kwargs)

    return HttpResponse(render_to_string('creme_core/generics/inner_popup.html',
                                         {'html':            html,
                                          'from_url':        request.path,
                                          'is_valid':        is_valid,
                                          'whoami':          POST.get('whoami') or GET.get('whoami'),
                                          'callback_url':    callback_url,
                                          'reload':          json_dump(reload),  # TODO: use '|jsonify' ?
                                          'persisted':       tpl_persist,
                                          'delegate_reload': delegate_reload,
                                         },
                                         request=request,
                                         *args, **kwargs
                                        ),
                        content_type='text/html',
                       )


class InnerPopupMixin:
    """ Mixin for views which use the 'inner-popup'.
    Inner-popups are display inside the HTML page, from above the content ;
    they do not use true windows.
    """
    # TODO: still useful
    # TODO: in the form and the popup template ??
    # TODO: cache (if used twice) ? inline ?
    # TODO: use GET or POST, not both ?
    def get_persisted(self):
        from itertools import chain  # TODO: remove of move up

        request = self.request
        GET = request.GET
        POST = request.POST

        return {
            persist_key: POST.getlist(persist_key) + GET.getlist(persist_key)
               for persist_key in chain(POST.getlist('persist'), GET.getlist('persist'))
        }

    def get_next_url(self):
        return ''

    # TODO: arg "context" ?
    def get_reload(self):
        # TODO: 'True' in base class
        return False

    def get_delegate_reload(self):
        # TODO: 'False' in base class
        # TODO: regroup with get_reload() ? (get_reload_policy() ?)
        return True

    def get_close(self, context):
        # TODO: 'True' in base class in the function ('False' is smarter ?)
        return context['form'].is_valid()

    # TODO: remove with the template rework
    def get_inner_html(self, context):
        from django.template.loader import render_to_string  # TODO: remove of move up

        return render_to_string(
            template_name=self.get_template_names(),
            context=context,
            request=self.request,
            using=self.template_engine,
        )

    def get_popup_context(self, context):
        request = self.request

        return {
            'html': self.get_inner_html(context),
            'from_url': request.path,
            'is_valid': self.get_close(context),  # TODO: rename "close" in new template
            # TODO: use GET or POST, not both ?
            'whoami': request.POST.get('whoami') or request.GET.get('whoami'),
            'callback_url': self.get_next_url(),
            'reload': self.get_reload(),
            'persisted': self.get_persisted(),
            'delegate_reload': self.get_delegate_reload(),
        }
