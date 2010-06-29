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

from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.constants import DROIT_MODULE_EST_ADMIN
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.views.generic import add_entity

from persons.models.other_models import MailSignature

from creme_config.forms.mail_signature import MailSignatureForm


portal_url = '/creme_config/mailsignature/portal/'

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request):
    """
        @Permissions : Admin to creme_config app
    """
    return add_entity(request, MailSignatureForm, portal_url, 'creme_core/generics/form/add.html')

@login_required
@get_view_or_die('creme_config')
def portal(request):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    request_get = request.REQUEST.get
    order = request_get('order', 'sign_name')
    way   = request_get('way',"")

#    order = way+order #not += !!

    mail_signatures = MailSignature.objects.all().order_by(way + order)

    paginator = Paginator(mail_signatures, 25)
    try:
        page = int(request_get('page', '1'))
    except ValueError:
        page = 1

    try:
        pagination = paginator.page(page)
    except (EmptyPage, InvalidPage):
        pagination = paginator.page(paginator.num_pages)

    paths = {
                'add':      '/creme_config/mailsignature/add/',
                'edit':     '/creme_config/mailsignature/edit/%s',
                'delete':   '/creme_config/mailsignature/delete/%s',
                'view':     '/creme_config/mailsignature/%s',
             }

    return render_to_response('creme_config/generics/portal_paginated.html',
                             {
                                'pagination':   pagination,
                                'model':        MailSignature,
                                'way':          way,
                                'paths':        paths,
                                #'fields':MailSignature._meta.fields + MailSignature._meta.many_to_many,
                                'order':        order,
                             },
                             context_instance=RequestContext(request ) )

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request, mailsignature_id):
    """
        @Permissions : Admin to creme_config app
    """
    mail_signature =  get_object_or_404(MailSignature, pk=mailsignature_id)
    mail_signature.delete()
    return HttpResponseRedirect(portal_url)

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit(request, mailsignature_id):
    """
        @Permissions : Admin to creme_config app
    """
    mail_signature = get_object_or_404(MailSignature, pk=mailsignature_id)

    if request.POST :
        mail_signature_form = MailSignatureForm(request.POST, instance=mail_signature)

        if mail_signature_form.is_valid():
            mail_signature_form.save()
            return HttpResponseRedirect(portal_url)
    else:
        mail_signature_form = MailSignatureForm(instance=mail_signature)

    return render_to_response('creme_core/generics/form/edit.html',
                              {'form': mail_signature_form},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config')
def view(request, mailsignature_id):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    mail_signature = get_object_or_404(MailSignature, pk=mailsignature_id)

    return render_to_response('creme_config/roles/view_role.html',
                              {
                                'object':   mail_signature,
                                'path':     portal_url,
                              },
                              context_instance=RequestContext(request ) )
