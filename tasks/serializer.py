from rest_framework import serializers

from tasks.models import Tags, TaskItem, Tasks, TemplateTaskItem, TemplateTasks


class BaseTaskSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ["id", "name", "description", "items"]
        abstract = True

    def create_task(self, items_model, validated_data):
        items = validated_data.pop("items", [])
        task = self.Meta.model.objects.create(**validated_data)

        for item in items:
            self._create_task_item(task, items_model, item)

        return task

    @staticmethod
    def _create_task_item(task, items_model, items):

        tag_names = items.pop("tags_input", [])
        tag_objs = []
        for tag_name in tag_names:
            tag_obj, _ = Tags.objects.get_or_create(name=tag_name, user=task.owner)
            tag_objs.append(tag_obj)

        taskitem = items_model.objects.create(task=task, **items)
        taskitem.tags.set(tag_objs)

    def update_task(self, instance, items_model, validated_data):
        excluded_fields = ("id", "created_at", "updated_at", "template")
        updated_items_ids = []
        items = validated_data.pop("items", [])
        if self.partial:

            for key, value in validated_data.items():
                setattr(instance, key, value)

            for item_data in items:
                self._update_task_item(
                    instance, items_model, item_data, updated_items_ids
                )

        else:
            model_fields = {
                f.name for f in instance._meta.fields if f.name not in excluded_fields
            }
            if model_fields <= set(validated_data.keys()):
                for key, value in validated_data.items():
                    setattr(instance, key, value)

                if not items and type(items) is list:
                    instance.items.all().delete()
                else:
                    for item_data in items:
                        self._update_task_item(
                            instance, items_model, item_data, updated_items_ids
                        )

        self.updated_items_ids = updated_items_ids
        instance.save()
        return instance

    @staticmethod
    def _update_task_item(instance, items_model, item_data, updated_items_ids: list):
        existing_items = {item.id: item for item in instance.items.all()}
        id = item_data.get("id", None)
        tag_names = item_data.pop("tags_input", [])
        tag_objs = []

        for tag_name in tag_names:
            tag_obj, _ = Tags.objects.get_or_create(name=tag_name, user=instance.owner)
            tag_objs.append(tag_obj)

        if id in existing_items:
            obj = existing_items[id]
            updated_items_ids.append(id)
            for key, value in item_data.items():
                setattr(obj, key, value)
            obj.save()
            obj.tags.set(tag_objs)
        else:
            obj = items_model.objects.create(task=instance, **item_data)
            updated_items_ids.append(f"New item {obj.id}")
            obj.tags.set(tag_objs)

        return updated_items_ids


class BaseTaskItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    tags = serializers.SlugRelatedField(many=True, slug_field="name", read_only=True)

    tags_input = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        abstract = True
        fields = [
            "id",
            "name",
            "description",
            "status",
            "tags",
            "tags_input",
            "planned_date",
        ]

    @staticmethod
    def _update_task_item(instance, validated_data):
        tag_names = validated_data.pop("tags_input", [])
        tag_objs = set()

        for key, value in validated_data.items():
            setattr(instance, key, value)

        for tag_name in tag_names:
            tag_obj, _ = Tags.objects.get_or_create(
                name=tag_name, user=instance.task.owner
            )
            tag_objs.add(tag_obj)

        instance.tags.set(tag_objs)
        return instance


class TemplateTaskItemSerializer(BaseTaskItemSerializer):
    class Meta(BaseTaskItemSerializer.Meta):
        model = TemplateTaskItem

    def update(self, instance, validated_data):
        return self._update_task_item(instance, validated_data)


class TemplateTaskSerializer(BaseTaskSerializer):
    name = serializers.CharField(required=True)
    items = TemplateTaskItemSerializer(many=True, write_only=True, required=False)
    items_count = serializers.IntegerField(read_only=True, required=False)
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta(BaseTaskSerializer.Meta):
        model = TemplateTasks
        fields = BaseTaskSerializer.Meta.fields + ["created_by", "items_count"]

    def create(self, validated_data):
        return self.create_task(TemplateTaskItem, validated_data)

    def update(self, instance, validated_data):
        return self.update_task(instance, TemplateTaskItem, validated_data)


class TaskItemSerializer(BaseTaskItemSerializer):
    class Meta(BaseTaskItemSerializer.Meta):
        model = TaskItem

    def update(self, instance, validated_data):
        return self._update_task_item(instance, validated_data)


class TaskSerializer(BaseTaskSerializer):
    name = serializers.CharField(required=True)
    items = TaskItemSerializer(many=True, write_only=True, required=False)
    items_count = serializers.IntegerField(read_only=True, required=False)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta(BaseTaskSerializer.Meta):
        model = Tasks
        fields = BaseTaskSerializer.Meta.fields + ["items_count", "user"]

    def update(self, instance, validated_data):
        return self.update_task(instance, TaskItem, validated_data)

    def create(self, validated_data):
        return self.create_task(TaskItem, validated_data)


class TagSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Tags
        fields = ["name", "user"]
