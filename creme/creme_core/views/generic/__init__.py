# -*- coding: utf-8 -*-

from .base import CheckedTemplateView, BricksView
from .add import (
    add_entity, add_to_entity, add_model_with_popup,
    CremeModelCreation, EntityCreation,
    CremeModelCreationPopup, EntityCreationPopup,
    AddingToEntity,
)
from .detailview import (
    view_entity,
    CremeModelDetail, EntityDetail,
    CremeModelDetailPopup, RelatedToEntityDetail,
)
from .edit import (
    edit_entity, edit_related_to_entity, edit_model_with_popup,
    CremeModelEdition, EntityEdition,
    CremeModelEditionPopup, EntityEditionPopup,
    RelatedToEntityEdition,
)
from .listview import list_view, list_view_popup
from .portal import app_portal
from .popup import inner_popup
