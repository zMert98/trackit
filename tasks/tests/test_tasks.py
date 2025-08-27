from re import template
from venv import create

import pytest

from tasks.factory import UserFactory, TemplateTaskFactory
from tasks.models import Tags, Tasks, TemplateTasks, TemplateTaskItem


@pytest.mark.django_db
class TestTasks:
    def test_create_task(self, user):
        task = Tasks.objects.create(
            name="test_task", description="test_description", user=user
        )

        assert Tasks.objects.filter(id=task.id).exists()

    def test_create_task_with_tags(self, api_client, user, task_data):
        api_client.force_authenticate(user)
        data_json, tags = task_data
        post_response_u = api_client.post("/api/v1/tasks/", data_json, format="json")
        assert post_response_u.status_code == 201

        id_task = post_response_u.data["id"]
        get_response_u = api_client.get(f"/api/v1/tasks/{id_task}/")
        assert get_response_u.status_code == 200
        item = get_response_u.data["results"]["items"]
        assert "tags" in item[0]
        assert item[0]["tags"] == tags

        tags_in_db = list(Tags.objects.values_list("name", flat=True))

        assert tags == tags_in_db

    def test_access_to_other_tasks(self, user, user1, api_client, task_data):
        api_client.force_authenticate(user)
        data_json, _ = task_data
        post_response_u = api_client.post("/api/v1/tasks/", data_json, format="json")
        assert post_response_u.status_code in [200, 201]
        id_task = post_response_u.data["id"]
        get_response_u = api_client.get(f"/api/v1/tasks/{id_task}/")
        assert get_response_u.status_code in [200, 201]
        item_id = get_response_u.data["results"]["items"][0]["id"]
        api_client.logout()
        api_client.force_authenticate(user1)

        assert len(post_response_u.data) > 0
        get_response_u1 = api_client.get(f"/api/v1/tasks/{id_task}/")
        assert get_response_u1.status_code in [403, 404]
        get_response_u1 = api_client.get(f"/api/v1/tasks/{id_task}/items/{item_id}/")
        assert get_response_u1.status_code in [403, 404]

    def test_access_to_other_tags(self, user, user1, api_client, task_data):
        api_client.force_authenticate(user)
        data_json, _ = task_data
        api_client.post("/api/v1/tasks/", data_json, format="json")
        api_client.logout()
        api_client.force_authenticate(user1)
        get_response_u1 = api_client.get("/api/v1/tasks/tags/")

        assert [] == get_response_u1.data

    def test_update_task_item(self, user, api_client, task_data):
        api_client.force_authenticate(user)
        data_json, _ = task_data
        response = api_client.post("/api/v1/tasks/", data_json, format="json")
        assert response.status_code in [200, 201]
        id_task = response.data["id"]

        task_item = Tasks.objects.get(id=id_task).items.all()[0]

        response = api_client.patch(
            f"/api/v1/tasks/{id_task}/",
            {"items": [{"id": task_item.id, "name": "билебердаберду"}]},
            format="json",
        )

        assert response.status_code in [200, 201]
        task_item = Tasks.objects.get(id=id_task).items.all()[0]
        assert task_item.name == "билебердаберду"

    def test_update_status_endpoint_many(self, user, api_client, task_data_many_items):
        api_client.force_authenticate(user)
        response = api_client.post(
            "/api/v1/tasks/", task_data_many_items, format="json"
        )
        assert response.status_code in [200, 201]
        task = Tasks.objects.get(id=response.data["id"])
        item_task1 = task.items.all()[0]
        item_task2 = task.items.all()[1]

        response = api_client.post(
            f"/api/v1/tasks/{task.id}/update_status/",
            data={
                "updates": [
                    {"id": item_task1.id, "status": "completed"},
                    {"id": item_task2.id, "status": "completed"},
                ]
            },
            format="json",
        )
        assert response.status_code in [200, 201]

        response = api_client.get(f"/api/v1/tasks/{task.id}/")

        for item in response.data["results"]["items"]:
            assert item["status"] == "completed"

    def test_search_params(self, user, api_client, task_data_many_task):
        api_client.force_authenticate(user)
        task1, task2 = task_data_many_task
        api_client.post("/api/v1/tasks/", task1, format="json")
        api_client.post("/api/v1/tasks/", task2, format="json")

        get_response_u = api_client.get("/api/v1/tasks/?search=Задача 1")

        assert len(get_response_u.data) > 0
        get_response_u = api_client.get("/api/v1/tasks/?search=Задача 2")
        assert len(get_response_u.data) > 0

    def test_filter_params(self, user, api_client, task_data_many_task):
        api_client.force_authenticate(user)

        response = api_client.post(
            "/api/v1/tasks/", data=task_data_many_task[0], format="json"
        )
        assert response.status_code in [200, 201]
        response = api_client.post(
            "/api/v1/tasks/", data=task_data_many_task[1], format="json"
        )
        assert response.status_code in [200, 201]

        response = api_client.get("/api/v1/tasks/?ordering=-name")
        assert response.status_code in [200, 201]
        assert response.data[0]["name"] == "Задача 2"

        response = api_client.get("/api/v1/tasks/?ordering=name")
        assert response.status_code in [200, 201]
        assert response.data[0]["name"] == "Задача 1"


@pytest.mark.django_db
class TestTemplateTasks:
    def test_create_template(self, user, api_client, task_data_many_items):
        api_client.force_authenticate(user)

        response = api_client.post('/api/v1/template/', data=task_data_many_items, format="json")
        assert response.status_code in [200, 201]

        name_template_task = response.data['name']
        qs = TemplateTasks.objects.filter(name=name_template_task)
        assert qs.exists()

    def test_update_template(self, user, api_client):
        template_task = TemplateTaskFactory(created_by=user)
        api_client.force_authenticate(user)
        response = api_client.patch(f'/api/v1/template/{template_task.id}/', data={"name":"111"}, format="json")
        assert response.status_code in [200, 201]
        template_task = TemplateTasks.objects.get(id=template_task.id)
        assert template_task.name == response.data['name']


    def test_delete_template(self, user, api_client):
        template_task = TemplateTaskFactory(created_by=user)
        api_client.force_authenticate(user)
        response = api_client.delete(f'/api/v1/template/{template_task.id}/', format='json')
        assert response.status_code == 204
        qs = TemplateTasks.objects.filter(id=template_task.id)
        assert not qs.exists()

    def test_update_task_another_person(self, user, api_client):
        template_task = TemplateTaskFactory.create()
        template_task_id = template_task.id
        template_sub_task_id = template_task.items.all()[0].id

        api_client.force_authenticate(user)
        response = api_client.patch(f'/api/v1/template/{template_task_id}/',
                                    data={"name": "111"},
                                    format='json')
        assert response.status_code == 403
        assert TemplateTaskItem.objects.get(id=template_sub_task_id).name != "111"

    def test_get_task_item_another_person(self, user, api_client):
        template_task = TemplateTaskFactory.create()
        template_task_id = template_task.id
        template_sub_task_id = template_task.items.all()[0].id

        api_client.force_authenticate(user)
        response = api_client.get(f'/api/v1/template/{template_task_id}/items/{template_sub_task_id}/', format='json')
        assert response.status_code == 200

    def test_update_task_item_another_person(self, user, api_client):
        template_task = TemplateTaskFactory.create()
        template_task_id = template_task.id
        template_sub_task_id = template_task.items.all()[0].id

        api_client.force_authenticate(user)
        response = api_client.patch(f'/api/v1/template/{template_task_id}/items/{template_sub_task_id}/',
                                    data={"name": "111"},
                                    format='json')
        assert response.status_code == 403
        assert TemplateTaskItem.objects.get(id=template_sub_task_id).name != "111"





