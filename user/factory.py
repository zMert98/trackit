import factory
from django.contrib.auth import get_user_model

from tasks.models import TaskItem, Tasks


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "defaultpassword123")
    is_active = True


class TaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tasks
        skip_postgeneration_save = True

    name = factory.Faker("sentence")
    description = factory.Faker("text")
    user = factory.SubFactory(UserFactory)

    @factory.post_generation
    def items(self, create, extracted, **kwargs):
        if not create:
            # объект не сохраняется в базе, пропускаем
            return

        if extracted:
            # если передали список подзадач — создаём их
            for item_data in extracted:
                TaskItemFactory(task=self, **item_data)
        else:
            # или создаём дефолтную подзадачу
            TaskItemFactory(task=self)


class TaskItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaskItem
        skip_postgeneration_save = True

    name = factory.Faker("sentence")
    description = factory.Faker("text")
    planned_date = factory.Faker("date")
    task = factory.SubFactory(TaskFactory)
