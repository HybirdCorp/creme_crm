from rest_framework import routers

import creme.creme_api.api.auth.viewsets
import creme.creme_api.api.contenttypes.viewsets
import creme.creme_api.api.persons.viewsets
import creme.creme_api.api.tokens.viewsets


class CremeRouter(routers.DefaultRouter):
    include_root_view = False
    include_format_suffixes = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resources_list = set()

    def register_viewset(self, resource_name, viewset):
        self.resources_list.add(resource_name)

        return self.register(
            resource_name,
            viewset,
            basename=f'creme_api__{resource_name}'
        )


router = CremeRouter()
router.register_viewset("tokens", creme.creme_api.api.tokens.viewsets.TokenViewSet)
router.register_viewset(
    "contenttypes", creme.creme_api.api.contenttypes.viewsets.ContentTypeViewSet)
router.register_viewset("users", creme.creme_api.api.auth.viewsets.UserViewSet)
router.register_viewset("teams", creme.creme_api.api.auth.viewsets.TeamViewSet)
router.register_viewset("roles", creme.creme_api.api.auth.viewsets.UserRoleViewSet)
router.register_viewset("credentials", creme.creme_api.api.auth.viewsets.SetCredentialsViewSet)
router.register_viewset("contacts", creme.creme_api.api.persons.viewsets.ContactViewSet)
router.register_viewset("organisations", creme.creme_api.api.persons.viewsets.OrganisationViewSet)
router.register_viewset("civilities", creme.creme_api.api.persons.viewsets.CivilityViewSet)
router.register_viewset("positions", creme.creme_api.api.persons.viewsets.PositionViewSet)
router.register_viewset("staff_sizes", creme.creme_api.api.persons.viewsets.StaffSizeViewSet)
router.register_viewset("legal_forms", creme.creme_api.api.persons.viewsets.LegalFormViewSet)
router.register_viewset("sectors", creme.creme_api.api.persons.viewsets.SectorViewSet)
