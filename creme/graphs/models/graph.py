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

from os import remove as delete_file
from os.path import basename

from django.conf import settings
from django.db.models import CharField, ManyToManyField, ForeignKey, CASCADE
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.models import CremeModel, CremeEntity, RelationType, Relation
from creme.creme_core.utils.file_handling import FileCreator


class AbstractGraph(CremeEntity):
    name                   = CharField(pgettext_lazy('graphs', u'Name of the graph'), max_length=100)
    orbital_relation_types = ManyToManyField(RelationType, verbose_name=_(u'Types of the peripheral relations'))

    creation_label = pgettext_lazy('graphs', u'Create a graph')
    save_label     = pgettext_lazy('graphs', u'Save the graph')

    class GraphException(Exception):
        pass

    class Meta:
        abstract = True
        app_label = 'graphs'
        verbose_name = pgettext_lazy('graphs', u'Graph')
        verbose_name_plural = pgettext_lazy('graphs', u'Graphs')
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('graphs__view_graph', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('graphs__create_graph')

    def get_edit_absolute_url(self):
        return reverse('graphs__edit_graph', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('graphs__list_graphs')

    def generate_png(self, user):
        from os.path import join  # exists
        # from os import makedirs

        import pygraphviz as pgv

        # NB: to work with utf8 label in node: all node must be added explicitly with
        #     unicode label, and when edges are a created, nodes identified by their
        #     labels encoded as string

        graph = pgv.AGraph(directed=True)

        # NB: "self.roots.all()" causes a strange additional query (retrieving of the base CremeEntity !)....
        has_perm_to_view = user.has_perm_to_view
        roots = [root for root in RootNode.objects.filter(graph=self.id).select_related('entity')
                    if not root.entity.is_deleted and has_perm_to_view(root.entity)
                ]

        add_node = graph.add_node
        add_edge = graph.add_edge

        # TODO: entity cache ? regroups relations by type ? ...

        CremeEntity.populate_real_entities([root.entity for root in roots]) #small optimisation

        for root in roots:
            add_node(unicode(root.entity), shape='box')
            # add_node('filled box',    shape='box', style='filled', color='#FF00FF')
            # add_node('filled box v2', shape='box', style='filled', fillcolor='#FF0000', color='#0000FF', penwidth='2.0') #default pensize="1.0"

        orbital_nodes = {} #cache

        for root in roots:
            subject = root.entity
            str_subject = unicode(subject)
            relations   = subject.relations.filter(type__in=root.relation_types.all())\
                                           .select_related('object_entity', 'type')

            Relation.populate_real_object_entities(relations)  # Small optimisation

            for relation in relations:
                object_ = relation.object_entity
                if not user.has_perm_to_view(object_):
                    continue

                uni_object = unicode(object_)
                str_object = uni_object

                orbital_node = orbital_nodes.get(object_.id)
                if not orbital_node:
                    add_node(uni_object)
                    orbital_nodes[object_.id] = str_object

                add_edge(str_subject, str_object,
                         label=unicode(relation.type.predicate))
                # add_edge('b', 'd', color='#FF0000', fontcolor='#00FF00', label='foobar', style='dashed')

        orbital_rtypes = self.orbital_relation_types.all()

        if orbital_rtypes:
            orbital_ids = orbital_nodes.keys()

            for relation in Relation.objects.filter(subject_entity__in=orbital_ids,
                                                    object_entity__in=orbital_ids,
                                                    type__in=orbital_rtypes).select_related('type'):
                add_edge(orbital_nodes[relation.subject_entity_id], orbital_nodes[relation.object_entity_id],
                         label=unicode(relation.type.predicate),
                         style='dashed')

        # print graph.string()

        graph.layout(prog='dot')  # Algo: neato dot twopi circo fdp nop

        try:
            path = FileCreator(join(settings.MEDIA_ROOT, 'upload', 'graphs'),
                               'graph_%i.png' % self.id,
                              ).create()
        except FileCreator.Error as e:
            raise Graph.GraphException(e)

        # TODO: delete old files ???
        try:
            # graph.draw(join(dir_path, filename), format='png')  # Format: pdf svg
            graph.draw(path, format='png')  # Format: pdf svg
        except IOError as e:
            delete_file(path)

            raise Graph.GraphException(str(e))

        return HttpResponseRedirect(reverse('creme_core__dl_file', args=('/upload/graphs/' + basename(path),)))

    def _post_save_clone(self, source):
        for node in RootNode.objects.filter(graph=source):
            rn = RootNode.objects.create(graph=self, entity=node.entity)
            rn.relation_types = node.relation_types.all()


class Graph(AbstractGraph):
    class Meta(AbstractGraph.Meta):
        swappable = 'GRAPHS_GRAPH_MODEL'


class RootNode(CremeModel):
    graph          = ForeignKey(settings.GRAPHS_GRAPH_MODEL, related_name='roots', editable=False, on_delete=CASCADE)
    entity         = ForeignKey(CremeEntity, editable=False, on_delete=CASCADE)
    # TODO: editable=False is only to avoid inner edition with an ugly widget
    relation_types = ManyToManyField(RelationType, editable=False)

    class Meta:
        app_label = 'graphs'

    def get_edit_absolute_url(self):
        return reverse('graphs__edit_root', args=(self.id,))

    def get_related_entity(self):  # For generic views (edit_related_to_entity)
        return self.graph

    def get_relation_types(self):
        return self.relation_types.select_related('symmetric_type')
