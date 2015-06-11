# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

#from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from django.http import HttpResponse #Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import get_from_POST_or_404

from .. import get_invoice_model, get_sales_order_model, get_quote_model, get_credit_note_model # get_template_base_model
#from creme.billing.models import SalesOrder, Invoice, TemplateBase


CreditNote = get_credit_note_model()
Quote      = get_quote_model()
Invoice    = get_invoice_model()
SalesOrder = get_sales_order_model()
_CLASS_MAP = {'credit_note': CreditNote, #NB: unused
              'invoice':     Invoice,
              'quote':       Quote,
              'sales_order': SalesOrder,
             }
CONVERT_MATRIX = {
    CreditNote: {'invoice'},
    Invoice:    {'quote', 'sales_order'},
    Quote:      {'sales_order', 'invoice'},
    SalesOrder: {'invoice'},
}

@login_required
@permission_required('billing')
def convert(request, document_id):
    src = get_object_or_404(CremeEntity, pk=document_id).get_real_entity()
    user = request.user

    allowed_dests = CONVERT_MATRIX.get(src.__class__)
    if not allowed_dests:
        raise ConflictError('This entity cannot be convert to a(nother) billing document')

    user.has_perm_to_view_or_die(src)

    dest_class_id = get_from_POST_or_404(request.POST, 'type')
    if not dest_class_id in allowed_dests:
        raise ConflictError('Invalid destination type '
                            '[allowed destinations for this type: %s]' % allowed_dests
                           )

#    dest_class = _CLASS_MAP.get(dest_class_id)
#    if not dest_class:
#        raise Http404('Error: "type" argument must be in : %s' % ', '.join(_CLASS_MAP.iterkeys()))
    dest_class = _CLASS_MAP[dest_class_id]

    user.has_perm_to_create_or_die(dest_class)

#    TemplateBase = get_template_base_model()

    with atomic():
#        if isinstance(src, TemplateBase):
#            dest = TemplateBase()
#            dest.build(src, ContentType.objects.get_for_model(dest_class))
#            dest.name = _(u'%(src)s (converted into template of <%(dest)s>)') % {
#                                'src':  src.name,
#                                'dest': dest_class._meta.verbose_name,
#                            }
#            dest.save()
#            # Generator of template src now works with converted template
#            generator = src.get_generator()
#            generator.template = dest #TODO: old Template is 'lost' ? (no deleted but no linkable to a generator anymore)
#            generator.save()
#        else:
#            dest = dest_class()
#            dest.build(src)
#            dest.name = _(u'%(src)s (converted into  %(dest)s)') % {
#                                'src':  src.name,
#                                'dest': dest._meta.verbose_name,
#                            }
#            dest.generate_number()
#            dest.save()
        dest = dest_class()
        dest.build(src)
        dest.name = _(u'%(src)s (converted into  %(dest)s)') % {
                            'src':  src.name,
                            'dest': dest._meta.verbose_name,
                        }
        dest.generate_number()
        dest.save()

    return HttpResponse("", content_type="text/javascript")
    #return redirect(dest)
