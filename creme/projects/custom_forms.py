# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import projects
from creme.creme_core.gui.custom_form import CustomFormDescriptor

from .forms import project, task

Project = projects.get_project_model()
ProjectTask = projects.get_task_model()

PROJECT_CREATION_CFORM = CustomFormDescriptor(
    id='projects-project_creation',
    model=Project,
    verbose_name=_('Creation form for project'),
    base_form_class=project.BaseProjectCreationCustomForm,
    extra_sub_cells=[project.ProjectLeadersSubCell(model=Project)],
)
PROJECT_EDITION_CFORM = CustomFormDescriptor(
    id='projects-project_edition',
    model=Project,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for project'),
)

TASK_CREATION_CFORM = CustomFormDescriptor(
    id='projects-task_creation',
    model=ProjectTask,
    verbose_name=pgettext_lazy('projects', 'Creation form for task'),
    base_form_class=task.BaseTaskCreationCustomForm,
    extra_sub_cells=[task.ParentTasksSubCell(model=ProjectTask)],
)
TASK_EDITION_CFORM = CustomFormDescriptor(
    id='projects-task_edition',
    model=ProjectTask,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('projects', 'Edition form for task'),
)

del Project
