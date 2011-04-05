# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from collections import defaultdict
from logging import debug

from django.utils.translation import ugettext as _
from django.utils.encoding import smart_unicode
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.context import RequestContext
from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.decorators import login_required

from creme_core.models import CremeEntity
from creme_core.utils import get_from_POST_or_404, get_ct_or_404


#TODO: move all functions to entity.py and delete this file ??


@login_required
def delete_entities(request):
    """Delete several CremeEntity, with a Ajax call (POSt method)."""
    try:
        entity_ids = [int(e_id) for e_id in get_from_POST_or_404(request.POST, 'ids').split(',') if e_id]
    except ValueError, e:
        return HttpResponse("Bad POST argument", mimetype="text/javascript", status=400)

    if not entity_ids:
        return HttpResponse(_(u"No selected entities"), mimetype="text/javascript", status=400)

    debug('delete_entities() -> ids: %s ', entity_ids)

    user     = request.user
    entities = list(CremeEntity.objects.filter(pk__in=entity_ids))
    errors   = defaultdict(list)

    len_diff = len(entity_ids) - len(entities)
    if len_diff:
        errors[404].append(_(u"%s entities doesn't exist / doesn't exist any more") % len_diff)

    CremeEntity.populate_credentials(entities, user)
    CremeEntity.populate_real_entities(entities)

    for entity in entities:
        if not entity.can_delete(user):
            errors[403].append(_(u'%s : <b>Permission denied</b>,') % entity.allowed_unicode(user))
            continue

        entity = entity.get_real_entity()

        if entity.get_delete_absolute_url() != CremeEntity.get_delete_absolute_url(entity):
            errors[404].append(_('%s does not use the generic deletion view.') % entity.allowed_unicode(user))
            continue

        try:
            entity.delete()
        except CremeEntity.CanNotBeDeleted, e:
            errors[400].append(_(u'"%s" can not be deleted because of its dependencies.') % entity.allowed_unicode(user))

    if not errors:
        status = 200
        message = _(u"Operation successfully completed")
    else:
        status = min(errors.iterkeys())
        message = ",".join(msg for error_messages in errors.itervalues() for msg in error_messages)

    return HttpResponse(message, mimetype="text/javascript", status=status)

@login_required
def delete_entity(request, entity_id, callback_url=None):
    if request.method != 'POST':
        raise Http404('Use POST method for this view')

    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    if entity.get_delete_absolute_url() != CremeEntity.get_delete_absolute_url(entity):
        raise Http404(_(u'This model does not use the generic deletion view.'))

    entity.can_delete_or_die(request.user)

    if callback_url is None: #TODO: useful ??
        callback_url = entity.get_lv_absolute_url()

    try:
        entity.delete()
    except CremeEntity.CanNotBeDeleted, e:
        if request.is_ajax():
            return HttpResponse(smart_unicode(e), mimetype="text/javascript", status=400)

        return render_to_response("creme_core/forbidden.html",
                                  {'error_message': unicode(e)},
                                  context_instance=RequestContext(request)
                                 )

    return HttpResponseRedirect(callback_url)

@login_required
def delete_related_to_entity(request, ct_id):
    """Delete a model related to a CremeEntity.
    @param request Request with POST method ; POST data should contain an 'id'(=pk) value.
    @param model A django model class that implements the method get_related_entity().
    """
    model = get_ct_or_404(ct_id).model_class()
    auxiliary = get_object_or_404(model, pk=get_from_POST_or_404(request.POST, 'id'))
    entity = auxiliary.get_related_entity()

    entity.can_change_or_die(request.user)
    auxiliary.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(entity.get_absolute_url())
