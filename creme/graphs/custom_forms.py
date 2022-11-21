from django.utils.translation import pgettext_lazy

from creme import graphs
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
)

Graph = graphs.get_graph_model()


class GraphFormDefault(CustomFormDefault):
    main_fields = ['user', 'name']


GRAPH_CREATION_CFORM = CustomFormDescriptor(
    id='graphs-graph_creation',
    model=Graph,
    verbose_name=pgettext_lazy('graphs', 'Creation form for graph'),
    default=GraphFormDefault,
)
GRAPH_EDITION_CFORM = CustomFormDescriptor(
    id='graphs-graph_edition',
    model=Graph,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('graphs', 'Edition form for graph'),
    default=GraphFormDefault,
)

del Graph
