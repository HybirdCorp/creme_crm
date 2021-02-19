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

from django.conf import settings
from django.db.models import (
    CASCADE,
    PROTECT,
    SET_NULL,
    BooleanField,
    CharField,
    ForeignKey,
    NullBooleanField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    TextField,
)
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import CremeEntity, CremeModel

from .base import _PollLine
from .poll_form import PollFormLine
from .poll_type import PollType


class AbstractPollReply(CremeEntity):
    name        = CharField(_('Name'), max_length=250)
    pform       = ForeignKey(settings.POLLS_FORM_MODEL, verbose_name=_('Related form'),
                             editable=False, on_delete=PROTECT,
                            )
    campaign    = ForeignKey(settings.POLLS_CAMPAIGN_MODEL,
                             verbose_name=pgettext_lazy('polls', 'Related campaign'),
                             on_delete=PROTECT, null=True, blank=True,
                            )
    person      = ForeignKey(CremeEntity, verbose_name=_('Person who filled'),
                             on_delete=PROTECT,
                             null=True, blank=True, related_name='+',
                            )
    type        = ForeignKey(PollType, verbose_name=_('Type'),
                             editable=False, on_delete=SET_NULL,
                             null=True, blank=True,
                            )
    is_complete = BooleanField(_('Is complete'), default=False, editable=False)

    creation_label = _('Create a reply')
    save_label     = _('Save the reply')
    multi_creation_label = _('Create replies')
    multi_save_label     = _('Save the replies')

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'polls'
        verbose_name = _('Form reply')
        verbose_name_plural = _('Form replies')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('polls__view_reply', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('polls__create_reply')

    def get_edit_absolute_url(self):
        return reverse('polls__edit_reply', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('polls__list_replies')


class PollReply(AbstractPollReply):
    class Meta(AbstractPollReply.Meta):
        swappable = 'POLLS_REPLY_MODEL'


# TODO: factorise (abstract class) ?
class PollReplySection(CremeModel):
    preply = ForeignKey(
        settings.POLLS_REPLY_MODEL, editable=False, related_name='sections',
        on_delete=CASCADE,
    )
    # TODO: related_name='children' ?
    parent = ForeignKey('self', editable=False, null=True, on_delete=CASCADE)
    order  = PositiveIntegerField(editable=False, default=1)
    name   = CharField(_('Name'), max_length=250)
    body   = TextField(_('Section body'), blank=True)

    class Meta:
        app_label = 'polls'
        verbose_name = _('Section')
        verbose_name_plural = _('Sections')
        ordering = ('order',)

    def __str__(self):
        return self.name


class PollReplyLine(CremeModel, _PollLine):
    preply = ForeignKey(
        settings.POLLS_REPLY_MODEL, editable=False, related_name='lines', on_delete=CASCADE,
    )
    # TODO: related_name='lines' ?
    section = ForeignKey(PollReplySection, editable=False, null=True, on_delete=CASCADE)
    # TODO: related_name='lines' ?
    pform_line = ForeignKey(PollFormLine, editable=False, on_delete=CASCADE)
    order = PositiveIntegerField(editable=False, default=1)
    type = PositiveSmallIntegerField(editable=False)
    type_args = TextField(editable=False, null=True)

    # null=True -> no conditions (NB: can we use it to avoid queries ?)
    applicable = BooleanField(_('Applicable'), default=True, editable=False)

    # null=True -> no conditions (NB: can we use it to avoid queries ?)
    conds_use_or = NullBooleanField(_('Use OR or AND between conditions'), editable=False)

    question = TextField(_('Question'))

    # NULL == not answered  [tip: use the property 'answer']
    raw_answer = TextField(_('Answer'), null=True)

    class Meta:
        app_label = 'polls'
        ordering = ('order',)

    def __repr__(self):
        return (
            f'PollReplyLine('
            f'section={self.section_id}, '
            f'question="{self.question}", '
            f'answer="{self.answer}"'
            f')'
        )

    @classmethod
    def _get_condition_class(cls):  # See _PollLine
        return PollReplyLineCondition

    @property
    def answer(self):
        try:
            return self.poll_line_type.decode_answer(self.raw_answer)
        except Exception:
            return 'INVALID'

    @answer.setter
    def answer(self, value):
        self.raw_answer = self.poll_line_type.encode_answer(value)

    @property
    def answer_formfield(self):
        line_type = self.poll_line_type

        if line_type.editable:
            answer_field = line_type.formfield(self.raw_answer)
            answer_field.label = gettext('Answer')
        else:
            answer_field = None

        return answer_field

    @property
    def stats(self):
        if not self.applicable:
            return []

        return self.poll_line_type.get_stats(self.raw_answer)


class PollReplyLineCondition(CremeModel):
    line = ForeignKey(
        PollReplyLine, editable=False, related_name='conditions', on_delete=CASCADE,
    )
    source = ForeignKey(PollReplyLine, on_delete=CASCADE)
    operator = PositiveSmallIntegerField()  # See EQUALS etc...
    raw_answer = TextField(null=True)

    class Meta:
        app_label = 'polls'

    # We give the source to simplify the deletion of useless queries
    def is_met(self, source):
        return source.poll_line_type.is_condition_met(source.raw_answer, self.raw_answer)
