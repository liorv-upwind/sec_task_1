# Flask Health Service

A minimal Flask service intended to run on an EC2 Linux VM. It currently exposes a single health endpoint.

## Requirements

- Python 3.9 or newer
- `python3-venv` (on Debian/Ubuntu: `sudo apt install python3-venv`; Amazon Linux ships `venv` with `python3`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Running

```bash
source .venv/bin/activate
python app.py
```

The service binds to `127.0.0.1:5000` by default, so it is reachable only from the VM itself. To change this, set these environment variables:

| Variable   | Default     | Description        |
|------------|-------------|--------------------|
| `APP_HOST` | `127.0.0.1` | Interface to bind  |
| `APP_PORT` | `5000`      | Port to listen on  |

`python app.py` uses Flask's development server. For production, run the app behind a WSGI server such as Gunicorn (`gunicorn -b 127.0.0.1:5000 app:app`), with a reverse proxy in front of it if it needs to be reachable externally.

## Endpoints

### `GET /health`

Returns the service status.

```bash
curl http://127.0.0.1:5000/health
```

```json
{"status": "ok"}
```

## System passwd reader

`services/passwd_reader.py` provides `read_passwd(path="/etc/passwd")`, which reads the file with the process's normal permissions and returns a `PasswdReadResult` (`ok`, `content`, `error`). Missing files, permission errors, directories, empty files and other read errors are returned as `error` values (`not_found`, `permission_denied`, `not_a_file`, `empty`, `read_error`) rather than raised. Log messages include only the path and the failure type, never the file contents. The reader is not exposed through any HTTP endpoint.

## Tests

```bash
source .venv/bin/activate
python -m unittest discover -s tests -t . -v
```
