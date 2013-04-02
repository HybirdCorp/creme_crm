# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def js_testview_or_404(request, message, error):
    from logging import warn
    from django.http import Http404
    from django.conf import settings
    from creme.creme_core.utils import is_testenvironment

    if not is_testenvironment(request) and not settings.FORCE_JS_TESTVIEW:
        raise Http404(error)

    warn(message)

@login_required
def home(request):
    return render(request, 'creme_core/home.html')

@login_required
def my_page(request):
    return render(request, 'creme_core/my_page.html')

@login_required
def test_js(request):
    js_testview_or_404(request, 
                       "Beware : If you are not running unittest this view shouldn't be reachable. Check your server configuration.",
                       'This is view is only reachable during unittests')

    return render(request, 'creme_core/test_js.html')

@login_required
def test_widget(request, widget):
    js_testview_or_404(request, 
                       "Beware : If you are not running unittest this view shouldn't be reachable. Check your server configuration.",
                       'This is view is only reachable during unittests')

    return render(request, 'creme_core/tests/test_' + widget + '_widget.html')
