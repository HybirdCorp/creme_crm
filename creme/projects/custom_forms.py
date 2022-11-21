from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import projects
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
)

from .forms import project as project_forms
from .forms import task as task_forms

Project = projects.get_project_model()
ProjectTask = projects.get_task_model()


# ------------------------------------------------------------------------------
class ProjectCreationFormDefault(CustomFormDefault):
    LEADERS = 'leaders'
    sub_cells = {
        LEADERS: project_forms.ProjectLeadersSubCell,
    }
    main_fields = [
        'user', 'name', 'status', LEADERS, 'start_date', 'end_date', 'currency',
    ]


class ProjectEditionFormDefault(CustomFormDefault):
    main_fields = [
        'user', 'name', 'status', 'start_date', 'end_date', 'currency',
    ]


PROJECT_CREATION_CFORM = CustomFormDescriptor(
    id='projects-project_creation',
    model=Project,
    verbose_name=_('Creation form for project'),
    base_form_class=project_forms.BaseProjectCreationCustomForm,
    extra_sub_cells=[project_forms.ProjectLeadersSubCell(model=Project)],
    default=ProjectCreationFormDefault,
)
PROJECT_EDITION_CFORM = CustomFormDescriptor(
    id='projects-project_edition',
    model=Project,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for project'),
    default=ProjectEditionFormDefault,
)


# ------------------------------------------------------------------------------
class ProjectTaskCreationFormDefault(CustomFormDefault):
    PARENTS = 'PARENTS'
    sub_cells = {
        PARENTS: task_forms.ParentTasksSubCell,
    }
    main_fields = [
        'user', 'title', 'start', 'end', 'duration', 'tstatus', PARENTS,
    ]


class ProjectTaskEditionFormDefault(CustomFormDefault):
    main_fields = [
        'user', 'title', 'start', 'end', 'duration', 'tstatus',
    ]


TASK_CREATION_CFORM = CustomFormDescriptor(
    id='projects-task_creation',
    model=ProjectTask,
    verbose_name=pgettext_lazy('projects', 'Creation form for task'),
    base_form_class=task_forms.BaseTaskCreationCustomForm,
    extra_sub_cells=[task_forms.ParentTasksSubCell(model=ProjectTask)],
    default=ProjectTaskCreationFormDefault,
)
TASK_EDITION_CFORM = CustomFormDescriptor(
    id='projects-task_edition',
    model=ProjectTask,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('projects', 'Edition form for task'),
    default=ProjectTaskEditionFormDefault,
)

del Project
del ProjectTask
