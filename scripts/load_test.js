#!/usr/bin/env node
/*
 * Minimal closed-loop HTTP load generator (Node built-ins only).
 *
 *   node scripts/load_test.js
 *   node scripts/load_test.js --port 8000 --path /api/v1/products?limit=20 --concurrency 200 --duration 10
 *   node scripts/load_test.js --method POST --path /api/v1/auth/customer/login \
 *     --body '{"email":"customer1@example.com","password":"Customer@123"}' --concurrency 20
 */
const http = require("http");

const args = process.argv.slice(2);
const arg = (name, fallback) => {
  const index = args.indexOf(`--${name}`);
  return index >= 0 && args[index + 1] !== undefined ? args[index + 1] : fallback;
};

const host = arg("host", "127.0.0.1");
const port = Number(arg("port", 8000));
const rawPath = arg("path", "/health");
// Git Bash rewrites leading-slash arguments into C:/Program Files/Git/... paths.
const path = rawPath.startsWith("/")
  ? rawPath
  : "/" + rawPath.replace(/^[A-Za-z]:[\\/].*?[\\/]Git[\\/]/i, "");
const concurrency = Number(arg("concurrency", 200));
const durationSeconds = Number(arg("duration", 10));
const method = arg("method", "GET").toUpperCase();
const body = arg("body", "");
const timeoutMs = Number(arg("timeout", 10000));

const agent = new http.Agent({ keepAlive: true, maxSockets: concurrency });
const latencies = [];
let ok = 0;
let failed = 0;
const errors = {};

function recordError(key) {
  failed += 1;
  errors[key] = (errors[key] || 0) + 1;
}

function request() {
  return new Promise((resolve) => {
    let finished = false;
    const started = process.hrtime.bigint();
    const finish = (error, statusCode) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      if (error) {
        recordError(error);
      } else {
        latencies.push(Number(process.hrtime.bigint() - started) / 1e6);
        if (statusCode === 200) ok += 1;
        else recordError(String(statusCode));
      }
      resolve();
    };
    const timer = setTimeout(() => {
      req.destroy();
      finish("timeout");
    }, timeoutMs);
    const options = { host, port, path, agent, method };
    if (body) {
      options.headers = {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
      };
    }
    const req = http.request(options, (res) => {
      res.resume();
      res.on("end", () => finish(null, res.statusCode));
    });
    req.on("error", (error) => finish(error.code || "error"));
    if (body) req.write(body);
    req.end();
  });
}

async function worker(stopAt) {
  while (Date.now() < stopAt) {
    await request();
  }
}

(async () => {
  const stopAt = Date.now() + durationSeconds * 1000;
  const startedAt = Date.now();
  await Promise.all(Array.from({ length: concurrency }, () => worker(stopAt)));
  const elapsed = (Date.now() - startedAt) / 1000;
  latencies.sort((a, b) => a - b);
  const percentile = (p) =>
    latencies[Math.min(latencies.length - 1, Math.floor(latencies.length * p))] || 0;
  const total = latencies.length + (errors.timeout || 0);

  console.log(
    JSON.stringify(
      {
        target: `${host}:${port}${path}`,
        method,
        concurrency,
        seconds: Number(elapsed.toFixed(2)),
        requests: total,
        ok,
        failed,
        errors,
        rps: Number((total / elapsed).toFixed(1)),
        p50_ms: Number(percentile(0.5).toFixed(1)),
        p95_ms: Number(percentile(0.95).toFixed(1)),
        p99_ms: Number(percentile(0.99).toFixed(1)),
        max_ms: Number((latencies[latencies.length - 1] || 0).toFixed(1)),
      },
      null,
      2
    )
  );
  agent.destroy();
})();
