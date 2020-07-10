from rest_framework import routers

import creme.creme_api.api.auth.viewsets


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

router.register_viewset("users", creme.creme_api.api.auth.viewsets.UserViewSet)
router.register_viewset("teams", creme.creme_api.api.auth.viewsets.TeamViewSet)
router.register_viewset("roles", creme.creme_api.api.auth.viewsets.UserRoleViewSet)
router.register_viewset("credentials", creme.creme_api.api.auth.viewsets.SetCredentialsViewSet)
