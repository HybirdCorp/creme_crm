################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ngettext

from creme.creme_core.models import CremeEntity, Workflow
from creme.creme_core.models.utils import model_verbose_name_plural


def form_help_message(model: type[CremeEntity]) -> str:
    """Generates a help message for forms to recall (if needed) there are
    enabled Workflows.
    """
    workflows = Workflow.objects.filter(enabled=True)
    if not workflows:
        return ''

    ctype = ContentType.objects.get_for_model(model)
    model_workflows = [wf for wf in workflows if wf.content_type == ctype]

    if not model_workflows:
        count = len(workflows)
        return ngettext(
            'Do not forget that Workflows can be triggered by the actions '
            'performed by this form (there is {count} enabled Workflow).',
            'Do not forget that Workflows can be triggered by the actions '
            'performed by this form (there are {count} enabled Workflows).',
            count,
        ).format(count=count)

    return ngettext(
        'Do not forget that Workflows can be triggered by the actions '
        'performed by this form. For example, this Workflow is '
        'directly related to «{models}»: {workflows}',
        'Do not forget that Workflows can be triggered by the actions '
        'performed by this form. For example, these Workflows are '
        'directly related to «{models}»: {workflows}',
        len(model_workflows),
    ).format(
        models=model_verbose_name_plural(model),
        workflows=', '.join(wf.title for wf in model_workflows),
    )
