# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _  # ugettext

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import get_ct_or_404
from creme.creme_core.views import generic, decorators

from ... import billing
from .. import constants
from ..forms import line as line_forms


ProductLine = billing.get_product_line_model()
ServiceLine = billing.get_service_line_model()


def abstract_add_multiple_product_line(request, document_id,
                                       form=line_forms.ProductLineMultipleAddForm,
                                       title=_(u'Add one or more product to «%s»'),
                                       submit_label=_(u'Save the lines'),
                                      ):
    return generic.add_to_entity(request, document_id, form, title,
                                 link_perm=True, submit_label=submit_label,
                                )


def abstract_add_multiple_service_line(request, document_id,
                                       form=line_forms.ServiceLineMultipleAddForm,
                                       title=_(u'Add one or more service to «%s»'),
                                       submit_label=_(u'Save the lines'),
                                      ):
    return generic.add_to_entity(request, document_id, form, title,
                                 link_perm=True, submit_label=submit_label,
                                )


@login_required
@permission_required('billing')
def add_multiple_product_line(request, document_id):
    return abstract_add_multiple_product_line(request, document_id)


@login_required
@permission_required('billing')
def add_multiple_service_line(request, document_id):
    return abstract_add_multiple_service_line(request, document_id)


@login_required
@permission_required('billing')
def listview_product_line(request):
    return generic.list_view(request, ProductLine, show_actions=False)


@login_required
@permission_required('billing')
def listview_service_line(request):
    return generic.list_view(request, ServiceLine, show_actions=False)


@login_required
@permission_required('billing')
def add_to_catalog(request, line_id):
    line = get_object_or_404(CremeEntity, pk=line_id).get_real_entity()

    try:
        related_item_class = line.related_item_class()
    except AttributeError:
        raise Http404('This entity is not a billing line')  # ConflictError ??

    user = request.user
    user.has_perm_to_create_or_die(related_item_class)

    if request.method == 'POST':
        form = line_forms.AddToCatalogForm(user=user, line=line, related_item_class=related_item_class,
                                           data=request.POST,
                                          )

        if form.is_valid():
            form.save()
    else:
        form = line_forms.AddToCatalogForm(user=user, line=line, related_item_class=related_item_class)

    return generic.inner_popup(request, 'creme_core/generics/blockform/add_popup.html',
                               {'form': form,
                                'title': _(u'Add this on the fly item to your catalog'),
                                'submit_label': _(u'Add to the catalog'),
                               },
                               is_valid=form.is_valid(),
                               reload=False,
                               delegate_reload=True,
                              )


LINE_FORMSET_PREFIX = {
    ProductLine: 'product_line_formset',
    ServiceLine: 'service_line_formset',
}


@decorators.POST_only
@login_required
@permission_required('billing')
def multi_save_lines(request, document_id):
    document = get_object_or_404(CremeEntity, pk=document_id).get_real_entity()

    user = request.user
    user.has_perm_to_change_or_die(document)

    formset_to_save = []
    errors = []

    class _LineForm(line_forms.LineEditForm):
        def __init__(self, *args, **kwargs):
            self.empty_permitted = False
            super(_LineForm, self).__init__(user=user, related_document=document, *args, **kwargs)

    # Only modified formsets land here
    for line_ct_id, data in request.POST.items():
        line_model = get_ct_or_404(line_ct_id).model_class()

        prefix = LINE_FORMSET_PREFIX.get(line_model)
        if prefix is None:
            raise ConflictError('Invalid model (not a line ?!)')

        qs = line_model.objects.filter(relations__object_entity=document.id,
                                       relations__type=constants.REL_OBJ_HAS_LINE,
                                      )

        lineformset_class = modelformset_factory(line_model, form=_LineForm, extra=0, can_delete=True)
        lineformset = lineformset_class(jsonloads(data), prefix=prefix, queryset=qs)

        if lineformset.is_valid():
            formset_to_save.append(lineformset)
        else:
            get_field = line_model._meta.get_field

            for form in lineformset:
                if form.errors:
                    instance = form.instance
                    # # We retrieve the line again because the field 'on_the_fly_item' may have been cleaned
                    # # todo: avoid this query
                    # on_the_fly = line_model.objects.get(pk=instance.pk).on_the_fly_item if instance.pk else \
                    #              ugettext(u'on the fly [creation]')
                    #
                    # errors.append(u'%s <b>%s</b> : <br>%s' % (
                    #                 ugettext(u'Errors on the line'),
                    #                 on_the_fly if on_the_fly else instance.related_item,
                    #                 u''.join(u"==> %s : %s" % (ugettext(u'General'), msg) if field == '__all__' else
                    #                          u'==> %s "<i>%s</i>" : %s' % (
                    #                                 ugettext(u'Specific on the field'),  # todo: format string instead
                    #                                 line_model._meta.get_field(field).verbose_name,
                    #                                 msg,
                    #                             )
                    #                             for field, msg in form.errors.items()
                    #                         )
                    #                 )
                    #              )
                    item = None

                    if instance.pk:
                        # We retrieve the line again because the field 'on_the_fly_item' may have been cleaned
                        # TODO: avoid this query (API for field modifications -- see HistoryLine)
                        item = line_model.objects.get(pk=instance.pk).on_the_fly_item or instance.related_item

                    errors.append({'item':     item,
                                   'instance': instance,
                                   'errors':   [(None if field == '__all__' else get_field(field),
                                                 msg,
                                                ) for field, msg in form.errors.items()
                                               ],
                                  }
                                 )

    if errors:
        # return HttpResponse(u'<center>--------------------</center><br>'.join(errors),
        #                     content_type='text/plain', status=409,
        #                    )
        return render(request, 'billing/frags/lines-errors.html', context={'errors': errors}, status=409)

    # Save all formset now that we haven't detect any errors
    for formset in formset_to_save:
        formset.save()

    return HttpResponse(content_type='text/javascript')
