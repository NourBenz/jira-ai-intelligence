// Runs the secure Electron desktop shell, connectivity gate, and Windows lifecycle behavior.
const {
  app,
  BrowserWindow,
  ipcMain,
  net,
  shell,
} = require("electron");

const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { loadRuntimeConfig } = require("./runtime-config.cjs");

// Some Windows GPU drivers produce Chromium compositor artifacts. This
// dashboard does not require GPU acceleration, so software rendering is safer.
app.disableHardwareAcceleration();

const runtimeConfig = loadRuntimeConfig();
const DASHBOARD_URL = runtimeConfig.dashboardUrl;
const HEALTHCHECK_URL = runtimeConfig.healthcheckUrl;

const NETWORK_PAGE_PATH = path.join(
  __dirname,
  "network-required.html",
);

const CONNECTION_CHECKING_PAGE_PATH = path.join(
  __dirname,
  "connection-checking.html",
);

const NETWORK_PAGE_URL = pathToFileURL(NETWORK_PAGE_PATH).href;
const CONNECTION_CHECKING_PAGE_URL = pathToFileURL(
  CONNECTION_CHECKING_PAGE_PATH,
).href;

let mainWindow = null;

const WINDOWS_APP_USER_MODEL_ID = "com.nourb.jira-ai-intelligence";
const LEGACY_WINDOWS_LOGIN_ITEM_NAMES = [
  "com.squirrel.jira_ai_intelligence.JiraAIIntelligence",
];

const hasSingleInstanceLock = app.requestSingleInstanceLock();

function configureWindowsLoginStartup() {
  if (process.platform !== "win32" || !app.isPackaged) {
    return;
  }

  const versionedAppDirectory = path.dirname(process.execPath);
  const isSquirrelInstallation = path
    .basename(versionedAppDirectory)
    .toLowerCase()
    .startsWith("app-");

  if (!isSquirrelInstallation) {
    return;
  }

  const squirrelLauncher = path.resolve(
    versionedAppDirectory,
    "..",
    path.basename(process.execPath),
  );

  for (const legacyName of LEGACY_WINDOWS_LOGIN_ITEM_NAMES) {
    app.setLoginItemSettings({
      openAtLogin: false,
      path: squirrelLauncher,
      args: [],
      name: legacyName,
    });
  }

  app.setLoginItemSettings({
    openAtLogin: true,
    path: squirrelLauncher,
    args: [],
    name: WINDOWS_APP_USER_MODEL_ID,
  });
}

function focusMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return;
  }

  if (mainWindow.isMinimized()) {
    mainWindow.restore();
  }

  mainWindow.show();
  mainWindow.focus();
}

function isTrustedDashboardUrl(candidateUrl) {
  try {
    const candidate = new URL(candidateUrl);
    const dashboard = new URL(DASHBOARD_URL);

    return candidate.origin === dashboard.origin;
  } catch {
    return false;
  }
}

async function isCompanyServiceAvailable() {
  try {
    const response = await net.fetch(HEALTHCHECK_URL, {
      method: "GET",
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    return response.ok;
  } catch {
    return false;
  }
}

async function loadNetworkRequiredPage() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return;
  }

  await mainWindow.loadFile(NETWORK_PAGE_PATH);
}

async function loadDashboard() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return false;
  }

  const available = await isCompanyServiceAvailable();

  if (!available) {
    await loadNetworkRequiredPage();
    return false;
  }

  try {
    await mainWindow.loadURL(DASHBOARD_URL);
    return true;
  } catch {
    await loadNetworkRequiredPage();
    return false;
  }
}

function configureWindowSecurity(window) {
  window.webContents.on("will-navigate", (event, targetUrl) => {
    const trustedDashboard = isTrustedDashboardUrl(targetUrl);
    const trustedNetworkPage = targetUrl === NETWORK_PAGE_URL;
    const trustedCheckingPage = targetUrl === CONNECTION_CHECKING_PAGE_URL;

    if (!trustedDashboard && !trustedNetworkPage && !trustedCheckingPage) {
      event.preventDefault();
    }
  });

  window.webContents.setWindowOpenHandler(({ url }) => {
    try {
      const target = new URL(url);

      if (target.protocol === "https:") {
        void shell.openExternal(url);
      }
    } catch {
      // Invalid external addresses are ignored.
    }

    return { action: "deny" };
  });

  window.webContents.session.setPermissionRequestHandler(
    (_webContents, _permission, callback) => {
      callback(false);
    },
  );
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1000,
    minHeight: 650,
    show: false,
    backgroundColor: "#f4f7fb",
    autoHideMenuBar: true,
    icon: path.join(__dirname, "..", "assets", "icon.ico"),
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  });

  configureWindowSecurity(mainWindow);

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  void (async () => {
    await mainWindow.loadFile(CONNECTION_CHECKING_PAGE_PATH);
    await loadDashboard();
  })();
}

if (!hasSingleInstanceLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    focusMainWindow();
  });

  app.whenReady().then(() => {
    if (process.platform === "win32") {
      app.setAppUserModelId(WINDOWS_APP_USER_MODEL_ID);
    }

    configureWindowsLoginStartup();

    ipcMain.handle("connection:retry", async (event) => {
      if (
        !mainWindow ||
        mainWindow.isDestroyed() ||
        event.sender !== mainWindow.webContents ||
        event.senderFrame?.url !== NETWORK_PAGE_URL
      ) {
        return { available: false };
      }

      const available = await loadDashboard();

      return { available };
    });

    createMainWindow();

    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
      } else {
        focusMainWindow();
      }
    });
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
      app.quit();
    }
  });
}
