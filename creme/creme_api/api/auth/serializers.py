# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2020  Hybird
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

from django.contrib.auth import get_user_model, password_validation
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from creme.creme_core.models import Sandbox, SetCredentials, UserRole
from creme.creme_core.models.fields import CremeUserForeignKey

CremeUser = get_user_model()


class PasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        label=_('Password'), trim_whitespace=False, write_only=True, required=False)

    def validate_password(self, password):
        password_validation.validate_password(password, self.instance)
        return password

    def save(self):
        self.instance.set_password(self.validated_data['password'])
        self.instance.save()
        return self.instance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CremeUser
        fields = [
            'id',
            'username',
            'last_name',
            'first_name',
            'email',

            'date_joined',
            'last_login',
            'is_active',
            # 'is_staff',
            'is_superuser',
            'role',
            # 'is_team',
            # 'teammates_set',
            'time_zone',
            'theme',
            # 'settings',
        ]
    # TODO forbid role + superuser

    def validate(self, attrs):
        # TODO: handle partial update
        if attrs.get('is_superuser') and attrs.get('role'):
            raise serializers.ValidationError(code='is_superuser_xor_role')
        return attrs


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = CremeUser
        fields = [
            'id',
            'username',
            'date_joined',
            'is_active',
            'role',
        ]


class UserAssignationSerializer(serializers.ModelSerializer):
    """
    Serializer which assigns the fields with type CremeUserForeignKey
    referencing a given user A to another user B, then deletes A.
    """
    to_user = serializers.PrimaryKeyRelatedField(queryset=CremeUser.objects.none())

    class Meta:
        model = CremeUser
        fields = ['to_user']

    def __init__(self, instance=None, **kwargs):
        super().__init__(instance=instance, **kwargs)
        if instance is not None:
            users = CremeUser.objects.exclude(pk=instance.pk).exclude(is_staff=True)
            self.fields['to_user'].queryset = users

    def save(self, **kwargs):
        CremeUserForeignKey._TRANSFER_TO_USER = self.validated_data['to_user']

        try:
            self.instance.delete()
        finally:
            CremeUserForeignKey._TRANSFER_TO_USER = None


class UserRoleSerializer(serializers.ModelSerializer):
    # allowed_apps = serializers.CharField(many=True)
    # admin_4_apps = serializers.CharField(many=True)
    class Meta:
        model = UserRole
        fields = [
            "id",
            "name",
            "creatable_ctypes",
            "exportable_ctypes",
            "allowed_apps",
            "admin_4_apps",
        ]


class SetCredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SetCredentials
        fields = [
            "id",
            "role",
            "value",
            "set_type",
            "ctype",
            "forbidden",
            "efilter",
        ]


class SandboxSerializer(serializers.ModelSerializer):
    """Readonly"""
    class Meta:
        model = Sandbox
        fields = [
            "id",
            "uuid",
            "type_id",
            "role",
            "user",
        ]
