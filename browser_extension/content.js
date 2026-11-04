// ==========================================================================
// FlexDown IDM-Style Video Detection & Floating Download Panel
// ==========================================================================

(function () {
    'use strict';

    const BRIDGE_URL = "http://127.0.0.1:18888/api/download";
    const LOGO_URL = chrome.runtime.getURL("icons/logo.png");

    function resolveVideoMedia(videoElem, container) {
        const pageUrl = window.location.href;
        let title = document.title || "Video";

        // 1. YouTube Specialized Resolution
        if (pageUrl.includes("youtube.com") || pageUrl.includes("youtu.be")) {
            let videoId = new URLSearchParams(window.location.search).get("v");
            if (videoId) {
                return { url: "https://www.youtube.com/watch?v=" + videoId, title: title };
            }
            if (pageUrl.includes("/shorts/")) {
                return { url: pageUrl.split("?")[0], title: title };
            }
        }

        // 2. TikTok Specialized Resolution
        if (pageUrl.includes("tiktok.com")) {
            // Case A: Exact video page (@username/video/1234567890)
            const exactMatch = pageUrl.match(/(https?:\/\/(?:www\.)?tiktok\.com\/@[^\/]+\/video\/\d+)/i);
            if (exactMatch) {
                return { url: exactMatch[1], title: title };
            }

            // Case B: Search container hierarchy for xgwrapper ID (standard TikTok web player container)
            let curr = videoElem || container;
            while (curr && curr !== document.body) {
                // Check wrapper id for xgwrapper-xxx-{VIDEO_ID}
                if (curr.id) {
                    const xgMatch = curr.id.match(/(?:xgwrapper|xgplayer).*?(\d{16,22})/i);
                    if (xgMatch) {
                        const authorLink = curr.querySelector('a[href*="/@"]');
                        const authorMatch = authorLink ? authorLink.href.match(/@([a-zA-Z0-9_.-]+)/) : null;
                        const author = authorMatch ? `@${authorMatch[1]}` : "@tiktok";
                        return { url: `https://www.tiktok.com/${author}/video/${xgMatch[1]}`, title: title };
                    }
                }

                // Check for any link with /video/{ID}
                const videoLink = curr.querySelector('a[href*="/video/"]');
                if (videoLink && videoLink.href) {
                    const m = videoLink.href.match(/(https?:\/\/(?:www\.)?tiktok\.com\/@[^\/]+\/video\/\d+)/i);
                    if (m) return { url: m[1], title: title };
                    const idMatch = videoLink.href.match(/\/video\/(\d{16,22})/);
                    if (idMatch) return { url: `https://www.tiktok.com/@tiktok/video/${idMatch[1]}`, title: title };
                }

                // Check for author link in the card
                const authorLink = curr.querySelector('a[href*="/@"]');
                if (authorLink && authorLink.href) {
                    // Check if card contains any 18-20 digit video ID
                    const digitsMatch = curr.innerHTML.match(/(\d{18,21})/);
                    if (digitsMatch) {
                        const authorMatch = authorLink.href.match(/@([a-zA-Z0-9_.-]+)/);
                        const author = authorMatch ? `@${authorMatch[1]}` : "@tiktok";
                        return { url: `https://www.tiktok.com/${author}/video/${digitsMatch[1]}`, title: title };
                    }
                }

                curr = curr.parentElement;
            }

            // Case C: Check any feed container matching TikTok selectors
            const feedCards = document.querySelectorAll(
                '[data-e2e="feed-video"], [data-e2e="recommend-list-item-container"], div[class*="DivItemContainer"], div[class*="ItemContainer"], div[class*="DivVideoWrapper"], article'
            );
            for (const card of feedCards) {
                if (card.contains(videoElem) || card.contains(container)) {
                    // Check xgwrapper inside card
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

            // Case D: Direct video CDN stream if available
            if (videoElem) {
                const src = videoElem.currentSrc || videoElem.src;
                if (src && src.startsWith("http") && !src.startsWith("blob:")) {
                    return { url: src, title: title };
                }
            }

            // Case E: If on generic feed URL like /foryou or homepage
            if (pageUrl.includes("/foryou") || pageUrl.endsWith("tiktok.com") || pageUrl.endsWith("tiktok.com/")) {
                return {
                    url: null,
                    error: "جاري التحميل... اضغط على الفيديو إذا كان في بداية الصفحة"
                };
            }
        }

        // 3. Instagram Resolution
        if (pageUrl.includes("instagram.com")) {
            if (pageUrl.includes("/reel/") || pageUrl.includes("/p/")) {
                return { url: pageUrl.split("?")[0], title: title };
            }
            let curr = videoElem || container;
            for (let i = 0; i < 8 && curr && curr !== document.body; i++) {
                const link = curr.querySelector('a[href*="/reel/"], a[href*="/p/"]');
                if (link && link.href) return { url: link.href.split("?")[0], title: title };
                curr = curr.parentElement;
            }
        }

        // 4. Facebook Resolution
        if (pageUrl.includes("facebook.com")) {
            if (pageUrl.includes("/watch/") || pageUrl.includes("/reel/") || pageUrl.includes("/videos/")) {
                return { url: pageUrl, title: title };
            }
            let curr = videoElem || container;
            for (let i = 0; i < 8 && curr && curr !== document.body; i++) {
                const link = curr.querySelector('a[href*="/videos/"], a[href*="/reel/"], a[href*="watch?v="]');
                if (link && link.href) return { url: link.href, title: title };
                curr = curr.parentElement;
            }
        }

        // 5. Twitter / X Resolution
        if (pageUrl.includes("twitter.com") || pageUrl.includes("x.com")) {
            if (pageUrl.includes("/status/")) {
                return { url: pageUrl.split("?")[0], title: title };
            }
            let curr = videoElem || container;
            for (let i = 0; i < 8 && curr && curr !== document.body; i++) {
                const link = curr.querySelector('a[href*="/status/"]');
                if (link && link.href) return { url: link.href.split("?")[0], title: title };
                curr = curr.parentElement;
            }
        }

        // 6. Direct media source fallback for HTML5 video elements
        if (videoElem) {
            const src = videoElem.currentSrc || videoElem.src;
            if (src && src.startsWith("http") && !src.startsWith("blob:")) {
                return { url: src, title: title };
            }
        }

        return { url: pageUrl, title: title };
    }

    function createFlexDownPanel(container, videoElem) {
        if (container.querySelector(".flexdown-panel-container")) {
            return;
        }

        const computedPos = window.getComputedStyle(container).position;
        if (computedPos === "static") {
            container.style.position = "relative";
        }

        const panel = document.createElement("div");
        panel.className = "flexdown-panel-container";

        panel.innerHTML = `
            <div class="flexdown-btn" title="Download this video with FlexDown">
                <img class="flexdown-logo" src="${LOGO_URL}" alt="FD" />
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
        btn.innerHTML = `<img class="flexdown-logo" src="${LOGO_URL}" /> <span class="flexdown-btn-text">Sending...</span>`;

        const token = window.FLEXDOWN_SECURITY_TOKEN || "";
        fetch(BRIDGE_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-FlexDown-Token": token
            },
            body: JSON.stringify({
                url: url,
                title: title,
                audio_only: isAudio,
                audio_format: "mp3",
                audio_quality: audio_quality,
                format_id: format_id,
                res: res,
                mode: mode,
                token: token
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                btn.classList.add("success");
                const label = isAudio ? `MP3 ${audio_quality}k` : (res ? `${res}p MP4` : "Downloading");
                btn.innerHTML = `✓ <span class="flexdown-btn-text">${label} Started!</span>`;
                setTimeout(() => {
                    btn.classList.remove("success");
                    btn.innerHTML = originalHtml;
                }, 3000);
            } else {
                throw new Error(data.error || "Failed to start download");
            }
        })
        .catch(err => {
            console.warn("[FlexDown Extension] Error:", err);
            btn.innerHTML = originalHtml;
            tooltip.innerText = "FlexDown is not running. Please open FlexDown!";
            tooltip.style.display = "block";
            setTimeout(() => {
                tooltip.style.display = "none";
            }, 4000);
        });
    }

    function scanForVideos() {
        const videos = document.querySelectorAll("video");
        videos.forEach(video => {
            let container = video.closest(
                "#movie_player, .html5-video-player, [data-e2e='feed-video'], [data-e2e='video-player'], .tiktok-video-player, [role='feed'] div, article, [data-testid='videoPlayer'], .player-container"
            );

            if (!container) {
                container = video.parentElement || video;
            }

            const rect = video.getBoundingClientRect();
            if (rect.width >= 160 && rect.height >= 120) {
                createFlexDownPanel(container, video);
            }
        });
    }

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
