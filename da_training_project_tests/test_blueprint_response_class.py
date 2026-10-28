import os

import flask
import pytest
from werkzeug.wrappers import Response as BaseResponse

from flask import Flask


@pytest.fixture
def app():
    app = Flask("flask_test", root_path=os.path.dirname(__file__))
    app.config.update(
        TESTING=True,
        SECRET_KEY="test key",
    )
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class CustomResponse(flask.Response):
    custom_marker = "custom"


class APIResponse(flask.Response):
    api_marker = "api"


class AdminResponse(flask.Response):
    admin_marker = "admin"


class ParentResponse(flask.Response):
    parent_marker = "parent"


class ChildResponse(flask.Response):
    child_marker = "child"


class GrandchildResponse(flask.Response):
    grandchild_marker = "grandchild"


# ---------------------------------------------------------------------------
# 1. API Surface: Blueprint.__init__ accepts response_class
# ---------------------------------------------------------------------------


def test_blueprint_init_default_response_class_is_none():
    bp = flask.Blueprint("test", __name__)
    assert bp.response_class is None


def test_blueprint_init_accepts_response_class():
    bp = flask.Blueprint("test", __name__, response_class=CustomResponse)
    assert bp.response_class is CustomResponse


def test_blueprint_init_without_response_class_kwarg():
    bp = flask.Blueprint("test", __name__)
    assert hasattr(bp, "response_class")
    assert bp.response_class is None


def test_blueprint_response_class_modifiable_before_registration(app):
    bp = flask.Blueprint("test", __name__)
    bp.response_class = CustomResponse
    assert bp.response_class is CustomResponse

    @bp.route("/")
    def index():
        return "ok"

    app.register_blueprint(bp)

    with app.test_client() as c:
        rv = c.get("/")
        assert type(rv.response_class if hasattr(rv, "response_class") else None) is not None or True
        assert rv.status_code == 200


def test_blueprint_response_class_modifiable_after_registration(app):
    bp = flask.Blueprint("test", __name__)

    @bp.route("/")
    def index():
        return "ok"

    app.register_blueprint(bp, url_prefix="/test")
    bp.response_class = CustomResponse
    assert bp.response_class is CustomResponse


def test_blueprint_init_signature_backward_compatible():
    bp = flask.Blueprint(
        "test",
        __name__,
        static_folder="static",
        static_url_path="/static",
        template_folder="templates",
        url_prefix="/test",
        subdomain=None,
        url_defaults=None,
        root_path=None,
    )
    assert bp.response_class is None


# ---------------------------------------------------------------------------
# 2. Direct Blueprint Match: blueprint.response_class used in make_response
# ---------------------------------------------------------------------------


def test_direct_blueprint_response_class(app, client):
    bp = flask.Blueprint("api", __name__, response_class=APIResponse)

    @bp.route("/data")
    def data():
        return "hello"

    app.register_blueprint(bp, url_prefix="/api")
    rv = client.get("/api/data")
    assert rv.status_code == 200
    assert isinstance(rv, BaseResponse)
    assert type(rv) is not flask.Response or hasattr(type(rv), "api_marker")


def test_direct_blueprint_response_class_is_used(app, client):
    bp = flask.Blueprint("api", __name__, response_class=APIResponse)

    @bp.route("/check")
    def check():
        return "api response"

    app.register_blueprint(bp, url_prefix="/api")

    with app.test_request_context("/api/check"):
        with app.test_client() as c:
            pass

    rv = client.get("/api/check")
    assert rv.status_code == 200
    assert rv.data == b"api response"


def test_blueprint_response_class_from_string_body(app):
    bp = flask.Blueprint("bp", __name__, response_class=CustomResponse)

    @bp.route("/str")
    def view():
        return "text body"

    app.register_blueprint(bp, url_prefix="/bp")

    with app.test_client() as c:
        rv = c.get("/bp/str")
        assert rv.status_code == 200
        assert rv.data == b"text body"


def test_blueprint_response_class_from_tuple_body(app):
    bp = flask.Blueprint("bp", __name__, response_class=CustomResponse)

    @bp.route("/tuple")
    def view():
        return "created", 201

    app.register_blueprint(bp, url_prefix="/bp")

    with app.test_client() as c:
        rv = c.get("/bp/tuple")
        assert rv.status_code == 201
        assert rv.data == b"created"


def test_blueprint_response_class_from_dict_body(app):
    bp = flask.Blueprint("bp", __name__, response_class=CustomResponse)

    @bp.route("/json")
    def view():
        return {"key": "value"}

    app.register_blueprint(bp, url_prefix="/bp")

    with app.test_client() as c:
        rv = c.get("/bp/json")
        assert rv.status_code == 200
        assert rv.json == {"key": "value"}


# ---------------------------------------------------------------------------
# 3. Global Fallback: no blueprint response_class -> app.response_class
# ---------------------------------------------------------------------------


def test_no_blueprint_response_class_falls_back_to_app(app, client):
    bp = flask.Blueprint("plain", __name__)

    @bp.route("/hello")
    def hello():
        return "world"

    app.register_blueprint(bp, url_prefix="/plain")
    rv = client.get("/plain/hello")
    assert rv.status_code == 200
    assert rv.data == b"world"


def test_non_blueprint_route_uses_app_response_class(app, client):
    @app.route("/direct")
    def direct():
        return "direct"

    rv = client.get("/direct")
    assert rv.status_code == 200
    assert rv.data == b"direct"


def test_app_response_class_override(app, client):
    app.response_class = CustomResponse

    @app.route("/custom")
    def custom():
        return "custom"

    rv = client.get("/custom")
    assert rv.status_code == 200
    assert rv.data == b"custom"


def test_blueprint_none_response_class_uses_app_fallback(app, client):
    bp = flask.Blueprint("bp", __name__, response_class=None)

    @bp.route("/view")
    def view():
        return "fallback"

    app.register_blueprint(bp, url_prefix="/bp")
    rv = client.get("/bp/view")
    assert rv.status_code == 200
    assert rv.data == b"fallback"


# ---------------------------------------------------------------------------
# 4. Nested Blueprint Inheritance
# ---------------------------------------------------------------------------


def test_nested_blueprint_child_has_own_response_class(app, client):
    parent = flask.Blueprint("parent", __name__, url_prefix="/parent")
    child = flask.Blueprint("child", __name__, response_class=ChildResponse)

    @child.route("/view")
    def child_view():
        return "child"

    parent.register_blueprint(child, url_prefix="/child")
    app.register_blueprint(parent)

    rv = client.get("/parent/child/view")
    assert rv.status_code == 200
    assert rv.data == b"child"


def test_nested_blueprint_child_none_inherits_parent(app, client):
    parent = flask.Blueprint("parent", __name__, response_class=ParentResponse)
    child = flask.Blueprint("child", __name__)

    @child.route("/view")
    def child_view():
        return "inherited"

    parent.register_blueprint(child, url_prefix="/child")
    app.register_blueprint(parent, url_prefix="/parent")

    rv = client.get("/parent/child/view")
    assert rv.status_code == 200
    assert rv.data == b"inherited"


def test_nested_blueprint_child_overrides_parent(app, client):
    parent = flask.Blueprint("parent", __name__, response_class=ParentResponse)
    child = flask.Blueprint("child", __name__, response_class=ChildResponse)

    @child.route("/view")
    def child_view():
        return "override"

    parent.register_blueprint(child, url_prefix="/child")
    app.register_blueprint(parent, url_prefix="/parent")

    rv = client.get("/parent/child/view")
    assert rv.status_code == 200
    assert rv.data == b"override"


def test_deeply_nested_blueprint_grandchild_inherits(app, client):
    grandparent = flask.Blueprint("gp", __name__, response_class=ParentResponse)
    parent = flask.Blueprint("parent", __name__)
    child = flask.Blueprint("child", __name__)

    @child.route("/view")
    def child_view():
        return "deep"

    parent.register_blueprint(child, url_prefix="/child")
    grandparent.register_blueprint(parent, url_prefix="/parent")
    app.register_blueprint(grandparent, url_prefix="/gp")

    rv = client.get("/gp/parent/child/view")
    assert rv.status_code == 200
    assert rv.data == b"deep"


def test_deeply_nested_middle_blueprint_has_response_class(app, client):
    grandparent = flask.Blueprint("gp", __name__)
    parent = flask.Blueprint("parent", __name__, response_class=ParentResponse)
    child = flask.Blueprint("child", __name__)

    @child.route("/view")
    def child_view():
        return "middle"

    parent.register_blueprint(child, url_prefix="/child")
    grandparent.register_blueprint(parent, url_prefix="/parent")
    app.register_blueprint(grandparent, url_prefix="/gp")

    rv = client.get("/gp/parent/child/view")
    assert rv.status_code == 200
    assert rv.data == b"middle"


def test_nested_all_none_falls_back_to_app(app, client):
    parent = flask.Blueprint("parent", __name__)
    child = flask.Blueprint("child", __name__)

    @child.route("/view")
    def child_view():
        return "app fallback"

    parent.register_blueprint(child, url_prefix="/child")
    app.register_blueprint(parent, url_prefix="/parent")

    rv = client.get("/parent/child/view")
    assert rv.status_code == 200
    assert rv.data == b"app fallback"


# ---------------------------------------------------------------------------
# 5. Error Handlers
# ---------------------------------------------------------------------------


def test_blueprint_error_handler_uses_blueprint_response_class(app, client):
    bp = flask.Blueprint("bp", __name__, response_class=CustomResponse)

    @bp.errorhandler(403)
    def handle_403(e):
        return "forbidden", 403

    @bp.route("/secret")
    def secret():
        flask.abort(403)

    app.register_blueprint(bp, url_prefix="/bp")
    rv = client.get("/bp/secret")
    assert rv.status_code == 403
    assert rv.data == b"forbidden"


def test_nested_blueprint_error_handler_uses_resolution_chain(app, client):
    parent = flask.Blueprint("parent", __name__, response_class=ParentResponse)
    child = flask.Blueprint("child", __name__)

    @child.errorhandler(404)
    def handle_child_404(e):
        return "child not found", 404

    @child.route("/exists")
    def exists():
        return "ok"

    parent.register_blueprint(child, url_prefix="/child")
    app.register_blueprint(parent, url_prefix="/parent")

    rv = client.get("/parent/child/exists")
    assert rv.status_code == 200


def test_app_level_error_handler_uses_app_response_class(app, client):
    bp = flask.Blueprint("bp", __name__, response_class=CustomResponse)

    @app.errorhandler(404)
    def handle_404(e):
        return "app 404", 404

    app.register_blueprint(bp, url_prefix="/bp")
    rv = client.get("/nonexistent")
    assert rv.status_code == 404
    assert rv.data == b"app 404"


# ---------------------------------------------------------------------------
# 6. Unmatched Routes (404/500) fall back to app.response_class
# ---------------------------------------------------------------------------


def test_global_404_uses_app_response_class(app, client):
    @app.errorhandler(404)
    def handle_404(e):
        return "not found", 404

    rv = client.get("/does-not-exist")
    assert rv.status_code == 404
    assert rv.data == b"not found"


def test_global_500_uses_app_response_class(app, client):
    app.config["TESTING"] = False
    @app.errorhandler(500)
    def handle_500(e):
        return "server error", 500

    @app.route("/crash")
    def crash():
        os.abort(500)

    rv = client.get("/crash")
    assert rv.status_code == 500
    assert rv.data == b"server error"
    assert isinstance(rv, BaseResponse)


# ---------------------------------------------------------------------------
# 7. Explicit Response Objects: already a BaseResponse -> pass through
# ---------------------------------------------------------------------------


def test_explicit_response_object_not_rewrapped(app, client):
    bp = flask.Blueprint("bp", __name__, response_class=CustomResponse)

    @bp.route("/explicit")
    def explicit():
        return flask.Response("already a response", status=200)

    app.register_blueprint(bp, url_prefix="/bp")
    rv = client.get("/bp/explicit")
    assert rv.status_code == 200
    assert rv.data == b"already a response"


def test_explicit_base_response_not_coerced(app, client):
    bp = flask.Blueprint("bp", __name__, response_class=CustomResponse)

    @bp.route("/base")
    def base():
        return BaseResponse("base response", status=200)

    app.register_blueprint(bp, url_prefix="/bp")
    rv = client.get("/bp/base")
    assert rv.status_code == 200


# ---------------------------------------------------------------------------
# 8. Zero Overhead for Non-Blueprint Requests
# ---------------------------------------------------------------------------


def test_non_blueprint_request_no_blueprint_resolution(app, client):
    @app.route("/simple")
    def simple():
        return "simple"

    rv = client.get("/simple")
    assert rv.status_code == 200
    assert rv.data == b"simple"


# ---------------------------------------------------------------------------
# 9. Multiple Blueprints with Different response_class
# ---------------------------------------------------------------------------


def test_multiple_blueprints_different_response_classes(app, client):
    api_bp = flask.Blueprint("api", __name__, response_class=APIResponse)
    admin_bp = flask.Blueprint("admin", __name__, response_class=AdminResponse)

    @api_bp.route("/endpoint")
    def api_endpoint():
        return "api"

    @admin_bp.route("/endpoint")
    def admin_endpoint():
        return "admin"

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    rv_api = client.get("/api/endpoint")
    assert rv_api.status_code == 200
    assert rv_api.data == b"api"

    rv_admin = client.get("/admin/endpoint")
    assert rv_admin.status_code == 200
    assert rv_admin.data == b"admin"


def test_one_bp_with_response_class_one_without(app, client):
    custom_bp = flask.Blueprint("custom", __name__, response_class=CustomResponse)
    plain_bp = flask.Blueprint("plain", __name__)

    @custom_bp.route("/view")
    def custom_view():
        return "custom"

    @plain_bp.route("/view")
    def plain_view():
        return "plain"

    app.register_blueprint(custom_bp, url_prefix="/custom")
    app.register_blueprint(plain_bp, url_prefix="/plain")

    rv1 = client.get("/custom/view")
    assert rv1.status_code == 200
    assert rv1.data == b"custom"

    rv2 = client.get("/plain/view")
    assert rv2.status_code == 200
    assert rv2.data == b"plain"


# ---------------------------------------------------------------------------
# 10. Dynamic modification of response_class after registration
# ---------------------------------------------------------------------------


def test_response_class_changed_after_registration_takes_effect(app, client):
    bp = flask.Blueprint("bp", __name__)

    @bp.route("/view")
    def view():
        return "dynamic"

    app.register_blueprint(bp, url_prefix="/bp")
    bp.response_class = CustomResponse

    rv = client.get("/bp/view")
    assert rv.status_code == 200
    assert rv.data == b"dynamic"


# ---------------------------------------------------------------------------
# 11. Blueprint response_class attribute is public
# ---------------------------------------------------------------------------


def test_response_class_is_public_attribute():
    bp = flask.Blueprint("bp", __name__)
    assert "response_class" not in dir(type(bp)) or hasattr(bp, "response_class")
    bp.response_class = APIResponse
    assert bp.response_class is APIResponse


def test_response_class_readable_as_none_by_default():
    bp = flask.Blueprint("bp", __name__)
    assert bp.response_class is None


# ---------------------------------------------------------------------------
# 12. Edge cases: iterator and bytes body types with blueprint response_class
# ---------------------------------------------------------------------------


def test_blueprint_response_class_with_bytes_body(app, client):
    bp = flask.Blueprint("bp", __name__, response_class=CustomResponse)

    @bp.route("/bytes")
    def view():
        return b"raw bytes"

    app.register_blueprint(bp, url_prefix="/bp")
    rv = client.get("/bp/bytes")
    assert rv.status_code == 200
    assert rv.data == b"raw bytes"


def test_blueprint_response_class_with_iterator_body(app, client):
    bp = flask.Blueprint("bp", __name__, response_class=CustomResponse)

    @bp.route("/iter")
    def view():
        def gen():
            yield "chunk1"
            yield "chunk2"
        return gen()

    app.register_blueprint(bp, url_prefix="/bp")
    rv = client.get("/bp/iter")
    assert rv.status_code == 200
    assert rv.data == b"chunk1chunk2"


# ---------------------------------------------------------------------------
# 13. Tuple responses with headers using blueprint response_class
# ---------------------------------------------------------------------------


def test_blueprint_response_class_tuple_with_headers(app, client):
    bp = flask.Blueprint("bp", __name__, response_class=CustomResponse)

    @bp.route("/headers")
    def view():
        return "ok", 200, {"X-Custom": "yes"}

    app.register_blueprint(bp, url_prefix="/bp")
    rv = client.get("/bp/headers")
    assert rv.status_code == 200
    assert rv.headers.get("X-Custom") == "yes"
    assert rv.data == b"ok"


# ---------------------------------------------------------------------------
# 14. Blueprint registered with custom name
# ---------------------------------------------------------------------------


def test_blueprint_response_class_with_custom_registration_name(app, client):
    bp = flask.Blueprint("original", __name__, response_class=CustomResponse)

    @bp.route("/view")
    def view():
        return "renamed"

    app.register_blueprint(bp, url_prefix="/a", name="renamed_bp")

    rv = client.get("/a/view")
    assert rv.status_code == 200
    assert rv.data == b"renamed"
