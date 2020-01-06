# -*- coding: utf-8 -*-

from .base import (
    CheckedView, CheckedTemplateView, BricksView,
    CremeFormView, CremeFormPopup,
    RelatedToEntityFormPopup,
)
from .add import (
    CremeModelCreation, EntityCreation,
    CremeModelCreationPopup, EntityCreationPopup,
    AddingInstanceToEntityPopup,
)
from .detailview import (
    CremeModelDetail, EntityDetail,
    CremeModelDetailPopup, EntityDetailPopup,
    RelatedToEntityDetail, RelatedToEntityDetailPopup,
)
from .edit import (
    CremeEdition, CremeEditionPopup,
    CremeModelEdition, EntityEdition,
    CremeModelEditionPopup, EntityEditionPopup,
    RelatedToEntityEditionPopup,
)
from .delete import CremeDeletion, CremeModelDeletion
from .listview import EntitiesList
from .wizard import (
    CremeModelCreationWizard, EntityCreationWizard,
    CremeModelCreationWizardPopup, EntityCreationWizardPopup,
    CremeModelEditionWizard, EntityEditionWizard,
    CremeModelEditionWizardPopup, EntityEditionWizardPopup,
)
