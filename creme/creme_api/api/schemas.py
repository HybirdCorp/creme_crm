from rest_framework.schemas.openapi import AutoSchema


class CremeSchema(AutoSchema):
    def get_operation_id(self, path, method):
        method_name = getattr(self.view, "action", method.lower())
        action = self._to_camel_case(method_name)
        name = self.get_operation_id_base(path, method, action)
        return action + name
