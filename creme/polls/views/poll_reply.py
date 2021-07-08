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

import logging

from django.db.transaction import atomic
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext

from creme import persons, polls
from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import (
    login_required,
    permission_required,
)
from creme.creme_core.http import is_ajax
from creme.creme_core.templatetags.creme_widgets import (
    get_icon_by_name,
    get_icon_size_px,
)
from creme.creme_core.utils import get_from_POST_or_404, update_model_instance
from creme.creme_core.utils.media import get_current_theme
from creme.creme_core.views import generic

from ..constants import DEFAULT_HFILTER_PREPLY
from ..core import MultiEnumPollLineType
from ..forms import poll_reply as preply_forms
from ..models import PollReplyLine
from ..utils import NodeStyle, ReplySectionTree

logger = logging.getLogger(__name__)
Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()
PollReply = polls.get_pollreply_model()
_CREATION_PERM = cperm(PollReply)


# Function views --------------------------------------------------------------

# TODO: do this job in template instead ??
def _format_previous_answered_question(preply_id, line, style):
    if not line.applicable:
        answer = pgettext('polls', 'N/A')
    # TODO: isinstance(answer, list) ??
    elif isinstance(line.poll_line_type, MultiEnumPollLineType):
        answer = mark_safe(', '.join(escape(choice) for choice in line.answer))
    else:
        answer = line.answer

    number = style.number(line)
    theme = get_current_theme()

    return format_html(
        '<b>{title}</b><br>'
        '{label} : {number} {question}<br>'
        '{answer_str} : {answer} <a class="add" href="{url}">{icon}</a>',
        title=gettext('Reminder of the previous answered question :'),
        label=gettext('Question'),
        number=f'{number} -' if number != 'None' else '',
        question=line.question,
        answer_str=gettext('Answer'),
        answer=answer,
        url=reverse('polls__edit_reply_line_wizard', args=(preply_id, line.id)),
        icon=get_icon_by_name(
            'edit',
            theme=theme, label=_('Edit'),
            size_px=get_icon_size_px(theme, size='instance-button'),
        ).render(css_class='polls-previous-edition'),
    )


@login_required
@permission_required('polls')
@atomic
def edit_line_wizard(request, preply_id, line_id):
    preply = get_object_or_404(PollReply.objects.select_for_update(), pk=preply_id)

    user = request.user
    user.has_perm_to_change_or_die(preply)

    tree = ReplySectionTree(preply)

    try:
        line_node = tree.find_line(int(line_id))
    except KeyError as e:
        msg = f'PollReplyLine with this id {line_id} does not exist for PollReply {preply}'
        logger.error(msg)
        raise Http404(msg) from e

    previous_answer = None

    # TODO: pass instance=preply
    if request.method == 'POST':
        form = preply_forms.PollReplyFillForm(
            line_node=line_node, user=user, data=request.POST,
        )

        if form.is_valid():
            form.save()

            # Optimize 'next_question_to_answer' & cie
            PollReplyLine.populate_conditions([
                node for node in tree if not node.is_section
            ])

            _clear_dependant_answers(tree, line_node)

            if not tree.next_question_to_answer:
                is_complete = True
                url = preply.get_absolute_url()
            else:
                is_complete = False
                url = reverse('polls__fill_reply', args=(preply_id,))

            update_model_instance(preply, is_complete=is_complete)

            return HttpResponseRedirect(url)
    else:
        previous = tree.get_previous_answered_question(line_node)

        if previous:
            previous_answer = _format_previous_answered_question(
                preply_id, previous, NodeStyle(),
            )

        form = preply_forms.PollReplyFillForm(line_node=line_node, user=user)

    return render(
        request, 'creme_core/generics/blockform/edit.html',
        {
            'title':        gettext('Answers of the form : {}').format(preply),
            'form':         form,
            'help_message': previous_answer,
            'cancel_url':   preply.get_absolute_url(),
        },
    )


@login_required
@permission_required('polls')
@atomic
def fill(request, preply_id):
    preply = get_object_or_404(PollReply.objects.select_for_update(), pk=preply_id)

    user = request.user
    user.has_perm_to_change_or_die(preply)

    if preply.is_complete:
        raise Http404(gettext('All questions have been answered.'))

    tree = ReplySectionTree(preply)
    line_node = tree.next_question_to_answer

    if line_node is None:
        msg = f'No empty PollReplyLine found in PollReply {preply}'
        logger.error(msg)
        raise Http404(msg)

    previous_answer = None

    # TODO: pass instance=preply
    if request.method == 'POST':
        form = preply_forms.PollReplyFillForm(
            line_node=line_node, user=user, data=request.POST,
        )

        if form.is_valid():
            form.save()

            next_line = tree.next_question_to_answer

            if not next_line:
                preply.is_complete = True
                preply.save()

                return redirect(preply)

            previous_answer = _format_previous_answered_question(
                preply_id, line_node, NodeStyle(),
            )
            form = preply_forms.PollReplyFillForm(line_node=next_line, user=user)
    else:
        previous = tree.get_previous_answered_question(line_node)
        if previous:
            previous_answer = _format_previous_answered_question(
                preply_id, previous, NodeStyle(),
            )

        form = preply_forms.PollReplyFillForm(line_node=line_node, user=user)

    return render(
        request, 'creme_core/generics/blockform/edit.html',
        {
            'title':        gettext('Answers of the form : {}').format(preply),
            'form':         form,
            'help_message': previous_answer,
            'cancel_url':   preply.get_absolute_url(),
        },
    )


def _clear_dependant_answers(tree, line_node):
    find_line = tree.find_line

    for condition in line_node.get_reversed_conditions():
        dep_line_node = find_line(condition.line_id)

        update_model_instance(dep_line_node, raw_answer=None)
        _clear_dependant_answers(tree, dep_line_node)


# Class-based views  ----------------------------------------------------------


class PollRepliesCreation(generic.CremeFormView):
    # model = PollReply
    form_class = preply_forms.PollRepliesCreateForm
    permissions = ('polls', _CREATION_PERM)
    title = PollReply.multi_creation_label
    submit_label = PollReply.multi_save_label

    def form_valid(self, form):
        form.save()
        preplies = form.preplies

        return HttpResponseRedirect(
            preplies[0].get_absolute_url() if preplies else self.get_success_url()
        )


class _RelatedRepliesCreationBase(generic.RelatedToEntityFormPopup):
    model = PollReply
    form_class = preply_forms.PollRepliesCreateForm
    permissions = ('polls', _CREATION_PERM)
    title = _('New replies for «{entity}»')
    submit_label = PollReply.multi_save_label

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)  # ??
        user.has_perm_to_link_or_die(entity)


class RepliesCreationFromCampaign(_RelatedRepliesCreationBase):
    entity_id_url_kwarg = 'campaign_id'
    entity_classes = polls.get_pollcampaign_model()


class RepliesCreationFromPForm(_RelatedRepliesCreationBase):
    entity_id_url_kwarg = 'pform_id'
    entity_classes = polls.get_pollform_model()


class RepliesCreationFromPerson(_RelatedRepliesCreationBase):
    entity_id_url_kwarg = 'person_id'
    entity_classes = [Contact, Organisation]


class PollReplyDetail(generic.EntityDetail):
    model = PollReply
    template_name = 'polls/view_pollreply.html'
    pk_url_kwarg = 'preply_id'


class PollReplyEdition(generic.EntityEdition):
    model = PollReply
    form_class = preply_forms.PollReplyEditForm
    pk_url_kwarg = 'preply_id'


class LinkingRepliesToPerson(generic.RelatedToEntityFormPopup):
    # model = PollReply
    template_name = 'creme_core/generics/blockform/link-popup.html'
    form_class = preply_forms.PersonAddRepliesForm
    title = _('Existing replies for «{entity}»')
    permissions = 'polls'
    submit_label = _('Link to the replies')
    entity_id_url_kwarg = 'person_id'
    entity_classes = [Contact, Organisation]

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)


# Beware: if we use RelatedToEntityEdition(), & transform PollReplyLine in a True
#         auxiliary model (ie: has a get_related_entity() method), the generic
#         delete view could be called without our consent.
# TODO: if not line's type.editable ??
# TODO: help_text (cleared answers + conditions etc...) ??
class LineEdition(generic.EntityEditionPopup):
    model = PollReply
    form_class = preply_forms.PollReplyFillForm
    pk_url_kwarg = 'preply_id'
    title = _('Answer edition')
    submit_label = _('Save the modification')
    line_id_url_kwarg = 'line_id'

    def __init__(self, *args, **kwargs):
        super(LineEdition, self).__init__(*args, **kwargs)
        self.tree = None
        self.line_node = None

    def get_tree(self):
        tree = self.tree
        if tree is None:
            self.tree = tree = ReplySectionTree(self.object)

        return tree

    def get_line_node(self, tree):
        line_node = self.line_node

        if line_node is None:
            try:
                line_node = tree.find_line(int(self.kwargs[self.line_id_url_kwarg]))
            except KeyError as e:
                raise Http404(
                    'This PollReplyLine id does not correspond to the PollReply instance'
                ) from e

            if not tree.conditions_are_met(line_node):
                raise Http404(
                    'This answered can not be edited (conditions are not met)'
                )

            self.line_node = line_node

        return line_node

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['line_node'] = self.get_line_node(tree=self.get_tree())

        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form=form)

        tree = self.get_tree()
        _clear_dependant_answers(tree, self.get_line_node(tree))
        update_model_instance(
            self.object,
            is_complete=not bool(tree.next_question_to_answer),
        )

        return response


class PollRepliesList(generic.EntitiesList):
    model = PollReply
    default_headerfilter_id = DEFAULT_HFILTER_PREPLY


class PollReplyCleaning(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'polls'
    entity_classes = PollReply
    preply_id_arg = 'id'
    entity_select_for_update = True

    def clean(self, preply):
        preply.lines.update(raw_answer=None, applicable=True)  # Avoids statistics artifacts
        update_model_instance(preply, is_complete=False)

    def get_related_entity_id(self):
        return get_from_POST_or_404(self.request.POST, self.preply_id_arg)

    def post(self, request, *args, **kwargs):
        with atomic():
            preply = self.get_related_entity()
            self.clean(preply)

        # if request.is_ajax():
        if is_ajax(request):
            return HttpResponse()

        return redirect(preply)
