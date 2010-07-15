# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from logging import debug

from django.utils.translation import ugettext_lazy as _
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.context import RequestContext
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from creme_core.entities_access.functions_for_permissions import delete_object_or_die
from creme_core.entities_access.permissions import user_has_delete_permission_for_an_object
from django.shortcuts import render_to_response
from creme_core.models.entity import CremeEntity

#TODO: ajouter le test sur l'app facon @get_view_or_die('persons') (ticket 196)

@login_required
def delete_entities_js(request, entities_ids):
    """
        @Permissions : Delete on object (No warning if user hasn't permissions just pass)
        TODO: use 'CremeEntity.get_real_entity()'
    """
    debug('delete_entities_js -> ids: %s ', entities_ids)

    return_str = ""
    get = CremeEntity.objects.get

    for id in entities_ids.split(','):
        debug('delete id=%s', id)

        if not id.isdigit():
            debug('not digit ?!')
            continue

        try:
            model_klass = get(pk=id).entity_type.model_class()
        except CremeEntity.DoesNotExist:
            debug("entity doesn't exist")
            continue #no need to return an error, the element won't be in the list after the refreshing

        f = model_klass.objects.get(pk=id) #can't fail (pk in CremeEntity.objects)

        if f.is_deleted:
            debug("already marked is_deleted")
            return_str += '%s : already marked is_deleted,' % f
            continue

        if not user_has_delete_permission_for_an_object(request, f):
            return_str += '%s : <b>Permission refusée</b>,' % f
            continue

        try:
            f.delete()
        except Exception, e: #TODO: find the exact Exception type
            debug('Exception: %s', e)
            try:
                debug('Force the suppression in case no relation matches')
                f.delete()  #TODO: is a second delete() useful ???
            except:
                debug('Forced suppression failed')
                try:
                    debug('Set is_deleted=True')
                    f.is_deleted = True
                    f.save()
                except:
                    debug('Setting is_deleted failed')
                    return_str += '%s : can not be marked as is_deleted,' % f

    return_status = 200 if not return_str else 400
    return_str    = "[%s]" % return_str
    debug('return string: %s', return_str)

    return HttpResponse(return_str, mimetype="text/javascript", status=return_status)


@login_required
def delete_entity(request, object_id, callback_url=None):
    """
        @Permissions : Delete on current object
    """
    entity = get_object_or_404(CremeEntity, pk=object_id).get_real_entity()

    die_status = delete_object_or_die(request, entity)
    if die_status:
        return die_status

    if callback_url is None:
        callback_url = entity.get_lv_absolute_url()

    if entity.can_be_deleted():
        entity.delete()
        return HttpResponseRedirect(callback_url)
    else:
        return render_to_response("creme_core/forbidden.html", {
                                    'error_message' : _(u'%s ne peut être effacé à cause des ses dépendances.' % entity)
                                 }, context_instance=RequestContext(request))
