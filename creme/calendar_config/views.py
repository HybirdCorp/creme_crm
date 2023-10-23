from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme.activities.views.calendar import CalendarView
from creme.creme_config.views.base import (
    ConfigDeletion,
    ConfigModelCreation,
    ConfigModelEdition,
)
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.utils import get_from_POST_or_404

from .forms import CalendarConfigItemCreateForm, CalendarConfigItemEditForm
from .models import CalendarConfigItem


class ConfiguredCalendarView(CalendarView):
    template_name = 'calendar_config/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['calendar_settings'] = CalendarConfigItem.objects.for_user(
            self.request.user
        ).as_dict()

        return context


class CalendarConfigItemEdition(ConfigModelEdition):
    model = CalendarConfigItem
    form_class = CalendarConfigItemEditForm
    pk_url_kwarg = 'item_id'
    title = _('Edit calendar view configuration')


class CalendarConfigItemCreation(ConfigModelCreation):
    form_class = CalendarConfigItemCreateForm
    title = _('Create calendar configuration for a role')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs['instance'] = instance = CalendarConfigItem.objects.get_default()
        instance.pk = None

        return kwargs


class CalendarConfigItemDeletion(ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        config = get_object_or_404(
            CalendarConfigItem,
            pk=get_from_POST_or_404(request.POST, self.id_arg),
        )

        if config.role is None and not config.superuser:
            raise ConflictError("Unable to remove default calendar configuration")

        config.delete()
