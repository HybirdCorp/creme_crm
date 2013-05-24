# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from datetime import date, datetime
import logging
from os.path import join
from os import listdir
from re import compile
from random import randint

from django.http import Http404
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from django.utils.formats import time_format

from ..gui import block_registry
from ..gui.block import PaginatedBlock
from ..gui.field_printers import (print_image,
                                  print_urlfield,
                                  print_datetime, print_date, print_duration,
                                  print_foreignkey, print_many2many,) 

from ..utils import is_testenvironment
from ..utils.media import get_current_theme, creme_media_themed_url as media_url

from ..global_info import set_global_info

from creme.persons.models.contact import Contact


logger = logging.getLogger(__name__)

TEST_TEMPLATE_PATH = join(settings.CREME_ROOT, 'creme_core', 'templates', 'creme_core', 'tests')
TEST_TEMPLATE_BLOCK_PATH = join(TEST_TEMPLATE_PATH, 'blocks')
TEST_IMAGE_URLS = ('images/add_32.png',
                   'images/404.png',
                   'images/500.png',
                   'images/action_48.png',
                   'images/action_not_in_time_48.png',
                   'images/wait.gif',)

class MockImage(object):
    def __init__(self, url, width, height=None):
        self.url = url
        self.width = width
        self.height = height or width
    
    def html(self, entity):
        return mark_safe(print_image(entity, self, entity.user));


class MockManyToMany(object):
    def __init__(self, model):
        self.model = model

    def all(self):
        return self.model.objects.all()

    def filter(self, **kwargs):
        return self.model.objects.filter(**kwargs)


class Dummy(object):
    def __init__(self, id, user):
        self.user = user
        self.name = u'Dummy (%d)' % id
        self.image = MockImage(media_url(TEST_IMAGE_URLS[randint(0, len(TEST_IMAGE_URLS) - 1)]), randint(16, 64)).html(self);
        self.url = mark_safe(print_urlfield(self, media_url('images/add_16.png'), self.user))
        self.datetime = mark_safe(print_datetime(self, datetime.now(), user))
        self.date = mark_safe(print_date(self, date.today(), user))
        self.duration = mark_safe(print_duration(self, '%d:%d:%d' % (randint(0, 23), randint(0, 59), randint(0, 59)), user))
        self.foreignkey = mark_safe(print_foreignkey(self, Contact.objects.filter(is_user=True, last_name='Creme').get(), user))
        self.manytomany = mark_safe(print_many2many(self, MockManyToMany(Contact), user))

    def __unicode__(self):
        return self.name


def print_datetime(entity, fval, user):
    return time_format(fval, 'TIME_FORMAT') if fval else ''

class DummyListBlock(PaginatedBlock):
    id_           = PaginatedBlock.generate_id('creme_core', 'test_dummy_list')
    verbose_name  = u'Dummies'
    dependencies  = ()
    permission    = 'creme_config.can_admin'
    template_name = join(TEST_TEMPLATE_BLOCK_PATH, 'block_dummy_list.html')
    data          = None

    def detailview_display(self, context):
        user = context['request'].user
        refresh = context['request'].GET.get('refresh', False)

        if refresh or self.data is None:
            self.data = [Dummy(id, user) for id in xrange(randint(0, 100))]

        return self._render(self.get_block_template_context(context, self.data,
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_
                                                           )
                           )

dummy_list_block = DummyListBlock()

block_registry.register(dummy_list_block)

def js_testview_or_404(request, message, error):

    if not is_testenvironment(request) and not settings.FORCE_JS_TESTVIEW:
        raise Http404(error)

    logger.warn(message)

def js_testview_context(request, viewname):
    test_view_pattern = compile('^test_(?P<name>[\d\w]+)\.html')
    test_views = []

    for filename in listdir(TEST_TEMPLATE_PATH):
        matches = test_view_pattern.match(filename)
        name = matches.group('name') if matches is not None else None 

        if name is not None:
            test_views.append((name, name.capitalize(),))

    context = {
        'THEME_LIST':      [(name, unicode(label)) for name, label in settings.THEMES],
        'THEME_NAME':      request.GET.get('theme', get_current_theme()),
        'TEST_VIEW_LIST':  test_views,
        'TEST_VIEW':       viewname,
        'TEST_SCREEN':     request.GET.get('screen', ''),
    }

    return context

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

    context = js_testview_context(request, widget)
    theme = context['THEME_NAME']
    usertheme = get_current_theme()

    set_global_info(usertheme=theme)

    try:
        return render(request, 'creme_core/tests/test_' + widget + '.html', context)
    finally:
        set_global_info(usertheme=usertheme)
