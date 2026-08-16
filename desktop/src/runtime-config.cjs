// Loads and validates non-secret desktop service URLs from IT-managed configuration.

const fs = require("node:fs");
const path = require("node:path");

const DEFAULT_DASHBOARD_URL = "http://127.0.0.1:3000";
const CONFIG_DIRECTORY_NAME = "Jira AI Intelligence";
const CONFIG_FILE_NAME = "desktop-config.json";

function requireHttpUrl(value, settingName) {
  let parsed;

  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`${settingName} must be a valid URL.`);
  }

  if (!new Set(["http:", "https:"]).has(parsed.protocol)) {
    throw new Error(`${settingName} must use HTTP or HTTPS.`);
  }

  return parsed.toString().replace(/\/$/, "");
}

function readMachineConfig(configPath) {
  if (!configPath || !fs.existsSync(configPath)) {
    return {};
  }

  const parsed = JSON.parse(fs.readFileSync(configPath, "utf8"));

  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("Desktop configuration must be a JSON object.");
  }

  return parsed;
}

function loadRuntimeConfig(environment = process.env) {
  const defaultConfigPath = environment.PROGRAMDATA
    ? path.join(
        environment.PROGRAMDATA,
        CONFIG_DIRECTORY_NAME,
        CONFIG_FILE_NAME,
      )
    : null;
  const configPath = environment.JIRA_AI_CONFIG_FILE || defaultConfigPath;
  const machineConfig = readMachineConfig(configPath);

  const dashboardUrl = requireHttpUrl(
    environment.JIRA_AI_DESKTOP_URL ||
      machineConfig.dashboardUrl ||
      DEFAULT_DASHBOARD_URL,
    "dashboardUrl",
  );
  const healthcheckUrl = requireHttpUrl(
    environment.JIRA_AI_HEALTH_URL ||
      machineConfig.healthcheckUrl ||
      new URL("/container-health", dashboardUrl).toString(),
    "healthcheckUrl",
  );

  return Object.freeze({
    configPath,
    dashboardUrl,
    healthcheckUrl,
  });
}

module.exports = {
  DEFAULT_DASHBOARD_URL,
  loadRuntimeConfig,
};
