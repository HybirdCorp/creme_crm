################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2025 Hybird
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

from django.db.models import F, ProtectedError
from django.db.transaction import atomic
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from ..core.workflow import WorkflowEngine
from ..models import DeletionCommand, FieldsConfig, JobResult
from ..signals import pre_replace_and_delete
from ..utils.translation import verbose_instances_groups
from .base import JobProgress, JobType


# TODO: possibility to resume the job if it failed ?
class _DeletorType(JobType):
    """Job which updates ForeignKeys referencing an instance before deleting it."""
    id = JobType.generate_id('creme_core', 'deletor')
    verbose_name = _('Replace & delete')

    def _execute(self, job):
        dcom_mngr = DeletionCommand.objects
        dcom = dcom_mngr.get(job=job)
        instance_2_del = (
            dcom.content_type.model_class()._default_manager.get(pk=dcom.pk_to_delete)
        )
        wf_engine = WorkflowEngine.get_current()

        # TODO: is_deleted field ?
        # TODO: regroup by same CType & update several fields at once when its possible
        for replacer in dcom.replacers:
            new_value = replacer.get_value()

            model_field = replacer.model_field
            rel_mngr   = model_field.model._default_manager
            field_name = model_field.name

            pre_replace_and_delete.send_robust(
                sender=instance_2_del,
                model_field=model_field,
                replacing_instance=new_value,
            )

            for pk in rel_mngr.filter(
                **{field_name: instance_2_del.pk}
            ).values_list('pk', flat=True):
                # NB1: we perform a .save(), not an .update() in order to:
                #       - let the model compute it's business logic (if there is one).
                #       - get a HistoryLine for entities.
                # NB2: as in edition view, we perform a select_for_update() to avoid
                #      overriding other fields (if there are concurrent accesses)
                with atomic(), wf_engine.run(user=None):
                    related_instance = rel_mngr.select_for_update().filter(pk=pk).first()
                    if related_instance is not None:
                        if model_field.many_to_many:
                            getattr(related_instance, field_name).add(new_value)
                        else:
                            setattr(related_instance, field_name, new_value)
                            related_instance.save()

                    dcom_mngr.filter(pk=dcom.pk).update(updated_count=F('updated_count') + 1)

        try:
            instance_2_del.delete()
        except ProtectedError as e:
            JobResult.objects.create(
                job=job,
                messages=[
                    gettext('«{instance}» can not be deleted because of its '
                            'dependencies: {dependencies}').format(
                        instance=instance_2_del,
                        dependencies=', '.join(verbose_instances_groups(e.args[1])),
                    ),
                ],
            )

    def progress(self, job):
        dcom = DeletionCommand.objects.get(job=job)
        total = dcom.total_count
        updated = dcom.updated_count

        return (
            JobProgress(percentage=updated * 100 / total)
            if total else
            JobProgress(
                percentage=None,
                label=ngettext(
                    '{count} entity updated.',
                    '{count} entities updated.',
                    updated
                ).format(count=updated),
            )
        )

    def get_description(self, job):
        dcom = DeletionCommand.objects.get(job=job)
        model = dcom.content_type.model_class()

        try:
            instance_to_delete = model._default_manager.get(pk=dcom.pk_to_delete)
        except model.DoesNotExist:
            instance_to_delete = dcom.deleted_repr

        description = [
            gettext('Deleting «{object}» ({model})').format(
                object=instance_to_delete,
                model=model._meta.verbose_name,
            ),
        ]

        get_model_conf = FieldsConfig.LocalCache().get_for_model

        for replacement in dcom.replacers:
            field = replacement.model_field

            if not get_model_conf(field.model).is_field_hidden(field):
                description.append(str(replacement))

        return description

    def get_stats(self, job):
        count = DeletionCommand.objects.get(job=job).updated_count

        return [
            ngettext(
                '{count} entity updated.',
                '{count} entities updated.',
                count
            ).format(count=count),
        ] if count else []


deletor_type = _DeletorType()
