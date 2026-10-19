"""Tests for shared.infrastructure.database.backup_service."""

import sys
import os
from unittest.mock import MagicMock, mock_open, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

import shared.infrastructure.database.backup_service as backup


@pytest.fixture(autouse=True)
def _patch_config(tmp_path):
    """Point the backup service at a temp directory and known credentials."""
    with patch.object(backup, 'DB_BACKUP_DIR', str(tmp_path)), \
            patch.object(backup, 'DB_BACKUP_CONTAINER', 'job-search-postgres'), \
            patch.object(backup, 'DB_BACKUP_KEEP_COUNT', 3), \
            patch.object(backup, '_db_credentials', return_value=('jobsearch', 'jobsearch')):
        yield tmp_path


def _touch_backup(dir_path: str, name: str) -> str:
    path = os.path.join(dir_path, name)
    with open(path, 'w') as fh:
        fh.write('dump')
    return path


class TestCreateDbBackup:
    def test_runs_local_pg_dump_inside_container(self, _patch_config):
        def fake_run(*_args, **kwargs):
            kwargs['stdout'].write(b'PGDMP-data')
            return MagicMock(returncode=0, stderr=b'')

        with patch.object(backup, '_uses_local_pg_dump', return_value=True), \
                patch.object(backup, '_database_url',
                             return_value=backup.make_url(
                                 'postgresql+psycopg://jobsearch:secret@postgres:5432/jobsearch')), \
                patch('shared.infrastructure.database.backup_service.subprocess.run',
                      side_effect=fake_run) as m_run:
            path = backup.create_db_backup()

        args = m_run.call_args.args[0]
        assert args[0] == 'pg_dump'
        assert '--host' in args and args[args.index('--host') + 1] == 'postgres'
        assert '--port' in args and args[args.index('--port') + 1] == '5432'
        assert '--username' in args and args[args.index('--username') + 1] == 'jobsearch'
        assert '--dbname' in args and args[args.index('--dbname') + 1] == 'jobsearch'
        assert '--format=custom' in args
        assert m_run.call_args.kwargs['env']['PGPASSWORD'] == 'secret'
        assert os.path.basename(path).startswith('jobsearch_')
        assert path.endswith('.dump')

    def test_falls_back_to_docker_exec_on_host(self, _patch_config):
        def fake_run(*_args, **kwargs):
            kwargs['stdout'].write(b'PGDMP-data')
            return MagicMock(returncode=0, stderr=b'')

        with patch.object(backup, '_uses_local_pg_dump', return_value=False), \
                patch('shared.infrastructure.database.backup_service.subprocess.run',
                      side_effect=fake_run) as m_run:
            path = backup.create_db_backup()

        args = m_run.call_args.args[0]
        assert args[:2] == ['docker', 'exec']
        assert args[2] == 'job-search-postgres'
        assert args[3] == 'pg_dump'
        assert '-U' in args and args[args.index('-U') + 1] == 'jobsearch'
        assert '-d' in args and args[args.index('-d') + 1] == 'jobsearch'
        assert '--format=custom' in args
        assert m_run.call_args.kwargs['env'] is None
        assert os.path.basename(path).startswith('jobsearch_')
        assert path.endswith('.dump')

    def test_removes_file_and_raises_on_failure(self, _patch_config):
        with patch.object(backup, '_uses_local_pg_dump', return_value=False), \
                patch('shared.infrastructure.database.backup_service.subprocess.run',
                      return_value=MagicMock(returncode=1, stderr=b'connection refused')), \
                patch('builtins.open', mock_open()), \
                patch('shared.infrastructure.database.backup_service.os.remove') as m_remove:
            with pytest.raises(RuntimeError, match='pg_dump failed'):
                backup.create_db_backup()
        m_remove.assert_called_once()
        assert backup.list_backups() == []

    def test_missing_pg_dump_binary_raises_and_cleans_up(self, _patch_config):
        with patch.object(backup, '_uses_local_pg_dump', return_value=True), \
                patch('shared.infrastructure.database.backup_service.subprocess.run',
                      side_effect=FileNotFoundError('pg_dump')):
            with pytest.raises(RuntimeError, match='could not run pg_dump'):
                backup.create_db_backup()
        assert backup.list_backups() == []

    def test_empty_dump_is_removed_and_rejected(self, _patch_config):
        def fake_run(*_args, **kwargs):
            kwargs['stdout'].write(b'')
            return MagicMock(returncode=0, stderr=b'')

        with patch.object(backup, '_uses_local_pg_dump', return_value=True), \
                patch.object(backup, '_database_url',
                             return_value=backup.make_url(
                                 'postgresql+psycopg://jobsearch:secret@postgres:5432/jobsearch')), \
                patch('shared.infrastructure.database.backup_service.subprocess.run',
                      side_effect=fake_run):
            with pytest.raises(RuntimeError, match='empty dump'):
                backup.create_db_backup()
        assert backup.list_backups() == []


class TestListBackups:
    def test_returns_oldest_first(self, _patch_config):
        _touch_backup(_patch_config, 'jobsearch_20260803_100000.dump')
        _touch_backup(_patch_config, 'jobsearch_20260805_100000.dump')
        _touch_backup(_patch_config, 'jobsearch_20260804_100000.dump')
        names = [os.path.basename(p) for p in backup.list_backups()]
        assert names == [
            'jobsearch_20260803_100000.dump',
            'jobsearch_20260804_100000.dump',
            'jobsearch_20260805_100000.dump',
        ]

    def test_ignores_unrelated_files(self, _patch_config):
        _touch_backup(_patch_config, 'jobsearch_20260805_100000.dump')
        _touch_backup(_patch_config, 'notes.txt')
        assert len(backup.list_backups()) == 1


class TestPruneOldBackups:
    def test_keeps_only_three_most_recent(self, _patch_config):
        for name in (
            'jobsearch_20260801_100000.dump',
            'jobsearch_20260802_100000.dump',
            'jobsearch_20260803_100000.dump',
            'jobsearch_20260804_100000.dump',
            'jobsearch_20260805_100000.dump',
        ):
            _touch_backup(_patch_config, name)

        removed = backup.prune_old_backups(keep=3)

        remaining = {os.path.basename(p) for p in backup.list_backups()}
        assert remaining == {
            'jobsearch_20260803_100000.dump',
            'jobsearch_20260804_100000.dump',
            'jobsearch_20260805_100000.dump',
        }
        assert {os.path.basename(p) for p in removed} == {
            'jobsearch_20260801_100000.dump',
            'jobsearch_20260802_100000.dump',
        }

    def test_keep_zero_removes_everything(self, _patch_config):
        _touch_backup(_patch_config, 'jobsearch_20260805_100000.dump')
        removed = backup.prune_old_backups(keep=0)
        assert len(removed) == 1
        assert backup.list_backups() == []

    def test_no_files_removed_within_keep(self, _patch_config):
        _touch_backup(_patch_config, 'jobsearch_20260805_100000.dump')
        assert backup.prune_old_backups(keep=3) == []


class TestRunDbBackup:
    def test_summary(self, _patch_config):
        with patch.object(backup, 'create_db_backup', return_value='/tmp/backups/jobsearch_20260805_100000.dump') as m_create, \
                patch.object(backup, 'prune_old_backups', return_value=['/tmp/backups/jobsearch_20260801_100000.dump']) as m_prune:
            result = backup.run_db_backup()

        m_create.assert_called_once()
        m_prune.assert_called_once_with(3)
        assert result['created'] == '/tmp/backups/jobsearch_20260805_100000.dump'
        assert result['removed'] == ['/tmp/backups/jobsearch_20260801_100000.dump']
