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

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity

from billing.models import SalesOrder, Invoice, ProductLine , ServiceLine, TemplateBase
#from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED


class_map = {'sales_order': SalesOrder, 'invoice': Invoice}


@login_required
def convert(request, document_id):
    src = get_object_or_404(CremeEntity, pk=document_id).get_real_entity()

    #TODO: credentials ?????

    try:
        if isinstance(src, TemplateBase):
            dest = TemplateBase()
            new_ct = class_map[request.GET['type']]
            debug("Convert template to template !!!!!!")
            dest.build(src, ContentType.objects.get_for_model(new_ct))
            dest.name = _(u'%(src)s (converti en template de <%(dest)s>)') % {'src': src.name, 'dest': dest.ct.name}
            dest.save()
            # Generator of template src now works with converted template
            generator = src.get_generator()
            generator.template = dest
            generator.save()
        else:
            dest = class_map[request.GET['type']]()
            dest.build(src)
            dest.name = _(u'%(src)s (converti en %(dest)s)') % {'src': src.name, 'dest': dest._meta.verbose_name}
            dest.generate_number()
            dest.save()
    except KeyError:
        raise Http404


#    get_relation = NewCremeRelation.objects.get
#    #source = get_relation(subject_id=src.id, predicate=pred_issued).object_creme_entity
#    source = get_relation(subject_id=src.id, predicate=REL_SUB_BILL_ISSUED).object_creme_entity
#    #target = get_relation(subject_id=src.id, predicate=pred_received).object_creme_entity
#    target = get_relation(subject_id=src.id, predicate=REL_SUB_BILL_RECEIVED).object_creme_entity
#
#    #creme entity
#    dest.user = src.user
#
#    #billing base
#    dest.name             = _(u'%(src)s (converti en %(dest)s)') % {'src': src.name, 'dest': dest._meta.verbose_name}
#    dest.number           = src.number
#    dest.issuing_date     = src.issuing_date
#    dest.expiration_date  = src.expiration_date
#    dest.discount         = src.discount
#    dest.billing_address  = src.billing_address
#    dest.shipping_address = src.shipping_address
#    dest.comment          = src.comment
#    dest.total            = src.total
#
#    #special fields
#    dest.generate_number()
#    dest.status_id = 1 #default status' pk is '1'. see populate.py :)
#
#    dest.save()
#
#    #lines
#    clone_lines(src, dest, ProductLine)
#    clone_lines(src, dest, ServiceLine)
#
#    create_relation = NewCremeRelation.create_relation_with_object
#    create_relation(dest, REL_SUB_BILL_ISSUED,   source)
#    create_relation(dest, REL_SUB_BILL_RECEIVED, target)

    return HttpResponseRedirect(dest.get_absolute_url())
