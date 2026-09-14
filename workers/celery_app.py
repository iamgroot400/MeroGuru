from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from celery import Celery

from app.core.config import settings

celery_app = Celery("meroguru", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"])

import workers.tasks  # noqa: E402  (registers tasks with the app above)
