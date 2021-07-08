# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2021  Hybird
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

from functools import partial

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity, CremeModel
from creme.creme_core.utils import split_filter

from .. import get_pollform_model, get_pollreply_model
from .base import _PollLine
from .poll_type import PollType


class AbstractPollForm(CremeEntity):
    name = models.CharField(_('Name'), max_length=220)
    type = models.ForeignKey(
        PollType,
        verbose_name=_('Type'), null=True, blank=True, on_delete=models.SET_NULL,
    )

    creation_label = _('Create a form')
    save_label     = _('Save the form of poll')

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'polls'
        verbose_name = _('Form of poll')
        verbose_name_plural = _('Forms of poll')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('polls__view_form', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('polls__create_form')

    def get_edit_absolute_url(self):
        return reverse('polls__edit_form', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('polls__list_forms')

    def _post_clone(self, source):
        source.duplicate_tree(self, source.lines.filter(disabled=False))

    def _build_section_matches(self, instance):
        """Build a dict that is the correspondence between PollFormSection &
        clone or PollReplySection instances.
        """
        instance_classname = instance.__class__.__name__

        if instance_classname == 'PollForm':
            create_section = partial(PollFormSection.objects.create, pform=instance)
        elif instance_classname == 'PollReply':
            from .poll_reply import PollReplySection
            create_section = partial(PollReplySection.objects.create, preply=instance)

        # id = ID of PollFormSection instance ;
        # value = corresponding PollReplySection or PollFormSection instance.
        matches = {}

        fsections = [*self.sections.all()]
        parents = [None]  # set ??

        # At each loop, we take a level of PollFormSection (root, then their
        # children, then the children of children etc...), and we create for each
        # PollFormSection the corresponding PollFormSection or PollReplySection.
        while fsections:
            children, fsections = split_filter(
                (lambda section: section.parent in parents),
                fsections,
            )

            matches.update(
                (
                    child.id,
                    create_section(
                        name=child.name,
                        body=child.body,
                        order=child.order,
                        parent=matches.get(child.parent_id),
                    )
                ) for child in children
            )

            parents = children

        return matches

    def duplicate_tree(self, instance, pform_lines):
        from .poll_reply import PollReplyLine, PollReplyLineCondition

        if isinstance(instance, get_pollform_model()):
            create_line = partial(PollFormLine.objects.create, pform=instance)
            create_cond = PollFormLineCondition.objects.create
            reply_tree = False
        elif isinstance(instance, get_pollreply_model()):
            create_line = partial(PollReplyLine.objects.create, preply=instance)
            create_cond = PollReplyLineCondition.objects.create
            reply_tree = True

        section_matches = self._build_section_matches(instance)

        line_matches = {}  # PollFormLine.id -> PollReplyLined

        for i, line in enumerate(pform_lines, start=1):
            extra_args = {'pform_line': line} if reply_tree else {}
            line_matches[line.id] = create_line(
                section=section_matches.get(line.section_id),
                order=i,
                type=line.type,
                type_args=line.poll_line_type.cleaned_serialized_args(),
                conds_use_or=line.conds_use_or,
                question=line.question,
                **extra_args
            )

        for fcond in PollFormLineCondition.objects.filter(
            line__in=[line.id for line in pform_lines],
        ):
            create_cond(
                line=line_matches[fcond.line_id],
                source=line_matches[fcond.source_id],
                operator=fcond.operator,
                raw_answer=fcond.raw_answer,
            )
        return instance


class PollForm(AbstractPollForm):
    class Meta(AbstractPollForm.Meta):
        swappable = 'POLLS_FORM_MODEL'


class PollFormSection(CremeModel):
    pform = models.ForeignKey(
        settings.POLLS_FORM_MODEL,
        editable=False, related_name='sections', on_delete=models.CASCADE,
    )
    # TODO: related_name='children' ?
    parent = models.ForeignKey(
        'self', editable=False, null=True, on_delete=models.CASCADE,
    )
    order = models.PositiveIntegerField(editable=False, default=1)
    name = models.CharField(_('Name'), max_length=250)
    body = models.TextField(_('Section body'), blank=True)

    creation_label = _('Create a section')
    save_label     = _('Save the section')

    class Meta:
        app_label = 'polls'
        verbose_name = _('Section')
        verbose_name_plural = _('Sections')
        ordering = ('order',)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'PollFormSection(id={self.id}, name={self.name}, parent={self.parent_id})'

    def delete(self, *args, **kwargs):
        from ..utils import SectionTree

        section_id = self.id

        for node in SectionTree(self.pform):
            if node.is_section and node.id == section_id:
                if not node.has_line:
                    break

                raise models.ProtectedError(
                    gettext('There is at least one question in this section.'),
                    [self],
                )

        super().delete(*args, **kwargs)

    def get_edit_absolute_url(self):
        return reverse('polls__edit_form_section', args=(self.id,))

    def get_related_entity(self):  # For generic views
        return self.pform


class PollFormLine(CremeModel, _PollLine):
    pform = models.ForeignKey(
        settings.POLLS_FORM_MODEL,
        editable=False, related_name='lines', on_delete=models.CASCADE,
    )
    # TODO: related_name='lines' ?
    section = models.ForeignKey(
        PollFormSection, editable=False, null=True, on_delete=models.CASCADE,
    )
    order = models.PositiveIntegerField(editable=False, default=1)
    disabled = models.BooleanField(default=False, editable=False)

    # See PollLineType
    #   ['choices' is not set here, in order to allow the contribution by other apps]
    type = models.PositiveSmallIntegerField(_('Type'))
    type_args = models.TextField(editable=False, null=True)  # TODO: use a JSONField ?

    # null=True -> no conditions (NB: can we use it to avoid queries ?)
    # conds_use_or = NullBooleanField(_('Use OR or AND between conditions'), editable=False)
    conds_use_or = models.BooleanField(
        _('Use OR or AND between conditions'), editable=False, null=True,
    )

    question = models.TextField(_('Question'))

    creation_label = _('Create a question')
    save_label     = _('Save the question')

    class Meta:
        app_label = 'polls'
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')
        ordering = ('order',)

    def __repr__(self):
        return f'PollFormLine(section={self.section_id}, question="{self.question}")'

    def __str__(self):
        return self.question

    @classmethod
    def _get_condition_class(cls):  # See _PollLine
        return PollFormLineCondition

    def delete(self, *args, **kwargs):
        if not self.disabled and PollFormLineCondition.objects.filter(source=self).exists():
            raise models.ProtectedError(
                gettext(
                    'There is at least one other question which depends on this question.'
                ),
                [self],
            )

        super().delete(*args, **kwargs)

    def disable(self):
        if self.disabled:
            raise models.ProtectedError(
                gettext('This question is already disabled.'), [self],
            )

        if PollFormLineCondition.objects.filter(source=self).exists():
            raise models.ProtectedError(
                gettext(
                    'There is at least one other question which depends on this question.'
                ),
                [self],
            )

        self.disabled = True
        self.conditions.all().delete()
        self.save()

    def get_edit_absolute_url(self):
        return reverse('polls__edit_form_line', args=(self.id,))

    def get_related_entity(self):  # For generic views
        return self.pform

    @property
    def verbose_conds_use_or(self):  # TODO: templatetag instead ?
        return gettext('OR') if self.conds_use_or else gettext('AND')


class PollFormLineCondition(CremeModel):
    # copied fom EntityFilterCondition
    EQUALS = 1
    # IEQUALS         =  2
    # EQUALS_NOT      =  3
    # IEQUALS_NOT     =  4
    # CONTAINS        =  5
    # ICONTAINS       =  6
    # CONTAINS_NOT    =  7
    # ICONTAINS_NOT   =  8
    # GT              =  9
    # GTE             = 10
    # LT              = 11
    # LTE             = 12
    # STARTSWITH      = 13
    # ISTARTSWITH     = 14
    # STARTSWITH_NOT  = 15
    # ISTARTSWITH_NOT = 16
    # ENDSWITH        = 17
    # IENDSWITH       = 18
    # ENDSWITH_NOT    = 19
    # IENDSWITH_NOT   = 20
    # ISEMPTY         = 21
    # RANGE           = 22

    line = models.ForeignKey(
        PollFormLine,
        editable=False, related_name='conditions', on_delete=models.CASCADE,
    )
    source = models.ForeignKey(PollFormLine, on_delete=models.CASCADE)
    operator = models.PositiveSmallIntegerField()  # See EQUALS etc...
    raw_answer = models.TextField(null=True)

    save_label = _('Save the condition')

    class Meta:
        app_label = 'polls'

    def __repr__(self):
        return f'PollFormLineCondition(source={self.source_id}, raw_answer="{self.raw_answer}")'

    # TODO: factorise with EntityFilterCondition.condition
    def update(self, other_condition):
        """Fill a condition with the content a another one
        (in order to reuse the old instance if possible).
        @return True if there is at least one change, else False.
        """
        changed = False

        for attr in ('source', 'operator', 'raw_answer'):
            other = getattr(other_condition, attr)

            if getattr(self, attr) != other:
                setattr(self, attr, other)
                changed = True

        return changed
