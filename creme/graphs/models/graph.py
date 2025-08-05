################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

# import warnings
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

import creme.creme_core.models.fields as core_fields
from creme.creme_core.models import (
    CremeEntity,
    CremeModel,
    Relation,
    RelationType,
)


class AbstractGraph(CremeEntity):
    name = models.CharField(
        pgettext_lazy('graphs', 'Name of the graph'), max_length=100,
    )
    orbital_relation_types = models.ManyToManyField(
        RelationType, verbose_name=_('Types of the peripheral relations'),
        editable=False,
    )

    creation_label = pgettext_lazy('graphs', 'Create a graph')
    save_label     = pgettext_lazy('graphs', 'Save the graph')

    class GraphException(Exception):
        pass

    class Meta:
        abstract = True
        app_label = 'graphs'
        verbose_name = pgettext_lazy('graphs', 'Graph')
        verbose_name_plural = pgettext_lazy('graphs', 'Graphs')
        ordering = ('name',)

    def __str__(self):
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

    def get_root_nodes(self, user):
        # NB: "self.roots.all()" causes a strange additional query
        #     (retrieving of the base CremeEntity !)....
        has_perm_to_view = user.has_perm_to_view
        return [
            root
            for root in (
                RootNode.objects.filter(graph=self.id)
                                .select_related('entity')
                                .prefetch_related('real_entity')
            ) if not root.entity.is_deleted and has_perm_to_view(root.entity)
        ]

    def get_root_node_relations(self, root, user):
        subject = root.real_entity

        relations = subject.relations.filter(
            type__in=root.relation_types.all(),
        ).select_related('type').prefetch_related('real_object')

        return [
            relation for relation in relations
            if user.has_perm_to_view(relation.real_object)
        ]

    def get_orbital_relations(self, limit_to=()):
        orbital_rtype_ids = self.orbital_relation_types.values_list('pk', flat=True)

        if orbital_rtype_ids:
            qs = Relation.objects.filter(
                type_id__in=orbital_rtype_ids,
            )

            if limit_to:
                qs = qs.filter(
                    subject_entity__in=limit_to,
                    object_entity__in=limit_to,
                )

            qs.select_related('type')
        else:
            qs = Relation.objects.none()

        return qs

    # def generate_png(self, user):
    #     warnings.warn(
    #         'The method graphs.models.AbstractGraph.generate_png() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     from os.path import join
    #
    #     import pygraphviz as pgv
    #
    #     # NB: to work with utf8 label in node: all node must be added explicitly with
    #     #     unicode label, and when edges are a created, nodes identified by their
    #     #     labels encoded as string
    #
    #     graph = pgv.AGraph(directed=True)
    #     roots = self.get_root_nodes(user)
    #
    #     add_node = graph.add_node
    #     add_edge = graph.add_edge
    #
    #     # todo: entity cache ? regroups relations by type ? ...
    #
    #     # # Small optimisation
    #     # CremeEntity.populate_real_entities([root.entity for root in roots])
    #
    #     for root in roots:
    #         # add_node(str(root.entity), shape='box')
    #         add_node(str(root.real_entity), shape='box')
    #         # add_node('filled box',    shape='box', style='filled', color='#FF00FF')
    #         # add_node(
    #         #     'filled box v2', shape='box', style='filled',
    #         #     fillcolor='#FF0000', color='#0000FF', penwidth='2.0'
    #         # )  # default pensize=="1.0"
    #
    #     orbital_nodes = {}  # Cache
    #
    #     for root in roots:
    #         subject = root.real_entity
    #         str_subject = str(subject)
    #
    #         relations = self.get_root_node_relations(root, user)
    #
    #         for relation in relations:
    #             # object_entity = relation.object_entity
    #             object_entity = relation.real_object
    #             #  if not user.has_perm_to_view(object_entity):
    #             #     continue
    #
    #             object_as_str = str(object_entity)
    #
    #             orbital_node = orbital_nodes.get(object_entity.id)
    #             if not orbital_node:
    #                 add_node(object_as_str)
    #                 orbital_nodes[object_entity.id] = object_as_str
    #
    #             add_edge(
    #                 str_subject, object_as_str,
    #                 label=str(relation.type.predicate),
    #             )
    #             # add_edge(
    #             #     'b', 'd', color='#FF0000', fontcolor='#00FF00',
    #             #     label='foobar', style='dashed'
    #             # )
    #
    #     orbital_rtypes = self.orbital_relation_types.all()
    #
    #     if orbital_rtypes:
    #         orbital_ids = orbital_nodes.keys()
    #
    #         for relation in Relation.objects.filter(
    #             subject_entity__in=orbital_ids,
    #             object_entity__in=orbital_ids,
    #             type__in=orbital_rtypes,
    #         ).select_related('type'):
    #             add_edge(
    #                 orbital_nodes[relation.subject_entity_id],
    #                 orbital_nodes[relation.object_entity_id],
    #                 label=str(relation.type.predicate),
    #                 style='dashed',
    #             )
    #
    #     graph.layout(prog='dot')  # Algo: neato dot twopi circo fdp nop
    #
    #     img_format = 'png'  # Format: pdf svg
    #     img_basename = f'graph_{self.id}.{img_format}'
    #
    #     try:
    #         path = FileCreator(
    #             # join(settings.MEDIA_ROOT, 'upload', 'graphs'), img_basename,
    #             join(settings.MEDIA_ROOT, 'graphs'), img_basename,
    #         ).create()
    #     except FileCreator.Error as e:
    #         raise self.GraphException(e) from e
    #
    #     try:
    #         graph.draw(path, format=img_format)  # Format: pdf svg
    #     except OSError as e:
    #         delete_file(path)
    #
    #         raise self.GraphException(str(e)) from e
    #
    #     fileref = FileRef.objects.create(
    #         user=user,
    #         filedata='graphs/' + basename(path),
    #         basename=img_basename,
    #         description='todo'
    #     )
    #
    #     return HttpResponseRedirect(fileref.get_download_absolute_url())

    # def _post_save_clone(self, source):
    #     warnings.warn(
    #         'The method Graph._post_save_clone() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     for node in RootNode.objects.filter(graph=source):
    #         rn = RootNode.objects.create(graph=self, real_entity=node.entity)
    #         rn.relation_types.set(node.relation_types.all())


class Graph(AbstractGraph):
    class Meta(AbstractGraph.Meta):
        swappable = 'GRAPHS_GRAPH_MODEL'


class RootNode(CremeModel):
    graph = models.ForeignKey(
        settings.GRAPHS_GRAPH_MODEL, related_name='roots',
        editable=False, on_delete=models.CASCADE,
    )

    entity_ctype = core_fields.EntityCTypeForeignKey(related_name='+', editable=False)
    entity = models.ForeignKey(
        CremeEntity, editable=False, on_delete=models.CASCADE,
    )
    real_entity = core_fields.RealEntityForeignKey(
        ct_field='entity_ctype', fk_field='entity',
    )

    # TODO: editable=False is only to avoid inner edition with an ugly widget
    relation_types = models.ManyToManyField(RelationType, editable=False)

    class Meta:
        app_label = 'graphs'

    def get_edit_absolute_url(self):
        return reverse('graphs__edit_root', args=(self.id,))

    def get_related_entity(self):  # For generic views (edit_related_to_entity)
        return self.graph
