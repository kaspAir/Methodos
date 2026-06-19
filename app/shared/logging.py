import logging


def configure_logging(app):
    logging.basicConfig(
        level=logging.DEBUG if app.config.get("DEBUG") else logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )


def register_request_logging(app):
    @app.after_request
    def log_request(response):
        app.logger.debug("%s %s -> %s", _safe_method(), _safe_path(), response.status_code)
        return response


def _safe_method():
    from flask import request
    return request.method


def _safe_path():
    from flask import request
    return request.path
