"""Normalize job work types from the job's location and notes text."""
import os
import re

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_file_dir = os.path.dirname(os.path.abspath(__file__))
_db_path = os.environ.get('DB_PATH', os.path.join(_file_dir, 'db', 'jobs.db'))
DB_PATH = _db_path if os.path.isabs(_db_path) else os.path.join(_file_dir, _db_path)

import sys
sys.path.insert(0, os.path.join(_file_dir, '..'))
from shared.infrastructure.process.logging_config import get_logger

log = get_logger('jobs.commands.normalize_locs')
import jobs.infrastructure.models.job_model
from jobs.infrastructure.models.job_model import JobModel

WORK_TYPE_PATTERNS = {
    'Remote': ['remote', 'fully remote', 'work from anywhere', 'work from home'],
    'Hybrid': ['hybrid', 'flexible', 'partial remote'],
    'On-site': ['on-site', 'onsite', 'in office', 'office'],
}


def detect_work_type(location_str, notes_str):
    text = (location_str or '').lower() + ' ' + (notes_str or '').lower()
    for work_type, patterns in WORK_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in text:
                return work_type
    return 'On-site'


def normalize_locations():
    engine = create_engine(f"sqlite:///{DB_PATH}")
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        rows = session.query(JobModel).filter(JobModel.deleted == 0).all()
        updated = 0
        for job in rows:
            location = job.location or ''
            notes = job.notes or ''
            detected_type = detect_work_type(location, notes)
            work_types = list(job.work_types or [])
            if detected_type not in work_types:
                work_types.append(detected_type)
                job.work_types = work_types
                updated += 1
        session.commit()
        log.info("Normalized work types", updated=updated)
    finally:
        session.close()
        engine.dispose()


if __name__ == '__main__':
    normalize_locations()
