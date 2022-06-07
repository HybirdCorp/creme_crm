from collections import defaultdict

from django.contrib.auth import get_user_model, password_validation
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from creme.creme_api.api.contenttypes.utils import (
    get_cremeentity_contenttype_queryset,
)
from creme.creme_config.forms.user_role import filtered_entity_ctypes
from creme.creme_core.apps import CremeAppConfig, creme_app_configs
from creme.creme_core.models import SetCredentials, UserRole
from creme.creme_core.models.fields import CremeUserForeignKey

CremeUser = get_user_model()


class PasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        label=_("Password"), trim_whitespace=False, write_only=True, required=True
    )

    def validate_password(self, password):
        password_validation.validate_password(password, self.instance)
        return password

    def save(self):
        self.instance.set_password(self.validated_data["password"])
        self.instance.save()
        return self.instance


class UserSerializer(serializers.ModelSerializer):
    default_error_messages = {
        "is_superuser_xor_role": _("A user must either have a role, or be a superuser.")
    }

    class Meta:
        model = CremeUser
        fields = [
            "id",
            "username",
            "last_name",
            "first_name",
            "email",
            "date_joined",
            "last_login",
            "is_active",
            # 'is_staff',
            "is_superuser",
            "role",
            # 'is_team',
            # 'teammates_set',
            "time_zone",
            "theme",
            # 'settings',
        ]
        read_only_fields = [
            "date_joined",
            "last_login",
        ]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
        }

    def validate(self, attrs):
        is_superuser = None
        role_id = None

        if self.instance is not None:
            is_superuser = self.instance.is_superuser
            role_id = self.instance.role_id

        has_is_superuser = bool(attrs.get("is_superuser", is_superuser))
        has_role = bool(attrs.get("role", role_id))
        if not (has_is_superuser ^ has_role):
            self.fail("is_superuser_xor_role")
        return attrs


class TeamSerializer(serializers.ModelSerializer):
    teammates = serializers.PrimaryKeyRelatedField(
        queryset=CremeUser.objects.filter(is_team=False, is_staff=False),
        many=True,
        label=_("Teammates"),
        required=True,
        source="teammates_set",
    )

    class Meta:
        model = CremeUser
        fields = [
            "id",
            "username",
            "teammates",
        ]
        extra_kwargs = {"username": {"label": _("Team name")}}

    def __init__(self, *args, **kwargs):
        super(TeamSerializer, self).__init__(*args, **kwargs)
        username_field = self.fields.pop("username")
        # username_field.source = "username"
        self.fields["name"] = username_field

    def save(self, **kwargs):
        kwargs["is_team"] = True
        team = super().save(**kwargs)
        return team


class DeleteUserSerializer(serializers.ModelSerializer):
    """
    Serializer which assigns the fields with type CremeUserForeignKey
    referencing a given user A to another user B, then deletes A.
    """

    transfer_to = serializers.PrimaryKeyRelatedField(
        queryset=CremeUser.objects.none(), required=True
    )

    class Meta:
        model = CremeUser
        fields = ["transfer_to"]

    def __init__(self, instance=None, **kwargs):
        super().__init__(instance=instance, **kwargs)
        users = CremeUser.objects.exclude(is_staff=True)
        if instance is not None:
            users = users.exclude(pk=instance.pk)
        self.fields["transfer_to"].queryset = users

    def save(self, **kwargs):
        CremeUserForeignKey._TRANSFER_TO_USER = self.validated_data["transfer_to"]

        try:
            self.instance.delete()
        finally:
            CremeUserForeignKey._TRANSFER_TO_USER = None


class UserRoleSerializer(serializers.ModelSerializer):
    allowed_apps = serializers.MultipleChoiceField(
        label=_("Allowed applications"),
        choices=(),
    )
    admin_4_apps = serializers.MultipleChoiceField(
        label=_("Administrated applications"),
        choices=(),
        help_text=_(
            "These applications can be configured. "
            "For example, the concerned users can create new choices "
            "available in forms (eg: position for contacts)."
        ),
    )
    creatable_ctypes = serializers.PrimaryKeyRelatedField(
        label=_("Creatable resources"),
        many=True,
        queryset=ContentType.objects.none(),
    )
    exportable_ctypes = serializers.PrimaryKeyRelatedField(
        label=_("Exportable resources"),
        many=True,
        queryset=ContentType.objects.none(),
        help_text=_(
            "This types of entities can be downloaded as CSV/XLS "
            "files (in the corresponding list-views)."
        ),
    )

    default_error_messages = {
        "admin_4_not_allowed_app": _(
            'App "{app}" is not an allowed app for this role.'
        ),
        "not_allowed_ctype": _(
            'Content type "{ct}" ({id}) is part of the app "{app}" '
            "which is not an allowed app for this role."
        ),
    }

    class Meta:
        model = UserRole
        fields = [
            "id",
            "name",
            "allowed_apps",
            "admin_4_apps",
            "creatable_ctypes",
            "exportable_ctypes",
            "credentials",
        ]
        read_only_fields = [
            "credentials",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apps = list(creme_app_configs())

        CRED_REGULAR = CremeAppConfig.CRED_REGULAR
        allowed_apps_f = self.fields["allowed_apps"]
        allowed_apps_f.choices = (
            (app.label, str(app.verbose_name))
            for app in apps
            if app.credentials & CRED_REGULAR
        )

        CRED_ADMIN = CremeAppConfig.CRED_ADMIN
        admin_4_apps_f = self.fields["admin_4_apps"]
        admin_4_apps_f.choices = (
            (app.label, str(app.verbose_name))
            for app in apps
            if app.credentials & CRED_ADMIN
        )

        ct_queryset = get_cremeentity_contenttype_queryset()

        creatable_ctypes_f = self.fields["creatable_ctypes"]
        creatable_ctypes_f.child_relation.queryset = ct_queryset.all()

        exportable_ctypes_f = self.fields["exportable_ctypes"]
        exportable_ctypes_f.child_relation.queryset = ct_queryset.all()

    def build_error_detail(self, error_code, **kwargs):
        msg = self.error_messages[error_code].format(**kwargs)
        return serializers.ErrorDetail(msg, code=error_code)

    def validate(self, attrs):
        # TODO: move in UserRole.clean ?
        errors = defaultdict(list)
        if self.instance is not None:
            allowed_apps = self.instance.allowed_apps
            admin_4_apps = self.instance.admin_4_apps
            creatable_ctypes = self.instance.creatable_ctypes.all()
            exportable_ctypes = self.instance.exportable_ctypes.all()
        else:
            allowed_apps = []
            admin_4_apps = []
            creatable_ctypes = []
            exportable_ctypes = []

        allowed_apps = set(attrs.get("allowed_apps", allowed_apps))
        admin_4_apps = set(attrs.get("admin_4_apps", admin_4_apps))
        creatable_ctypes = set(attrs.get("creatable_ctypes", creatable_ctypes))
        exportable_ctypes = set(attrs.get("exportable_ctypes", exportable_ctypes))

        allowed_ctypes = set(filtered_entity_ctypes(allowed_apps))

        for admin_not_allowed_app in admin_4_apps - allowed_apps:
            errors["admin_4_apps"].append(
                self.build_error_detail(
                    "admin_4_not_allowed_app",
                    app=admin_not_allowed_app,
                )
            )

        for create_not_allowed_ctype in creatable_ctypes - allowed_ctypes:
            errors["creatable_ctypes"].append(
                self.build_error_detail(
                    "not_allowed_ctype",
                    id=create_not_allowed_ctype.id,
                    ct=create_not_allowed_ctype.model,
                    app=create_not_allowed_ctype.app_label,
                )
            )

        for export_not_allowed_ctype in exportable_ctypes - allowed_ctypes:
            errors["exportable_ctypes"].append(
                self.build_error_detail(
                    "not_allowed_ctype",
                    id=export_not_allowed_ctype.id,
                    ct=export_not_allowed_ctype.model,
                    app=export_not_allowed_ctype.app_label,
                )
            )

        if errors:
            raise serializers.ValidationError(dict(errors))

        return attrs


class SetCredentialsSerializer(serializers.ModelSerializer):
    can_view = serializers.BooleanField(
        label=_("View"),
        required=True,
    )
    can_change = serializers.BooleanField(
        label=_("Change"),
        required=True,
    )
    can_delete = serializers.BooleanField(
        label=_("Delete"),
        required=True,
    )

    can_link = serializers.BooleanField(
        label=_("Link"),
        required=True,
        help_text=_(
            "You must have the permission to link on 2 entities "
            "to create a relationship between them. "
            "Beware: if you use «Filtered entities», you won't "
            "be able to add relationships in the creation forms "
            "(you'll have to add them later).",
        ),
    )
    can_unlink = serializers.BooleanField(
        label=_("Unlink"),
        required=True,
        help_text=_(
            "You must have the permission to unlink on "
            "2 entities to delete a relationship between them."
        ),
    )

    class Meta:
        model = SetCredentials
        fields = [
            "id",
            "role",
            "set_type",
            "ctype",
            "can_view",
            "can_change",
            "can_delete",
            "can_link",
            "can_unlink",
            "forbidden",
            "efilter",
        ]
        read_only_fields = [
            "efilter",
        ]
        extra_kwargs = {
            "set_type": {"required": True},
            "ctype": {"required": True},
            "forbidden": {"required": True},
        }

    def update(self, instance, validated_data):
        instance.set_value(
            can_view=validated_data.pop("can_view", instance.can_view),
            can_change=validated_data.pop("can_change", instance.can_change),
            can_delete=validated_data.pop("can_delete", instance.can_delete),
            can_link=validated_data.pop("can_link", instance.can_link),
            can_unlink=validated_data.pop("can_unlink", instance.can_unlink),
        )
        return super().update(instance, validated_data)


class SetCredentialsCreateSerializer(SetCredentialsSerializer):
    role = serializers.PrimaryKeyRelatedField(
        queryset=UserRole.objects.all(),
        required=True,
    )

    def create(self, validated_data):
        instance = SetCredentials(
            role=validated_data["role"],
            set_type=validated_data["set_type"],
            ctype=validated_data["ctype"],
            forbidden=validated_data["forbidden"],
            # efilter=validated_data['efilter'],
        )
        instance.set_value(
            can_view=validated_data["can_view"],
            can_change=validated_data["can_change"],
            can_delete=validated_data["can_delete"],
            can_link=validated_data["can_link"],
            can_unlink=validated_data["can_unlink"],
        )
        instance.save()
        return instance
