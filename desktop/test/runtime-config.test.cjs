// Verifies safe defaults, machine configuration, overrides, and URL validation.

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  DEFAULT_DASHBOARD_URL,
  loadRuntimeConfig,
} = require("../src/runtime-config.cjs");

test("uses the local prototype URLs when no company config exists", () => {
  const config = loadRuntimeConfig({});

  assert.equal(config.dashboardUrl, DEFAULT_DASHBOARD_URL);
  assert.equal(config.healthcheckUrl, "http://127.0.0.1:3000/container-health");
});

test("loads IT-managed company URLs from the selected config file", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "jira-ai-desktop-"));
  const configPath = path.join(directory, "desktop-config.json");

  fs.writeFileSync(
    configPath,
    JSON.stringify({
      dashboardUrl: "https://jira-ai.company.example/",
      healthcheckUrl: "https://jira-ai.company.example/container-health",
    }),
  );

  const config = loadRuntimeConfig({ JIRA_AI_CONFIG_FILE: configPath });

  assert.equal(config.dashboardUrl, "https://jira-ai.company.example");
  assert.equal(
    config.healthcheckUrl,
    "https://jira-ai.company.example/container-health",
  );
});

test("environment variables override machine configuration", () => {
  const config = loadRuntimeConfig({
    JIRA_AI_DESKTOP_URL: "https://override.company.example/app/",
    JIRA_AI_HEALTH_URL: "https://override.company.example/health/",
  });

  assert.equal(config.dashboardUrl, "https://override.company.example/app");
  assert.equal(config.healthcheckUrl, "https://override.company.example/health");
});

test("rejects executable and file URLs", () => {
  assert.throws(
    () => loadRuntimeConfig({ JIRA_AI_DESKTOP_URL: "file:///unsafe.html" }),
    /HTTP or HTTPS/,
  );
});
