const BRIDGE_BASE = "http://127.0.0.1:18888";
const statusBadge = document.getElementById("statusBadge");
const pageTitle = document.getElementById("pageTitle");
const pageUrl = document.getElementById("pageUrl");
const btnDlVideo = document.getElementById("btnDlVideo");
const btnDlAudio = document.getElementById("btnDlAudio");
const feedback = document.getElementById("feedback");

let currentTab = null;

// 1. Check bridge status
fetch(`${BRIDGE_BASE}/api/ping`)
    .then(res => res.json())
    .then(data => {
        if (data.status === "online") {
            statusBadge.innerText = "🟢 FlexDown Connected";
            statusBadge.classList.remove("offline");
        }
    })
    .catch(() => {
        statusBadge.innerText = "🔴 FlexDown Offline";
        statusBadge.classList.add("offline");
    });

// 2. Fetch active tab
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs.length > 0) {
        currentTab = tabs[0];
        pageTitle.innerText = currentTab.title || "No Title";
        pageUrl.innerText = currentTab.url || "";
    }
});

function sendDownload(isAudio) {
    if (!currentTab || !currentTab.url) return;

    feedback.innerText = "Sending to FlexDown...";
    feedback.className = "feedback";
    feedback.style.display = "block";

    const token = window.FLEXDOWN_SECURITY_TOKEN || "";
    fetch(`${BRIDGE_BASE}/api/download`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-FlexDown-Token": token
        },
        body: JSON.stringify({
            url: currentTab.url,
            title: currentTab.title,
            audio_only: isAudio,
            mode: "quick",
            token: token
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            feedback.innerText = "✓ Download Started in FlexDown!";
            feedback.className = "feedback success";
            setTimeout(() => window.close(), 1800);
        } else {
            throw new Error(data.error);
        }
    })
    .catch(err => {
        feedback.innerText = "Error: FlexDown app is not running!";
        feedback.className = "feedback error";
    });
}

btnDlVideo.addEventListener("click", () => sendDownload(false));
btnDlAudio.addEventListener("click", () => sendDownload(true));
