# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2013  Hybird
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

from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.html import escape
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.models import CremeEntity
from creme.creme_core.views.generic import (add_model_with_popup, edit_entity,
    inner_popup, view_entity, list_view, add_to_entity) #add_entity
from creme.creme_core.utils import get_from_POST_or_404, update_model_instance
from creme.creme_core.utils.media import creme_media_themed_url as media_url

from creme.persons.models import Contact, Organisation

from ..core import MultiEnumPollLineType
from ..models import PollForm, PollReply, PollReplyLine, PollCampaign
from ..forms.poll_reply import (PollRepliesCreateForm, PollReplyEditForm,
                                PollReplyFillForm, PersonAddRepliesForm)
from ..utils import ReplySectionTree, NodeStyle


logger = logging.getLogger(__name__)

#TODO: change url (reply->replies or add_several ??)
@login_required
@permission_required('polls')
@permission_required('polls.add_pollreply')
def add(request):
    #return add_entity(request, PollRepliesCreateForm)

    if request.method == 'POST':
        reply_form = PollRepliesCreateForm(user=request.user, data=request.POST)

        if reply_form.is_valid():
            reply_form.save()

            return redirect(reply_form.instance)
    else: #GET
        reply_form = PollRepliesCreateForm(user=request.user)

    return render(request, 'creme_core/generics/blockform/add.html',
                  {'form':  reply_form,
                   'title': PollReply.creation_label,
                  }
                 )

@login_required
@permission_required('polls')
@permission_required('polls.add_pollreply')
def add_from_pform(request, pform_id): #TODO: factorise ? (see documents.views)
    pform = get_object_or_404(PollForm, pk=pform_id)
    user = request.user

    user.has_perm_to_view_or_die(pform)
    user.has_perm_to_link_or_die(pform)

    return add_model_with_popup(request, PollRepliesCreateForm,
                                _(u'New replies for <%s>') % pform,
                                initial={'pform': pform},
                               )

@login_required
@permission_required('polls')
@permission_required('polls.add_pollreply')
def add_from_campaign(request, campaign_id): #TODO: factorise ?
    campaign = get_object_or_404(PollCampaign, pk=campaign_id)
    user = request.user

    user.has_perm_to_view_or_die(campaign)
    user.has_perm_to_link_or_die(campaign)

    return add_model_with_popup(request, PollRepliesCreateForm,
                                _(u'New replies for <%s>') % campaign,
                                initial={'campaign': campaign},
                               )

@login_required
@permission_required('polls')
@permission_required('polls.add_pollreply')
def add_from_person(request, person_id):
    person = get_object_or_404(CremeEntity, pk=person_id)
    user = request.user

    user.has_perm_to_view_or_die(person)
    user.has_perm_to_link_or_die(person)

    person = person.get_real_entity()

    if not isinstance(person, (Contact, Organisation)):
        raise Http404('You can only create from Contacts & Organisations')

    return add_model_with_popup(request, PollRepliesCreateForm,
                                _(u'New replies for <%s>') % person,
                                initial={'persons': [person]},
                               )

@login_required
@permission_required('polls')
def edit(request, preply_id):
    return edit_entity(request, preply_id, PollReply, PollReplyEditForm)

@login_required
@permission_required('polls')
def detailview(request, preply_id):
    return view_entity(request, preply_id, PollReply,
                       '/polls/poll_reply', 'polls/view_pollreply.html'
                      )

@login_required
@permission_required('polls')
def listview(request):
    return list_view(request, PollReply, extra_dict={'add_url': '/polls/poll_reply/add'})

@login_required
@permission_required('polls')
@permission_required('persons')
def link_to_person(request, person_id):
    return add_to_entity(request, person_id, PersonAddRepliesForm,
                         _('Existing replies for <%s>'), link_perm=True,
                        )

#TODO: do this job in template instead ??
def _format_previous_answered_question(preply_id, line, style):
    if not line.applicable:
        answer = _('N/A')
    elif isinstance(line.poll_line_type, MultiEnumPollLineType): #TODO: isinstance(answer, list) ??
        answer = u", ".join(escape(choice) for choice in line.answer)
    else:
        answer = escape(line.answer)

    number = style.number(line)
    return mark_safe(u'<b>%(title)s</b><br>'
                      '%(label)s : %(number)s %(question)s<br>'
                      '%(answer_str)s : %(answer)s <a class="add" href="/polls/poll_reply/%(mreply_id)s/line/%(line_id)s/edit_wizard"><img src="%(img_src)s" alt="Edit" title="Edit"></a>'
                        % {'title':         _(u"Reminder of the previous answered question :"),
                           'label':         _('Question'),
                           'number':        '%s -' % number if number != 'None' else '',
                           'question':      escape(line.question),
                           'answer_str':    _('Answer'),
                           'answer':        answer,
                           'mreply_id':     preply_id,
                           'line_id':       line.id,
                           'img_src':       media_url('images/edit_16.png'),
                          }
                    )

@login_required
@permission_required('polls')
def edit_line_wizard(request, preply_id, line_id):
    preply = get_object_or_404(PollReply, pk=preply_id)
    user = request.user

    user.has_perm_to_change_or_die(preply)

    tree = ReplySectionTree(preply)

    try:
        line_node = tree.find_line(int(line_id))
    except KeyError:
        msg = 'PollReplyLine with this id %s does not exist for PollReply %s' % (
                    line_id,
                    preply
                )
        logger.error(msg)
        raise Http404(msg)

    previous_answer = None

    if request.method == 'POST':
        form = PollReplyFillForm(line_node=line_node, user=user, data=request.POST)

        if form.is_valid():
            with transaction.commit_on_success():
                form.save()

                #optimize 'next_question_to_answer' & cie
                PollReplyLine.populate_conditions([node for node in tree if not node.is_section])

                _clear_dependant_answers(tree, line_node)

                if not tree.next_question_to_answer:
                    is_complete = True
                    url = preply.get_absolute_url()
                else:
                    is_complete = False
                    url = '/polls/poll_reply/fill/%s' % preply_id

                update_model_instance(preply, is_complete=is_complete)

            return HttpResponseRedirect(url)
    else:
        previous = tree.get_previous_answered_question(line_node)

        if previous:
            previous_answer = _format_previous_answered_question(preply_id, previous, NodeStyle())

        form = PollReplyFillForm(line_node=line_node, user=user)

    return render(request, 'creme_core/generics/blockform/edit.html',
                  {'title' :       _(u'Answers of the form : %s') % preply,
                   'form':         form,
                   'help_message': previous_answer,
                  }
                 )

@login_required
@permission_required('polls')
def fill(request, preply_id):
    preply = get_object_or_404(PollReply, pk=preply_id)
    user = request.user

    user.has_perm_to_change_or_die(preply)

    if preply.is_complete:
        raise Http404(_(u'All questions have been answered.'))

    tree = ReplySectionTree(preply)
    line_node = tree.next_question_to_answer

    if line_node is None:
        msg = 'No empty PollReplyLine found in PollReply %s' % preply
        logger.error(msg)
        raise Http404(msg)

    previous_answer = None

    if request.method == 'POST':
        form = PollReplyFillForm(line_node=line_node, user=user, data=request.POST)

        if form.is_valid():
            with transaction.commit_on_success():
                form.save()

                next_line = tree.next_question_to_answer

                if not next_line:
                    preply.is_complete = True
                    preply.save()

                    return redirect(preply)

            previous_answer = _format_previous_answered_question(preply_id, line_node, NodeStyle())
            form = PollReplyFillForm(line_node=next_line, user=user)
    else:
        previous = tree.get_previous_answered_question(line_node)
        if previous:
            previous_answer = _format_previous_answered_question(preply_id, previous, NodeStyle())

        form = PollReplyFillForm(line_node=line_node, user=user)

    return render(request, 'creme_core/generics/blockform/edit.html',
                  {'title':        _(u'Answers of the form : %s') % preply,
                   'form':         form,
                   'help_message': previous_answer,
                  }
                 )

@login_required
@permission_required('polls')
def clean(request):
    preply = get_object_or_404(PollReply, pk=get_from_POST_or_404(request.POST, 'id'))

    request.user.has_perm_to_change_or_die(preply)

    with transaction.commit_on_success():
        preply.lines.update(raw_answer=None, applicable=True) #avoids statistics artefacts
        update_model_instance(preply, is_complete=False)

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return redirect(preply)

def _clear_dependant_answers(tree, line_node):
    find_line = tree.find_line

    for condition in line_node.get_reversed_conditions():
        dep_line_node = find_line(condition.line_id)

        update_model_instance(dep_line_node, raw_answer=None)
        _clear_dependant_answers(tree, dep_line_node)

#TODO: if not line's type.editable ??
@login_required
@permission_required('polls')
def edit_line(request, preply_id, line_id):
    #return edit_related_to_entity(request, line_id, PollReplyLine,
                                  #PollReplyLineEditForm, _(u'Answer for <%s>')
                                 #)

    #NB: we do not use the generic view edit_related_to_entity(), because it would
    #    oblige us to transform PollReplyLine in a True auxiliary model
    #    (get_related_entity() method), so the delete view could be called without
    #    our consent
    preply = get_object_or_404(PollReply, pk=preply_id)
    user = request.user

    user.has_perm_to_change_or_die(preply)

    tree = ReplySectionTree(preply)

    try:
        line_node = tree.find_line(int(line_id))
    except KeyError:
        raise Http404('This PollReplyLine id does not correspond to the PollReply instance')

    if not tree.conditions_are_met(line_node):
        raise Http404('This answered can not be edited (conditions are not met)')

    if request.method == 'POST':
        edit_form = PollReplyFillForm(line_node=line_node, user=user, data=request.POST)

        if edit_form.is_valid():
            with transaction.commit_on_success():
                edit_form.save()
                _clear_dependant_answers(tree, line_node)
                update_model_instance(preply, is_complete=not bool(tree.next_question_to_answer))
    else: #GET
        edit_form = PollReplyFillForm(line_node=line_node, user=user)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':  edit_form,
                        'title': _(u'Answer edition'),
                        #TODO: help_text (cleared answers + conditions etc...) ??
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )
