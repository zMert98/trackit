from django.urls import include, path
from rest_framework import routers

from tasks.views import (TagsListCreateAPIView,
                         TaskItemRetrieveUpdateDestroyAPIView,
                         TemplateTaskViewSet, ViewSetTasks, TemplateTaskItemRetrieveUpdateDestroyAPIView)
from trackit import settings

app_name = "task"

tasks_router = routers.DefaultRouter()
tasks_router.register(r"tasks", ViewSetTasks, basename="task")

tasks_template_router = routers.DefaultRouter()
tasks_template_router.register(r"template", TemplateTaskViewSet, basename='template_task')

urlpatterns = [
    path("tasks/tags/", TagsListCreateAPIView.as_view()),
path(
        "template/<int:task_id>/items/<int:pk>/", TemplateTaskItemRetrieveUpdateDestroyAPIView.as_view()
    ),

    path(
        "tasks/<int:task_id>/items/<int:pk>/", TaskItemRetrieveUpdateDestroyAPIView.as_view()
    ),
    path("", include(tasks_template_router.urls)),
    path("", include(tasks_router.urls)),


]
