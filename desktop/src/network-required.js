// Controls the retry interaction on the network-required screen.

const retryButton = document.querySelector("#retry-button");
const connectionStatus = document.querySelector("#connection-status");

retryButton.addEventListener("click", async () => {
  retryButton.disabled = true;
  retryButton.textContent = "Checking connection…";
  connectionStatus.textContent = "Attempting to reach the company service…";

  try {
    const result = await window.desktopAPI.retryConnection();

    if (!result.available) {
      connectionStatus.textContent =
        "The company service is still unavailable. Check your network or VPN.";
    }
  } catch {
    connectionStatus.textContent =
      "The connection check failed. Please try again.";
  } finally {
    retryButton.disabled = false;
    retryButton.textContent = "Retry connection";
  }
});