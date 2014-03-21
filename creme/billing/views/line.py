# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.forms.models import modelformset_factory
from django.http import HttpResponse #Http404
from django.shortcuts import get_object_or_404
from django.utils.simplejson import loads as jsonloads
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import get_ct_or_404 #jsonify
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic import add_to_entity, list_view, inner_popup

from creme.products.models import Product, Service

from ..constants import PRODUCT_LINE_TYPE
from ..models import Line, ProductLine, ServiceLine
from ..forms.line import ProductLineMultipleAddForm, ServiceLineMultipleAddForm, LineEditForm, AddToCatalogForm


# commented on 23/07/2013 because adding a line on the fly is managed by client side js now
# @login_required
# @permission_required('billing')
# def _add_line(request, form_class, document_id):
#     return add_to_entity(request, document_id, form_class, _(u"New line in the document <%s>"))

@login_required
@permission_required('billing')
def add_multiple_product_line(request, document_id):
    return add_to_entity(request, document_id, ProductLineMultipleAddForm,
                         _(u"Add one or more product to <%s>"), link_perm=True,
                        )

# def add_product_line_on_the_fly(request, document_id):
#     return _add_line(request, ProductLineOnTheFlyForm, document_id)

@login_required
@permission_required('billing')
def add_multiple_service_line(request, document_id):
    return add_to_entity(request, document_id, ServiceLineMultipleAddForm,
                         _(u"Add one or more service to <%s>"), link_perm=True,
                        )

# def add_service_line_on_the_fly(request, document_id):
#     return _add_line(request, ServiceLineOnTheFlyForm, document_id)

# commented on 23/07/2013 because this type of edit no longer exists for lines
# @login_required
# @permission_required('billing')
# def edit_line(request, line_id):
#     return edit_model_with_popup(request, {'pk': line_id},
#                                  Line, LineEditForm,
#                                 ) #todo check line or billing document credentials ??
#
# @jsonify
# @login_required
# @permission_required('billing')
# def edit_inner_line(request, line_id):
#     if request.method != 'POST':
#         raise Http404('This view uses POST method')
#
#     line     = get_object_or_404(Line, pk=line_id)
#     document = line.related_document
#
#     request.user.has_perm_to_change_or_die(document)
#
#     request_POST = request.POST
#     request_POST_get = request_POST.get
#
#     # todo try/catch in case POST values didnt match Decimal, int ?
#     new_unit_price      = Decimal(request_POST_get('unit_price')) if 'unit_price' in request_POST else None
#     new_quantity        = Decimal(request_POST_get('quantity'))   if 'quantity' in request_POST else None
#     new_vat             = request_POST_get('vat')                 if 'vat' in request_POST else None
#     new_discount_value  = Decimal(request_POST_get('discount'))   if 'discount' in request_POST else None
#     new_discount_unit   = int(request_POST_get('discount_unit'))  if 'discount_unit' in request_POST else None
#     new_unit            = request_POST_get('unit')                if 'unit' in request_POST else None
#     new_on_the_fly_item = request_POST_get('on_the_fly')          if 'on_the_fly' in request_POST else None
#
#     if 'total_discount' in request_POST:
#         new_discount_type = request_POST_get('total_discount') == '1'
#     else:
#         new_discount_type = None
#
#     if new_on_the_fly_item:
#         line.on_the_fly_item = new_on_the_fly_item
#     if new_unit_price is not None:
#         line.unit_price = new_unit_price
#     if new_quantity is not None:
#         line.quantity = new_quantity
#     if new_discount_value is not None:
#         line.discount = new_discount_value
#     if new_discount_unit is not None:
#         line.discount_unit = new_discount_unit
#     if new_discount_type is not None:
#         line.total_discount = new_discount_type
#     if new_vat is not None:
#         line.vat_value_id = new_vat
#     if new_unit is not None:
#         line.unit = new_unit
#
#     line.full_clean()
#     line.save()

@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, Line, show_actions=False)

@login_required
@permission_required('billing')
def listview_product_line(request):
    return list_view(request, ProductLine, show_actions=False)

@login_required
@permission_required('billing')
def listview_service_line(request):
    return list_view(request, ServiceLine, show_actions=False)

@login_required
@permission_required('billing')
def add_to_catalog(request, line_id):
    line = get_object_or_404(Line, pk=line_id)
    related_item_class = Product if line.type == PRODUCT_LINE_TYPE else Service

    request.user.has_perm_to_create_or_die(related_item_class)

    if request.method == 'POST':
        form = AddToCatalogForm(line=line, related_item_class=related_item_class, user=request.user, data=request.POST)

        if form.is_valid():
            form.save()
    else:
        form = AddToCatalogForm(request.user, line, related_item_class=related_item_class)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':   form,
                        'title': _(u'Add this on the fly item to your catalog'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


LINE_FORMSET_PREFIX = {
    ProductLine : 'product_line_formset',
    ServiceLine : 'service_line_formset',
}

@POST_only
@login_required
@permission_required('billing')
def multi_save_lines(request, document_id):
    document = CremeEntity.objects.get(pk=document_id).get_real_entity()

    request.user.has_perm_to_change_or_die(document)

    formset_to_save = []
    # only modified formsets land here
    for line_ct_id, data in request.POST.items():
        model_line = get_ct_or_404(line_ct_id).model_class()
        qs = model_line.objects.filter(relations__object_entity=document.id)

        class _LineForm(LineEditForm):
            def __init__(self, *args, **kwargs):
                self.empty_permitted = False
                super(_LineForm, self).__init__(user=request.user, related_document=document, *args, **kwargs)

        # TODO can always delete ??? for example a quote accepted, can we really delete a line of this document ???
        lineformset_class = modelformset_factory(model_line, form=_LineForm, extra=0, can_delete=True)
        lineformset = lineformset_class(jsonloads(data),
                                        prefix=LINE_FORMSET_PREFIX[model_line],
                                        queryset=qs)

        if lineformset.is_valid():
            formset_to_save.append(lineformset)
        else:
            # TODO better display errors ??
            errors = []

            for form in lineformset:
                if form.errors:
                    instance = form.instance
                    #we retrieve the line again because the field 'on_the_fly_item' may have been cleaned #TODO: avoid this query
                    on_the_fly = Line.objects.get(pk=instance.pk).on_the_fly_item if instance.pk else \
                                 _(u"on the fly [creation]")

                    errors.append(u"%s <b>%s</b> : <br>%s" % (
                                    _(u"Errors on the line"),
                                    on_the_fly if on_the_fly else instance.related_item,
                                    u''.join(u"==> %s : %s" % (_(u"General"), msg) if field == "__all__" else
                                             u'==> %s "<i>%s</i>" : %s' % (
                                                    _(u"Specific on the field"), #TODO: format string instead
                                                    model_line._meta.get_field(field).verbose_name,
                                                    msg,
                                                )
                                                for field, msg in form.errors.items()
                                            )
                                    )
                                 )

            return HttpResponse(u'<center>--------------------</center><br>'.join(errors),
                                mimetype="text/plain", status=409,
                               )

    # save all formset now that we haven't detect any errors
    for formset in formset_to_save:
        formset.save()

    return HttpResponse("", mimetype="text/javascript")
