# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2014  Hybird
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

from django.db.models import (CharField, TextField, BooleanField, NullBooleanField,
                              PositiveIntegerField, PositiveSmallIntegerField,
                              ForeignKey, PROTECT, SET_NULL)
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.models import CremeModel, CremeEntity

from .base import _PollLine
from .poll_type import PollType
from .poll_form import PollForm, PollFormLine
from .campaign import PollCampaign


class PollReply(CremeEntity):
    name        = CharField(_(u'Name'), max_length=250)
    pform       = ForeignKey(PollForm, verbose_name=_(u'Related form'),
                             editable=False, on_delete=PROTECT,
                            )
    campaign    = ForeignKey(PollCampaign, verbose_name=_(u'Related campaign'),
                             on_delete=PROTECT, null=True, blank=True, #editable=False,
                            )
    person      = ForeignKey(CremeEntity, verbose_name=_(u'Person who filled'),
                             on_delete=PROTECT, #editable=False,
                             null=True, blank=True, related_name='+',
                            )
    type        = ForeignKey(PollType, verbose_name=_(u'Type'),
                             editable=False, on_delete=SET_NULL,
                             null=True, blank=True,
                            )
    is_complete = BooleanField(_(u'Is complete'), default=False, editable=False)

    #creation_label = _('Add a reply')
    creation_label = _(u'Add replies')

    class Meta:
        app_label = 'polls'
        verbose_name = _(u'Form reply')
        verbose_name_plural = _(u'Form replies')
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/polls/poll_reply/%s" % self.id

    def get_edit_absolute_url(self):
        return "/polls/poll_reply/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/polls/poll_replies"


#TODO: factorise (abstract class) ?
class PollReplySection(CremeModel):
    preply = ForeignKey(PollReply, editable=False, related_name='sections')
    parent = ForeignKey('self', editable=False, null=True) #, related_name='children'
    order  = PositiveIntegerField(editable=False, default=1)
    name   = CharField(_(u'Name'), max_length=250)
    body   = TextField(_(u'Section body'), null=True, blank=True)

    class Meta:
        app_label = 'polls'
        verbose_name = _(u'Section')
        verbose_name_plural = _(u'Sections')
        ordering = ('order',)

    def __unicode__(self):
        return self.name


class PollReplyLine(CremeModel, _PollLine):
    preply       = ForeignKey(PollReply, editable=False, related_name='lines')
    section      = ForeignKey(PollReplySection, editable=False, null=True) #, related_name='lines'
    pform_line   = ForeignKey(PollFormLine, editable=False) #, related_name='lines'
    order        = PositiveIntegerField(editable=False, default=1)
    type         = PositiveSmallIntegerField(editable=False)
    type_args    = TextField(editable=False, null=True)
    applicable   = BooleanField(_(u'Applicable'), default=True, editable=False) #null=True -> no conditions (NB: can we use it to avoid queries ?)
    conds_use_or = NullBooleanField(_(u'Use OR or AND between conditions'), editable=False) #null=True -> no conditions (NB: can we use it to avoid queries ?)
    question     = TextField(_(u'Question'))
    raw_answer   = TextField(_(u'Answer'), null=True) #NULL == not answered  [tip: use the property 'answer']

    class Meta:
        app_label = 'polls'
        ordering = ('order',)

    def __repr__(self):
        from django.utils.encoding import smart_str
        return smart_str(u'PollReplyLine(section=%s, question="%s", answer="%s")' % (
                            self.section_id, self.question, self.answer
                        ))

    @classmethod
    def _get_condition_class(cls): #See _PollLine
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
            answer_field.label = ugettext(u'Answer')
        else:
            answer_field = None

        return answer_field

    @property
    def stats(self):
        if not self.applicable:
            return []

        return self.poll_line_type.get_stats(self.raw_answer)


class PollReplyLineCondition(CremeModel):
    line       = ForeignKey(PollReplyLine, editable=False, related_name='conditions')
    source     = ForeignKey(PollReplyLine)
    operator   = PositiveSmallIntegerField() #see EQUALS etc...
    raw_answer = TextField(null=True)

    class Meta:
        app_label = 'polls'

    def is_met(self, source): #we give the source to simplify the deletion of useless queries
        return source.poll_line_type.is_condition_met(source.raw_answer, self.raw_answer)
