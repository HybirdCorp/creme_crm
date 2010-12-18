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

from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _

from creme_core.views.generic import add_to_entity, edit_related_to_entity, delete_related_to_entity

from assistants.models import Memo
from assistants.forms.memo import MemoCreateForm, MemoEditForm


def add(request, entity_id):
    return add_to_entity(request, entity_id, MemoCreateForm, _(u'New Memo for <%s>'))

@login_required
def edit(request, memo_id):
    return edit_related_to_entity(request, memo_id, Memo, MemoEditForm, _(u"Memo for <%s>"))

@login_required
def delete(request):
    return delete_related_to_entity(request, Memo)
