# 💬 GreenChat

GreenChat is a self-hosted private messaging application built with Python 3, Flask, Bootstrap-Flask, AJAX, and SQLite3. It provides browser-based account management, private conversations, multiline messages, file transfer, unread-message tracking, real-time user search, conversation management, and readable TXT transcript export.

The project includes two editions:

- 📁 **Standard multi-file edition** — uses separate templates and static assets and is recommended for normal development.
- 📦 **Standalone single-file edition** — contains the Flask back end, templates, CSS, and JavaScript in one Python file.

GreenChat is intended for small private deployments, internal teams, classrooms, local networks, personal servers, and Flask development practice. Users only need a modern web browser; no desktop or mobile client is required.

## 🎯 Project purpose

GreenChat allows users to register, sign in, search for another account, and open a private conversation through a route such as:

```text
/chat/username
```

Messages are sent and retrieved through AJAX, so the page does not reload after every action. User accounts, password hashes, message metadata, read positions, and conversation history are stored in SQLite3. Uploaded files are stored in the local `uploads` directory.

The interface is inspired by common QQ and WeChat layouts. It includes clickable conversation rows, unread badges, message previews, timestamps, a right-click context menu, left/right message bubbles, and a message composer at the bottom of the chat page.

## ✨ Main features

### 👤 Accounts and authentication

- User registration
- User login and logout
- Password change page
- Case-insensitive unique usernames
- Session-based authentication
- PBKDF2-HMAC-SHA256 password hashing
- Random password salts
- CSRF validation for state-changing requests
- No application-level password length limit; passwords must only be non-empty

Passwords are never stored as readable plain text. The SQLite3 database stores salted PBKDF2-HMAC-SHA256 password hashes.

### 💬 Private messaging

- Direct private chat at `/chat/<username>`
- AJAX message sending and polling
- Incoming and outgoing message bubbles
- Message timestamps
- Unread-message counts
- Automatic read-position updates
- `Ctrl+Enter` to send
- `Enter` to insert a new line

### 🧾 Exact text formatting

GreenChat preserves the original structure of a message, which is useful for source code, configuration files, logs, commands, and other preformatted content.

It preserves:

- Line breaks
- Leading spaces
- Repeated spaces
- Tab indentation
- Blank lines
- Long multiline messages

The server checks whether a message contains visible content without stripping its original indentation before saving it.

### 📎 File transfer

- Send a file with or without accompanying text
- Display the original file name and file size
- Authenticated file downloads
- Download access restricted to the two conversation participants
- Maximum Flask request size of 4 GiB

A 4 GiB Flask setting does not override upload limits imposed by Nginx, Apache, Cloudflare, hosting platforms, or other reverse proxies. Those limits must be configured separately.

### 🔎 Real-time user search

- AJAX search suggestions while typing
- Original user-list page remains available
- Longest Common Subsequence scoring
- Results sorted by LCS score in descending order
- Keyboard navigation with arrow keys
- Enter to open the selected result
- Esc to close the suggestion menu
- Click a result to open `/chat/<username>` directly

### 📋 Conversation management

The conversation page works like a QQ or WeChat message list. Each row displays:

- The other user's name
- The latest message preview
- The latest activity time
- The unread-message count

The entire row can be clicked to open the chat. Right-clicking a conversation opens a context menu with actions to open the chat or export the complete transcript.

### 🤝 Mutual-conversation visibility rule

A conversation appears in the normal conversation list only after both users have sent at least one message to each other.

```text
Alice sends a message to Bob.
Bob has not replied.
Result: the conversation is not shown in the normal conversation list.

Bob opens /chat/Alice and sends a reply.
Result: the conversation becomes visible in both users' conversation lists.
```

This reduces conversation-list spam from accounts that send unsolicited one-way messages.

### 📤 TXT transcript export

Users can export a complete private conversation as a readable UTF-8 TXT file from the chat page or the conversation-list context menu.

The transcript includes:

- Both participant names
- Export date and time
- Total message count
- Message sequence numbers
- Sender and recipient names
- Message timestamps and direction
- Original multiline text and indentation
- Attachment names and sizes
- Related message identifiers

Only a participant in the conversation can export its transcript.

## 🗂️ Project structure

```text
GreenChat/
├── greenchat_server.py          # Standard multi-file Flask entry point
├── greenchat_standalone.py      # Complete standalone single-file edition
├── requirements.txt
├── README.md
├── LICENSE
├── chat.db                      # Created automatically after first start
├── uploads/                     # Created automatically for uploaded files
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── change_password.html
│   ├── conversations.html
│   ├── users.html
│   ├── chat.html
│   └── error.html
└── static/
    ├── css/
    │   └── app.css
    └── js/
        ├── common.js
        ├── conversations.js
        ├── users.js
        └── chat.js
```

## 📦 Requirements

- Python 3.10 or later is recommended
- pip
- Git
- A modern web browser

The standard edition uses the dependencies listed in `requirements.txt`:

```text
Flask>=3.1,<4
Bootstrap-Flask>=2.5,<3
```

The standalone edition only requires Flask.

## 🚀 Standard edition: complete installation and startup

Replace the repository URL below with the real HTTPS URL after publishing the project. The URL must normally end with `.git`.

Copy the entire command block. Each command remains on its own line, so it is easy to read and can still be copied with one button.

### Linux and macOS

```bash
git clone https://github.com/aaa/GreenChat.git
cd GreenChat
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
export CHAT_SECRET_KEY="replace-this-with-a-long-random-secret-key"
python3 greenchat_server.py
```

### Windows PowerShell

```powershell
git clone https://github.com/aaa/GreenChat.git
cd GreenChat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:CHAT_SECRET_KEY="replace-this-with-a-long-random-secret-key"
python greenchat_server.py
```

After the server starts, open:

```text
http://127.0.0.1:5000
```

The application automatically creates `chat.db`, the required database tables, and the `uploads` directory.

## 📦 Standalone edition: complete installation and startup

The standalone edition does not use the `templates` or `static` directories. It contains the complete front end and back end inside `greenchat_standalone.py`.

### Linux and macOS

```bash
git clone https://github.com/wangyifan349/GreenChat.git
cd GreenChat
python3 -m pip install --upgrade pip
python3 -m pip install Flask
export CHAT_SECRET_KEY="replace-this-with-a-long-random-secret-key"
python3 greenchat_standalone.py
```

### Windows PowerShell

```powershell
git clone https://github.com/wangyifan349/GreenChat.git
cd GreenChat
python -m pip install --upgrade pip
python -m pip install Flask
$env:CHAT_SECRET_KEY="replace-this-with-a-long-random-secret-key"
python greenchat_standalone.py
```

Do not run `greenchat_server.py` and `greenchat_standalone.py` on the same host and port at the same time.

## 🌐 Public deployment notes

The built-in Flask server is intended for development, testing, and trusted local environments. For public deployment, use a production WSGI server and a properly configured reverse proxy.

Important deployment requirements:

- Set a long, fixed `CHAT_SECRET_KEY`
- Disable Flask debug mode
- Use HTTPS
- Restrict database and upload-directory permissions
- Back up `chat.db` and `uploads` together
- Configure reverse-proxy upload limits and timeouts
- Monitor available disk space
- Never expose `chat.db` or `uploads` as unrestricted public static files

For Nginx, a 4 GiB request body requires at least:

```nginx
client_max_body_size 4G;
```

Large files are uploaded as a single HTTP request. Interrupted uploads cannot currently resume. Frequent multi-gigabyte transfers should use a future chunked and resumable upload implementation.

## 💾 Database and backups

GreenChat stores the following data in SQLite3:

- Usernames
- Password hashes
- Account creation times
- Message text
- Sender and recipient relationships
- Attachment metadata
- Message timestamps
- Read positions

Uploaded file contents are stored separately in `uploads`. A complete backup must include both `chat.db` and the entire `uploads` directory.

## ❤️ Sponsor

If GreenChat is useful to you, voluntary cryptocurrency donations can support continued development. The addresses below are placeholders and should be replaced by the project owner before publication.

```text
Bitcoin (BTC): bc1qxqfhumpqtnxrznkx9r4xsp8m6zsedtgusjns7p
Ethereum (ETH): 0x2d92f9e4d8ac7effa9cd7cd5eccd364cac7c201b
```

Verify every address carefully before publishing it. Cryptocurrency transactions are generally irreversible.

## ⚖️ License

GreenChat is licensed under the **GNU Affero General Public License v3.0 only** (`AGPL-3.0-only`).

You may use, modify, and redistribute the project under the license terms. If you modify the software and make it available for users to interact with over a network, you must offer those users access to the corresponding source code as required by the AGPL. See the included `LICENSE` file for the complete license text.

## 🔓 Security and encryption notice

GreenChat is **not an encrypted messaging tool**. It does not provide end-to-end encryption, encrypted message storage, encrypted attachments, or cryptographic identity verification.

Messages and uploaded files are readable by the server. A server administrator, or anyone who gains sufficient server access, may be able to read them. HTTPS protects traffic between the browser and server, but it does not prevent the server itself from accessing message content.

Do not use this project for highly sensitive, confidential, or regulated communications without adding an appropriate encryption design and completing a professional security review.
