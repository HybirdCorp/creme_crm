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

from django.conf import settings
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from creme.creme_core.gui.field_printers import simple_print_html
from creme.creme_core.templatetags.creme_widgets import (
    get_icon_by_name,
    get_icon_size_px,
)
from creme.creme_core.utils.media import get_current_theme


# def print_phone(entity, fval, user, field) -> str:
def print_phone_html(entity, fval, user, field) -> str:
    if not fval:
        return simple_print_html(entity, fval, user, field)

    # TODO: need the context to use faster get_current_theme_from_context()
    theme = get_current_theme()

    return format_html(
        # """{number}&nbsp;"""
        """{number}"""
        """<a class="cti-phonecall" """
        """onclick="creme.cti.phoneCall('{external_url}', '{creme_url}', '{number}', {id});">"""
        """{icon}"""
        """</a>""",
        external_url=settings.ABCTI_URL,
        creme_url=reverse('cti__create_phonecall_as_caller'),
        number=fval,
        id=entity.id,
        icon=get_icon_by_name(
            name='phone', theme=theme, label=_('Call'),
            size_px=get_icon_size_px(theme, size='brick-header'),
            css_class='text_icon',
        ).render(),
    )
