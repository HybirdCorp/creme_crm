# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

import logging
from collections import defaultdict
from itertools import islice

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.db import IntegrityError
from django.db.models import ProtectedError, Q
from django.db.transaction import atomic
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .. import constants
from ..auth import SUPERUSER_PERM
from ..auth.decorators import login_required
from ..auth.entity_credentials import EntityCredentials
from ..core.exceptions import (
    BadRequestError,
    ConflictError,
    SpecificProtectedError,
)
from ..creme_jobs import trash_cleaner_type
from ..forms import CremeEntityForm
from ..forms.bulk import BulkDefaultEditForm
from ..forms.merge import MergeEntitiesBaseForm
from ..forms.merge import form_factory as merge_form_factory
# NB: do no import <bulk_update_registry> to facilitate unit testing
from ..gui import bulk_update
from ..gui.merge import merge_form_registry
from ..http import CremeJsonResponse, is_ajax
from ..models import (
    CremeEntity,
    EntityJobResult,
    FieldsConfig,
    Job,
    Relation,
    Sandbox,
    TrashCleaningCommand,
)
from ..models.fields import UnsafeHTMLField
from ..utils import (
    bool_from_str_extended,
    get_from_GET_or_404,
    get_from_POST_or_404,
)
from ..utils.html import sanitize_html
from ..utils.meta import ModelFieldEnumerator
from ..utils.serializers import json_encode
from ..utils.translation import get_model_verbose_name
from . import generic
from .decorators import jsonify
from .generic import base, listview

logger = logging.getLogger(__name__)


@login_required
@jsonify
def get_creme_entities_repr(request, entities_ids):
    # With the url regexp we are sure that int() will work
    e_ids = [int(e_id) for e_id in entities_ids.split(',') if e_id]

    entities = CremeEntity.objects.in_bulk(e_ids)
    CremeEntity.populate_real_entities([*entities.values()])

    user = request.user
    has_perm = user.has_perm_to_view

    return [
        {
            'id': e_id,
            'text': (
                entity.get_real_entity().get_entity_summary(user)
                if has_perm(entity) else
                gettext('Entity #{id} (not viewable)').format(id=e_id)
            ),
        }
        for e_id, entity in ((e_id, entities.get(e_id)) for e_id in e_ids)
        if entity is not None
    ]


@method_decorator(xframe_options_sameorigin, name='dispatch')
class HTMLFieldSanitizing(generic.base.EntityRelatedMixin,
                          generic.CheckedView):
    """Used to show an HTML document in an <iframe>."""
    field_name_url_kwarg = 'field_name'

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)

    def get(self, request, *args, **kwargs):
        entity = self.get_related_entity()
        field_name = kwargs[self.field_name_url_kwarg]

        try:
            field = entity._meta.get_field(field_name)
        except FieldDoesNotExist as e:
            raise ConflictError('This field does not exist.') from e

        if not isinstance(field, UnsafeHTMLField):
            raise ConflictError('This field is not an HTMLField.')

        unsafe_value = getattr(entity, field_name)

        return HttpResponse(
            '' if not unsafe_value else
            sanitize_html(
                unsafe_value,
                allow_external_img=request.GET.get('external_img', False),
            )
        )


# TODO: bake the result in HTML instead of ajax view ??
class FieldsInformation(generic.base.EntityCTypeRelatedMixin,
                        generic.CheckedView):
    response_class = CremeJsonResponse

    def get_info(self):
        model = self.get_ctype().model_class()

        # TODO: use django.forms.models.fields_for_model ?
        form = modelform_factory(model, CremeEntityForm)(user=self.request.user)
        required_fields = [
            name
            for name, field in form.fields.items()
            if field.required and name != 'user'
        ]

        kwargs = {}
        if len(required_fields) == 1:
            required_field = required_fields[0]
            kwargs['printer'] = lambda field: (
                str(field.verbose_name)
                if field.name != required_field else
                gettext('{field} [CREATION]').format(field=field.verbose_name)
            )

        is_hidden = FieldsConfig.objects.get_for_model(model).is_field_hidden

        # return ModelFieldEnumerator(model).filter(viewable=True) \
        #                                   .exclude(lambda f, deep: is_hidden(f)) \
        #                                   .choices(**kwargs)
        return ModelFieldEnumerator(model).filter(
            viewable=True,
        ).exclude(
            lambda model, field, depth: is_hidden(field)
        ).choices(**kwargs)

    def get(self, *args, **kwargs):
        return self.response_class(
            self.get_info(),
            safe=False,  # Result is not a dictionary
        )


class Clone(base.EntityRelatedMixin, base.CheckedView):
    entity_id_arg = 'id'

    def check_related_entity_permissions(self, entity, user):
        if entity.get_clone_absolute_url() != CremeEntity.get_clone_absolute_url():
            raise Http404(gettext('This model does not use the generic clone view.'))

        user.has_perm_to_create_or_die(entity)
        user.has_perm_to_view_or_die(entity)

    def get_related_entity_id(self):
        return get_from_POST_or_404(self.request.POST, self.entity_id_arg)

    def post(self, request, *args, **kwargs):
        new_entity = self.get_related_entity().clone()  # NB: clone() is @atomic

        # if request.is_ajax():
        if is_ajax(request):
            return HttpResponse(new_entity.get_absolute_url())

        return redirect(new_entity)


class SearchAndView(base.CheckedView):
    allowed_classes = CremeEntity
    value_arg = 'value'
    field_names_arg = 'fields'
    model_ids_arg = 'models'

    def build_q(self, *, model, value, field_names, fields_configs):
        query = Q()

        for field_name in field_names:
            try:
                field = model._meta.get_field(field_name)
            except FieldDoesNotExist:
                pass
            else:
                if fields_configs[model].is_field_hidden(field):
                    raise ConflictError(gettext('This field is hidden.'))

                query |= Q(**{field.name: value})

        return query

    def build_response(self, entity):
        return redirect(entity)

    def get_field_names(self):
        return get_from_GET_or_404(self.request.GET, self.field_names_arg).split(',')

    def get_model_ids(self):
        return get_from_GET_or_404(self.request.GET, self.model_ids_arg).split(',')

    def get_models(self):
        model_ids = self.get_model_ids()

        check_app = self.request.user.has_perm_to_access_or_die
        models = []
        get_ct = ContentType.objects.get_by_natural_key

        for model_id in model_ids:
            try:
                ct = get_ct(*model_id.split('-'))
            except (ContentType.DoesNotExist, TypeError) as e:
                raise Http404(f'This model does not exist: {model_id}') from e

            check_app(ct.app_label)

            model = ct.model_class()

            if self.is_model_allowed(model):
                models.append(model)

        if not models:
            raise Http404('No valid model')

        return models

    def get_value(self):
        value = get_from_GET_or_404(self.request.GET, self.value_arg)

        if not value:  # Avoid useless queries
            raise Http404('Void "value" arg')

        return value

    def get(self, request, *args, **kwargs):
        value = self.get_value()
        field_names = self.get_field_names()
        models = self.get_models()
        fconfigs = FieldsConfig.objects.get_for_models(models)
        user = request.user

        for model in models:
            query = self.build_q(
                model=model, value=value,
                field_names=field_names, fields_configs=fconfigs,
            )

            if query:  # Avoid useless query
                found = EntityCredentials.filter(user, model.objects.filter(query)).first()

                if found:
                    return self.build_response(found)

        raise Http404(gettext('No entity corresponding to your search was found.'))

    def is_model_allowed(self, model):
        return issubclass(model, self.allowed_classes)


# TODO: remove when bulk_update_registry has been rework to manage different
#       types of cells (eg: RelationType => LINK)
def _bulk_has_perm(entity, user):  # NB: indeed 'entity' can be a simple model...
    # TODO: factorise
    owner = entity.get_related_entity() if hasattr(entity, 'get_related_entity') else entity

    return user.has_perm_to_change(owner) if isinstance(owner, CremeEntity) else False


class InnerEdition(base.ContentTypeRelatedMixin,
                   generic.CremeModelEditionPopup):
    # model = ...
    # form_class = ...
    pk_url_kwarg = 'id'

    field_name_url_kwarg = 'field_name'
    bulk_update_registry = bulk_update.bulk_update_registry

    def check_instance_permissions(self, instance, user):
        super().check_instance_permissions(instance=instance, user=user)

        if not _bulk_has_perm(instance, user):
            raise PermissionDenied(gettext('You are not allowed to edit this entity'))

    def dispatch(self, *args, **kwargs):
        try:
            return super().dispatch(*args, **kwargs)
        except (FieldDoesNotExist, bulk_update.FieldNotAllowed) as e:
            return HttpResponseBadRequest(str(e))

    def get_form_class(self):
        return self.bulk_update_registry.get_form(
            model=self.object.__class__,
            field_name=self.kwargs[self.field_name_url_kwarg],
            default=BulkDefaultEditForm,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        del kwargs['instance']  # TODO: use CremeEdition & remove this ?
        kwargs['entities'] = [self.object]  # TODO: rename 'entities' arg

        return kwargs

    def get_queryset(self):
        return self.get_ctype().model_class()._default_manager.all()


# TODO: factorise with InnerEdition
class BulkUpdate(base.EntityCTypeRelatedMixin, generic.CremeEditionPopup):
    # model = ...
    # form_class = ...
    # pk_url_kwarg = ...
    title = _('Multiple update')

    field_name_url_kwarg = 'field_name'
    bulk_update_registry = bulk_update.bulk_update_registry

    def dispatch(self, *args, **kwargs):
        try:
            return super().dispatch(*args, **kwargs)
        except (FieldDoesNotExist, bulk_update.FieldNotAllowed) as e:
            return HttpResponseBadRequest(str(e))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        count = len(self.get_entity_ids())
        # TODO: select_label in model instead (e.g. gender issue)
        # meta = self.get_ctype().model_class()._meta
        # context['help_message'] = format_html(
        #     '<span class="bulk-selection-summary" data-msg="{msg}" data-msg-plural="{plural}">'
        #     '</span>',
        #     msg=gettext('{count} «{model}» has been selected.').format(
        #         count='%s', model=meta.verbose_name,
        #     ),
        #     plural=gettext('{count} «{model}» have been selected.').format(
        #         count='%s', model=meta.verbose_name_plural,
        #     ),
        # )
        context['help_message'] = ngettext(
            '{count} «{model}» has been selected.',
            '{count} «{model}» have been selected.',
            count
        ).format(
            count=count,
            model=get_model_verbose_name(model=self.get_ctype().model_class(), count=count),
        )

        return context

    def get_form_class(self):
        model = self.get_ctype().model_class()
        registry = self.bulk_update_registry
        field_name = self.kwargs.get(self.field_name_url_kwarg)

        if field_name is None:
            field_name = registry.get_default_field(model).name

        return registry.get_form(
            model=model, field_name=field_name, default=BulkDefaultEditForm,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['entities'] = self.get_entities()
        kwargs['is_bulk'] = True

        return kwargs

    def get_summary(self, form):
        initial_count = len(self.get_entity_ids())
        success_count = len(form.bulk_cleaned_entities)
        invalid_count = len(form.bulk_invalid_entities)
        forbidden_count = initial_count - success_count - invalid_count

        context = {
            'model': get_model_verbose_name(form.model, success_count),
            'success': success_count,
            'initial': initial_count,
            'invalid': invalid_count,
            'forbidden': forbidden_count,
        }

        # TODO: modification_label/bulk_label/... in model instead (fr: masculin/féminin)
        if initial_count == success_count:
            summary = ngettext(
                '{success} «{model}» has been successfully modified.',
                '{success} «{model}» have been successfully modified.',
                success_count
            )
        else:
            summary = ngettext(
                '{success} of {initial} «{model}» has been successfully modified.',
                '{success} of {initial} «{model}» have been successfully modified.',
                success_count
            )

            if forbidden_count:
                summary += ' ' + ngettext(
                    '{forbidden} was not editable.',
                    '{forbidden} were not editable.',
                    forbidden_count
                )

            if invalid_count:
                summary += ' ' + ngettext(
                    '{invalid} has returned an error.',
                    '{invalid} have returned an error.',
                    invalid_count
                )

        return summary.format(**context)

    # TODO: avoid the use of 2 templates ?
    def form_valid(self, form):
        super().form_valid(form=form)

        return render(
            self.request,
            template_name='creme_core/frags/bulk_process_report.html',  # TODO: attributes ?
            context={
                'form': form,
                'title': self.get_title(),
                'summary': self.get_summary(form=form),
            },
        )

    def get_entity_ids(self):
        if self.request.method == 'POST':
            return self.request.POST.getlist('entities', [])
        else:
            raw_ids = self.request.GET.get('entities')
            return raw_ids.split('.') if raw_ids else []

    def get_entities(self):
        entity_ids = self.get_entity_ids()

        # NB (#60): 'SELECT FOR UPDATE' in a query using an 'OUTER JOIN' and
        #    nullable ids will fail with postgresql (both 9.6 & 10.x).
        # TODO: This bug may be fixed in django>=2.0
        #       (see https://code.djangoproject.com/ticket/28010)
        # entities = self.get_queryset().select_for_update().filter(pk__in=entity_ids)
        qs = self.get_queryset()
        entities = qs.filter(pk__in=entity_ids)

        filtered = EntityCredentials.filter(
            self.request.user, queryset=entities, perm=EntityCredentials.CHANGE,
        )

        # NB: Move 'SELECT FOR UPDATE' here for now.
        #     It could cause performance issues with a large amount of
        #     selected entities, but this never happens with common use cases.
        # return filtered
        if self.request.method == 'POST':
            if not filtered:
                raise PermissionDenied(_('You are not allowed to edit these entities'))

            return qs.select_for_update().filter(pk__in=filtered)
        else:
            return qs.filter(pk__in=filtered)

    def get_queryset(self):
        return self.get_ctype().model_class()._default_manager.all()


class MergeFormMixin:
    merge_form_registry = merge_form_registry

    def get_merge_form_class(self, model):
        form_cls = merge_form_factory(
            model=model,
            merge_form_registry=self.get_merge_form_registry(),
        )

        if form_cls is None:
            raise ConflictError('This type of entity cannot be merged')

        return form_cls

    def get_merge_form_registry(self):
        return self.merge_form_registry


class EntitiesToMergeSelection(base.EntityRelatedMixin,
                               MergeFormMixin,
                               listview.BaseEntitiesListPopup):
    """List-view to select a second entity to merge with a given entity.

    The second entity must have the same type than the first one, and cannot
    have the same ID.
    """
    mode = listview.SelectionMode.SINGLE
    entity1_id_arg = 'id1'

    def check_related_entity_permissions(self, entity, user):
        self.get_merge_form_class(type(entity))  # NB: can raise exception

        user.has_perm_to_view_or_die(entity)
        super().check_related_entity_permissions(entity=entity, user=user)

    def get_related_entity_id(self):
        return get_from_GET_or_404(self.request.GET, self.entity1_id_arg, cast=int)

    @property
    def model(self):
        return type(self.get_related_entity())

    def get_internal_q(self):
        return ~Q(pk=self.get_related_entity().id)


class Merge(MergeFormMixin, generic.CremeFormView):
    template_name = 'creme_core/forms/merge.html'
    title = _('Merge «{entity1}» with «{entity2}»')
    submit_label = _('Merge')

    entity1_id_arg = 'id1'
    entity2_id_arg = 'id2'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entity1 = self.entity2 = None

    def check_entity1_permissions(self, entity1, user):
        user.has_perm_to_view_or_die(entity1)
        user.has_perm_to_change_or_die(entity1)

    def check_entity2_permissions(self, entity2, user):
        user.has_perm_to_view_or_die(entity2)
        user.has_perm_to_delete_or_die(entity2)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['help_message'] = _(
            'You are going to merge two entities into a new one.\n'
            'Choose which information you want the old entities give to the new entity.\n'
            'The relationships, the properties and the other links with any of '
            'old entities will be automatically available in the new merged entity.'
        )

        return context

    # TODO: use POST for POST request ?
    def get_entity1_id(self, request):
        return get_from_GET_or_404(request.GET, self.entity1_id_arg, cast=int)

    def get_entity2_id(self, request):
        return get_from_GET_or_404(request.GET, self.entity2_id_arg, cast=int)

    def get_entities(self):
        if self.entity1 is None:
            request = self.request

            entity1_id = self.get_entity1_id(request)
            entity2_id = self.get_entity2_id(request)

            if entity1_id == entity2_id:
                raise ConflictError('You can not merge an entity with itself.')

            entities = CremeEntity.objects.all()

            if request.method == 'POST':
                entities = entities.select_for_update()

            entities_per_id = entities.in_bulk((entity1_id, entity2_id))

            try:
                entity1 = entities_per_id[entity1_id]
                entity2 = entities_per_id[entity2_id]
            except IndexError as e:
                raise Http404(f'Entity not found: {e}') from e

            if entity1.entity_type_id != entity2.entity_type_id:
                raise ConflictError('You can not merge entities of different types.')

            user = request.user
            self.check_entity1_permissions(entity1=entity1, user=user)
            self.check_entity2_permissions(entity2=entity2, user=user)

            # TODO: try to swap 1 & 2

            CremeEntity.populate_real_entities([entity1, entity2])
            self.entity1 = entity1.get_real_entity()
            self.entity2 = entity2.get_real_entity()

        return self.entity1, self.entity2

    def get_form(self, *args, **kwargs):
        try:
            return super().get_form(*args, **kwargs)
        except MergeEntitiesBaseForm.CanNotMergeError as e:
            raise ConflictError(e) from e

    def get_form_class(self):
        return self.get_merge_form_class(type(self.get_entities()[0]))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['entity1'], kwargs['entity2'] = self.get_entities()

        return kwargs

    def form_valid(self, form):
        form.save()

        # NB: we get the entity1 attribute (ie: not the attribute),
        #     because the entities can be swapped in the form (but form.entity1
        #     is always kept & form.entity2 deleted).
        return redirect(form.entity1)

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['entity2'], data['entity1'] = self.get_entities()

        return data


class Trash(generic.BricksView):
    template_name = 'creme_core/trash.html'


# TODO: disable the button "Empty the trash" while the job is active
class TrashCleaning(generic.base.TitleMixin, generic.CheckedView):
    title = _('Empty the trash')
    job_type = trash_cleaner_type
    command_model = TrashCleaningCommand
    conflict_msg = _('A job is already cleaning the trash.')
    confirmation_template_name = 'creme_core/forms/confirmation.html'
    job_template_name = 'creme_core/job/trash-cleaning-popup.html'

    # TODO: add a new brick action type (with confirmation + display of a result form)
    #       and remove these get() method ??
    def get(self, request, *args, **kwargs):
        return render(
            request=request,
            template_name=self.confirmation_template_name,
            context={
                'title': self.get_title(),
                'message': gettext(
                    'Are you sure you want to delete definitely '
                    'all the entities in the trash?'
                ),
            },
        )

    def post(self, request, *args, **kwargs):
        user = request.user
        cmd_model = self.command_model

        cmd = cmd_model.objects.filter(user=user).first()
        if cmd is not None:
            if cmd.job.status == Job.STATUS_OK:
                with atomic():
                    # NB: we do not recycle the instances :
                    #    - of job, to start the job correctly
                    #    - of command, to avoid race conditions
                    cmd.job.delete()
            else:
                raise ConflictError(self.conflict_msg)

        try:
            with atomic():
                job = Job.objects.create(type_id=self.job_type.id, user=user)
                cmd_model.objects.create(user=user, job=job)
        except IntegrityError as e:  # see TrashCleaningCommand uniqueness
            raise ConflictError(self.conflict_msg) from e

        return render(
            request=self.request,
            template_name=self.job_template_name,
            context={'job': job},
        )


class TrashCleanerEnd(generic.CheckedView):
    job_type = trash_cleaner_type
    job_id_url_kwarg = 'job_id'

    def post(self, request, *args, **kwargs):
        job = get_object_or_404(
            Job,
            id=kwargs[self.job_id_url_kwarg],
            type_id=self.job_type.id,
        )

        if job.user != request.user:
            raise PermissionDenied('You can only terminate your cleaner jobs.')

        if not job.is_finished:
            raise ConflictError('A non finished job cannot be terminated.')

        if EntityJobResult.objects.filter(job=job).exists():
            # if request.is_ajax():
            if is_ajax(request):
                return HttpResponse(job.get_absolute_url(), content_type='text/plain')

            return redirect(job)

        job.delete()

        return HttpResponse()


class EntityRestoration(base.EntityRelatedMixin, base.CheckedView):
    entity_select_for_update = True

    def build_related_entity_queryset(self, model):
        return super().build_related_entity_queryset(model=model).filter(is_deleted=True)

    def check_related_entity_permissions(self, entity, user):
        if entity.get_delete_absolute_url() != CremeEntity.get_delete_absolute_url(entity):
            raise Http404(gettext('This model does not use the generic deletion view.'))

        if hasattr(entity, 'get_related_entity'):
            raise Http404('Can not restore an auxiliary entity')  # See trash_entity()

        user.has_perm_to_delete_or_die(entity)

    @atomic
    def post(self, request, *args, **kwargs):
        entity = self.get_related_entity()

        entity.restore()

        # if request.is_ajax():
        if is_ajax(request):
            return HttpResponse()

        return redirect(entity)


# TODO: used by EntityFilterDeletion => split ? rename ?
class EntityDeletionMixin:
    dependencies_limit = 3

    def check_entity_for_deletion(self, entity, user):
        if entity.get_delete_absolute_url() != CremeEntity.get_delete_absolute_url(entity):
            raise ConflictError(
                gettext('«{entity}» does not use the generic deletion view.').format(
                    entity=entity.allowed_str(user),
                )
            )

        if hasattr(entity, 'get_related_entity'):
            related = entity.get_related_entity()

            if related is None:
                logger.critical(
                    'delete_entity(): an auxiliary entity seems orphan (id=%s)',
                    entity.id,
                )
                raise PermissionDenied(
                    gettext('You are not allowed to delete this entity: {}').format(
                        entity.allowed_str(user),
                    )
                )

            if not user.has_perm_to_change(related):
                raise PermissionDenied(
                    gettext('{entity} : <b>Permission denied</b>').format(
                        entity=entity.allowed_str(user),
                    )
                )
        else:
            if not user.has_perm_to_delete(entity):
                raise PermissionDenied(
                    gettext('{entity} : <b>Permission denied</b>').format(
                        entity=entity.allowed_str(user),
                    )
                )

    def delete_entity(self, entity, user):
        try:
            if self.move_to_trash(entity):
                entity.trash()
            else:
                entity.delete()
        except SpecificProtectedError as e:
            raise ConflictError(
                '{} {}'.format(
                    gettext('«{entity}» can not be deleted.').format(
                        entity=entity.allowed_str(user),
                    ),
                    e.args[0],
                ),
            ) from e
        except ProtectedError as e:
            raise ConflictError(
                gettext(
                    '«{entity}» can not be deleted because of its dependencies '
                    '({dependencies}).'
                ).format(
                    entity=entity.allowed_str(user),
                    dependencies=self.dependencies_to_str(
                        dependencies=e.args[1],
                        user=user,
                    ),
                ),
            ) from e
        except Exception as e:
            logger.exception('Error when trying to empty the trash')
            raise ConflictError(
                gettext('«{entity}» deletion caused an unexpected error [{error}].').format(
                    entity=entity.allowed_str(user),
                    error=e,
                ),
            ) from e

    def dependencies_to_str(self, *, dependencies, user):
        def deps_generator():
            not_viewable_count = 0
            can_view = user.has_perm_to_view

            def is_printable_relation(dep):
                return isinstance(dep, Relation) and '-object_' not in dep.type_id

            for dep in dependencies:
                if isinstance(dep, CremeEntity):
                    if can_view(dep):
                        yield gettext('«{object}» ({model})').format(
                            object=dep, model=dep.entity_type,
                        )
                    else:
                        not_viewable_count += 1

            for dep in dependencies:
                if is_printable_relation(dep) and can_view(dep.object_entity):
                    yield f'{dep.type.predicate} «{dep.object_entity}»'

            if not_viewable_count:
                yield ngettext(
                    '{count} not viewable entity',
                    '{count} not viewable entities',
                    not_viewable_count
                ).format(count=not_viewable_count)

            for dep in dependencies:
                if is_printable_relation(dep) and not can_view(dep.object_entity):
                    yield f'{dep.type.predicate} «{settings.HIDDEN_VALUE}»'

            for dep in dependencies:
                if not isinstance(dep, (CremeEntity, Relation)):
                    yield str(dep)

        limit = self.dependencies_limit
        str_deps = [*islice(deps_generator(), limit + 1)]

        do_ellipsis = False
        if len(str_deps) > limit:
            str_deps.pop()
            do_ellipsis = True

        result = ', '.join(str_deps[:limit])

        return result + '…' if do_ellipsis else result

    def move_to_trash(self, entity):
        return False if hasattr(entity, 'get_related_entity') else not entity.is_deleted


class EntitiesDeletion(EntityDeletionMixin, base.CheckedView):
    "Delete several CremeEntities, with a Ajax call (POST method)."

    def get_entity_ids(self):
        try:
            entity_ids = [
                int(e_id)
                for e_id in get_from_POST_or_404(self.request.POST, 'ids').split(',')
                if e_id
            ]
        except ValueError as e:
            raise BadRequestError(f'Bad POST argument ({e})') from e

        if not entity_ids:
            raise BadRequestError('Empty "ids" argument.')

        logger.debug('delete_entities() -> ids: %s ', entity_ids)

        return entity_ids

    def post(self, request, *args, **kwargs):
        entity_ids = self.get_entity_ids()
        user = request.user
        errors = defaultdict(list)

        with atomic():
            entities = [*CremeEntity.objects.select_for_update().filter(pk__in=entity_ids)]

            len_diff = len(entity_ids) - len(entities)
            if len_diff:
                errors[404].append(
                    ngettext(
                        "{count} entity doesn't exist or has been removed.",
                        "{count} entities don't exist or have been removed.",
                        len_diff
                    ).format(count=len_diff)
                )

            CremeEntity.populate_real_entities(entities)

            for entity in entities:
                real_entity = entity.get_real_entity()

                try:
                    self.check_entity_for_deletion(entity=real_entity, user=user)
                    self.delete_entity(entity=entity.get_real_entity(), user=user)
                except PermissionDenied as e:
                    errors[403].append(e.args[0])
                except ConflictError as e:
                    errors[409].append(e.args[0])

        if not errors:
            status = 200
            message = gettext('Operation successfully completed')
            content_type = None
        else:
            status = min(errors)
            message = json_encode({
                'count': len(entity_ids),
                'errors': [msg for error_messages in errors.values() for msg in error_messages],
            })
            content_type = 'application/json'

        return HttpResponse(message, content_type=content_type, status=status)


class EntityDeletion(EntityDeletionMixin,
                     base.EntityRelatedMixin,
                     generic.CremeDeletion):
    entity_select_for_update = True

    def check_related_entity_permissions(self, entity, user):
        self.check_entity_for_deletion(entity, user)

    def get_url_for_entity(self):
        entity = self.get_related_entity()

        if hasattr(entity, 'get_lv_absolute_url'):
            return entity.get_lv_absolute_url()

        if hasattr(entity, 'get_related_entity'):
            return entity.get_related_entity().get_absolute_url()

        return reverse('creme_core__home')

    def get_ajax_success_url(self):
        # NB: we redirect because this view can be used from the detail-view
        #     (if it's a definitive deletion, we MUST go to a new page anyway)
        return self.get_url_for_entity()

    def get_success_url(self):
        # TODO: callback_url?
        return self.get_url_for_entity()

    @atomic
    def perform_deletion(self, request):
        self.delete_entity(entity=self.get_related_entity(), user=request.user)


class RelatedToEntityDeletion(generic.base.ContentTypeRelatedMixin,
                              generic.CremeModelDeletion):
    def check_instance_permissions(self, instance, user):
        try:
            entity = instance.get_related_entity()
        except AttributeError:
            raise ConflictError('This is not an auxiliary model.')

        user.has_perm_to_change_or_die(entity)

    @property
    def model(self):
        model = self.get_ctype().model_class()
        if issubclass(model, CremeEntity):
            raise ConflictError('This view can not delete CremeEntities.')

        return model

    def get_success_url(self):
        return self.object.get_related_entity().get_absolute_url()

    def perform_deletion(self, request):
        try:
            super().perform_deletion(request)
        except ProtectedError as e:
            raise PermissionDenied(e.args[0]) from e


class SuperusersRestriction(base.CheckedView):
    permissions = SUPERUSER_PERM
    enable_sandbox_arg = 'set'
    entity_id_arg = 'id'
    sandbox_uuid = constants.UUID_SANDBOX_SUPERUSERS

    def get_enable_sandbox(self):
        return get_from_POST_or_404(
            self.request.POST,
            key=self.enable_sandbox_arg,
            cast=bool_from_str_extended,
            default='1',
        )

    def get_entity_id(self):
        return get_from_POST_or_404(
            self.request.POST,
            key=self.entity_id_arg,
            cast=int,
        )

    def get_entity(self):
        return get_object_or_404(
            CremeEntity.objects.select_for_update(),
            id=self.get_entity_id(),
        )

    @atomic
    def post(self, request, *args, **kwargs):
        set_sandbox = self.get_enable_sandbox()
        entity = self.get_entity()

        if set_sandbox:
            if entity.sandbox_id:
                raise ConflictError('This entity is already in a sandbox.')

            entity.sandbox = Sandbox.objects.get(uuid=self.sandbox_uuid)
            entity.save()
        else:
            sandbox = entity.sandbox

            if not sandbox or str(sandbox.uuid) != self.sandbox_uuid:
                raise ConflictError(
                    'This entity is not in the "Restricted to superusers" sandbox.'
                )

            entity.sandbox = None
            entity.save()

        return HttpResponse()


# TODO: only GET ?
class EntitiesListPopup(base.EntityCTypeRelatedMixin, listview.BaseEntitiesListPopup):
    """ Displays a list-view selector in an inner popup, to select one or more
    entities of a given type.

    New GET/POST parameter:
      - 'ct_id': the ContentType's ID of the model we want. Required.
    """
    def get_ctype_id(self):
        request = self.request

        return (
            get_from_POST_or_404(request.POST, self.ctype_id_url_kwarg)
            if request.method == 'POST' else
            get_from_GET_or_404(request.GET, self.ctype_id_url_kwarg)
        )

    @property
    def model(self):
        return self.get_ctype().model_class()

    def get_state_id(self):
        return f'{self.get_ctype().id}#{super().get_state_id()}'
