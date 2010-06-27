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

from assistants.models import Memo
from assistants.forms.memo import MemoCreateForm, MemoEditForm
from assistants.blocks import memos_block
from utils import generic_add, generic_edit, generic_delete


def add(request, entity_id):
    return generic_add(request, entity_id, MemoCreateForm, u'Nouveau Mémo pour <%s>')

def edit(request, memo_id):
    return generic_edit(request, memo_id, Memo, MemoEditForm, u"Mémo pour <%s>")

def delete(request):
    return generic_delete(request, Memo)

@login_required
def reload_detailview(request, entity_id):
    return memos_block.detailview_ajax(request, entity_id)

@login_required
def reload_home(request):
    return memos_block.home_ajax(request)

@login_required
def reload_portal(request, ct_ids):
    return memos_block.portal_ajax(request, ct_ids)
