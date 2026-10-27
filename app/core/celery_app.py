"""
Instância Celery do Zarpou Backend.

Usada para tarefas assíncronas de longa duração (ex.: importação em massa de
catálogo a partir de CSV/Excel) que não podem rodar no ciclo da requisição
HTTP (risco de timeout 504 em arquivos grandes).

Para rodar o worker (obrigatório em produção/dev para processar as tarefas):

    celery -A app.core.celery_app.celery_app worker -l info --pool=solo

(--pool=solo no Windows; em Linux use o default prefork.)

O broker/result backend aponta para o Redis (settings.REDIS_URL). Sem Redis
disponível, o enqueue falha com erro claro (a feature de importação responde
503 com instrução).
"""
from celery import Celery

from app.core.config import settings

_broker = settings.CELERY_BROKER_URL or settings.REDIS_URL
_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app = Celery(
    "zarpou",
    broker=_broker,
    backend=_backend,
    include=["app.features.imports.app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Tarefas de importação podem demorar minutos em arquivos grandes
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    broker_connection_retry_on_startup=True,
)
