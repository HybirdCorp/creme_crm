# -*- coding: utf-8 -*-

from .add import (
    AddingInstanceToEntityPopup,
    CremeModelCreation,
    CremeModelCreationPopup,
    EntityCreation,
    EntityCreationPopup,
)
from .base import (
    BricksView,
    CheckedTemplateView,
    CheckedView,
    CremeFormPopup,
    CremeFormView,
    RelatedToEntityFormPopup,
)
from .delete import CremeDeletion, CremeModelDeletion
from .detailview import (
    CremeModelDetail,
    CremeModelDetailPopup,
    EntityDetail,
    EntityDetailPopup,
    RelatedToEntityDetail,
    RelatedToEntityDetailPopup,
)
from .edit import (
    CremeEdition,
    CremeEditionPopup,
    CremeModelEdition,
    CremeModelEditionPopup,
    EntityEdition,
    EntityEditionPopup,
    RelatedToEntityEditionPopup,
)
from .listview import EntitiesList
from .wizard import (
    CremeModelCreationWizard,
    CremeModelCreationWizardPopup,
    CremeModelEditionWizard,
    CremeModelEditionWizardPopup,
    EntityCreationWizard,
    EntityCreationWizardPopup,
    EntityEditionWizard,
    EntityEditionWizardPopup,
)
