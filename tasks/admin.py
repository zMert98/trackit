from django.contrib import admin
from django.db.models import Count

from tasks.models import Tags, TaskItem, Tasks, TemplateTaskItem, TemplateTasks


# Register your models here.
class BaseTaskItemInline(admin.TabularInline):
    model = TaskItem
    extra = 1
    classes = ["collapse", "wide"]


class TaskItemInline(BaseTaskItemInline):
    model = TaskItem


class TaskItemTemplateInline(BaseTaskItemInline):
    model = TemplateTaskItem


@admin.register(Tasks)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "description", "item_count"]
    list_display_links = ["name"]
    readonly_fields = ["created_at", "updated_at", "item_count"]
    search_fields = ["id", "name", "description"]
    exclude = ["user"]
    inlines = [TaskItemInline]
    actions = ["create_template_from_task"]

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj is not None:
            fields = [f for f in fields if f != "template"]
        else:
            fields = [
                f for f in fields if f not in ("created_at", "updated_at", "item_count")
            ]
        return fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(item_count=Count("items"))

    def save_model(self, request, obj, form, change):
        cleaned_data = form.cleaned_data
        template = cleaned_data.get("template")
        if not change:
            obj.user = request.user
            if template:
                obj.name = template.name
                obj.description = template.description
                obj.save()

                for item in template.items.all():
                    task_item = TaskItem()
                    task_item.name = item.name
                    task_item.description = item.description
                    task_item.planned_date = item.planned_date
                    task_item.task = obj
                    task_item.save()
                    tag_names = item.tags.values_list("name", flat=True)

                    tag_objs = []

                    for tag_name in tag_names:
                        tag_obj, _ = Tags.objects.get_or_create(
                            name=tag_name, user=obj.user
                        )
                        tag_objs.append(tag_obj)

                    task_item.tags.set(tag_objs)

        return super().save_model(request, obj, form, change)

    @admin.display(description="Количество подзадач", ordering="item_count")
    def item_count(self, obj):
        return obj.item_count()

    @admin.action(description="Создать шаблон из выбранных задач")
    def create_template_from_task(self, request, queryset):
        for task in queryset:
            template = TemplateTasks.objects.create(
                name=task.name, description=task.description, created_by=task.user
            )
            for item in task.items.all():
                task_item = TemplateTaskItem.objects.create(
                    name=item.name,
                    description=item.description,
                    planned_date=item.planned_date,
                    task=template,
                )

                tag_objs = []
                for tag_name in item.tags.values_list("name", flat=True):
                    tag_obj, _ = Tags.objects.get_or_create(
                        name=tag_name, user=task.user
                    )
                    tag_objs.append(tag_obj)
                task_item.tags.set(tag_objs)


@admin.register(TaskItem)
class TaskItemAdmin(admin.ModelAdmin):
    list_display = ["task__name", "name", "status"]
    list_editable = ["status"]
    search_fields = ["task__name", "name"]
    list_filter = ["task__name", "status"]
    filter_horizontal = ["tags"]
    actions = ["mark_as_completed", "mark_as_in_process"]

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj is not None:
            fields = [f for f in fields if f != "task"]
        return fields

    @admin.action(description="Пометить как завершённые")
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status=TaskItem.StatusChoices.COMPLETED)
        self.message_user(request, f"{updated} задач(и) помечены как завершённые.")

    @admin.action(description="Пометить как в процессе")
    def mark_as_in_process(self, request, queryset):
        updated = queryset.update(status=TaskItem.StatusChoices.IN_PROCESS)
        self.message_user(request, f"{updated} задач(и) помечены как в процессе.")


@admin.register(TemplateTasks)
class TemplateTasksAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "description", "item_count", "created_by__username"]
    list_filter = ["created_by__username"]
    list_display_links = ["name"]
    inlines = [TaskItemTemplateInline]
    exclude = ["created_by"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(item_count=Count("items"))

    @admin.display(description="Количество подзадач", ordering="item_count")
    def item_count(self, obj):
        return obj.item_count()


@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    exclude = ["user"]
