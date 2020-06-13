# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django import shortcuts
from django.db.transaction import atomic
# from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from creme.creme_core.auth.decorators import login_required
# from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views import generic

from ..forms.alert import AlertForm
from ..models import Alert


# @login_required
# def add(request, entity_id):
#     return generic.add_to_entity(request, entity_id, AlertForm,
#                                  _('New alert for «%s»'),
#                                  submit_label=_('Save the alert'),
#                                 )
class AlertCreation(generic.AddingInstanceToEntityPopup):
    model = Alert
    form_class = AlertForm
    title = _('New alert for «{entity}»')


# @login_required
# def edit(request, alert_id):
#     return generic.edit_related_to_entity(request, alert_id, Alert, AlertForm,
#                                           _('Alert for «%s»'),
#                                          )
class AlertEdition(generic.RelatedToEntityEditionPopup):
    model = Alert
    form_class = AlertForm
    pk_url_kwarg = 'alert_id'
    title = _('Alert for «{entity}»')


@require_POST
@login_required
# @POST_only
@atomic
def validate(request, alert_id):
    # try:
    #     alert = Alert.objects.select_for_update().get(pk=alert_id)
    # except Alert.DoesNotExist as e:
    #     raise Http404(str(e)) from e
    alert = shortcuts.get_object_or_404(
        Alert.objects.select_for_update(),
        pk=alert_id,
    )

    entity = alert.creme_entity
    request.user.has_perm_to_change_or_die(entity)

    alert.is_validated = True
    alert.save()

    return shortcuts.redirect(entity)
