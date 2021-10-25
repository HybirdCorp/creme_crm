# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

import logging
from datetime import date
from os import listdir
from os.path import join
from random import choice as random_choice
from random import randint
from re import compile as re_compile
from time import sleep

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.utils.timezone import now

from mediagenerator.utils import media_url

from ..auth.decorators import login_required
from ..core.exceptions import ConflictError
from ..gui.bricks import PaginatedBrick, brick_registry
from ..gui.field_printers import (
    print_date,
    print_datetime,
    print_duration,
    print_foreignkey_html,
    print_image_html,
    print_url_html,
)
from ..http import is_ajax

logger = logging.getLogger(__name__)

TEST_TEMPLATE_PATH = join(settings.CREME_ROOT, 'creme_core', 'templates', 'creme_core', 'tests')
TEST_TEMPLATE_BRICK_PATH = join(TEST_TEMPLATE_PATH, 'bricks')
TEST_IMAGE_URLS = (
    ('add',                'icecream/images/add_32.png'),
    ('not_found',          'common/images/404_200.png'),
    ('creme',              'common/images/creme_logo.png'),
    ('action',             'chantilly/images/action_48.png'),
    ('action_not_in_time', 'icecream/images/action_not_in_time_48.png'),
    ('wait',               'icecream/images/wait.gif'),
)
TEST_IMAGES_SIZES = (16, 22, 32, 48, 64)


class MockImage:
    def __init__(self, url, width, height=None):
        self.url = url
        self.width = width
        self.height = height or width
        self.name = url

    def html(self, entity):
        return mark_safe(
            print_image_html(
                entity=entity,
                fval=self,
                user=entity.user,
                field=self
            )
        )


class MockManyToMany:
    def __init__(self, model):
        self.model = model

    def all(self):
        return self.model.objects.all()

    def filter(self, **kwargs):
        return self.model.objects.filter(**kwargs)


class Dummy:
    def __init__(self, name, user, image_url):
        self.user = user
        self.name = name
        self.url = mark_safe(print_url_html(self, image_url, self.user, None))
        self.datetime = mark_safe(print_datetime(self, now(), user, None))
        self.date = mark_safe(print_date(self, date.today(), user, None))
        self.duration = mark_safe(print_duration(
            self, '{}:{}:{}'.format(randint(0, 23), randint(0, 59), randint(0, 59)), user, None
        ))
        self.foreignkey = (
            None
            if property is None else
            mark_safe(print_foreignkey_html(self, property, user, None))
        )
        # API Breaking : TODO refactor this
#         self.image = MockImage(image_url, random_choice(TEST_IMAGES_SIZES)).html(self)
#         property = CremeProperty.objects.first()
#         self.manytomany = mark_safe(
#             print_many2many_html(self, MockManyToMany(CremeProperty), user, None)
#         )

    def __str__(self):
        return self.name


class DummyListBrick(PaginatedBrick):
    id_ = PaginatedBrick.generate_id('creme_core', 'test_dummy_list')
    verbose_name = 'Dummies'
    dependencies = ()
    permissions = 'creme_config.can_admin'
    template_name = join(TEST_TEMPLATE_BRICK_PATH, 'dummy-list.html')
    configurable = False

    def detailview_display(self, context):
        request = context['request']
        user = request.user
        reloading_info = self.reloading_info or {}

        item_count_str = str(request.GET.get('count') or reloading_info.get('count', ''))
        item_count = int(item_count_str) if item_count_str.isdigit() else 20

        images = TEST_IMAGE_URLS
        image_count = len(images)
        image_ids = [*range(0, image_count - 1)]

        data = []

        for item_id in range(item_count):
            image_name, image_url = images[random_choice(image_ids)]
            data.append(Dummy(
                'Dummy ({}) - {}'.format(item_id + 1, image_name),
                user,
                media_url(image_url),
            ))

        return self._render(self.get_template_context(
            context, data,
            reloading_info={'count': item_count},
        ))


def js_testview_or_404(message, error):
    if settings.TESTS_ON or not settings.FORCE_JS_TESTVIEW:
        raise Http404(error)

    logger.warning(message)


def js_testview_context(request, viewname):
    try:
        brick_registry[DummyListBrick.id_]
    except KeyError:
        logger.info('Register dummy object list block %s', DummyListBrick.id_)
        brick_registry.register(DummyListBrick)

    test_view_pattern = re_compile(r'^test_(?P<name>[\d\w]+)\.html$')
    test_views = []

    for filename in listdir(TEST_TEMPLATE_PATH):
        matches = test_view_pattern.match(filename)
        name = matches['name'] if matches is not None else None

        if name:
            test_views.append((name, name.capitalize()))

    get = request.GET.get

    return {
        'THEME_LIST': [
            (theme_id, str(theme_vname)) for theme_id, theme_vname in settings.THEMES
        ],
        'THEME_NAME':      get('theme') or request.user.theme_info[0],
        'TEST_VIEW_LIST':  test_views,
        'TEST_VIEW':       viewname,
        'TEST_SCREEN':     get('screen', ''),
        'TEST_HEADLESS':     get('headless', False),
        'TEST_CONTENTTYPES': dict(ContentType.objects.values_list('model', 'id')),
    }


def test_http_response(request):
    if not settings.TESTS_ON and not settings.FORCE_JS_TESTVIEW:
        raise Http404('This is view is only reachable during javascript or server unittests')

    logger.warning(
        "Beware : If you are not running unittest this view shouldn't be reachable."
        " Check your server configuration."
    )

    status = int(request.GET.get('status', 200))
    delay = int(request.GET.get('delay', 0))

    if delay > 0:
        sleep(delay / 1000.0)

    if status == 403:
        raise PermissionDenied('Tests: operation is not allowed')

    if status == 404:
        raise Http404('Tests: no such result or unknown url')

    if status == 409:
        raise ConflictError('Tests: conflicting operation')

    if status == 500:
        raise Exception('Tests: server internal error')

    # if request.is_ajax():
    if is_ajax(request):
        return HttpResponse(f'XML Http Response {status}', status=status)

    return HttpResponse(f'<p>Http Response {status}</p>', status=status)


@login_required
def test_js(request):
    js_testview_or_404(
        "Beware: if you are not running unittest this view shouldn't be reachable. "
        "Check your server configuration.",
        "This is view is only reachable during javascript unittests."
    )

    return render(request, 'creme_core/test_js.html')


@login_required
def test_widget(request, widget=None):
    js_testview_or_404(
        "Beware: if you are not in testing javascript widgets this view shouldn't be reachable. "
        "Check your server configuration.",
        "This is view is only reachable during javascript debug."
    )

    context = js_testview_context(request, widget)
    request.user.theme = context['THEME_NAME']

    if widget:
        return render(request, f'creme_core/tests/test_{widget}.html', context)

    return render(request, 'creme_core/tests/test.html', context)
