from flask import (abort, make_response, redirect,
                   Response, render_template, request)
import functools
import uuid
import warnings

from app.config import Configuration, ProtocolKey, ResponseStatus
from app.modules import (chat, user, user_session)
from app.modules.user import User
from app.modules.user_session import UserSession


def _auth_required(func):
    """
    [DECORATOR] Makes sure a valid session exists for the user
    making the request before proceeding with the called function.
    """

    @functools.wraps(func)
    def wrapper_auth_required(*args, **kwargs):
        authenticated = False
        session_id = request.cookies.get(ProtocolKey.USER_SESSION_ID)
        if session_id and UserSession.exists(session_id):
            authenticated = True

        if authenticated:
            value = func(*args, **kwargs)
        else:
            abort(_map_response_status(ResponseStatus.UNAUTHORIZED))

        return value
    return wrapper_auth_required


def _deprecated(func):
    """
    [DECORATOR] This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.simplefilter("always", DeprecationWarning)  # Turn off filter.
        warnings.warn("Call to deprecated function {}.".format(func.__name__),
                      category=DeprecationWarning,
                      stacklevel=2)
        warnings.simplefilter("default", DeprecationWarning)  # Reset filter.

        return func(*args, **kwargs)
    return new_func


def _map_response_status(response_status: ResponseStatus) -> int:
    """
    Maps service response status codes to HTTP response status codes."""

    """Set to the HTTP Internal Server Error code by default because if
    this doesn't get set to the correct code later on then it's likely
    because of an internal server error.
    """

    ret = 500
    if response_status == ResponseStatus.OK:
        ret = 200
    elif response_status == ResponseStatus.BAD_REQUEST:
        ret = 400
    elif response_status == ResponseStatus.FORBIDDEN:
        ret = 403
    elif response_status == ResponseStatus.INTERNAL_SERVER_ERROR:
        ret = 500
    elif response_status == ResponseStatus.NOT_FOUND:
        ret = 404
    elif response_status == ResponseStatus.NOT_IMPLEMENTED:
        ret = 501
    elif response_status == ResponseStatus.PAYLOAD_TOO_LARGE:
        ret = 413
    elif response_status == ResponseStatus.TOO_MANY_REQUESTS:
        ret = 429
    elif response_status == ResponseStatus.UNAUTHORIZED:
        ret = 401
    return ret


def _session_id() -> str:
    session_id = request.cookies.get(ProtocolKey.USER_SESSION_ID)
    if not session_id:
        session_id = request.cookies.get(ProtocolKey.SESSION_ID)

    if not session_id:
        # Generate an ephemeral session ID to uniquely identify this visitor.
        session_id = UserSession.generate_id()
    return session_id


def _stub(func):
    """
    [DECORATOR]
    """

    @functools.wraps(func)
    def wrapper_stub():
        error = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: ResponseStatus.NOT_IMPLEMENTED.value,
                ProtocolKey.ERROR_MESSAGE: "This function has not been implemented yet.",
            }
        }
        response = make_response(error, _map_response_status(ResponseStatus.NOT_IMPLEMENTED))
        # Clients would cache this response by default - disable that behavior.
        response.headers["Cache-Control"] = "no-store"

        return response
    return wrapper_stub


def chat_composer() -> Response:
    session_id = _session_id()
    user_session.update_session(session_id)

    user = User.get_by_session(session_id)
    http_response = make_response(
        render_template("pages/chat_composer.html", current_user=user, debug_mode=str(Configuration.DEBUG)),
        _map_response_status(ResponseStatus.OK)
    )

    if not request.cookies.get(ProtocolKey.USER_SESSION_ID):
        if Configuration.DEBUG:
            secure_cookie = False
        else:
            secure_cookie = True
        http_response.set_cookie(ProtocolKey.SESSION_ID, session_id, secure=secure_cookie)

    return http_response


def chat_page(chat_id: str) -> Response:
    session_id = _session_id()
    user_session.update_session(session_id)

    service_response = chat.get_chat(session_id, uuid.UUID(chat_id))
    if service_response[1] == ResponseStatus.OK:
        user = User.get_by_session(session_id)
        c = service_response[0]
        http_response = make_response(
            render_template("pages/chat.html", chat=c, current_user=user, debug_mode=str(Configuration.DEBUG)),
            _map_response_status(ResponseStatus.OK)
        )
    else:
        if service_response[1] == ResponseStatus.NOT_FOUND:
            abort(404)
        else:
            http_response = make_response(service_response[0], _map_response_status(service_response[1]))

    if not request.cookies.get(ProtocolKey.USER_SESSION_ID):
        if Configuration.DEBUG:
            secure_cookie = False
        else:
            secure_cookie = True
        http_response.set_cookie(ProtocolKey.SESSION_ID, session_id, secure=secure_cookie)

    return http_response


def error_bad_request(e) -> str:
    return render_template("pages/errors/400.html"), 400


def error_forbidden(e) -> str:
    return render_template("pages/errors/403.html"), 403


def error_not_allowed(e) -> str:
    return render_template("pages/errors/405.html"), 405


def error_not_found(e) -> str:
    return render_template("pages/errors/404.html"), 404


def error_uauthorized(e) -> str:
    return render_template("pages/errors/401.html"), 401


def join() -> Response:
    session_id = request.cookies.get(ProtocolKey.USER_SESSION_ID)
    if session_id and UserSession.exists(session_id):
        # User is already logged in.
        return redirect("/")

    email = request.form.get(ProtocolKey.EMAIL_ADDRESS)
    password = request.form.get(ProtocolKey.PASSWORD)

    service_response = user.join(
        email_address=email,
        password=password
    )
    if ProtocolKey.USER_SESSION in service_response[0]:
        if Configuration.DEBUG:
            secure_cookie = False
        else:
            secure_cookie = True

        session = service_response[0][ProtocolKey.USER_SESSION]
        session_id = session[ProtocolKey.ID]
        http_response = redirect("/")
        http_response.set_cookie(ProtocolKey.USER_SESSION_ID, session_id, secure=secure_cookie)
        # Update after joining because session won't exist before it.
        user_session.update_session(session_id)

        return http_response
    else:
        abort(_map_response_status(service_response[1]))


def index() -> Response:
    session_id = _session_id()
    if session_id and UserSession.exists(session_id):
        user = User.get_by_session(session_id)

        service_response = chat.get_chats(session_id)
        chats = service_response[0]

        http_response = make_response(
            render_template("pages/index.html", current_user=user, chats=chats),
            _map_response_status(service_response[1])
        )
    else:
        http_response = make_response(
            render_template("pages/index_public.html"),
            _map_response_status(ResponseStatus.OK)
        )

    if not request.cookies.get(ProtocolKey.USER_SESSION_ID):
        if Configuration.DEBUG:
            secure_cookie = False
        else:
            secure_cookie = True
        http_response.set_cookie(ProtocolKey.SESSION_ID, session_id, secure=secure_cookie)

    return http_response


def log_in() -> Response:
    session_id = request.cookies.get(ProtocolKey.USER_SESSION_ID)
    if session_id and UserSession.exists(session_id):
        # User is already logged in.
        return redirect("/")

    email = request.form.get(ProtocolKey.EMAIL_ADDRESS)
    password = request.form.get(ProtocolKey.PASSWORD)

    service_response = user.log_in(email, password)
    if ProtocolKey.USER_SESSION in service_response[0]:
        if Configuration.DEBUG:
            secure_cookie = False
        else:
            secure_cookie = True

        session = service_response[0][ProtocolKey.USER_SESSION]
        session_id = session[ProtocolKey.ID]
        http_response = redirect("/")
        http_response.set_cookie(ProtocolKey.USER_SESSION_ID, session_id, secure=secure_cookie)
        # Update after joining because session won't exist before it.
        user_session.update_session(session_id)

        return http_response
    else:
        return make_response(service_response[0], _map_response_status(service_response[1]))


@_auth_required
def log_out() -> Response:
    session_id = _session_id()
    user_session.update_session(session_id)

    service_response = user.log_out()
    http_response = redirect("/")
    if service_response[1] == ResponseStatus.OK:
        http_response.set_cookie(ProtocolKey.USER_SESSION_ID, "", expires=0)

    return http_response


def make_chat() -> Response:
    session_id = _session_id()
    user_session.update_session(session_id)

    context_range_length = request.form.get(ProtocolKey.CONTEXT_RANGE_LEN)
    context_range_start = request.form.get(ProtocolKey.CONTEXT_RANGE_START)
    content_md = request.form.get(ProtocolKey.CONTENT_MARKDOWN)
    message_id = request.form.get(ProtocolKey.MESSAGE_ID)

    if message_id:
        message_id = uuid.UUID(message_id)

    service_response = chat.make(
        session_id,
        context_range_length=context_range_length,
        context_range_start=context_range_start,
        content_md=content_md,
        message_id=message_id
    )
    if service_response[1] == ResponseStatus.OK:
        new_chat = service_response[0]
        http_response = redirect(f"/c/{new_chat[ProtocolKey.ID]}")
        return http_response
    else:
        return make_response(service_response[0], _map_response_status(service_response[1]))


@_auth_required
def remove_chat(chat_id: str) -> Response:
    session_id = _session_id()
    user_session.update_session(session_id)

    service_response = chat.remove(session_id, uuid.UUID(chat_id))
    if service_response[1] == ResponseStatus.OK:
        http_response = redirect("/")
        return http_response
    else:
        return make_response(service_response[0], _map_response_status(service_response[1]))
