from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "farming_assistant",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "generate-daily-reports": {
            "task": "app.workers.tasks.generate_daily_reports_task",
            "schedule": crontab(hour=6, minute=0),
        },
    },
)
