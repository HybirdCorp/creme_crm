################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from django.apps import apps
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import pgettext_lazy

from creme.activities.forms.activity_type import NarrowedActivitySubTypeForm
from creme.activities.models import ActivitySubType, ActivityType
from creme.creme_config.registry import config_registry
from creme.creme_core.gui.bricks import QuerysetBrick
from creme.creme_core.views.bricks import BricksReloading
from creme.creme_core.views.generic import BricksView, CremeModelCreationPopup
from creme.creme_core.views.generic.order import ReorderInstances


class NarrowedSubTypesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('activities', 'narrowed_subtypes_config')
    dependencies = (ActivitySubType,)
    template_name = 'activities/bricks/activity-narrowed-subtypes.html'

    def __init__(self, activity_type):
        super().__init__()
        self.activity_type = activity_type

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            ActivitySubType.objects.filter(type=self.activity_type),
            model_config=config_registry.get_app_registry('activities')
                                        .get_model_conf(ActivitySubType),
        ))


class ActivityTypeRelatedMixin:
    activity_type_id_url_kwarg = 'type_id'

    _activity_type = None

    def get_activity_type(self):
        atype = self._activity_type
        if atype is None:
            self._activity_type = atype = get_object_or_404(
                ActivityType, id=self.kwargs[self.activity_type_id_url_kwarg],
            )

        return atype


class ActivityTypePortal(ActivityTypeRelatedMixin, BricksView):
    """Configuration portal to configure the subtypes related to one ActivityType instance"""
    template_name = 'activities/config/activity-type-portal.html'
    permissions = 'activities.can_admin'
    bricks = [NarrowedSubTypesBrick]

    def get_bricks(self):
        return {
            'main': [
                brick_cls(activity_type=self.get_activity_type())
                for brick_cls in self.bricks
            ],
        }

    def get_bricks_reload_url(self):
        return reverse(
            'activities__reload_type_brick', args=(self.get_activity_type().id,),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['activity_type'] = self.get_activity_type()
        context['app_verbose_name'] = apps.get_app_config('activities').verbose_name

        return context


class ActivityTypeBricksReloading(ActivityTypeRelatedMixin, BricksReloading):
    permissions = 'activities.can_admin'
    bricks = ActivityTypePortal.bricks

    def get_bricks(self):
        bricks = []
        atype = self.get_activity_type()
        allowed_bricks = {brick_cls.id: brick_cls for brick_cls in self.bricks}

        for brick_id in self.get_brick_ids():
            try:
                brick_cls = allowed_bricks[brick_id]
            except KeyError as e:
                raise Http404('Invalid brick ID') from e

            bricks.append(brick_cls(activity_type=atype))

        return bricks

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['activity_type'] = self.get_activity_type()

        return context


class NarrowedActivitySubTypeCreation(ActivityTypeRelatedMixin,
                                      CremeModelCreationPopup):
    model = ActivitySubType
    form_class = NarrowedActivitySubTypeForm
    title = pgettext_lazy('activities-type', 'New sub-type for «{type}»')
    permissions = 'activities.can_admin'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['activity_type'] = self.get_activity_type()

        return kwargs

    def get_title_format_data(self):
        return {'type': self.get_activity_type()}


class ActivitySubTypeReordering(ReorderInstances):
    pk_url_kwarg = 'subtype_id'

    def get_queryset(self):
        self.request.user.has_perm_to_admin_or_die('activities')

        sub_type = get_object_or_404(
            ActivitySubType, pk=self.kwargs[self.pk_url_kwarg],
        )

        return ActivitySubType.objects.filter(type=sub_type.type_id)
