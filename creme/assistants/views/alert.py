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

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from assistants.models import Alert
from assistants.forms.alert import AlertCreateForm, AlertEditForm
from utils import generic_add, generic_edit, generic_delete


def add(request, entity_id):
    return generic_add(request, entity_id, AlertCreateForm, u'Nouvelle alerte pour <%s>')

def edit(request, alert_id):
    return generic_edit(request, alert_id, Alert, AlertEditForm, u"Alerte pour <%s>")

def delete(request):
    return generic_delete(request, Alert)

@login_required
def validate(request, alert_id):
    alert = get_object_or_404(Alert, pk=alert_id)
    alert.is_validated = True
    alert.save()
    return HttpResponseRedirect(alert.creme_entity.get_absolute_url())
