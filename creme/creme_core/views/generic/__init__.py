# -*- coding: utf-8 -*-

from .base import (
    CheckedTemplateView, BricksView,
    CremeFormView, CremeFormPopup,
    RelatedToEntityFormPopup,
)
from .add import (
    # add_entity, add_to_entity, add_model_with_popup,
    CremeModelCreation, EntityCreation,
    CremeModelCreationPopup, EntityCreationPopup,
    AddingInstanceToEntityPopup,
)
from .detailview import (
    # view_entity,
    CremeModelDetail, EntityDetail,
    CremeModelDetailPopup, EntityDetailPopup,
    RelatedToEntityDetail, RelatedToEntityDetailPopup,
)
from .edit import (
    # edit_entity, edit_related_to_entity, edit_model_with_popup,
    CremeEdition, CremeEditionPopup,
    CremeModelEdition, EntityEdition,
    CremeModelEditionPopup, EntityEditionPopup,
    RelatedToEntityEditionPopup,
)
from .listview import EntitiesList  # list_view list_view_popup
# from .portal import app_portal
# from .popup import inner_popup
