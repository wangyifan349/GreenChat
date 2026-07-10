"""GreenChat: a private Flask web chat application.

The application provides user registration, authentication, password changes,
private text and file messaging, mutual-conversation filtering, unread counts,
and readable TXT transcript export. SQLite3 stores all application data.
"""

import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_bootstrap import Bootstrap5
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Application configuration
# ---------------------------------------------------------------------------

BASE_DIRECTORY = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIRECTORY / "chat.db"
UPLOAD_DIRECTORY = BASE_DIRECTORY / "uploads"
UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_SIZE = 4 * 1024 * 1024 * 1024
MAX_MESSAGE_LENGTH = 5000
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 32
PASSWORD_HASH_METHOD = "pbkdf2:sha256:600000"

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("CHAT_SECRET_KEY", secrets.token_hex(32)),
    MAX_CONTENT_LENGTH=MAX_UPLOAD_SIZE,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
bootstrap = Bootstrap5(app)


# ---------------------------------------------------------------------------
# Database lifecycle
# ---------------------------------------------------------------------------

def get_database_connection():
    """Return the SQLite connection for the current request."""
    if "database" not in g:
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        g.database = connection
    return g.database


@app.teardown_appcontext
def close_database_connection(exception):
    """Close the request-scoped SQLite connection."""
    connection = g.pop("database", None)
    if connection is not None:
        connection.close()


def initialize_database():
    """Create the required tables and indexes when they do not exist."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message_text TEXT,
            stored_file_name TEXT,
            original_file_name TEXT,
            file_size INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE,
            CHECK (
                (message_text IS NOT NULL AND length(message_text) > 0)
                OR stored_file_name IS NOT NULL
            )
        );

        CREATE TABLE IF NOT EXISTS conversation_reads (
            user_id INTEGER NOT NULL,
            other_user_id INTEGER NOT NULL,
            last_read_message_id INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, other_user_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (other_user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS index_messages_conversation
        ON messages(sender_id, receiver_id, id);

        CREATE INDEX IF NOT EXISTS index_messages_receiver
        ON messages(receiver_id, id);
        """
    )
    connection.commit()
    connection.close()


# ---------------------------------------------------------------------------
# Authentication, validation, and shared helpers
# ---------------------------------------------------------------------------

def get_current_utc_timestamp():
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def login_required(view_function):
    """Require an authenticated session for a view."""
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify(ok=False, error="Authentication required."), 401
            return redirect(url_for("login", next=request.path))
        return view_function(*args, **kwargs)
    return wrapped_view


def get_current_user():
    """Return the currently authenticated user row."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return get_database_connection().execute(
        "SELECT id, username, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def find_user_by_username(username):
    """Find a user by username using a case-insensitive lookup."""
    return get_database_connection().execute(
        "SELECT id, username, created_at FROM users WHERE username = ? COLLATE NOCASE",
        (username,),
    ).fetchone()


def get_or_create_csrf_token():
    """Return the session CSRF token, creating one when required."""
    token = session.get("csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validate_csrf_token():
    """Reject a state-changing request with an invalid CSRF token."""
    submitted_token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    stored_token = session.get("csrf_token")
    if not submitted_token or not stored_token or not secrets.compare_digest(submitted_token, stored_token):
        abort(403, description="Invalid CSRF token.")


def validate_username(username):
    """Validate a username and return an error message when invalid."""
    if not USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH:
        return f"Username must contain {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} characters."
    if not username.replace("_", "").isalnum():
        return "Username may contain only letters, numbers, and underscores."
    return None


def has_mutual_conversation(first_user_id, second_user_id):
    """Return True only when both users have sent at least one message."""
    result = get_database_connection().execute(
        """
        SELECT
            EXISTS(SELECT 1 FROM messages WHERE sender_id = ? AND receiver_id = ?) AS first_to_second,
            EXISTS(SELECT 1 FROM messages WHERE sender_id = ? AND receiver_id = ?) AS second_to_first
        """,
        (first_user_id, second_user_id, second_user_id, first_user_id),
    ).fetchone()
    return bool(result["first_to_second"] and result["second_to_first"])


def update_conversation_read_position(user_id, other_user_id):
    """Mark all messages received from another user as read."""
    latest_message_id = get_database_connection().execute(
        "SELECT COALESCE(MAX(id), 0) AS latest_id FROM messages WHERE sender_id = ? AND receiver_id = ?",
        (other_user_id, user_id),
    ).fetchone()["latest_id"]
    get_database_connection().execute(
        """
        INSERT INTO conversation_reads(user_id, other_user_id, last_read_message_id, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, other_user_id)
        DO UPDATE SET last_read_message_id = excluded.last_read_message_id,
                      updated_at = excluded.updated_at
        """,
        (user_id, other_user_id, latest_message_id, get_current_utc_timestamp()),
    )
    get_database_connection().commit()


def format_file_size(file_size_bytes):
    """Return a readable binary file size."""
    if file_size_bytes is None:
        return "Unknown"
    display_value = float(file_size_bytes)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    unit_index = 0
    while display_value >= 1024 and unit_index < len(units) - 1:
        display_value /= 1024
        unit_index += 1
    precision = 0 if unit_index == 0 else 2
    return f"{display_value:.{precision}f} {units[unit_index]}"


# ---------------------------------------------------------------------------
# Template context and account routes
# ---------------------------------------------------------------------------

@app.context_processor
def inject_template_globals():
    return {"current_user": get_current_user, "csrf_token": get_or_create_csrf_token}


@app.get("/")
def index():
    return redirect(url_for("conversations" if session.get("user_id") else "login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("conversations"))
    error = None
    if request.method == "POST":
        validate_csrf_token()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        error = validate_username(username)
        if error is None and password == "":
            error = "Password cannot be empty."
        if error is None and password != confirm_password:
            error = "The passwords do not match."
        if error is None:
            try:
                cursor = get_database_connection().execute(
                    "INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password, method=PASSWORD_HASH_METHOD), get_current_utc_timestamp()),
                )
                get_database_connection().commit()
                session.clear()
                session["user_id"] = cursor.lastrowid
                session["csrf_token"] = secrets.token_urlsafe(32)
                return redirect(url_for("conversations"))
            except sqlite3.IntegrityError:
                error = "That username is already registered."
    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("conversations"))
    error = None
    if request.method == "POST":
        validate_csrf_token()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_database_connection().execute(
            "SELECT id, username, password_hash FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Incorrect username or password."
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["csrf_token"] = secrets.token_urlsafe(32)
            next_url = request.args.get("next")
            return redirect(next_url if next_url and next_url.startswith("/") else url_for("conversations"))
    return render_template("login.html", error=error)


@app.post("/logout")
@login_required
def logout():
    validate_csrf_token()
    session.clear()
    return redirect(url_for("login"))


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    error = None
    success = None
    if request.method == "POST":
        validate_csrf_token()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        user = get_database_connection().execute(
            "SELECT id, password_hash FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
        if not check_password_hash(user["password_hash"], current_password):
            error = "The current password is incorrect."
        elif new_password == "":
            error = "The new password cannot be empty."
        elif new_password != confirm_password:
            error = "The new passwords do not match."
        else:
            get_database_connection().execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(new_password, method=PASSWORD_HASH_METHOD), user["id"]),
            )
            get_database_connection().commit()
            success = "Your password has been changed."
    return render_template("change_password.html", error=error, success=success)


# ---------------------------------------------------------------------------
# Conversation and user discovery routes
# ---------------------------------------------------------------------------

@app.get("/conversations")
@login_required
def conversations():
    signed_in_user = get_current_user()
    # Show a conversation only when both participants have sent a message.
    # The same query also retrieves the latest message and unread count.
    conversation_rows = get_database_connection().execute(
        """
        WITH related_users AS (
            SELECT DISTINCT CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS other_user_id
            FROM messages
            WHERE sender_id = ? OR receiver_id = ?
        )
        SELECT
            users.id,
            users.username,
            latest.id AS latest_message_id,
            latest.message_text,
            latest.original_file_name,
            latest.created_at,
            latest.sender_id,
            COALESCE(read_state.last_read_message_id, 0) AS last_read_message_id,
            (
                SELECT COUNT(*) FROM messages unread
                WHERE unread.sender_id = users.id
                  AND unread.receiver_id = ?
                  AND unread.id > COALESCE(read_state.last_read_message_id, 0)
            ) AS unread_count
        FROM related_users
        JOIN users ON users.id = related_users.other_user_id
        JOIN messages latest ON latest.id = (
            SELECT MAX(candidate.id) FROM messages candidate
            WHERE (candidate.sender_id = ? AND candidate.receiver_id = users.id)
               OR (candidate.sender_id = users.id AND candidate.receiver_id = ?)
        )
        LEFT JOIN conversation_reads read_state
          ON read_state.user_id = ? AND read_state.other_user_id = users.id
        WHERE EXISTS(
            SELECT 1 FROM messages outbound
            WHERE outbound.sender_id = ? AND outbound.receiver_id = users.id
        )
        AND EXISTS(
            SELECT 1 FROM messages inbound
            WHERE inbound.sender_id = users.id AND inbound.receiver_id = ?
        )
        ORDER BY latest.id DESC
        """,
        (
            signed_in_user["id"], signed_in_user["id"], signed_in_user["id"],
            signed_in_user["id"], signed_in_user["id"], signed_in_user["id"],
            signed_in_user["id"], signed_in_user["id"], signed_in_user["id"],
        ),
    ).fetchall()
    return render_template("conversations.html", conversations=conversation_rows)


@app.get("/users")
@login_required
def users():
    signed_in_user = get_current_user()
    search_query = request.args.get("q", "").strip()
    parameters = [signed_in_user["id"]]
    sql = "SELECT id, username, created_at FROM users WHERE id != ?"
    if search_query:
        sql += " AND username LIKE ? COLLATE NOCASE"
        parameters.append(f"%{search_query}%")
    sql += " ORDER BY username COLLATE NOCASE LIMIT 100"
    user_rows = get_database_connection().execute(sql, tuple(parameters)).fetchall()
    return render_template("users.html", users=user_rows, query=search_query)


def calculate_longest_common_subsequence_length(first_value, second_value):
    """Calculate a case-insensitive LCS score using two rolling rows.

    Keeping only the current and previous rows limits memory use while still
    producing the same longest-common-subsequence length.
    """
    first_value = first_value.casefold()
    second_value = second_value.casefold()
    if len(first_value) < len(second_value):
        first_value, second_value = second_value, first_value
    previous_row = [0] * (len(second_value) + 1)
    for first_character in first_value:
        current_row = [0]
        for column_index, second_character in enumerate(second_value, start=1):
            if first_character == second_character:
                current_row.append(previous_row[column_index - 1] + 1)
            else:
                current_row.append(max(previous_row[column_index], current_row[-1]))
        previous_row = current_row
    return previous_row[-1]


@app.get("/api/users/search")
@login_required
def api_user_search():
    signed_in_user = get_current_user()
    search_query = request.args.get("q", "").strip()
    user_rows = get_database_connection().execute(
        "SELECT username FROM users WHERE id != ? ORDER BY username COLLATE NOCASE",
        (signed_in_user["id"],),
    ).fetchall()

    # Empty queries provide a short alphabetical list. Non-empty queries are
    # ranked by LCS length, match density, username length, and alphabetically.
    if not search_query:
        results = [row["username"] for row in user_rows[:20]]
    else:
        scored_users = []
        normalized_query_length = max(len(search_query), 1)
        for row in user_rows:
            username = row["username"]
            lcs_length = calculate_longest_common_subsequence_length(search_query, username)
            if lcs_length == 0:
                continue
            density = lcs_length / max(len(username), normalized_query_length)
            scored_users.append((username, lcs_length, density))
        scored_users.sort(key=lambda item: (-item[1], -item[2], len(item[0]), item[0].casefold()))
        results = [item[0] for item in scored_users[:20]]

    return jsonify(ok=True, users=results)


# ---------------------------------------------------------------------------
# Chat messages, file transfer, and transcript export
# ---------------------------------------------------------------------------

@app.get("/chat/<username>")
@login_required
def chat(username):
    signed_in_user = get_current_user()
    other_user = find_user_by_username(username)
    if other_user is None:
        abort(404, description="User not found.")
    if other_user["id"] == signed_in_user["id"]:
        return redirect(url_for("conversations"))
    update_conversation_read_position(signed_in_user["id"], other_user["id"])
    return render_template(
        "chat.html",
        other_user=other_user,
        is_mutual=has_mutual_conversation(signed_in_user["id"], other_user["id"]),
        max_upload_bytes=MAX_UPLOAD_SIZE,
        max_upload_label="4 GiB",
    )


@app.get("/api/chat/<username>/messages")
@login_required
def api_messages(username):
    signed_in_user = get_current_user()
    other_user = find_user_by_username(username)
    if other_user is None:
        return jsonify(ok=False, error="User not found."), 404
    try:
        after_id = max(0, int(request.args.get("after_id", "0")))
    except ValueError:
        return jsonify(ok=False, error="Invalid message position."), 400
    rows = get_database_connection().execute(
        """
        SELECT messages.*, sender.username AS sender_username
        FROM messages
        JOIN users sender ON sender.id = messages.sender_id
        WHERE messages.id > ?
          AND ((messages.sender_id = ? AND messages.receiver_id = ?)
            OR (messages.sender_id = ? AND messages.receiver_id = ?))
        ORDER BY messages.id ASC
        LIMIT 300
        """,
        (after_id, signed_in_user["id"], other_user["id"], other_user["id"], signed_in_user["id"]),
    ).fetchall()
    messages = []
    for row in rows:
        message = dict(row)
        message["is_mine"] = row["sender_id"] == signed_in_user["id"]
        message["download_url"] = url_for("download_file", message_id=row["id"]) if row["stored_file_name"] else None
        messages.append(message)
    if rows:
        update_conversation_read_position(signed_in_user["id"], other_user["id"])
    return jsonify(
        ok=True,
        messages=messages,
        mutual=has_mutual_conversation(signed_in_user["id"], other_user["id"]),
    )


@app.post("/api/chat/<username>/send")
@login_required
def api_send(username):
    validate_csrf_token()
    signed_in_user = get_current_user()
    other_user = find_user_by_username(username)
    if other_user is None:
        return jsonify(ok=False, error="User not found."), 404
    if other_user["id"] == signed_in_user["id"]:
        return jsonify(ok=False, error="You cannot message yourself."), 400

    # Preserve the submitted message exactly, including indentation, tabs,
    # and line breaks. Stripping is used only to determine whether it is empty.
    original_message_text = request.form.get("message", "")
    uploaded_file = request.files.get("file")
    if len(original_message_text) > MAX_MESSAGE_LENGTH:
        return jsonify(ok=False, error=f"Message exceeds {MAX_MESSAGE_LENGTH} characters."), 400

    stored_file_name = None
    original_file_name = None
    file_size = None
    if uploaded_file and uploaded_file.filename:
        original_file_name = secure_filename(uploaded_file.filename)
        if not original_file_name:
            return jsonify(ok=False, error="Invalid file name."), 400
        extension = Path(original_file_name).suffix[:20]
        stored_file_name = f"{uuid.uuid4().hex}{extension}"
        destination = UPLOAD_DIRECTORY / stored_file_name
        uploaded_file.save(destination)
        file_size = destination.stat().st_size
        if file_size > MAX_UPLOAD_SIZE:
            destination.unlink(missing_ok=True)
            return jsonify(ok=False, error="File exceeds the 4 GiB upload limit."), 413

    if not original_message_text.strip() and stored_file_name is None:
        return jsonify(ok=False, error="Enter a message or select a file."), 400

    message_text = original_message_text if original_message_text.strip() else None
    try:
        cursor = get_database_connection().execute(
            """
            INSERT INTO messages(
                sender_id, receiver_id, message_text, stored_file_name,
                original_file_name, file_size, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signed_in_user["id"], other_user["id"], message_text,
                stored_file_name, original_file_name, file_size, get_current_utc_timestamp(),
            ),
        )
        get_database_connection().commit()
    except Exception:
        if stored_file_name:
            (UPLOAD_DIRECTORY / stored_file_name).unlink(missing_ok=True)
        raise

    return jsonify(
        ok=True,
        message_id=cursor.lastrowid,
        mutual=has_mutual_conversation(signed_in_user["id"], other_user["id"]),
    )


@app.get("/files/<int:message_id>")
@login_required
def download_file(message_id):
    signed_in_user = get_current_user()
    message = get_database_connection().execute(
        "SELECT sender_id, receiver_id, stored_file_name, original_file_name FROM messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    if message is None or not message["stored_file_name"]:
        abort(404)
    if signed_in_user["id"] not in (message["sender_id"], message["receiver_id"]):
        abort(403)
    file_path = UPLOAD_DIRECTORY / message["stored_file_name"]
    if not file_path.is_file():
        abort(404)
    return send_file(file_path, as_attachment=True, download_name=message["original_file_name"])


@app.get("/chat/<username>/export")
@login_required
def export_chat(username):
    signed_in_user = get_current_user()
    other_user = find_user_by_username(username)
    if other_user is None:
        abort(404, description="User not found.")
    if other_user["id"] == signed_in_user["id"]:
        abort(400, description="A self-conversation cannot be exported.")

    messages = get_database_connection().execute(
        """
        SELECT messages.*, sender.username AS sender_username, receiver.username AS receiver_username
        FROM messages
        JOIN users sender ON sender.id = messages.sender_id
        JOIN users receiver ON receiver.id = messages.receiver_id
        WHERE (messages.sender_id = ? AND messages.receiver_id = ?)
           OR (messages.sender_id = ? AND messages.receiver_id = ?)
        ORDER BY messages.id ASC
        """,
        (signed_in_user["id"], other_user["id"], other_user["id"], signed_in_user["id"]),
    ).fetchall()

    separator = "=" * 88
    message_separator = "-" * 88
    lines = [
        separator,
        "GREENCHAT PRIVATE CONVERSATION TRANSCRIPT",
        separator,
        f"Your username : {signed_in_user['username']}",
        f"Other user    : {other_user['username']}",
        f"Participants  : {signed_in_user['username']} <-> {other_user['username']}",
        f"Exported at   : {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"Total messages: {len(messages)}",
        separator,
        "",
    ]
    for number, message in enumerate(messages, start=1):
        timestamp = datetime.fromisoformat(message["created_at"]).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        direction = "You -> Other user" if message["sender_id"] == signed_in_user["id"] else "Other user -> You"
        lines.extend([
            f"Message #{number}",
            f"Time      : {timestamp}",
            f"From      : {message['sender_username']}",
            f"To        : {message['receiver_username']}",
            f"Direction : {direction}",
        ])
        if message["message_text"] is not None:
            lines.extend(["Text:", message["message_text"]])
        if message["original_file_name"]:
            lines.extend([
                "Attachment:",
                f"  File name : {message['original_file_name']}",
                f"  File size : {format_file_size(message['file_size'])}",
                f"  Message ID: {message['id']}",
            ])
        lines.extend([message_separator, ""])

    # A UTF-8 BOM improves compatibility with Windows text editors. The
    # temporary transcript is deleted after Flask finishes sending it.
    transcript_path = BASE_DIRECTORY / f"chat_{signed_in_user['username']}_{other_user['username']}_{uuid.uuid4().hex}.txt"
    transcript_path.write_text("\ufeff" + "\n".join(lines), encoding="utf-8")
    response = send_file(
        transcript_path,
        as_attachment=True,
        download_name=f"GreenChat_{signed_in_user['username']}_{other_user['username']}.txt",
        mimetype="text/plain; charset=utf-8",
    )
    response.call_on_close(lambda: transcript_path.unlink(missing_ok=True))
    return response


# ---------------------------------------------------------------------------
# Error handlers and development entry point
# ---------------------------------------------------------------------------

@app.errorhandler(413)
def upload_too_large(error):
    if request.path.startswith("/api/"):
        return jsonify(ok=False, error="File exceeds the 4 GiB upload limit."), 413
    return render_template("error.html", code=413, message="The uploaded file exceeds the 4 GiB limit."), 413


@app.errorhandler(403)
def forbidden(error):
    if request.path.startswith("/api/"):
        return jsonify(ok=False, error="Forbidden."), 403
    return render_template("error.html", code=403, message=error.description), 403


@app.errorhandler(404)
def not_found(error):
    if request.path.startswith("/api/"):
        return jsonify(ok=False, error="Not found."), 404
    return render_template("error.html", code=404, message=error.description), 404


if __name__ == "__main__":
    initialize_database()
    app.run(host="127.0.0.1", port=5000, debug=True)
