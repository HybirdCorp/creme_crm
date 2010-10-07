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

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.contrib.auth.admin import get_object_or_404
from django.utils.simplejson import JSONEncoder
from django.db.models import Q
from django.contrib.auth.models import ContentType

from creme_core.models import CremeEntity
from creme_core.models.custom_field import CustomField
from creme_core.registry import creme_registry, NotRegistered
from creme_core.entities_access.functions_for_permissions import edit_object_or_die
from creme_core.utils.meta import get_flds_with_fk_flds, get_flds_with_fk_flds_str
from creme_core.utils import get_ct_or_404, get_from_POST_or_404
#from creme.creme_utils.views import handle_uploaded_file


#def ajax_uploaded_file(request):
#    FILES = request.FILES
#    response = {'error':'', 'file':''}
#    debug("request.FILES : %s", request.FILES)
#    if FILES:
#        for k, f in FILES.items():
#            response['file'] = handle_uploaded_file(f, 'upload/')
#    else:
#        response['error'] = "Aucun fichier fourni"
#
#    return HttpResponse(JSONEncoder().encode(response))

TRI = {"asc":"", "desc":"-"}

#TODO: broken (see creme_registry.get_listview_modelform_for_model)
@login_required
def edit_js(request):
    """
        @Permissions : Edit on current object
    """
    debug('\n\n##########edit_js#########"\n\n')
    id = request.POST.get('id')
    if id is not None:
        try :
            #TODO: use get_real_entity() and get_object_or_404 ??
            entite = CremeEntity.objects.get(pk=id)
            object = entite.entity_type.model_class().objects.get(pk=id)

            die_status = edit_object_or_die(request, object)
            if die_status:
                return HttpResponse("Vous n'avez pas la permission d'éditer cet objet", mimetype="text/javascript", status=400)

        except Exception, e:
            debug('\nException 1 : %s' % e)
            raise Http404
        #broken: could form be generated (with modelform_factoryfor example)
        form = creme_registry.get_listview_modelform_for_model(object.__class__)(request.POST, instance=object)
        if form.is_valid():
            form.save()
            debug('Save ok')
            return HttpResponse('', mimetype="text/javascript")
        else :
            debug('Erreurs : %s ' % form.errors)
            return HttpResponse('%s' % form.errors, mimetype="text/javascript", status=400)
    else : #TODO: use a guard instead
        #debug('\n2')
        raise Http404


#TODO: rename to field_has_n_get_fk
#TODO: refactor ("datas"->"data", code could be simplified etc...)
@login_required
def fieldHasNGetFK(request):
    """
    To verify if a field is a foreign key for a model
    and if it is get related field (in JSON format)
    """
    fieldname = request.POST.get('fieldname')
    ct_id = request.POST.get('ct_id')

    if fieldname and ct_id:
        klass = get_object_or_404(ContentType, pk=ct_id).model_class()
        field = [f for f in klass._meta.fields + klass._meta.many_to_many if f.name == fieldname]
        if field and field[0].get_internal_type() == 'ForeignKey':
            datas = [(u'%s' % f.name, u'%s' % f.verbose_name) for f in get_flds_with_fk_flds(field[0].rel.to, 0)]
        elif field and field[0].get_internal_type() == 'ManyToManyField':
            datas = []
            for f in get_flds_with_fk_flds(field[0].rel.to, 0):
                #TODO;  factorise "if f.get_internal_type() != 'ManyToManyField'"
                if f.get_internal_type() != 'ManyToManyField' and f.get_internal_type() != 'ForeignKey':
                    datas.append((u'%s' % f.name, u'%s' % f.verbose_name))
                #TODO: stupid ?? (if == 'ForeignKey' => != 'ManyToManyField' of course !!)
                if f.get_internal_type() != 'ManyToManyField' and f.get_internal_type() == 'ForeignKey':
                    #TODO: use generator expression
                    datas.extend([(u'%s__%s' % (f.name, sub_f.name), u'%s - %s' % (f.verbose_name, sub_f.verbose_name)) for sub_f in get_flds_with_fk_flds(f.rel.to, 0)])
        else:
            datas = []
        return HttpResponse(JSONEncoder().encode(datas), mimetype="text/javascript")
    return HttpResponse('', mimetype="text/javascript", status=400)

@login_required
def get_fields(request):
    """@return Fields for a model [('field1', 'field1_verbose_name'),...]"""
    POST = request.POST

    try:
        model = get_ct_or_404(int(get_from_POST_or_404(POST, 'ct_id'))).model_class()
        deep  = int(POST.get('deep', 1))
    except ValueError, e:
        msg    = str(e)
        status = 400
    except Http404, e:
        msg    = str(e)
        status = 404
    else:
        msg    = JSONEncoder().encode(get_flds_with_fk_flds_str(model, deep))
        status = 200

    return HttpResponse(msg, mimetype="text/javascript", status=status)

@login_required
def _get_ct_info(request, generator):
    try:
        ct = get_ct_or_404(int(get_from_POST_or_404(request.POST, 'ct_id')))
    except ValueError, e:
        status = 400
        msg    = str(e)
    except Http404, e:
        status = 404
        msg    = str(e)
    else:
        status = 200
        msg    = JSONEncoder().encode(generator(ct))

    return HttpResponse(msg, mimetype="text/javascript", status=status)

def get_custom_fields(request):
    """@return Custom fields for a model [('cfield1_name', 'cfield1_name'), ...]"""
    return _get_ct_info(request,
                        lambda ct: [(cf.name, cf.name) for cf in CustomField.objects.filter(content_type=ct)])

def get_function_fields(request):
    """@return functions fields for a model [('func_name', 'func_verbose_name'), ...]"""
    return _get_ct_info(request,
                        lambda ct: [(f_field.name, unicode(f_field.verbose_name)) for f_field in ct.model_class().function_fields])
