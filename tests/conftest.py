"""Shared pytest fixtures for the formflow test suite."""
import os

import pytest
from flask import Flask

from formflow.config import AppSettings
from formflow.form_engine import FormEngine


@pytest.fixture
def config():
    """Returns a default AppSettings config as a dict."""
    return AppSettings().model_dump()


@pytest.fixture
def cwd_tmp(tmp_path, monkeypatch):
    """Changes CWD to tmp_path for the duration of the test; returns tmp_path."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def app(cwd_tmp, config):
    """Flask test app with formflow config set (no routes registered yet)."""
    flask_app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "formflow", "templates"),
    )
    flask_app.config["TESTING"] = True
    flask_app.config["formflow"] = config
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client for the app fixture."""
    return app.test_client()


@pytest.fixture
def engine(config):
    """FormEngine without app binding (suitable for unit tests)."""
    return FormEngine(forms_dir="forms", config=config)


@pytest.fixture
def engine_with_app(app, config):
    """FormEngine bound to the app fixture via init_app (for integration tests)."""
    eng = FormEngine(forms_dir="forms", config=config)
    eng.init_app(app)
    return eng
