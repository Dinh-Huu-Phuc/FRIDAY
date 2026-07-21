from __future__ import annotations

import threading

from friday.config import config
from friday.news import NewsService
from friday.trainModel import BatchTrainingScheduler, TrainModelConfig


_BATCH_SCHEDULER: BatchTrainingScheduler | None = None
_BATCH_SCHEDULER_LOCK = threading.Lock()


def build_train_model_config() -> TrainModelConfig:
    cfg = TrainModelConfig(
        auto_train_enabled=config.BATCH_TRAINING_ENABLED,
        auto_train_check_interval_seconds=config.BATCH_TRAINING_CHECK_INTERVAL_SEC,
        auto_train_daily_time_utc=config.BATCH_TRAINING_DAILY_TIME_UTC,
        auto_train_min_pending_samples=config.BATCH_TRAINING_MIN_PENDING_SAMPLES,
    )
    cfg.ensure_directories()
    return cfg


def build_news_service() -> NewsService:
    return NewsService(
        api_key=config.NEWSDATA_API_KEY,
        world_api_key=config.WORLD_NEWS,
        default_language=config.NEWS_DEFAULT_LANGUAGE,
        default_country=config.NEWS_DEFAULT_COUNTRY,
        default_limit=config.NEWS_DEFAULT_LIMIT,
        timeout_seconds=config.NEWS_REQUEST_TIMEOUT,
    )


def get_or_start_scheduler(train_cfg: TrainModelConfig) -> BatchTrainingScheduler:
    global _BATCH_SCHEDULER
    with _BATCH_SCHEDULER_LOCK:
        if _BATCH_SCHEDULER is None:
            _BATCH_SCHEDULER = BatchTrainingScheduler(train_cfg)
            _BATCH_SCHEDULER.start()
        return _BATCH_SCHEDULER

