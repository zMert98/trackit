import os

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from django_redis import get_redis_connection
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from tasks.filters import DateFilterBackend
from tasks.models import Tags, TaskItem, Tasks, TemplateTasks, AbstractTaskItem, TemplateTaskItem
from tasks.permissions import IsOwner, TemplateIsOwnerOrReadOnly
from tasks.serializer import (TagSerializer, TaskItemSerializer,
                              TaskSerializer, TemplateTaskSerializer, TemplateTaskItemSerializer)


# Create your views here.
def create_task_from_template(template: TemplateTasks, user: get_user_model()) -> Tasks:
    task = Tasks.objects.create(
        user=user,
        name=template.name,
        description=template.description,
        template=template,
    )

    for item in template.items.all():
        TaskItem.objects.create(
            name=item.name,
            description=item.description,
            planned_date=item.planned_date,
            task=task,
        )

    return task


class TaskItemPagination(PageNumberPagination):
    page_size = 2
    page_query_param = "items_page"


class TaskPagination(PageNumberPagination):
    page_size = 5


class TemplateTaskViewSet(viewsets.ModelViewSet):
    serializer_class = TemplateTaskSerializer
    permission_classes = [IsAuthenticated, TemplateIsOwnerOrReadOnly]


    def get_queryset(self):

        return TemplateTasks.objects.select_related(
            'created_by',
        ).prefetch_related('items').all()

    @action(methods=["post", "get"], detail=True)
    def create_from_template(self, request, pk=None):

        if request.method == 'GET':

            return self.retrieve(request)

        elif request.method == 'POST':
            template = self.get_object()
            task = create_task_from_template(template, user=request.user)
            serializer = TaskSerializer(task)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        template_id = kwargs.get("pk")
        page_number = request.query_params.get("items_page", 1)
        cache_key = f"template_tasks:{template_id}:page:{page_number}"

        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)

        template = self.get_object()
        items_qs = template.items.all().order_by("id")

        paginator = TaskItemPagination()
        paginated_items = paginator.paginate_queryset(items_qs, request)

        task_data = self.get_serializer(template).data
        task_data["items"] = TemplateTaskItemSerializer(paginated_items, many=True).data
        cache.set(cache_key, task_data, timeout=300)


        return paginator.get_paginated_response(task_data)

    def list(self, request, *args, **kwargs):
        cache_key = f"template_tasks_list"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        qs = self.filter_queryset(
            self.get_queryset().annotate(items_count=Count("items"))
        )
        serialized = self.get_serializer(qs, many=True).data
        cache.set(cache_key, serialized)
        return Response(serialized)

    @staticmethod
    def delete_pattern(redis, pattern):
        """Удаляет все ключи по шаблону."""
        for key in redis.scan_iter(pattern):
            redis.delete(key)

    def perform_update(self, serializer):
        instance = serializer.save()
        redis = get_redis_connection("default")

        self.delete_pattern(redis, f"template_tasks:{instance.pk}:page:*")
        redis.delete("template_tasks:list")

        return instance

    def perform_destroy(self, instance):
        redis = get_redis_connection("default")

        self.delete_pattern(redis, f"template_tasks:{instance.pk}:page:*")
        redis.delete("template_tasks:list")

        return instance.delete()

class ViewSetTasks(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        DateFilterBackend,
        filters.SearchFilter,
    ]
    ordering_fields = ["name", "id"]
    search_fields = ["name"]

    def get_queryset(self):
        return Tasks.objects.select_related(
            'user', 'template'
        ).prefetch_related('items').filter(user=self.request.user)

    @action(methods=["post", "get"], detail=True)
    def update_status(self, request, pk=None):
        if request.method == 'GET':
            task = self.get_object()
            current_statuses = {status_item: [] for status_item in AbstractTaskItem.StatusChoices.values}
            for id, status_item in frozenset(task.items.values_list('id', 'status')):
                current_statuses[status_item].append(id)

            return Response({'id_task_and_current_status': current_statuses})

        elif request.method == 'POST':

            updates = request.data.get("updates")

            if not isinstance(updates, list) or not updates:
                return Response(
                    {"error": "subtask_ids must be a list"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            task = self.get_object()
            valid_id = frozenset(task.items.values_list('id', flat=True))
            updated_data = {status_item: [] for status_item in AbstractTaskItem.StatusChoices.values}
            not_found = []

            for on_update in updates:
                id = on_update.get("id")
                new_status = on_update.get("status")

                if new_status not in AbstractTaskItem.StatusChoices:
                    return Response(
                        {"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST
                    )

                if id not in valid_id:
                    not_found.append(id)
                    continue

                updated_data[new_status].append(id)

            with transaction.atomic():
                update_successfully = []
                for status_item, ids in updated_data.items():
                    task.items.filter(id__in=ids).update(status=status_item)
                    update_successfully.extend(ids)

            return Response({"updated": update_successfully, "not_found": not_found})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        updated_instance = serializer.save()
        updated_item_ids = serializer.updated_items_ids
        response_data = self.get_serializer(updated_instance).data

        return Response(
            {
                "message": "Обновление успешно",
                "updated_items": updated_item_ids,
                "task": response_data,
            },
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        items_qs = task.items.all().order_by("id")

        paginator = TaskItemPagination()
        paginated_items = paginator.paginate_queryset(items_qs, request)

        task_data = self.get_serializer(task).data
        task_data["items"] = TaskItemSerializer(paginated_items, many=True).data

        return paginator.get_paginated_response(task_data)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(
            self.get_queryset().prefetch_related('items').annotate(items_count=Count("items"))
        )
        serialized = self.get_serializer(qs, many=True).data

        return Response(serialized)


class TaskItemRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TaskItemPagination

    def get_queryset(self):
        return TaskItem.objects.select_related('task', 'task__user').prefetch_related('tags').filter(
            task__user=self.request.user, task_id=self.kwargs["task_id"]
        )


class TaskItemRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TaskItemPagination

    def get_queryset(self):
        return TaskItem.objects.select_related('task', 'task__user').prefetch_related('tags').filter(
            task__user=self.request.user, task_id=self.kwargs["task_id"]
        )


class TemplateTaskItemRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TemplateTaskItemSerializer
    permission_classes = [IsAuthenticated, TemplateIsOwnerOrReadOnly]
    pagination_class = TaskItemPagination

    def get_queryset(self):
        return TemplateTaskItem.objects.select_related('task', 'task__created_by').prefetch_related('tags').filter(
            task_id=self.kwargs["task_id"]
            )


class TagsListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tags.objects.select_related('user').filter(user=self.request.user)
