"""Test del backup DB (routes/backup.py) senza DB né pg_dump: coprono la
guardia admin, il fail-loud sul volume mancante, e la logica di rotazione/
elenco (pura, su file finti). Il round-trip dump->restore si verifica su un
Postgres vero, non in CI."""
import os
import flask
import pytest

import routes.backup as backup


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "segreto-test")
    app = flask.Flask(__name__)
    app.register_blueprint(backup.bp)
    return app.test_client()


def test_backup_senza_secret_403(client):
    assert client.get("/admin/backup-grafo").status_code == 403
    assert client.get("/admin/backup-grafo?s=sbagliato").status_code == 403
    assert client.get("/admin/backup-grafo/lista").status_code == 403


def test_backup_fail_closed_senza_admin_secret(monkeypatch):
    # ADMIN_SECRET assente -> nega sempre, anche con ?s= vuoto
    monkeypatch.delenv("ADMIN_SECRET", raising=False)
    app = flask.Flask(__name__)
    app.register_blueprint(backup.bp)
    c = app.test_client()
    assert c.get("/admin/backup-grafo?s=").status_code == 403


def test_lista_volume_mancante_503(client, monkeypatch):
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    monkeypatch.delenv("BACKUP_DIR", raising=False)
    r = client.get("/admin/backup-grafo/lista?s=segreto-test")
    assert r.status_code == 503


def test_dir_backup_segue_env(monkeypatch, tmp_path):
    monkeypatch.delenv("BACKUP_DIR", raising=False)
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(tmp_path))
    d = backup._dir_backup()
    assert d == os.path.join(str(tmp_path), "backup")
    assert os.path.isdir(d)
    # fallback su BACKUP_DIR se il mount Railway manca
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "alt"))
    d2 = backup._dir_backup()
    assert d2 == os.path.join(str(tmp_path / "alt"), "backup")
    # nessuno dei due -> None (il chiamante fa fail-loud)
    monkeypatch.delenv("BACKUP_DIR", raising=False)
    assert backup._dir_backup() is None


def test_rotazione_tiene_ultimi_n(tmp_path):
    d = str(tmp_path)
    nomi = ["matter-20260101-000000.dump", "matter-20260102-000000.dump",
            "matter-20260103-000000.dump", "matter-20260104-000000.dump"]
    for n in nomi:
        open(os.path.join(d, n), "w").close()
    cancellati = backup._ruota(d, 2)
    rimasti = sorted(x["file"] for x in backup._elenco(d))
    assert rimasti == ["matter-20260103-000000.dump", "matter-20260104-000000.dump"]
    assert set(cancellati) == {"matter-20260101-000000.dump", "matter-20260102-000000.dump"}


def test_elenco_ignora_file_estranei(tmp_path):
    d = str(tmp_path)
    open(os.path.join(d, "matter-20260105-120000.dump"), "w").close()
    open(os.path.join(d, "note.txt"), "w").close()
    open(os.path.join(d, "matter-cattivo.dump"), "w").close()  # nome non conforme
    files = [x["file"] for x in backup._elenco(d)]
    assert files == ["matter-20260105-120000.dump"]
