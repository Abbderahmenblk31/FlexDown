// ==UserScript==
// @name         FlexDown Video Downloader Panel
// @namespace    https://flexdown.app/
// @version      1.2.0
// @description  Adds a floating IDM-style FlexDown logo over any online video to download video or audio with multiple resolutions and bitrates.
// @author       FlexDown Team
// @match        *://*/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    const BRIDGE_URL = "http://127.0.0.1:18888/api/download";

    function injectStyles() {
        if (document.getElementById("flexdown-styles")) return;
        const style = document.createElement("style");
        style.id = "flexdown-styles";
        style.textContent = `
            .flexdown-panel-container {
                position: absolute;
                top: 14px;
                right: 14px;
                z-index: 2147483647 !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 13px;
                direction: ltr;
                text-align: left;
                user-select: none;
                opacity: 0.90;
                transition: opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1), transform 0.2s ease;
            }
            .flexdown-panel-container:hover { opacity: 1 !important; transform: translateY(-1px); }
            .flexdown-btn {
                display: flex;
                align-items: center;
                gap: 7px;
                background: linear-gradient(135deg, #16213e 0%, #0f172a 100%);
                border: 1px solid rgba(0, 240, 255, 0.5);
                color: #ffffff !important;
                padding: 6px 12px 6px 9px;
                border-radius: 20px;
                cursor: pointer;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5), 0 0 10px rgba(0, 240, 255, 0.25);
                backdrop-filter: blur(8px);
                transition: all 0.2s ease;
            }
            .flexdown-btn:hover {
                background: linear-gradient(135deg, #1a2744 0%, #1e293b 100%);
                border-color: #00f0ff;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.6), 0 0 16px rgba(0, 240, 255, 0.45);
            }
            .flexdown-logo {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                background: #e94560;
                color: #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 800;
                font-size: 11px;
            }
            .flexdown-btn-text {
                font-weight: 600;
                font-size: 12px;
                letter-spacing: 0.3px;
                color: #f1f5f9;
            }
            .flexdown-arrow {
                font-size: 9px;
                margin-left: 2px;
                color: #38bdf8;
                transition: transform 0.2s ease;
            }
            .flexdown-panel-container.open .flexdown-arrow {
                transform: rotate(180deg);
            }
            .flexdown-menu {
                display: none;
                position: absolute;
                top: calc(100% + 6px);
                right: 0;
                background: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 10px;
                padding: 6px;
                min-width: 230px;
                box-shadow: 0 12px 28px rgba(0, 0, 0, 0.7), 0 0 1px rgba(255, 255, 255, 0.15);
                backdrop-filter: blur(14px);
                flex-direction: column;
                gap: 2px;
                z-index: 2147483647;
            }
            .flexdown-panel-container.open .flexdown-menu {
                display: flex;
                animation: flexdownFadeIn 0.18s cubic-bezier(0.4, 0, 0.2, 1);
            }
            @keyframes flexdownFadeIn {
                from { opacity: 0; transform: translateY(-6px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .flexdown-header {
                font-size: 10.5px;
                font-weight: 700;
                color: #94a3b8;
                padding: 5px 8px 3px 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .flexdown-divider {
                height: 1px;
                background: #1e293b;
                margin: 4px 6px;
            }
            .flexdown-item {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px 10px;
                border-radius: 6px;
                color: #e2e8f0;
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                transition: background 0.15s ease, color 0.15s ease;
                white-space: nowrap;
            }
            .flexdown-item:hover {
                background: #1e293b;
                color: #38bdf8;
            }
            .flexdown-item.audio:hover {
                color: #fb7185;
            }
            .flexdown-badge {
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 4px;
                min-width: 38px;
                text-align: center;
                flex-shrink: 0;
            }
            .flexdown-badge.hd { background: #0284c7; color: #ffffff; }
            .flexdown-badge.sd { background: #334155; color: #cbd5e1; }
            .flexdown-badge.audio { background: #e11d48; color: #ffffff; }
            .flexdown-label { flex: 1; font-weight: 500; font-size: 12px; }
            .flexdown-ext { font-size: 10.5px; color: #64748b; font-weight: 600; }
            .flexdown-item-icon { font-size: 13px; width: 18px; text-align: center; }
            .flexdown-btn.success {
                background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
                border-color: #34d399 !important;
                box-shadow: 0 0 14px rgba(16, 185, 129, 0.6) !important;
            }
            .flexdown-tooltip {
                position: absolute;
                top: calc(100% + 6px);
                right: 0;
                background: #e11d48;
                color: #ffffff;
                font-size: 11px;
                padding: 6px 10px;
                border-radius: 6px;
                white-space: nowrap;
                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                display: none;
                z-index: 2147483647;
            }
        `;
        document.head.appendChild(style);
    }

    function resolveVideoMedia(videoElem, container) {
        const pageUrl = window.location.href;
        let title = document.title || "Video";

        if (pageUrl.includes("youtube.com") || pageUrl.includes("youtu.be")) {
            let videoId = new URLSearchParams(window.location.search).get("v");
            if (videoId) return { url: "https://www.youtube.com/watch?v=" + videoId, title: title };
            if (pageUrl.includes("/shorts/")) return { url: pageUrl.split("?")[0], title: title };
        }

        if (pageUrl.includes("tiktok.com")) {
            const exactMatch = pageUrl.match(/(https?:\/\/(?:www\.)?tiktok\.com\/@[^\/]+\/video\/\d+)/i);
            if (exactMatch) return { url: exactMatch[1], title: title };

            let curr = videoElem || container;
            while (curr && curr !== document.body) {
                if (curr.id) {
                    const xgMatch = curr.id.match(/(?:xgwrapper|xgplayer).*?(\d{16,22})/i);
                    if (xgMatch) {
                        const authorLink = curr.querySelector('a[href*="/@"]');
                        const authorMatch = authorLink ? authorLink.href.match(/@([a-zA-Z0-9_.-]+)/) : null;
                        const author = authorMatch ? `@${authorMatch[1]}` : "@tiktok";
                        return { url: `https://www.tiktok.com/${author}/video/${xgMatch[1]}`, title: title };
                    }
                }

                const videoLink = curr.querySelector('a[href*="/video/"]');
                if (videoLink && videoLink.href) {
                    const m = videoLink.href.match(/(https?:\/\/(?:www\.)?tiktok\.com\/@[^\/]+\/video\/\d+)/i);
                    if (m) return { url: m[1], title: title };
                    const idMatch = videoLink.href.match(/\/video\/(\d{16,22})/);
                    if (idMatch) return { url: `https://www.tiktok.com/@tiktok/video/${idMatch[1]}`, title: title };
                }

                const authorLink = curr.querySelector('a[href*="/@"]');
                if (authorLink && authorLink.href) {
                    const digitsMatch = curr.innerHTML.match(/(\d{18,21})/);
                    if (digitsMatch) {
                        const authorMatch = authorLink.href.match(/@([a-zA-Z0-9_.-]+)/);
                        const author = authorMatch ? `@${authorMatch[1]}` : "@tiktok";
                        return { url: `https://www.tiktok.com/${author}/video/${digitsMatch[1]}`, title: title };
                    }
                }

                curr = curr.parentElement;
            }

            const feedCards = document.querySelectorAll(
                '[data-e2e="feed-video"], [data-e2e="recommend-list-item-container"], div[class*="DivItemContainer"], div[class*="ItemContainer"], div[class*="DivVideoWrapper"], article'
            );
            for (const card of feedCards) {
                if (card.contains(videoElem) || card.contains(container)) {
                    const xgInside = card.querySelector('[id*="xgwrapper"], [id*="xgplayer"]');
                    if (xgInside && xgInside.id) {
                        const m = xgInside.id.match(/(\d{16,22})/);
                        if (m) {
                            const authorLink = card.querySelector('a[href*="/@"]');
                            const authorMatch = authorLink ? authorLink.href.match(/@([a-zA-Z0-9_.-]+)/) : null;
                            const author = authorMatch ? `@${authorMatch[1]}` : "@tiktok";
                            return { url: `https://www.tiktok.com/${author}/video/${m[1]}`, title: title };
                        }
                    }

                    const link = card.querySelector('a[href*="/video/"]');
                    if (link && link.href) {
                        const m = link.href.match(/(https?:\/\/(?:www\.)?tiktok\.com\/@[^\/]+\/video\/\d+)/i);
                        if (m) return { url: m[1], title: title };
                        const idMatch = link.href.match(/\/video\/(\d{16,22})/);
                        if (idMatch) return { url: `https://www.tiktok.com/@tiktok/video/${idMatch[1]}`, title: title };
                    }

                    const digitsMatch = card.innerHTML.match(/(\d{18,21})/);
                    if (digitsMatch) {
                        return { url: `https://www.tiktok.com/@tiktok/video/${digitsMatch[1]}`, title: title };
                    }
                }
            }

            if (videoElem) {
                const src = videoElem.currentSrc || videoElem.src;
                if (src && src.startsWith("http") && !src.startsWith("blob:")) return { url: src, title: title };
            }

            if (pageUrl.includes("/foryou") || pageUrl.endsWith("tiktok.com") || pageUrl.endsWith("tiktok.com/")) {
                return {
                    url: null,
                    error: "جاري التحميل... اضغط على الفيديو إذا كان في بداية الصفحة"
                };
            }
        }

        if (pageUrl.includes("instagram.com")) {
            if (pageUrl.includes("/reel/") || pageUrl.includes("/p/")) return { url: pageUrl.split("?")[0], title: title };
            let curr = videoElem || container;
            for (let i = 0; i < 8 && curr && curr !== document.body; i++) {
                const link = curr.querySelector('a[href*="/reel/"], a[href*="/p/"]');
                if (link && link.href) return { url: link.href.split("?")[0], title: title };
                curr = curr.parentElement;
            }
        }

        if (pageUrl.includes("facebook.com")) {
            if (pageUrl.includes("/watch/") || pageUrl.includes("/reel/") || pageUrl.includes("/videos/")) return { url: pageUrl, title: title };
            let curr = videoElem || container;
            for (let i = 0; i < 8 && curr && curr !== document.body; i++) {
                const link = curr.querySelector('a[href*="/videos/"], a[href*="/reel/"], a[href*="watch?v="]');
                if (link && link.href) return { url: link.href, title: title };
                curr = curr.parentElement;
            }
        }

        if (pageUrl.includes("twitter.com") || pageUrl.includes("x.com")) {
            if (pageUrl.includes("/status/")) return { url: pageUrl.split("?")[0], title: title };
            let curr = videoElem || container;
            for (let i = 0; i < 8 && curr && curr !== document.body; i++) {
                const link = curr.querySelector('a[href*="/status/"]');
                if (link && link.href) return { url: link.href.split("?")[0], title: title };
                curr = curr.parentElement;
            }
        }

        if (videoElem) {
            const src = videoElem.currentSrc || videoElem.src;
            if (src && src.startsWith("http") && !src.startsWith("blob:")) return { url: src, title: title };
        }

        return { url: pageUrl, title: title };
    }

    function createFlexDownPanel(container, videoElem) {
        if (container.querySelector(".flexdown-panel-container")) return;

        const computedPos = window.getComputedStyle(container).position;
        if (computedPos === "static") {
            container.style.position = "relative";
        }

        const panel = document.createElement("div");
        panel.className = "flexdown-panel-container";

        panel.innerHTML = `
            <div class="flexdown-btn" title="Download with FlexDown">
                <div class="flexdown-logo">⬇</div>
                <span class="flexdown-btn-text">FlexDown</span>
                <span class="flexdown-arrow">▼</span>
            </div>
            <div class="flexdown-menu">
                <div class="flexdown-header">🎬 Video (MP4)</div>
                <div class="flexdown-item video" data-action="video" data-res="1080">
                    <span class="flexdown-badge hd">1080p</span>
                    <span class="flexdown-label">Full HD</span>
                    <span class="flexdown-ext">MP4</span>
                </div>
                <div class="flexdown-item video" data-action="video" data-res="720">
                    <span class="flexdown-badge hd">720p</span>
                    <span class="flexdown-label">HD Quality</span>
                    <span class="flexdown-ext">MP4</span>
                </div>
                <div class="flexdown-item video" data-action="video" data-res="480">
                    <span class="flexdown-badge sd">480p</span>
                    <span class="flexdown-label">Standard (خفيف)</span>
                    <span class="flexdown-ext">MP4</span>
                </div>

                <div class="flexdown-divider"></div>

                <div class="flexdown-header">🎵 Audio (MP3)</div>
                <div class="flexdown-item audio" data-action="audio" data-kbps="320">
                    <span class="flexdown-badge audio">320k</span>
                    <span class="flexdown-label">Ultra Quality</span>
                    <span class="flexdown-ext">MP3</span>
                </div>
                <div class="flexdown-item audio" data-action="audio" data-kbps="256">
                    <span class="flexdown-badge audio">256k</span>
                    <span class="flexdown-label">High Quality</span>
                    <span class="flexdown-ext">MP3</span>
                </div>
                <div class="flexdown-item audio" data-action="audio" data-kbps="192">
                    <span class="flexdown-badge audio">192k</span>
                    <span class="flexdown-label">Medium Quality</span>
                    <span class="flexdown-ext">MP3</span>
                </div>
                <div class="flexdown-item audio" data-action="audio" data-kbps="128">
                    <span class="flexdown-badge audio">128k</span>
                    <span class="flexdown-label">Standard Quality</span>
                    <span class="flexdown-ext">MP3</span>
                </div>

                <div class="flexdown-divider"></div>

                <div class="flexdown-item dialog" data-action="dialog">
                    <span class="flexdown-item-icon">⚙️</span>
                    <span class="flexdown-label">More Formats & Quality...</span>
                </div>
            </div>
            <div class="flexdown-tooltip"></div>
        `;

        const btn = panel.querySelector(".flexdown-btn");
        const menu = panel.querySelector(".flexdown-menu");
        const tooltip = panel.querySelector(".flexdown-tooltip");

        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            e.preventDefault();
            panel.classList.toggle("open");
        });

        document.addEventListener("click", (e) => {
            if (!panel.contains(e.target)) {
                panel.classList.remove("open");
            }
        });

        panel.querySelectorAll(".flexdown-item").forEach(item => {
            item.addEventListener("click", (e) => {
                e.stopPropagation();
                e.preventDefault();
                panel.classList.remove("open");

                const action = item.getAttribute("data-action");
                const res = item.getAttribute("data-res");
                const kbps = item.getAttribute("data-kbps");

                const info = resolveVideoMedia(videoElem, container);

                if (!info.url) {
                    tooltip.innerText = info.error || "Please open the specific video page first!";
                    tooltip.style.display = "block";
                    setTimeout(() => { tooltip.style.display = "none"; }, 5000);
                    return;
                }

                sendToFlexDown(info.url, info.title, action, res, kbps, btn, tooltip);
            });
        });

        container.appendChild(panel);
    }

    function sendToFlexDown(url, title, action, res, kbps, btn, tooltip) {
        const isAudio = (action === "audio");
        const mode = (action === "dialog") ? "dialog" : "quick";

        let format_id = "";
        let audio_quality = "320";

        if (isAudio) {
            audio_quality = kbps || "320";
        } else if (res) {
            format_id = `bestvideo[height<=${res}][vcodec^=avc]+bestaudio[acodec^=mp4a]/bestvideo[height<=${res}]+bestaudio/best[height<=${res}]/best`;
        }

        const originalHtml = btn.innerHTML;
        btn.innerHTML = `<div class="flexdown-logo">⬇</div> <span class="flexdown-btn-text">Sending...</span>`;

        const token = "9d2ea36b769a2acb7ad140f03a7f65edf17a00f9c5e303c9";
        const payload = JSON.stringify({
            url: url,
            title: title,
            audio_only: isAudio,
            audio_format: "mp3",
            audio_quality: audio_quality,
            format_id: format_id,
            res: res,
            mode: mode,
            token: token
        });

        const handleSuccess = () => {
            btn.classList.add("success");
            const label = isAudio ? `MP3 ${audio_quality}k` : (res ? `${res}p MP4` : "Downloading");
            btn.innerHTML = `✓ <span class="flexdown-btn-text">${label} Started!</span>`;
            setTimeout(() => {
                btn.classList.remove("success");
                btn.innerHTML = originalHtml;
            }, 3000);
        };

        const handleError = () => {
            btn.innerHTML = originalHtml;
            tooltip.innerText = "FlexDown is not running. Please open FlexDown!";
            tooltip.style.display = "block";
            setTimeout(() => { tooltip.style.display = "none"; }, 4000);
        };

        const headers = {
            "Content-Type": "application/json",
            "X-FlexDown-Token": token
        };

        if (typeof GM_xmlhttpRequest !== "undefined") {
            GM_xmlhttpRequest({
                method: "POST",
                url: BRIDGE_URL,
                headers: headers,
                data: payload,
                onload: (response) => {
                    if (response.status >= 200 && response.status < 300) {
                        handleSuccess();
                    } else {
                        handleError();
                    }
                },
                onerror: handleError
            });
        } else {
            fetch(BRIDGE_URL, {
                method: "POST",
                headers: headers,
                body: payload
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) handleSuccess();
                else handleError();
            })
            .catch(handleError);
        }
    }

    function scanForVideos() {
        const videos = document.querySelectorAll("video");
        videos.forEach(video => {
            let container = video.closest(
                "#movie_player, .html5-video-player, [data-e2e='feed-video'], [data-e2e='video-player'], .tiktok-video-player, [role='feed'] div, article, [data-testid='videoPlayer'], .player-container"
            );
            if (!container) container = video.parentElement || video;
            const rect = video.getBoundingClientRect();
            if (rect.width >= 160 && rect.height >= 120) {
                createFlexDownPanel(container, video);
            }
        });
    }

    injectStyles();
    scanForVideos();
    setInterval(scanForVideos, 2000);

    const observer = new MutationObserver(() => {
        scanForVideos();
    });

    observer.observe(document.body || document.documentElement, {
        childList: true,
        subtree: true
    });

})();
