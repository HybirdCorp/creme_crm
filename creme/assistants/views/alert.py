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
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.views.generic import add_to_entity, edit_related_to_entity, delete_related_to_entity

from assistants.models import Alert
from assistants.forms.alert import AlertCreateForm, AlertEditForm


@login_required
def add(request, entity_id):
    return add_to_entity(request, entity_id, AlertCreateForm, _(u'New alert for <%s>'))

@login_required
def edit(request, alert_id):
    return edit_related_to_entity(request, alert_id, Alert, AlertEditForm, _(u"Alert for <%s>"))

@login_required
def delete(request):
    return delete_related_to_entity(request, Alert)

#TODO: credentials ???
@login_required
def validate(request, alert_id):
    alert = get_object_or_404(Alert, pk=alert_id)
    alert.is_validated = True
    alert.save()
    return HttpResponseRedirect(alert.creme_entity.get_absolute_url())
