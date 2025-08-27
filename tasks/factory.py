import factory
from django.contrib.auth import get_user_model

from tasks.models import TemplateTasks, TemplateTaskItem


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "defaultpassword123")
    is_active = True


class TemplateTaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TemplateTasks
        skip_postgeneration_save = True

    name = factory.Faker("sentence")
    description = factory.Faker("text")
    created_by = factory.SubFactory(UserFactory)


    @factory.post_generation
    def items(self, create, extracted, **kwargs):
        if not create:
            # объект не сохраняется в базе, пропускаем
            return

        if extracted:
            # если передали список подзадач — создаём их
            for item_data in extracted:
                TemplateTaskItemFactory(task=self, **item_data)
        else:
            # или создаём дефолтную подзадачу
            TemplateTaskItemFactory(task=self)


class TemplateTaskItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TemplateTaskItem

    name = factory.Faker("sentence")
    description = factory.Faker("text")
    planned_date = factory.Faker("date")
    task = factory.SubFactory(TemplateTaskFactory)
