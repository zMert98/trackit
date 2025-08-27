> *Task Tracker API — Demo project for skill demonstration*
## Название проекта: Trackit

---

## Описание:

**REST API приложение** для управления задачами с поддержкой регистрации, JWT аутентификации, восстановления пароля через email, CRUD, пагинацией и создания задач на основе шаблонов.

---

## Стек технологий:

* **Backend:** Django Rest Framework (API-only)
* **База данных:** PostgreSQL
* **Кэш:** Redis 
* **Очереди**: Celery 
* **Аутентификация:** Simple JWT, регистрация, сброс пароля через email
* **Контейнеризация**: Docker + docker compose
* **Тестирование:** pytest 
* **CI/CD:** GitHub Actions 
* **Веб-сервер**: Nginx
* **Контроль версий:** Git 

---

## Запуск проекта:

* Создать .env с переменными окружения:
```
	 SECRET_KEY=<your_secret_key>
	 DEBUG=True
	 DB_NAME=trackitdb
	 DB_USER=trackit_root
	 DB_PASSWORD=<your_password>
	 DB_HOST=db
	 DB_PORT=5432
	 DJANGO_SETTINGS_MODULE=trackit.settings
	 PASSWORD_RESET_BASE_URL='password-reset/'
	 CELERY_BROKER=redis://redis:6379/0
	 CELERY_BACKEND=redis://redis:6379/1
```
* Создать .env.db с следующими переменными окружения:
```
	 POSTGRES_DB=trackitdb
	 POSTGRES_USER=trackit_root
	 POSTGRES_PASSWORD=<your_password>
```
*  Создать и поднять контейнеры `docker compose up --build` 
*  Запуск тестов (опционально) `docker exec -it trackit_app pytest`

---

## Примечания:

- Redis используется для простого кеширования шаблонов задач (статические данные), которые автоматически удаляются при изменении/удалении.
    
- Celery выполняет фоновые задачи: отправку писем и ежедневную очистку чёрного списка access токенов JWT.
    
- Тесты (29 интеграционных) покрывают ключевые сценарии работы с пользователями, задачами и шаблонами (регистрация, аутентификация, восстановление пароля через email, CRUD операций, фильтры, права доступа и обновление статусов задач). не все кейсы могут быть охвачены.
    
- CI/CD реализован простым пайплайном: сборка образа, прогон тестов и линтер (flake8).
    
- Nginx настроен очень просто, используется для проксирования запросов к нескольким контейнерам.
