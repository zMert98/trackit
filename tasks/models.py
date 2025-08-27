from django.contrib.auth import get_user_model
from django.db import models


class AbstractTaskBase(models.Model):
    name = models.CharField(blank=True, max_length=256, verbose_name="Name")

    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        abstract = True

    @property
    def owner(self):
        return getattr(self, "user", getattr(self, "created_by", None))

class AbstractTaskItem(models.Model):
    class StatusChoices(models.TextChoices):
        IN_PROCESS = "process", "In Process"
        COMPLETED = "completed", "Completed"

    name = models.CharField(max_length=256, verbose_name="Name", default="temp")

    description = models.TextField(blank=True, verbose_name="Description")

    status = models.CharField(
        max_length=10,
        choices=StatusChoices,
        default=StatusChoices.IN_PROCESS,
        verbose_name="Status",
    )

    planned_date = models.DateField(null=True, blank=True, verbose_name="Planned date")

    class Meta:
        abstract = True


class TemplateTasks(AbstractTaskBase):
    created_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Шаблон задачи"
        verbose_name_plural = "Шаблоны задач"


class TemplateTaskItem(AbstractTaskItem):
    task = models.ForeignKey(
        "TemplateTasks", on_delete=models.CASCADE, related_name="items"
    )
    tags = models.ManyToManyField(
        "Tags", blank=True, verbose_name="Tags", related_name="templatetasks"
    )


class Tasks(AbstractTaskBase):
    template = models.ForeignKey(
        "TemplateTasks", on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Time_create")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Time_update")

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        verbose_name="Owner",
        related_name="tasks",
    )

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name or "Untitled Task"


class TaskItem(AbstractTaskItem):
    task = models.ForeignKey(
        "Tasks", on_delete=models.CASCADE, verbose_name="Task", related_name="items"
    )
    tags = models.ManyToManyField(
        "Tags", blank=True, verbose_name="Tags", related_name="tasks"
    )

    class Meta:
        verbose_name = "Подзадача"
        verbose_name_plural = "Подзадачи"

    def __str__(self):
        return self.name


class Tags(models.Model):
    name = models.CharField(max_length=24, unique=True)
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        verbose_name="Owner",
        related_name="tags",
    )

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ["name"]

    def __str__(self):
        return self.name
