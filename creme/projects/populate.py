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

from creme_core.utils import create_or_update_models_instance as create
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.models import RelationType, SearchConfigItem
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import Contact

from projects.models import ProjectStatus, TaskStatus, Project, ProjectTask, Resource
from projects.constants import REL_OBJ_PROJECT_MANAGER, REL_SUB_PROJECT_MANAGER


class Populator(BasePopulator):
    dependencies = ['creme.core','creme.persons']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_PROJECT_MANAGER, u'est un des responsables du projet', [Contact]),
                            (REL_OBJ_PROJECT_MANAGER, u'a pour responsable',                [Project]))

        create(ProjectStatus, 1, name=u"Appel d'offre",  description=u"Un appel d'offre a été lancé")
        create(ProjectStatus, 2, name=u"Initialisation", description=u"Le projet démarre")
        create(ProjectStatus, 3, name=u"Avant-phase",    description=u"Le projet est en phase d'analyse et de conception")
        create(ProjectStatus, 4, name=u"Réalisation",    description=u"Le projet est en phase de réalisation")
        create(ProjectStatus, 5, name=u"Tests",          description=u"Le projet est en phase de tests (unitaires / intégration / fonctionnels)")
        create(ProjectStatus, 6, name=u"Recette",        description=u"Le projet est en recette")
        create(ProjectStatus, 7, name=u"Terminé",        description=u"Le projet est terminé")

        create(TaskStatus, 1, name=u"Non commencée", description=u"La tâche n'a pas encore démarrée")
        create(TaskStatus, 2, name=u"En cours",      description=u"La tâche est en cours")
        create(TaskStatus, 3, name=u"Annulée",       description=u"La tâche a été annulée")
        create(TaskStatus, 4, name=u"Redémarrée",    description=u"La tâche a été redémarrée")
        create(TaskStatus, 5, name=u"Terminée",      description=u"La tâche est terminée")

        get_ct = ContentType.objects.get_for_model

        hf_id = create(HeaderFilter, 'projects-hf_project', name=u'Vue de Projet', entity_type_id=get_ct(Project).id, is_custom=False).id
        pref  = 'projects-hfi_project_'
        create(HeaderFilterItem, pref + 'name', order=1, name='name',        title=u'Nom projet',          type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'desc', order=2, name='description', title=u'Description project', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="description__icontains")

        #useless no ?? (no listview for tasks)
        hf_id = create(HeaderFilter, 'projects-hf_task', name=u'Vue de Tâche', entity_type_id=get_ct(ProjectTask).id, is_custom=False).id
        pref  = 'projects-hfi_task_'
        create(HeaderFilterItem, pref + 'title', order=1, name='title',       title=u'Nom de la tâche',         type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        create(HeaderFilterItem, pref + 'desc',  order=2, name='description', title=u'Description de la tâche', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="description__icontains")

        #useless no ?? (no listview for resources)
        hf_id = create(HeaderFilter, 'projects-hf_resource', name='Vue de Resource', entity_type_id=get_ct(Resource).id, is_custom=False).id
        pref  = 'projects-hfi_resource_'
        create(HeaderFilterItem, pref + 'contact', order=1, name='linked_contact', title=u'Nom de la ressource', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="linked_contact__icontains")
        create(HeaderFilterItem, pref + 'cost',    order=2, name='hourly_cost',    title=u'Coût horaire',        type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="hourly_cost__icontains")


        SearchConfigItem.create(Project,     ['name', 'description', 'status__name'])
        SearchConfigItem.create(Resource,    ['linked_contact__first_name', 'linked_contact__last_name', 'hourly_cost'])
        SearchConfigItem.create(ProjectTask, ['project__name', 'duration', 'status__name'])
        