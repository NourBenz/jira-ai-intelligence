// Configures secure packaging for the Jira AI Intelligence desktop client.

const path = require("node:path");

const electronZipDir = process.env.ELECTRON_ZIP_DIR;
const iconPath = path.join(__dirname, "assets", "icon.ico");

module.exports = {
  outDir: "../desktop-dist",
  buildIdentifier: require("./package.json").version,

  packagerConfig: {
    asar: true,
    name: "Jira AI Intelligence",
    executableName: "JiraAIIntelligence",
    icon: iconPath,
    ...(electronZipDir ? { electronZipDir } : {}),
  },

  rebuildConfig: {},

  makers: [
    {
      name: "@electron-forge/maker-squirrel",
      config: {
        name: "jira_ai_intelligence",
        setupExe: "JiraAIIntelligenceSetup.exe",
        setupIcon: iconPath,
      },
    },
  ],
};
