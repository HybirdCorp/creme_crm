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

from json import loads as jsonloads

from django.forms.models import modelformset_factory
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import get_ct_or_404
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic import add_to_entity, list_view, inner_popup

from creme.products import get_product_model, get_service_model
#from creme.products.models import Product, Service

from .. import get_product_line_model, get_service_line_model
#from ..constants import PRODUCT_LINE_TYPE
from ..forms.line import (ProductLineMultipleAddForm, ServiceLineMultipleAddForm,
        LineEditForm, AddToCatalogForm)
from ..models import ProductLine, ServiceLine #Line


@login_required
@permission_required('billing')
def add_multiple_product_line(request, document_id):
    return add_to_entity(request, document_id, ProductLineMultipleAddForm,
                         _(u"Add one or more product to «%s»"), link_perm=True,
                         submit_label=_('Save the lines'),
                        )

@login_required
@permission_required('billing')
def add_multiple_service_line(request, document_id):
    return add_to_entity(request, document_id, ServiceLineMultipleAddForm,
                         _(u"Add one or more service to «%s»"), link_perm=True,
                         submit_label=_('Save the lines'),
                        )

#@login_required
#@permission_required('billing')
#def listview(request):
#    return list_view(request, Line, show_actions=False)

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
#    line = get_object_or_404(Line, pk=line_id)
#    related_item_class = Product if line.type == PRODUCT_LINE_TYPE else Service
    line = get_object_or_404(CremeEntity, pk=line_id).get_real_entity()

    #TODO: method in Line instead ?
    if isinstance(line, get_product_line_model()):
        related_item_class = get_product_model()
    elif isinstance(line, get_service_line_model()):
        related_item_class = get_service_model()
    else:
        raise Http404('This entity is not a billing line')

    request.user.has_perm_to_create_or_die(related_item_class)

    if request.method == 'POST':
        form = AddToCatalogForm(line=line, related_item_class=related_item_class,
                                user=request.user, data=request.POST,
                               )

        if form.is_valid():
            form.save()
    else:
        form = AddToCatalogForm(request.user, line, related_item_class=related_item_class)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form': form,
                        'title': _(u'Add this on the fly item to your catalog'),
                        'submit_label': _('Add to the catalog'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


LINE_FORMSET_PREFIX = {
#    ProductLine : 'product_line_formset',
#    ServiceLine : 'service_line_formset',
    get_product_line_model(): 'product_line_formset',
    get_service_line_model(): 'service_line_formset',
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
        qs = model_line.objects.filter(relations__object_entity=document.id) #TODO: relation type too...

        #TODO: move out the 'for' loop ?
        class _LineForm(LineEditForm):
            def __init__(self, *args, **kwargs):
                self.empty_permitted = False
                super(_LineForm, self).__init__(user=request.user, related_document=document, *args, **kwargs)

        # TODO can always delete ??? for example a quote accepted, can we really delete a line of this document ???
        lineformset_class = modelformset_factory(model_line, form=_LineForm, extra=0, can_delete=True)
        lineformset = lineformset_class(jsonloads(data),
                                        prefix=LINE_FORMSET_PREFIX[model_line],
                                        queryset=qs,
                                       )

        if lineformset.is_valid():
            formset_to_save.append(lineformset)
        else:
            # TODO better display errors ??
            errors = []

            for form in lineformset:
                if form.errors:
                    instance = form.instance
                    # We retrieve the line again because the field 'on_the_fly_item' may have been cleaned #TODO: avoid this query
#                    on_the_fly = Line.objects.get(pk=instance.pk).on_the_fly_item if instance.pk else \
                    on_the_fly = model_line.objects.get(pk=instance.pk).on_the_fly_item if instance.pk else \
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
                                content_type="text/plain", status=409,
                               )

    # save all formset now that we haven't detect any errors
    for formset in formset_to_save:
        formset.save()

    return HttpResponse("", content_type="text/javascript")
