# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import warnings

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_list_or_404, get_object_or_404, render, redirect
from django.utils.translation import ugettext_lazy as _  # ungettext

# TODO: move them to creme_core ?
from creme.creme_config.forms.creme_property_type import CremePropertyTypeAddForm, CremePropertyTypeEditForm

from ..auth.decorators import login_required, permission_required
from ..forms.creme_property import AddPropertiesForm, AddPropertiesBulkForm
from ..gui.bricks import QuerysetBrick, Brick
from ..models import CremeEntity, CremePropertyType
from ..utils import creme_entity_content_types, get_ct_or_404, get_from_POST_or_404, jsonify  # get_from_GET_or_404
# from ..utils.translation import get_model_verbose_name
from . import generic, bricks as bricks_views
from .utils import build_cancel_path

# TODO: Factorise with views in creme_config


# TODO: Factorise with add_relations_bulk and bulk_update?
@login_required
def add_properties_bulk(request, ct_id):
    user = request.user
    model = get_ct_or_404(ct_id).model_class()
    # entities = get_list_or_404(model, pk__in=request.POST.getlist('ids') or
    #                                          request.GET.getlist('ids')
    #                           )
    entities = get_list_or_404(model,
                               pk__in=request.POST.getlist('ids')
                                      if request.method == 'POST' else
                                      request.GET.getlist('ids'),
                              )

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

    return generic.inner_popup(request, 'creme_core/generics/blockform/add_popup.html',
                               {'form':  form,
                                'title': _(u'Multiple adding of properties'),
                                'submit_label': _(u'Add the properties'),
                               },
                               is_valid=form.is_valid(),
                               reload=False,
                               delegate_reload=True,
                              )


@login_required
def add_to_entity(request, entity_id):
    return generic.add_to_entity(request, entity_id, AddPropertiesForm,
                                 _(u'New properties for «%s»'),
                                 submit_label=_(u'Add the properties'),
                                )


@login_required
@permission_required('creme_core.can_admin')
def add_type(request):
    # NB: does not work because it is not a ModelForm
    # return add_entity(request, CremePropertyTypeAddForm)

    if request.method == 'POST':
        POST = request.POST
        form = CremePropertyTypeAddForm(user=request.user, data=POST)

        if form.is_valid():
            ptype = form.save()

            return redirect(ptype)

        cancel_url = POST.get('cancel_url')
    else:  # GET
        form = CremePropertyTypeAddForm(user=request.user)
        # cancel_url = request.META.get('HTTP_REFERER')
        cancel_url = build_cancel_path(request)

    return render(request, 'creme_core/generics/blockform/add.html',
                  {'form':         form,
                   'title':        CremePropertyType.creation_label,
                   'submit_label': _(u'Save the type of property'),
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
        POST = request.POST
        form = CremePropertyTypeEditForm(ptype, user=request.user, data=POST)

        if form.is_valid():
            form.save()

            return redirect(ptype)

        cancel_url = POST.get('cancel_url')
    else:  # GET
        form = CremePropertyTypeEditForm(ptype, user=request.user)
        # cancel_url = request.META.get('HTTP_REFERER')
        cancel_url = build_cancel_path(request)

    return render(request, 'creme_core/generics/blockform/edit.html',
                  {'form': form,
                   'object': ptype,
                   'submit_label': _(u'Save the modifications'),
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
        return HttpResponse(content_type='text/javascript')

    return redirect(ptype)


@login_required
@permission_required('creme_core.can_admin')
def delete_type(request, ptype_id):
    ptype = get_object_or_404(CremePropertyType, pk=ptype_id)

    if not ptype.is_custom:
        raise Http404("Can't delete a standard PropertyType")

    ptype.delete()

    return HttpResponseRedirect(CremePropertyType.get_lv_absolute_url())


# class PropertyTypeInfoBlock(Block):
class PropertyTypeInfoBrick(Brick):
    id_           = Brick.generate_id('creme_core', 'property_type_info')
    dependencies  = '*'
    read_only     = True
    # template_name = 'creme_core/templatetags/block_ptype_info.html'
    template_name = 'creme_core/bricks/ptype-info.html'

    def __init__(self, ptype, ctypes):
        super(PropertyTypeInfoBrick, self).__init__()
        self.ptype = ptype
        self.ctypes = ctypes

    def detailview_display(self, context):
        ptype = self.ptype

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    # # update_url='/creme_core/property/type/%s/reload_block/%s/' % (ptype.id, self.id_),
                    # update_url=reverse('creme_core__reload_ptype_blocks', args=(ptype.id, self.id_)),
                    ctypes=self.ctypes,
                    count_stat=CremeEntity.objects.filter(properties__type=ptype).count(),
        ))


# class TaggedEntitiesBlock(QuerysetBlock):
class TaggedEntitiesBrick(QuerysetBrick):
    # template_name = 'creme_core/templatetags/block_tagged_entities.html'
    template_name = 'creme_core/bricks/tagged-entities.html'

    def __init__(self, ptype, ctype):
        super(TaggedEntitiesBrick, self).__init__()
        self.ptype = ptype
        self.ctype = ctype
        self.id_ = self.generate_id('creme_core', 'tagged-%s-%s' % (ctype.app_label, ctype.model))
        self.dependencies = (ctype.model_class(),)

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
        # meta = model._meta
        # verbose_name = meta.verbose_name
        ptype = self.ptype

        # btc = self.get_block_template_context(
        btc = self.get_template_context(
                    context,
                    model.objects.filter(properties__type=ptype),
                    # # update_url='/creme_core/property/type/%s/reload_block/%s/' % (ptype.id, self.id_),
                    # update_url=reverse('creme_core__reload_ptype_blocks', args=(ptype.id, self.id_)),
                    ptype_id=ptype.id,
                    ctype=ctype,  # If the model is inserted in the context,
                                  #  the template call it and create an instance...
                    # short_title=verbose_name,
                )

        # count = btc['page'].paginator.count
        # btc['title'] = _(u'%(count)s %(model)s') % {
        #                     'count': count,
        #                     # 'model': ungettext(verbose_name, meta.verbose_name_plural, count),
        #                     'model': get_model_verbose_name(model, count),
        #                 }

        return self._render(btc)


# class TaggedMiscEntitiesBlock(QuerysetBlock):
class TaggedMiscEntitiesBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('creme_core', 'misc_tagged_entities')
    dependencies  = (CremeEntity,)
    # template_name = 'creme_core/templatetags/block_tagged_entities.html'
    template_name = 'creme_core/bricks/tagged-entities.html'

    def __init__(self, ptype, excluded_ctypes):
        super(TaggedMiscEntitiesBrick, self).__init__()
        self.ptype = ptype
        self.excluded_ctypes = excluded_ctypes

    def detailview_display(self, context):
        ptype = self.ptype
        # btc = self.get_block_template_context(
        btc = self.get_template_context(
                    context,
                    CremeEntity.objects.filter(properties__type=ptype)
                                       .exclude(entity_type__in=self.excluded_ctypes),
                    # # update_url='/creme_core/property/type/%s/reload_block/%s/' % (ptype.id, self.id_),
                    # update_url=reverse('creme_core__reload_ptype_blocks', args=(ptype.id, self.id_)),
                    ptype_id=ptype.id,
                    ctype=None,
                )

        CremeEntity.populate_real_entities(btc['page'].object_list)

        return self._render(btc)


@login_required
def type_detailview(request, ptype_id):
    ptype = get_object_or_404(CremePropertyType, id=ptype_id)
    ctypes = ptype.subject_ctypes.all()

    bricks = [PropertyTypeInfoBrick(ptype, ctypes)]
    bricks.extend(TaggedEntitiesBrick(ptype, ctype)
                      for ctype in (ctypes or creme_entity_content_types())
                 )

    if ctypes:
        bricks.append(TaggedMiscEntitiesBrick(ptype, excluded_ctypes=ctypes))

    return render(request, 'creme_core/view_property_type.html',
                  {'object': ptype,
                   'blocks': bricks,  # TODO: rename 'bricks'
                   'bricks_reload_url': reverse('creme_core__reload_ptype_bricks', args=(ptype_id,)),
                  }
                 )


@login_required
@jsonify
def reload_block(request, ptype_id, block_id):
    warnings.warn("The view /creme_core/property/type/{{pt_id}}/reload_block/{{block_id}} is now deprecated."
                  "Use /creme_core/property/type/{{pt_id}}/reload_bricks/ view instead"
                  "[ie: reverse('creme_core__reload_ptype_bricks', args=(ptype.id,)) ].",
                  DeprecationWarning
                 )
    from .blocks import build_context, _get_depblock_ids

    ptype = get_object_or_404(CremePropertyType, id=ptype_id)
    block_renders = []
    ctypes = ptype.subject_ctypes.all()

    context = build_context(request, object=ptype)

    for b_id in _get_depblock_ids(request, block_id):
        if b_id == PropertyTypeInfoBrick.id_:
            block = PropertyTypeInfoBrick(ptype, ctypes)
        elif b_id == TaggedMiscEntitiesBrick.id_:
            block = TaggedMiscEntitiesBrick(ptype, ctypes)
        else:
            ctype = TaggedEntitiesBrick.parse_block_id(b_id)
            if ctype is None:
                raise Http404('Invalid block id "%s"' % b_id)

            block = TaggedEntitiesBrick(ptype, ctype)

        block_renders.append((block.id_, block.detailview_display(context)))

    return block_renders


@login_required
@jsonify
def reload_bricks(request, ptype_id):
    brick_ids = bricks_views.get_brick_ids_or_404(request)
    ptype = get_object_or_404(CremePropertyType, id=ptype_id)
    bricks = []
    ctypes = ptype.subject_ctypes.all()

    for b_id in brick_ids:
        if b_id == PropertyTypeInfoBrick.id_:
            brick = PropertyTypeInfoBrick(ptype, ctypes)
        elif b_id == TaggedMiscEntitiesBrick.id_:
            brick = TaggedMiscEntitiesBrick(ptype, ctypes)
        else:
            ctype = TaggedEntitiesBrick.parse_block_id(b_id)
            if ctype is None:
                raise Http404('Invalid brick id "%s"' % b_id)

            brick = TaggedEntitiesBrick(ptype, ctype)

        bricks.append(brick)

    return bricks_views.bricks_render_info(request, bricks=bricks,
                                           context=bricks_views.build_context(request, object=ptype),
                                          )
