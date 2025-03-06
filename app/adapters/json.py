from flask import make_response, request, Response
import functools
import warnings

from app.config import Configuration, ProtocolKey, ResponseStatus
from app.modules import (chat, chat_message, model,
                         user)
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
            error = {
                ProtocolKey.ERROR: {
                    ProtocolKey.ERROR_CODE: ResponseStatus.UNAUTHORIZED.value,
                    ProtocolKey.ERROR_MESSAGE: "A valid session is required to perform this function.",
                }
            }
            value = make_response(error, _map_response_status(ResponseStatus.UNAUTHORIZED))

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
        warnings.warn(
            "Call to deprecated function {}.".format(func.__name__),
            category=DeprecationWarning,
            stacklevel=2
        )
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
        response = make_response(
            error,
            _map_response_status(ResponseStatus.NOT_IMPLEMENTED)
        )
        # Clients would cache this response by default - disable that behavior.
        response.headers["Cache-Control"] = "no-store"

        return response

    return wrapper_stub


@_auth_required
def delete_chat() -> Response:
    chat_id = request.form.get(ProtocolKey.CHAT_ID)

    service_response = chat.delete_chat(chat_id)
    http_response = make_response(
        service_response[0],
        _map_response_status(service_response[1])
    )
    return http_response


@_auth_required
def edit_chat_topic() -> Response:
    chat_id = request.form.get(ProtocolKey.CHAT_ID)
    topic = request.form.get(ProtocolKey.TOPIC)

    service_response = chat.edit_chat_topic(chat_id, topic)
    http_response = make_response(
        service_response[0],
        _map_response_status(service_response[1])
    )
    return http_response


@_auth_required
def get_chat() -> Response:
    chat_id = request.form.get(ProtocolKey.CHAT_ID)
    offset = request.form.get(ProtocolKey.OFFSET)

    service_response = chat_message.get_chat(chat_id, offset)
    http_response = make_response(
        service_response[0],
        _map_response_status(service_response[1])
    )
    return http_response


@_auth_required
def get_chats() -> Response:
    service_response = chat.get_chats()
    http_response = make_response(
        service_response[0],
        _map_response_status(service_response[1])
    )
    return http_response


@_auth_required
def get_current_user() -> Response:
    service_response = user.get_current()
    http_response = make_response(
        service_response[0],
        _map_response_status(service_response[1])
    )
    return http_response


@_auth_required
def get_models() -> Response:
    service_response = model.get_models()
    http_response = make_response(
        service_response[0],
        _map_response_status(service_response[1])
    )
    return http_response


def log_in() -> Response:
    email_address = request.form.get(ProtocolKey.EMAIL_ADDRESS)
    password = request.form.get(ProtocolKey.PASSWORD)

    service_response = user.log_in(
        email_address=email_address,
        password=password
    )
    http_response = make_response(
        service_response[0],
        _map_response_status(service_response[1])
    )
    if ProtocolKey.USER_SESSION in service_response[0]:
        if Configuration.DEBUG:
            secure_cookie = False
        else:
            secure_cookie = True
        session = service_response[0][ProtocolKey.USER_SESSION]
        session_id = session[ProtocolKey.ID]
        http_response.set_cookie(
            ProtocolKey.USER_SESSION_ID,
            session_id,
            secure=secure_cookie
        )
    return http_response


@ _auth_required
def log_out() -> Response:
    service_response = user.log_out()
    http_response = make_response(
        service_response[0],
        _map_response_status(service_response[1])
    )
    http_response.set_cookie(
        ProtocolKey.USER_SESSION_ID,
        "",
        expires=0
    )
    return http_response
