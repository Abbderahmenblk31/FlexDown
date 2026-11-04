// ==========================================================================
// FlexDown Service Worker, Download Interception & Context Menu Integration
// ==========================================================================

try {
    importScripts("token.js");
} catch (e) {
    // Firefox or context where importScripts is not available
}

const BRIDGE_URL = "http://127.0.0.1:18888/api/download";

// صيغ الملفات التي يتم التقاطها تلقائياً من المتصفح مثل IDM تماماً
const INTERCEPT_EXTENSIONS = new Set([
    "apk", "exe", "msi", "zip", "rar", "7z", "iso", "tar", "gz", "bz2", "xz",
    "dmg", "pkg", "deb", "rpm", "bin",
    "mp4", "mkv", "avi", "mov", "flv", "webm", "ts", "m4v",
    "mp3", "m4a", "wav", "flac", "aac", "ogg", "opus",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"
]);

// تجنب التقاط الروابط المكررة في نفس الثانية
const _recentlyIntercepted = new Set();

chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "flexdown_download_link",
        title: "Download with FlexDown",
        contexts: ["link", "video", "audio", "page"]
    });

    chrome.contextMenus.create({
        id: "flexdown_download_audio",
        title: "Download Audio (MP3) with FlexDown",
        contexts: ["link", "video", "audio", "page"]
    });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
    const targetUrl = info.linkUrl || info.srcUrl || info.pageUrl;
    if (!targetUrl) return;

    const isAudio = (info.menuItemId === "flexdown_download_audio");
    let token = "";
    if (typeof FLEXDOWN_SECURITY_TOKEN !== "undefined") {
        token = FLEXDOWN_SECURITY_TOKEN;
    }

    fetch(BRIDGE_URL, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-FlexDown-Token": token
        },
        body: JSON.stringify({
            url: targetUrl,
            title: tab ? tab.title : "",
            audio_only: isAudio,
            token: token,
            mode: "quick"
        })
    }).catch(err => {
        console.warn("[FlexDown Extension] Context menu dispatch error:", err);
    });
});

// ==========================================================================
// 🚀 IDM-Style Automatic Browser Download Interception (التقاط التنزيلات التلقائي)
// ==========================================================================
if (chrome.downloads && chrome.downloads.onCreated) {
    chrome.downloads.onCreated.addListener(async (item) => {
        if (!item || !item.url) return;
        if (item.url.startsWith("blob:") || item.url.startsWith("data:") || item.url.startsWith("filesystem:")) {
            return;
        }

        const rawUrl = (item.finalUrl || item.url || "").trim();
        if (_recentlyIntercepted.has(rawUrl)) {
            return;
        }

        const fn = (item.filename || "").toLowerCase();
        const urlLower = rawUrl.toLowerCase();

        let shouldIntercept = false;

        // 1. التحقق من الامتدادات المستهدفة (.apk, .exe, .iso, .zip, etc.)
        for (const ext of INTERCEPT_EXTENSIONS) {
            if (fn.endsWith("." + ext) || urlLower.includes("." + ext) || urlLower.includes("b/apk/")) {
                shouldIntercept = true;
                break;
            }
        }

        // 2. التحقق من نوع الملف MIME إذا كان تطبيقاً أو حزمة
        if (!shouldIntercept && item.mime) {
            const m = item.mime.toLowerCase();
            if (m.includes("application/vnd.android") || m.includes("application/octet-stream") ||
                m.includes("application/x-") || m.includes("application/zip")) {
                shouldIntercept = true;
            }
        }

        if (shouldIntercept) {
            _recentlyIntercepted.add(rawUrl);
            setTimeout(() => _recentlyIntercepted.delete(rawUrl), 5000);

            console.log("[FlexDown] Intercepting browser download to FlexDown:", rawUrl);

            // إلغاء تنزيل المتصفح البطيء فوراً
            try {
                await chrome.downloads.cancel(item.id);
                await chrome.downloads.erase({ id: item.id });
            } catch (ex) {
                console.warn("[FlexDown] Could not cancel native download:", ex);
            }

            let token = "";
            if (typeof FLEXDOWN_SECURITY_TOKEN !== "undefined") {
                token = FLEXDOWN_SECURITY_TOKEN;
            }

            fetch(BRIDGE_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-FlexDown-Token": token
                },
                body: JSON.stringify({
                    url: rawUrl,
                    title: item.filename ? item.filename.replace(/^.*[\\\/]/, '') : "",
                    filesize: item.totalBytes || 0,
                    token: token,
                    mode: "dialog"
                })
            }).catch(err => {
                console.warn("[FlexDown] Failed to send download to local bridge:", err);
            });
        }
    });
}
