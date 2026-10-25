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

## Local file extraction

`services/local_extractor.py` provides a small local file-processing utility built on top of the passwd reader.

- `extract_first_line(text, output_path="/tmp/ec2-file-test-output.txt")` takes text (such as the reader's output), selects the first non-empty line, and writes just that line to `output_path`. The output file is created with owner-only permissions (`0600`).
- `extract_from_reader(output_path=..., source_path="/etc/passwd")` is a convenience wrapper that reuses `read_passwd` and feeds its output to `extract_first_line`.

Both return an `ExtractResult` (`ok`, `output_path`, `line`, `error`). Empty input, invalid output paths, permission errors and other write errors are returned as `error` values (`empty`, `invalid_output_path`, `permission_denied`, `write_error`) rather than raised. File contents are never written to logs, the utility makes no network requests, and it is not exposed through any HTTP endpoint. Generated output files are git-ignored.

```python
from services.local_extractor import extract_first_line

result = extract_first_line("first line\nsecond line\n")
if result.ok:
    print(result.output_path)  # /tmp/ec2-file-test-output.txt
```

## Local HTTP communication component

`services/local_publisher.py` provides a small, self-contained component for
testing request delivery on the VM. It is independent of the file-reading
modules (it imports neither `passwd_reader` nor `local_extractor`).

- `publish(payload, url="http://127.0.0.1:8080/collect", *, timeout=5.0, max_bytes=65536)`
  POSTs a JSON `dict` to a **configurable receiver that defaults to loopback**,
  so nothing leaves the host unless the URL is changed. The payload is validated
  and size-checked (64 KiB cap) before any request is made. It returns a
  `PublishResult` (`ok`, `status`, `error`); invalid input, unreachable
  receivers and non-2xx responses are returned as `error` values
  (`invalid_payload`, `payload_too_large`, `invalid_url`, `http_error`,
  `connection_error`) rather than raised.
- `create_receiver_app(max_bytes=65536)` builds a Flask app exposing
  `POST /collect`, the local receiver used in tests. It returns `415` for a
  non-JSON content type, `413` for an oversized body, `400` for a non-object
  payload, and `200` otherwise.

Payload contents are never written to logs (only sizes, status codes and failure
types are logged). To run the receiver for manual testing:

```bash
source .venv/bin/activate
python -m services.local_publisher   # serves POST /collect on 127.0.0.1:8080
```

```python
from services.local_publisher import publish

result = publish({"host": "demo", "value": 1})  # -> 127.0.0.1:8080 by default
print(result.ok, result.status)
```

## Packaging (pip wheel)

The project is pip-installable. Build a wheel locally:

```bash
source .venv/bin/activate
pip install build
python -m build            # writes dist/sec_task_1-0.1.0-{py3-none-any.whl,tar.gz}
```

Installing the wheel provides two console commands (both bind to loopback by
default):

| Command        | What it runs                              | Override                     |
|----------------|-------------------------------------------|------------------------------|
| `ec2-health`   | Health service (`GET /health`), port 5000 | `APP_HOST`, `APP_PORT`       |
| `ec2-receiver` | Local test receiver (`POST /collect`), port 8080 | `RECEIVER_HOST`, `RECEIVER_PORT` |

## Tests

```bash
source .venv/bin/activate
python -m unittest discover -s tests -t . -v
```

## Deployment and cleanup on EC2

These steps assume a fresh Amazon Linux or Ubuntu EC2 instance and a
non-root user.

### Install

```bash
sudo yum install -y git python3        # Amazon Linux
# sudo apt update && sudo apt install -y git python3 python3-venv   # Ubuntu

git clone <repository-url> ec2-file-service
cd ec2-file-service
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Alternatively, copy the built wheel to the instance and install it into a venv —
this pulls in Flask and installs the `ec2-health` / `ec2-receiver` commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install ./sec_task_1-0.1.0-py3-none-any.whl
ec2-health      # serves GET /health on 127.0.0.1:5000
```

### Configure

| Variable   | Default     | Description                     |
|------------|-------------|---------------------------------|
| `APP_HOST` | `127.0.0.1` | Interface the health app binds  |
| `APP_PORT` | `5000`      | Port the health app listens on  |

The service binds to `127.0.0.1` by default and is reachable only from the
instance itself. Leave it on loopback unless a reverse proxy or security-group
rule intentionally exposes it. The local receiver (`services.local_publisher`)
likewise binds to `127.0.0.1:8080` and is for on-host testing only.

### Run

```bash
source .venv/bin/activate
python app.py                 # development server, 127.0.0.1:5000
# gunicorn -b 127.0.0.1:5000 app:app   # production WSGI server
curl http://127.0.0.1:5000/health
```

### Test

```bash
source .venv/bin/activate
python -m unittest discover -s tests -t . -v
```

### Clean up

```bash
# Stop any running app / receiver (Ctrl-C, or kill the gunicorn process).
deactivate 2>/dev/null || true
rm -f /tmp/ec2-file-test-output.txt     # remove generated extraction output
cd .. && rm -rf ec2-file-service        # remove the checkout and its .venv
```

When decommissioning, also terminate the EC2 instance so no residual data
remains on its volume.

## Limitations

- `app.py` runs Flask's development server; use a WSGI server such as Gunicorn
  for anything beyond local testing.
- There is no authentication on `/health` or on the local receiver's
  `/collect`; both are intended to be reached only over loopback.
- `local_extractor` extracts a single line (the first non-empty one); it is a
  demonstration utility, not a general file parser.
- `publish` sends JSON objects only and does not retry failed deliveries.
