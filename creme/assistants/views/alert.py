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

from django import shortcuts
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import BrickStateExtraDataSetting

from ..bricks import AlertsBrick
from ..constants import BRICK_STATE_HIDE_VALIDATED_ALERTS
from ..forms.alert import AlertForm
from ..models import Alert


class AlertCreation(generic.AddingInstanceToEntityPopup):
    model = Alert
    form_class = AlertForm
    title = _('New alert for «{entity}»')


class AlertEdition(generic.RelatedToEntityEditionPopup):
    model = Alert
    form_class = AlertForm
    pk_url_kwarg = 'alert_id'
    title = _('Alert for «{entity}»')


@require_POST
@login_required
@atomic
def validate(request, alert_id):
    alert = shortcuts.get_object_or_404(
        Alert.objects.select_for_update(),
        pk=alert_id,
    )

    entity = alert.creme_entity
    request.user.has_perm_to_change_or_die(entity)

    alert.is_validated = True
    alert.save()

    return shortcuts.redirect(entity)


class HideValidatedAlerts(BrickStateExtraDataSetting):
    brick_cls = AlertsBrick
    data_key = BRICK_STATE_HIDE_VALIDATED_ALERTS
