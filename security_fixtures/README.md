# security_fixtures

Security-test fixture. It is NOT part of the application and is never packaged
or installed (`pyproject.toml` only packages `app*`).

All data here is fabricated. Network activity is limited to 127.0.0.1.
The lifecycle hook under `lifecycle_hook/` is meant for static analysis and is
never executed: its manifest is named `package.fixture.json`, so npm/yarn/pnpm
do not recognise it.
