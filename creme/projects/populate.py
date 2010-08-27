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

from django.contrib.contenttypes.models import ContentType

from django.utils.translation import ugettext as _
from creme_core.utils import create_or_update_models_instance as create
from creme_core.utils.meta import get_verbose_field_name
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.models import RelationType, SearchConfigItem, SearchField
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import Contact

from projects.models import ProjectStatus, TaskStatus, Project, ProjectTask, Resource
from projects.constants import REL_OBJ_PROJECT_MANAGER, REL_SUB_PROJECT_MANAGER, TASK_STATUS


class Populator(BasePopulator):
    dependencies = ['creme.core','creme.persons']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_PROJECT_MANAGER, _(u'is one of the leaders of this project'), [Contact]),
                            (REL_OBJ_PROJECT_MANAGER, _(u'has as leader'),                         [Project]))

        create(ProjectStatus, 1, name=_(u"Invitation to tender"),  description=_(u"Response to an invitation to tender"))
        create(ProjectStatus, 2, name=_(u"Initialization"),        description=_(u"The project is starting"))
        create(ProjectStatus, 3, name=_(u"Preliminary phase"),     description=_(u"The project is in the process of analysis and design"))
        create(ProjectStatus, 4, name=_(u"Achievement"),           description=_(u"The project is being implemented"))
        create(ProjectStatus, 5, name=_(u"Tests"),                 description=_(u"The project is in the testing process (unit / integration / functional)"))
        create(ProjectStatus, 6, name=_(u"User acceptance tests"), description=_(u"The project is in the user acceptance testing process"))
        create(ProjectStatus, 7, name=_(u"Finished"),               description=_(u"The project is finished"))

        #create(TaskStatus, 1, name=_(u"Non commencée"), description=_(u"La tâche n'a pas encore démarrée"))
        #create(TaskStatus, 2, name=_(u"En cours"),      description=_(u"La tâche est en cours"))
        #create(TaskStatus, 3, name=_(u"Annulée"),       description=_(u"La tâche a été annulée"))
        #create(TaskStatus, 4, name=_(u"Redémarrée"),    description=_(u"La tâche a été redémarrée"))
        #create(TaskStatus, 5, name=_(u"Terminée"),      description=_(u"La tâche est terminée"))
        for pk, statusdesc in TASK_STATUS:
            create(TaskStatus, pk, name=statusdesc.name, description=statusdesc.verbose_name)

        get_ct = ContentType.objects.get_for_model

        hf_id = create(HeaderFilter, 'projects-hf_project', name=_(u'Project view'), entity_type_id=get_ct(Project).id, is_custom=False).id
        pref  = 'projects-hfi_project_'
        create(HeaderFilterItem, pref + 'name', order=1, name='name',        title=_(u'Name'),        type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'desc', order=2, name='description', title=_(u'Description'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="description__icontains")

        ##useless no ?? (no listview for tasks)
        #hf_id = create(HeaderFilter, 'projects-hf_task', name=u'Vue de Tâche', entity_type_id=get_ct(ProjectTask).id, is_custom=False).id
        #pref  = 'projects-hfi_task_'
        #create(HeaderFilterItem, pref + 'title', order=1, name='title',       title=u'Nom de la tâche',         type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        #create(HeaderFilterItem, pref + 'desc',  order=2, name='description', title=u'Description de la tâche', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="description__icontains")

        ##useless no ?? (no listview for resources)
        #hf_id = create(HeaderFilter, 'projects-hf_resource', name='Vue de Resource', entity_type_id=get_ct(Resource).id, is_custom=False).id
        #pref  = 'projects-hfi_resource_'
        #create(HeaderFilterItem, pref + 'contact', order=1, name='linked_contact', title=u'Nom de la ressource', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="linked_contact__icontains")
        #create(HeaderFilterItem, pref + 'cost',    order=2, name='hourly_cost',    title=u'Coût horaire',        type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="hourly_cost__icontains")

        model = Project
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', 'description', 'status__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)

        model = Resource
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['linked_contact__first_name', 'linked_contact__last_name', 'hourly_cost']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)

        model = ProjectTask
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['project__name', 'duration', 'status__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)
