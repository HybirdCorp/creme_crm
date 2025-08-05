################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

# import warnings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import localtime, now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core import models as core_models
from creme.creme_core.models.currency import get_default_currency_pk

from .projectstatus import ProjectStatus


class AbstractProject(core_models.CremeEntity):
    name = models.CharField(_('Name of the project'), max_length=100)

    status = models.ForeignKey(
        ProjectStatus, verbose_name=_('Status'), on_delete=core_models.CREME_REPLACE,
    )

    start_date = models.DateTimeField(
        _('Estimated start'), blank=True, null=True,
    ).set_tags(optional=True)
    end_date = models.DateTimeField(
        _('Estimated end'), blank=True, null=True,
    ).set_tags(optional=True)
    effective_end_date = models.DateTimeField(
        _('Effective end date'), blank=True, null=True, editable=False,
    ).set_tags(optional=True)

    currency = models.ForeignKey(
        core_models.Currency, verbose_name=_('Currency'), related_name='+',
        default=get_default_currency_pk,
        on_delete=models.PROTECT,
    )

    tasks_list = None

    allowed_related = core_models.CremeEntity.allowed_related | {'tasks_set'}

    creation_label = _('Create a project')
    save_label     = _('Save the project')

    class Meta:
        abstract = True
        app_label = 'projects'
        verbose_name = _('Project')
        verbose_name_plural = _('Projects')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('projects__view_project', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('projects__create_project')

    def get_edit_absolute_url(self):
        return reverse('projects__edit_project', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('projects__list_projects')

    def get_html_attrs(self, context):
        attrs = super().get_html_attrs(context)

        # NB: if 'status' if not in the HeaderFilter, it will cause an extra query...
        color = self.status.color_code
        if color:
            attrs['style'] = f'background-color:#{color};'

        return attrs

    def clean(self):
        super().clean()

        # TODO: refactor if start/end can not be null
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError(
                gettext('Start ({start}) must be before end ({end}).').format(
                    start=date_format(localtime(self.start_date), 'DATE_FORMAT'),
                    end=date_format(localtime(self.end_date), 'DATE_FORMAT'),
                )
            )  # TODO: code & params ??

    def delete(self, *args, **kwargs):
        for task in self.get_tasks():
            task.delete(*args, **kwargs)

        super().delete(*args, **kwargs)

    def get_tasks(self):
        if self.tasks_list is None:
            self.tasks_list = self.tasks_set.order_by('order')
        return self.tasks_list

    def attribute_order_task(self):
        max_order = self.get_tasks().aggregate(models.Max('order'))['order__max']
        return (max_order + 1) if max_order is not None else 1

    def get_project_cost(self):
        return sum(task.get_task_cost() for task in self.get_tasks())

    def get_expected_duration(self):  # TODO: not used ??
        return sum(task.duration for task in self.get_tasks())

    def get_effective_duration(self):  # TODO: not used ??
        return sum(task.get_effective_duration() for task in self.get_tasks())

    def get_delay(self):
        return sum(max(0, task.get_delay()) for task in self.get_tasks())

    def close(self):
        """@return Boolean -> False means the project has not been closed
        (because it is already closed).
        """
        if self.effective_end_date:
            already_closed = False
        else:
            already_closed = True
            self.effective_end_date = now()

        return already_closed

    close.alters_data = True

    @property
    def is_closed(self):
        return bool(self.effective_end_date)

    # def _post_save_clone(self, source):
    #     from creme.projects.models.task import ProjectTask
    #
    #     warnings.warn(
    #         'The method Project._post_save_clone() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     ProjectTask.clone_scope(source.get_tasks(), self)


class Project(AbstractProject):
    class Meta(AbstractProject.Meta):
        swappable = 'PROJECTS_PROJECT_MODEL'
