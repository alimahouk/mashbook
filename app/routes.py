from flask import Response

from app import app, socketio
from app.adapters import json, web
from app.modules.chat import ChatNamespace


########################
# WEBSOCKETS ENDPOINTS #
########################


socketio.on_namespace(ChatNamespace("/"))


@socketio.on_error("/")
def chat_error_handler(e):
    print("Socket error occurred:", str(e))


##################################
# API V1 JSON RESPONSE ENDPOINTS #
##################################


@app.route("/api/v1/delete-chat", methods=["POST"])
def api_v1_delete_chat() -> Response:
    """
    Delete a chat.
    """

    return json.delete_chat()


@app.route("/api/v1/edit-chat-topic", methods=["POST"])
def api_v1_edit_chat_topic() -> Response:
    """
    Rename a chat.
    """

    return json.edit_chat_topic()


@app.route("/api/v1/get-chat", methods=["POST"])
def api_v1_get_chat() -> Response:
    """
    Get the last messages in a chat.
    """

    return json.get_chat()


@app.route("/api/v1/get-chats", methods=["POST"])
def api_v1_get_chats() -> Response:
    """
    Get a list of all the user's chats. This is a list of
    the chat topics excluding any messages.
    """

    return json.get_chats()


@app.route("/api/v1/get-models", methods=["POST"])
def api_v1_get_models() -> Response:
    """
    Get a list of available language models.
    """

    return json.get_models()


@app.route("/api/v1/log-in", methods=["POST"])
def api_v1_log_in() -> Response:
    """
    For logging a user in and creating a new session.
    """

    return json.log_in()


@app.route("/api/v1/log-out", methods=["POST"])
def api_v1_log_out() -> Response:
    """
    For logging a user out and destroying the current session.
    """

    return json.log_out()


@app.route("/api/v1/me", methods=["POST"])
def api_v1_me() -> Response:
    """
    Get the profile of the currently logged in user.
    """

    return json.get_current_user()


#############
# WEB VIEWS #
#############


@app.route("/c/<chat_id>", methods=["GET"])
def web_chat(chat_id: str) -> Response:
    return web.chat_page(chat_id)


@app.route("/c/new", methods=["GET"])
def web_chat_composer() -> Response:
    return web.chat_composer()


@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
def web_index() -> Response:
    return web.index()


@app.route("/join", methods=["POST"])
def web_join() -> Response:
    return web.join()


@app.route("/log-in", methods=["POST"])
def web_login() -> Response:
    return web.log_in()


@app.route("/log-out", methods=["POST"])
def web_log_out() -> Response:
    return web.log_out()


@app.route("/c/new", methods=["POST"])
def web_make_chat() -> Response:
    return web.make_chat()


@app.route("/c/<chat_id>/remove")
def web_remove_chat(chat_id: str) -> Response:
    return web.remove_chat(chat_id)


##################
# ERROR HANDLERS #
##################


@app.errorhandler(400)
def error_bad_request(e):
    return web.error_bad_request(e)


@app.errorhandler(403)
def error_forbidden(e):
    return web.error_forbidden(e)


@app.errorhandler(404)
def error_not_found(e):
    return web.error_not_found(e)


@app.errorhandler(405)
def error_not_allowed(e):
    return web.error_not_allowed(e)


@app.errorhandler(401)
def error_uauthorized(e):
    return web.error_uauthorized(e)
