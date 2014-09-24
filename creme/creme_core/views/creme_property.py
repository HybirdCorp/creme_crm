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

from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_list_or_404, get_object_or_404, render, redirect
from django.template import RequestContext
from django.utils.translation import ugettext as _, ungettext

#TODO: move them to creme_core ?
from creme.creme_config.forms.creme_property_type import CremePropertyTypeAddForm, CremePropertyTypeEditForm

from ..auth.decorators import login_required, permission_required
from ..forms.creme_property import AddPropertiesForm, AddPropertiesBulkForm
from ..gui.block import QuerysetBlock
from ..models import CremeEntity, CremePropertyType
from ..utils import creme_entity_content_types, get_ct_or_404, get_from_POST_or_404, jsonify
from .generic import inner_popup, add_to_entity as generic_add_to_entity

#TODO: Factorise with views in creme_config

@login_required
def add_properties_bulk(request, ct_id):#TODO: Factorise with add_relations_bulk and bulk_update?
    user     = request.user
    model    = get_ct_or_404(ct_id).model_class()
    entities = get_list_or_404(model, pk__in=request.REQUEST.getlist('ids'))

    CremeEntity.populate_real_entities(entities)

    filtered = {True: [], False: []}
    has_perm = user.has_perm_to_change
    for entity in entities:
        filtered[has_perm(entity)].append(entity)

    if request.method == 'POST':
        form = AddPropertiesBulkForm(model=model, user=user,
                                     entities=filtered[True],
                                     forbidden_entities=filtered[False],
                                     data=request.POST,
                                    )

        if form.is_valid():
            form.save()
    else:
        form = AddPropertiesBulkForm(model=model, user=user,
                                     entities=filtered[True],
                                     forbidden_entities=filtered[False],
                                    )

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':  form,
                        'title': _(u'Multiple adding of properties'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
def add_to_entity(request, entity_id):
    return generic_add_to_entity(request, entity_id, AddPropertiesForm, _('New properties for <%s>'))

@login_required
@permission_required('creme_core.can_admin')
def add_type(request):
    #NB Does not work because it is not a ModelForm
    #return add_entity(request, CremePropertyTypeAddForm)

    if request.method == 'POST':
        form = CremePropertyTypeAddForm(user=request.user, data=request.POST)

        if form.is_valid():
            ptype = form.save()

            return redirect(ptype)

        cancel_url = POST.get('cancel_url')
    else: #GET
        form = CremePropertyTypeAddForm(user=request.user)
        cancel_url = request.META.get('HTTP_REFERER')

    return render(request, 'creme_core/generics/blockform/add.html',
                  {'form':         form,
                   'title':        CremePropertyType.creation_label,
                   'submit_label': _('Save the type of property'),
                   'cancel_url':   cancel_url,
                  }
                 )

@login_required
@permission_required('creme_core.can_admin')
def edit_type(request, ptype_id):
    ptype = get_object_or_404(CremePropertyType, id=ptype_id)

    if not ptype.is_custom:
        raise Http404("Can't edit a standard PropertyType")

    if request.method == 'POST':
        form = CremePropertyTypeEditForm(ptype, user=request.user, data=request.POST)

        if form.is_valid():
            form.save()

            return redirect(ptype)

        cancel_url = POST.get('cancel_url')
    else: #GET
        form = CremePropertyTypeEditForm(ptype, user=request.user)
        cancel_url = request.META.get('HTTP_REFERER')

    return render(request, 'creme_core/generics/blockform/edit.html',
                  {'form': form,
                   'object': ptype,
                   'submit_label': _('Save the modifications'),
                   'cancel_url': cancel_url,
                  }
                 )

@login_required
def delete_from_type(request):
    POST = request.POST
    ptype = get_object_or_404(CremePropertyType, id=get_from_POST_or_404(POST, 'ptype_id'))
    entity = get_object_or_404(CremeEntity, id=get_from_POST_or_404(POST, 'entity_id'))

    request.user.has_perm_to_change_or_die(entity)

    ptype.cremeproperty_set.filter(creme_entity=entity).delete()

    if request.is_ajax():
        return HttpResponse(mimetype='text/javascript')

    return redirect(ptype)

@login_required
@permission_required('creme_core.can_admin')
def delete_type(request, ptype_id):
    ptype = get_object_or_404(CremePropertyType, pk=ptype_id)

    if not ptype.is_custom:
        raise Http404("Can't delete a standard PropertyType")

    ptype.delete()

    return HttpResponseRedirect(CremePropertyType.get_lv_absolute_url())


class TaggedEntitiesBlock(QuerysetBlock):
    #dependencies  = (CremeProperty,) #TODO: ??
    template_name = 'creme_core/templatetags/block_tagged_entities.html'

    def __init__(self, ptype, ctype):
        self.ptype = ptype
        self.ctype = ctype
        self.id_ = self.generate_id('creme_core', 'tagged-%s-%s' % (ctype.app_label, ctype.model))

    @staticmethod
    def parse_block_id(block_id):
        "@return A ContentType instance if valid, else None"
        parts = block_id.split('-')
        ctype = None

        if len(parts) == 4:
            try:
                tmp_ctype = ContentType.objects.get_by_natural_key(parts[2], parts[3])
            except ContentType.DoesNotExist:
                pass
            else:
                if issubclass(tmp_ctype.model_class(), CremeEntity):
                    ctype = tmp_ctype

        return ctype

    def detailview_display(self, context):
        ctype = self.ctype
        model = ctype.model_class()
        meta = model._meta
        verbose_name = meta.verbose_name
        ptype = self.ptype

        btc = self.get_block_template_context(
                    context,
                    model.objects.filter(properties__type=ptype),
                    update_url='/creme_core/property/type/%s/reload_block/%s/' % (ptype.id, self.id_),
                    ptype_id=ptype.id,
                    ctype=ctype, #if the model is inserted in the context, the template call it and create an instance...
                    short_title=verbose_name,
                )

        count = btc['page'].paginator.count
        btc['title'] = _('%(count)s %(model)s') % {
                            'count': count,
                            'model': ungettext(verbose_name, meta.verbose_name_plural, count),
                        }

        return self._render(btc)


class TaggedMiscEntitiesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'misc_tagged_entities')
    #dependencies  = (CremeProperty,) #TODO: ??
    template_name = 'creme_core/templatetags/block_tagged_entities.html'

    def __init__(self, ptype, excluded_ctypes):
        self.ptype = ptype
        self.excluded_ctypes = excluded_ctypes

    def detailview_display(self, context):
        ptype = self.ptype
        btc = self.get_block_template_context(
                    context,
                    CremeEntity.objects.filter(properties__type=ptype)
                                       .exclude(entity_type__in=self.excluded_ctypes),
                    update_url='/creme_core/property/type/%s/reload_block/%s/' % (ptype.id, self.id_),
                    ptype_id=ptype.id,
                    ctype=None,
                )

        CremeEntity.populate_real_entities(btc['page'].object_list)

        return self._render(btc)


@login_required
def type_detailview(request, ptype_id):
    ptype = get_object_or_404(CremePropertyType, id=ptype_id)
    ctypes = ptype.subject_ctypes.all()
    blocks = [TaggedEntitiesBlock(ptype, ctype)
                for ctype in (ctypes or creme_entity_content_types())
             ]

    if ctypes:
        blocks.append(TaggedMiscEntitiesBlock(ptype, excluded_ctypes=ctypes))

    return render(request, 'creme_core/view_property_type.html',
                  {'object':     ptype,
                   'ctypes':     ctypes,
                   'blocks':     blocks,
                   'count_stat': CremeEntity.objects.filter(properties__type=ptype).count(),
                  }
                 )

@login_required
@jsonify
def reload_block(request, ptype_id, block_id):
    ptype = get_object_or_404(CremePropertyType, id=ptype_id)

    if block_id == TaggedMiscEntitiesBlock.id_:
        block = TaggedMiscEntitiesBlock(ptype, ptype.subject_ctypes.all())
    else:
        ctype = TaggedEntitiesBlock.parse_block_id(block_id)
        if ctype is None:
            raise Http404('Invalid block id "%s"' % block_id)

        block = TaggedEntitiesBlock(ptype, ctype)

    return [(block.id_, block.detailview_display(RequestContext(request)))]
