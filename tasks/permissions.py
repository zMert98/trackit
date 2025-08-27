from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class TemplateIsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        try:
            if view.action == "create_from_template" and request.method == "POST":
                return True
        except AttributeError:
            pass

        if hasattr(obj, "task"):
            owner = obj.task.created_by
        else:
            owner = obj.created_by

        return owner == request.user