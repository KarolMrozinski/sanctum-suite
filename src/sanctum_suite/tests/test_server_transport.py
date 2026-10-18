import pytest

from sanctum_suite import main


def test_loopback_host_detection():
    assert main._is_loopback_bind_host("127.0.0.1")
    assert main._is_loopback_bind_host("::1")
    assert main._is_loopback_bind_host("localhost")
    assert not main._is_loopback_bind_host("0.0.0.0")
    assert not main._is_loopback_bind_host("api.example.com")


def test_api_server_rejects_remote_plaintext_bind(monkeypatch):
    monkeypatch.delenv("SANCTUM_TLS_CERT_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_TLS_KEY_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_TRUST_TLS_TERMINATION_PROXY", raising=False)
    with pytest.raises(main.typer.BadParameter, match="requires TLS files"):
        main.start_api_server("0.0.0.0", 8000)


def test_api_server_allows_plaintext_bind_only_with_proxy_approval(monkeypatch):
    monkeypatch.delenv("SANCTUM_TLS_CERT_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_TLS_KEY_FILE", raising=False)
    monkeypatch.setenv("SANCTUM_TRUST_TLS_TERMINATION_PROXY", "true")
    captured = {}
    monkeypatch.setattr(main.uvicorn, "run", lambda *args, **kwargs: captured.update(kwargs))

    main.start_api_server("0.0.0.0", 8000)

    assert captured["ssl_certfile"] is None
    assert captured["ssl_keyfile"] is None


def test_api_server_supplies_tls_files_to_uvicorn(monkeypatch, tmp_path):
    certificate = tmp_path / "cert.pem"
    private_key = tmp_path / "key.pem"
    certificate.write_text("test certificate")
    private_key.write_text("test private key")
    monkeypatch.setenv("SANCTUM_TLS_CERT_FILE", str(certificate))
    monkeypatch.setenv("SANCTUM_TLS_KEY_FILE", str(private_key))
    captured = {}
    monkeypatch.setattr(main.uvicorn, "run", lambda *args, **kwargs: captured.update(kwargs))

    main.start_api_server("0.0.0.0", 8000)

    assert captured["ssl_certfile"] == str(certificate)
    assert captured["ssl_keyfile"] == str(private_key)
