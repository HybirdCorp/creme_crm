# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2018  Hybird
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
import warnings

from django.db.transaction import atomic
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity
from creme.creme_core.templatetags.creme_widgets import get_icon_by_name, get_icon_size_px
from creme.creme_core.utils import get_from_POST_or_404, update_model_instance
from creme.creme_core.utils.media import get_current_theme
from creme.creme_core.views import generic

from creme import persons

from creme import polls

from ..constants import DEFAULT_HFILTER_PREPLY
from ..core import MultiEnumPollLineType
from ..forms import poll_reply as preply_forms
from ..models import PollReplyLine
from ..utils import ReplySectionTree, NodeStyle


logger = logging.getLogger(__name__)
Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()
PollReply = polls.get_pollreply_model()
_CREATION_PERM = cperm(PollReply)

# Function views --------------------------------------------------------------


def abstract_add_pollreply(request, form=preply_forms.PollRepliesCreateForm,
                           template='creme_core/generics/blockform/add.html',
                           submit_label=PollReply.multi_save_label,
                          ):
    warnings.warn('polls.views.poll_reply.abstract_add_pollreply() is deprecated ; '
                  'use the class-based view PollRepliesCreation instead.',
                  DeprecationWarning
                 )
    from creme.creme_core.views.utils import build_cancel_path

    if request.method == 'POST':
        POST = request.POST
        reply_form = form(user=request.user, data=POST)

        if reply_form.is_valid():
            reply_form.save()

            return redirect(reply_form.instance)

        cancel_url = POST.get('cancel_url')
    else:  # GET
        reply_form = form(user=request.user)
        cancel_url = build_cancel_path(request)

    return render(request, template,
                  {'form':         reply_form,
                   'title':        PollReply.creation_label,
                   'submit_label': submit_label,
                   'cancel_url':   cancel_url,
                  }
                 )


def abstract_add_preply_from_campaign(request, campaign_id,
                                      form=preply_forms.PollRepliesCreateForm,
                                      title=_('New replies for «%s»'),
                                      submit_label=PollReply.multi_save_label,
                                     ):
    warnings.warn('polls.views.poll_reply.abstract_add_preply_from_campaign() is deprecated ; '
                  'use the class-based view PollRepliesCreationFromCampaign instead.',
                  DeprecationWarning
                 )

    campaign = get_object_or_404(polls.get_pollcampaign_model(), pk=campaign_id)
    user = request.user

    user.has_perm_to_view_or_die(campaign)
    user.has_perm_to_link_or_die(campaign)

    return generic.add_model_with_popup(request, form,
                                        title % campaign,
                                        initial={'campaign': campaign},
                                        submit_label=submit_label,
                                       )


def abstract_add_preply_from_pform(request, pform_id, form=preply_forms.PollRepliesCreateForm,
                                   title=_('New replies for «%s»'),
                                   submit_label=PollReply.multi_save_label,
                                  ):
    warnings.warn('polls.views.poll_reply.abstract_add_preply_from_pform() is deprecated ; '
                  'use the class-based view PollRepliesCreationFromPForm instead.',
                  DeprecationWarning
                 )

    pform = get_object_or_404(polls.get_pollform_model(), pk=pform_id)
    user = request.user

    user.has_perm_to_view_or_die(pform)
    user.has_perm_to_link_or_die(pform)

    return generic.add_model_with_popup(request, form,
                                        title % pform,
                                        initial={'pform': pform},
                                        submit_label=submit_label,
                                       )


def abstract_add_preply_from_person(request, person_id,
                                    form=preply_forms.PollRepliesCreateForm,
                                    title=_('New replies for «%s»'),
                                    submit_label=PollReply.multi_save_label,
                                   ):
    warnings.warn('polls.views.poll_reply.abstract_add_preply_from_person() is deprecated ; '
                  'use the class-based view PollRepliesCreationFromPerson instead.',
                  DeprecationWarning
                 )

    person = get_object_or_404(CremeEntity, pk=person_id)
    user = request.user

    user.has_perm_to_view_or_die(person)
    user.has_perm_to_link_or_die(person)

    person = person.get_real_entity()

    if not isinstance(person, (Contact, Organisation)):
        raise Http404('You can only create from Contacts & Organisations')

    return generic.add_model_with_popup(request, form,
                                        title % person,
                                        initial={'persons': [person]},
                                        submit_label=submit_label,
                                       )


def abstract_edit_pollreply(request, preply_id, form=preply_forms.PollReplyEditForm):
    warnings.warn('polls.views.poll_reply.abstract_edit_pollreply() is deprecated ; '
                  'use the class-based view PollReplyEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, preply_id, PollReply, form)


def abstract_view_pollreply(request, preply_id,
                            template='polls/view_pollreply.html',
                           ):
    warnings.warn('polls.views.poll_reply.abstract_view_pollreply() is deprecated ; '
                  'use the class-based view PollReplyDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, preply_id, PollReply, template=template)


@login_required
@permission_required(('polls', _CREATION_PERM))
def add(request):
    warnings.warn('polls.views.poll_reply.add() is deprecated.', DeprecationWarning)
    return abstract_add_pollreply(request)


@login_required
@permission_required(('polls', _CREATION_PERM))
def add_from_pform(request, pform_id):
    warnings.warn('polls.views.poll_reply.add_from_pform() is deprecated.', DeprecationWarning)
    return abstract_add_preply_from_pform(request, pform_id)


@login_required
@permission_required(('polls', _CREATION_PERM))
def add_from_campaign(request, campaign_id):
    warnings.warn('polls.views.poll_reply.add_from_campaign() is deprecated.', DeprecationWarning)
    return abstract_add_preply_from_campaign(request, campaign_id)


@login_required
@permission_required(('polls', _CREATION_PERM))
def add_from_person(request, person_id):
    warnings.warn('polls.views.poll_reply.add_from_person() is deprecated.', DeprecationWarning)
    return abstract_add_preply_from_person(request, person_id)


@login_required
@permission_required('polls')
def edit(request, preply_id):
    warnings.warn('polls.views.poll_reply.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_pollreply(request, preply_id)


@login_required
@permission_required('polls')
def detailview(request, preply_id):
    warnings.warn('polls.views.poll_reply.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_pollreply(request, preply_id)


@login_required
@permission_required('polls')
def listview(request):
    return generic.list_view(request, PollReply, hf_pk=DEFAULT_HFILTER_PREPLY)


# @login_required
# @permission_required(('polls', 'persons'))
# def link_to_person(request, person_id):
#     return generic.add_to_entity(request, person_id, preply_forms.PersonAddRepliesForm,
#                                  ugettext('Existing replies for «%s»'),
#                                  link_perm=True,
#                                  submit_label=_('Link to the replies'),
#                                  template='creme_core/generics/blockform/link_popup.html',
#                                 )


# TODO: do this job in template instead ??
def _format_previous_answered_question(preply_id, line, style):
    if not line.applicable:
        answer = pgettext('polls', 'N/A')
    elif isinstance(line.poll_line_type, MultiEnumPollLineType):  # TODO: isinstance(answer, list) ??
        answer = mark_safe(', '.join(escape(choice) for choice in line.answer))
    else:
        answer = line.answer

    number = style.number(line)
    theme = get_current_theme()

    return format_html(
        '<b>{title}</b><br>'
        '{label} : {number} {question}<br>'
        '{answer_str} : {answer} <a class="add" href="{url}">{icon}</a>',
        title=ugettext('Reminder of the previous answered question :'),
        label=ugettext('Question'),
        number='{} -'.format(number) if number != 'None' else '',
        question=line.question,
        answer_str=ugettext('Answer'),
        answer=answer,
        url=reverse('polls__edit_reply_line_wizard', args=(preply_id, line.id)),
        icon=get_icon_by_name('edit', theme=theme, label=_('Edit'),
                              size_px=get_icon_size_px(theme, size='instance-button'),
                             ).render(css_class='polls-previous-edition'),
    )


@login_required
@permission_required('polls')
@atomic
def edit_line_wizard(request, preply_id, line_id):
    # preply = get_object_or_404(PollReply, pk=preply_id)
    try:
        preply = PollReply.objects.select_for_update().get(pk=preply_id)
    except PollReply.DoesNotExist as e:
        raise Http404(str(e))

    user = request.user

    user.has_perm_to_change_or_die(preply)

    tree = ReplySectionTree(preply)

    try:
        line_node = tree.find_line(int(line_id))
    except KeyError as e:
        msg = 'PollReplyLine with this id {} does not exist for PollReply {}'.format(
                    line_id,
                    preply,
                )
        logger.error(msg)
        raise Http404(msg) from e

    previous_answer = None

    # TODO: pass instance=preply
    if request.method == 'POST':
        form = preply_forms.PollReplyFillForm(line_node=line_node, user=user, data=request.POST)

        if form.is_valid():
            # with atomic():
            form.save()

            # Optimize 'next_question_to_answer' & cie
            PollReplyLine.populate_conditions([node for node in tree if not node.is_section])

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
            previous_answer = _format_previous_answered_question(preply_id, previous, NodeStyle())

        form = preply_forms.PollReplyFillForm(line_node=line_node, user=user)

    return render(request, 'creme_core/generics/blockform/edit.html',
                  {'title':        ugettext('Answers of the form : {}').format(preply),
                   'form':         form,
                   'help_message': previous_answer,
                   'cancel_url':   preply.get_absolute_url(),
                  }
                 )


@login_required
@permission_required('polls')
@atomic
def fill(request, preply_id):
    # preply = get_object_or_404(PollReply, pk=preply_id)
    try:
        preply = PollReply.objects.select_for_update().get(pk=preply_id)
    except PollReply.DoesNotExist as e:
        raise Http404(str(e))

    user = request.user

    user.has_perm_to_change_or_die(preply)

    if preply.is_complete:
        raise Http404(ugettext('All questions have been answered.'))

    tree = ReplySectionTree(preply)
    line_node = tree.next_question_to_answer

    if line_node is None:
        msg = 'No empty PollReplyLine found in PollReply {}'.format(preply)
        logger.error(msg)
        raise Http404(msg)

    previous_answer = None

    # TODO: pass instance=preply
    if request.method == 'POST':
        form = preply_forms.PollReplyFillForm(line_node=line_node, user=user, data=request.POST)

        if form.is_valid():
            # with atomic():
            form.save()

            next_line = tree.next_question_to_answer

            if not next_line:
                preply.is_complete = True
                preply.save()

                return redirect(preply)

            previous_answer = _format_previous_answered_question(preply_id, line_node, NodeStyle())
            form = preply_forms.PollReplyFillForm(line_node=next_line, user=user)
    else:
        previous = tree.get_previous_answered_question(line_node)
        if previous:
            previous_answer = _format_previous_answered_question(preply_id, previous, NodeStyle())

        form = preply_forms.PollReplyFillForm(line_node=line_node, user=user)

    return render(request, 'creme_core/generics/blockform/edit.html',
                  {'title':        ugettext('Answers of the form : {}').format(preply),
                   'form':         form,
                   'help_message': previous_answer,
                   'cancel_url':   preply.get_absolute_url(),
                  }
                 )


@login_required
@permission_required('polls')
def clean(request):
    preply = get_object_or_404(PollReply, pk=get_from_POST_or_404(request.POST, 'id'))

    request.user.has_perm_to_change_or_die(preply)

    with atomic():
        preply.lines.update(raw_answer=None, applicable=True)  # Avoids statistics artifacts
        update_model_instance(preply, is_complete=False)

    if request.is_ajax():
        return HttpResponse()

    return redirect(preply)


def _clear_dependant_answers(tree, line_node):
    find_line = tree.find_line

    for condition in line_node.get_reversed_conditions():
        dep_line_node = find_line(condition.line_id)

        update_model_instance(dep_line_node, raw_answer=None)
        _clear_dependant_answers(tree, dep_line_node)


# # todo: if not line's type.editable ??
# @login_required
# @permission_required('polls')
# def edit_line(request, preply_id, line_id):
#     # NB: we do not use the generic view edit_related_to_entity(), because it would
#     #     oblige us to transform PollReplyLine in a True auxiliary model
#     #     (get_related_entity() method), so the delete view could be called without
#     #     our consent.
#     preply = get_object_or_404(PollReply, pk=preply_id)
#     user = request.user
#
#     user.has_perm_to_change_or_die(preply)
#
#     tree = ReplySectionTree(preply)
#
#     try:
#         line_node = tree.find_line(int(line_id))
#     except KeyError as e:
#         raise Http404('This PollReplyLine id does not correspond to the PollReply instance') from e
#
#     if not tree.conditions_are_met(line_node):
#         raise Http404('This answered can not be edited (conditions are not met)')
#
#     if request.method == 'POST':
#         edit_form = preply_forms.PollReplyFillForm(line_node=line_node, user=user, data=request.POST)
#
#         if edit_form.is_valid():
#             with atomic():
#                 edit_form.save()
#                 _clear_dependant_answers(tree, line_node)
#                 update_model_instance(preply, is_complete=not bool(tree.next_question_to_answer))
#     else:  # GET
#         edit_form = preply_forms.PollReplyFillForm(line_node=line_node, user=user)
#
#     return generic.inner_popup(
#         request, 'creme_core/generics/blockform/edit_popup.html',
#         {'form':  edit_form,
#          'title': ugettext('Answer edition'),
#          # todo: help_text (cleared answers + conditions etc...) ??
#          'submit_label': _('Save the modification'),
#         },
#         is_valid=edit_form.is_valid(),
#         reload=False,
#         delegate_reload=True,
#     )


# Class-based views  ----------------------------------------------------------

# TODO: use PollReply.multi_creation_label when all views are class based.
#       then fix PollReply.creation_label

class PollRepliesCreation(generic.EntityCreation):
    model = PollReply
    form_class = preply_forms.PollRepliesCreateForm
    submit_label = PollReply.multi_save_label


class _RelatedRepliesCreationBase(generic.AddingToEntity):
    model = PollReply
    form_class = preply_forms.PollRepliesCreateForm
    permissions = ('polls', _CREATION_PERM)
    title_format = _('New replies for «{}»')
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


class LinkingRepliesToPerson(generic.AddingToEntity):
    # model = PollReply
    template_name = 'creme_core/generics/blockform/link-popup.html'
    form_class = preply_forms.PersonAddRepliesForm
    title_format =  _('Existing replies for «{}»')
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
    title_format = _('Answer edition')
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
                raise Http404('This PollReplyLine id does not correspond to the PollReply instance') from e

            if not tree.conditions_are_met(line_node):
                raise Http404('This answered can not be edited (conditions are not met)')

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
        update_model_instance(self.object, is_complete=not bool(tree.next_question_to_answer))

        return response