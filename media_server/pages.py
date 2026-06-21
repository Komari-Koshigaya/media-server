import html as html_mod
import json
from pathlib import Path
from urllib.parse import quote

from .utils import get_file_icon, get_file_type, format_size

# ─── CSS ──────────────────────────────────────────────────────────────────────

BASE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
    --bg: #0c0d14;
    --surface: #111220;
    --surface2: #191a2e;
    --surface3: #22233a;
    --border: #2a2b42;
    --text: #e8e8f0;
    --text2: #9090a8;
    --text3: #606078;
    --accent: #6c8cff;
    --accent2: #4a6aee;
    --accent-bg: rgba(108,140,255,0.08);
    --green: #4ade80;
    --red: #f87171;
    --orange: #fb923c;
    --yellow: #facc15;
    --radius: 14px;
    --radius-sm: 10px;
    --glass: rgba(12,13,20,0.82);
}
html { scroll-behavior: smooth; }
body {
    font-family: -apple-system, 'SF Pro Display', 'Helvetica Neue', 'PingFang SC', Arial, sans-serif;
    background: var(--bg); color: var(--text); min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    background-image:
        radial-gradient(circle at 0% 0%, rgba(80,120,255,0.18) 0%, transparent 40%),
        radial-gradient(circle at 100% 100%, rgba(140,100,255,0.14) 0%, transparent 40%),
        radial-gradient(circle at 50% 50%, rgba(60,180,120,0.04) 0%, transparent 35%);
}
a { color: inherit; text-decoration: none; }

/* 动画 */
@keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
@keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
@keyframes pulse { 0%,100%{ opacity:1; } 50%{ opacity:0.6; } }
@keyframes loadSlide { 0%{ transform:translateX(-100%); } 100%{ transform:translateX(400%); } }
.animate-in { animation: fadeUp 0.35s ease-out; animation-fill-mode: backwards; }

/* 顶部栏 */
.topbar {
    position: sticky; top: 0; z-index: 100;
    background: var(--glass); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
}
.topbar h1 {
    font-size: 17px; color: #fff; font-weight: 600; letter-spacing: -0.3px;
    background: linear-gradient(135deg, #fff 40%, var(--accent));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.topbar-right { display: flex; gap: 16px; align-items: center; }
.topbar-right a { color: var(--text3); font-size: 13px; transition: color 0.2s; }
.topbar-right a:hover { color: var(--accent); }

/* 面包屑 */
.breadcrumb {
    padding: 10px 20px; font-size: 12px; color: var(--text3);
    background: var(--surface); border-bottom: 1px solid var(--border);
    word-break: break-all; letter-spacing: 0.2px;
}
.breadcrumb a { color: var(--accent); transition: opacity 0.15s; }
.breadcrumb a:hover { opacity: 0.7; }

/* 文件列表 */
.file-list { padding: 10px 14px 90px; }
.file-item {
    display: flex; align-items: center; padding: 6px 14px;
    border-radius: var(--radius); margin-bottom: 6px;
    background: var(--surface); border: 1px solid rgba(255,255,255,0.03);
    transition: background 0.2s, border-color 0.2s, transform 0.15s, box-shadow 0.2s;
    will-change: transform;
}
.file-item:hover {
    background: var(--surface2); border-color: rgba(108,140,255,0.15);
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}
.file-item-main {
    display: flex; align-items: center; flex: 1; min-width: 0;
    padding: 12px 4px; text-decoration: none; color: inherit;
}
.dl-btn {
    display: flex; align-items: center; justify-content: center;
    width: 44px; height: 44px; border-radius: var(--radius-sm);
    background: var(--accent-bg); color: var(--accent); flex-shrink: 0;
    text-decoration: none; transition: background 0.2s, transform 0.15s;
}
.dl-btn:hover { background: rgba(108,140,255,0.18); transform: scale(1.08); }
.dl-btn .material-symbols-outlined { font-size: 18px; }
.dl-btn-del { background: rgba(248,113,113,0.06); color: var(--red); margin-left: 4px; }
.dl-btn-del:hover { background: rgba(248,113,113,0.18); }
.file-item .icon {
    width: 46px; height: 46px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    margin-right: 14px; flex-shrink: 0; font-size: 22px;
    transition: transform 0.15s;
}
.file-item:hover .icon { transform: scale(1.08); }
.icon-folder { background: linear-gradient(135deg, #1a2a5c, #2a4a8c); color: #6c8cff; box-shadow: 0 2px 8px rgba(108,140,255,0.15); }
.icon-video  { background: linear-gradient(135deg, #3a1a2e, #5a2a48); color: #f87171; box-shadow: 0 2px 8px rgba(248,113,113,0.15); }
.icon-audio  { background: linear-gradient(135deg, #1a3a2e, #2a5a48); color: #4ade80; box-shadow: 0 2px 8px rgba(74,222,128,0.15); }
.icon-image  { background: linear-gradient(135deg, #3a2a1a, #5a4428); color: #fb923c; box-shadow: 0 2px 8px rgba(251,146,60,0.15); }
.icon-text   { background: linear-gradient(135deg, #2a2a1a, #4a4428); color: #facc15; box-shadow: 0 2px 8px rgba(250,204,21,0.1); }
.icon-file   { background: var(--surface3); color: var(--text3); }
.thumb-img {
    width: 110px; height: 70px; border-radius: 10px;
    object-fit: cover; flex-shrink: 0; margin-right: 14px;
    background: var(--surface3); border: 1px solid rgba(255,255,255,0.04);
}
.file-info { flex: 1; min-width: 0; }
.file-name {
    font-size: 14px; color: var(--text); white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; font-weight: 500;
}
.file-meta { font-size: 12px; color: var(--text3); margin-top: 4px; }
.empty {
    text-align: center; padding: 100px 20px; color: var(--text3); font-size: 14px;
    animation: fadeIn 0.5s ease-out;
}
.empty .material-symbols-outlined { font-size: 56px; display: block; margin-bottom: 12px; opacity: 0.3; }

/* 搜索 + 排序筛选 */
.search-box { padding: 10px 14px; background: var(--surface); }
.search-input {
    width: 100%; padding: 10px 16px; border-radius: var(--radius-sm);
    border: 1px solid var(--border); background: var(--bg); color: var(--text);
    font-size: 14px; outline: none; transition: border-color 0.2s, box-shadow 0.2s;
}
.search-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(108,140,255,0.15), 0 0 20px rgba(108,140,255,0.05); }
.search-input::placeholder { color: var(--text3); }
.sort-bar {
    display: flex; align-items: center; gap: 6px; padding: 8px 14px;
    flex-wrap: wrap; background: var(--surface); border-bottom: 1px solid var(--border);
}
.sort-lbl { font-size: 12px; color: var(--text3); margin-right: 2px; }
.sort-btn, .filter-btn {
    padding: 7px 16px; border-radius: 20px; border: 1px solid var(--border);
    background: transparent; color: var(--text2); font-size: 12px;
    min-height: 36px; cursor: pointer;
    transition: background 0.15s, color 0.15s, border-color 0.15s, box-shadow 0.15s;
}
.sort-btn:hover, .filter-btn:hover { border-color: var(--accent); color: var(--text); }
.sort-btn.active, .filter-btn.active {
    background: var(--accent); color: #000; border-color: var(--accent);
    font-weight: 600; box-shadow: 0 2px 10px rgba(108,140,255,0.25);
}

/* 上传栏 */
.upload-bar {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: var(--glass); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
    padding: 12px 16px;
    border-top: 1px solid var(--border); z-index: 100;
    display: flex; align-items: center; gap: 12px;
}
.upload-btn {
    flex: 1; padding: 12px; border: 2px dashed var(--border); border-radius: var(--radius);
    background: transparent; color: var(--text3); font-size: 13px;
    text-align: center; cursor: pointer; transition: border-color 0.2s, color 0.2s, background 0.2s;
}
.upload-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-bg); }
#fileInput { display: none; }
.upload-progress {
    position: fixed; bottom: 72px; left: 12px; right: 12px;
    background: var(--surface2); border-radius: var(--radius); padding: 16px;
    display: none; z-index: 101; border: 1px solid var(--border);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    animation: fadeUp 0.25s ease-out;
}
.progress-bar { height: 6px; background: var(--surface3); border-radius: 3px; margin-top: 10px; overflow: hidden; }
.progress-fill {
    height: 100%; border-radius: 3px; width: 0%; transition: width 0.3s;
    background: linear-gradient(90deg, var(--accent), var(--green));
}
.progress-text { font-size: 12px; color: var(--text3); margin-top: 6px; }
.progress-name { font-size: 13px; color: var(--text); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 播放器 */
.player-page { position: fixed; inset: 0; background: #000; z-index: 200; display: flex; flex-direction: column; }
.player-header {
    display: flex; align-items: center; padding: 12px 16px;
    background: linear-gradient(180deg, rgba(0,0,0,0.9) 0%, transparent 100%);
    position: absolute; top: 0; left: 0; right: 0; z-index: 10;
}
.back-btn {
    background: rgba(255,255,255,0.1); border: none; color: #fff;
    font-size: 18px; cursor: pointer; padding: 8px 12px;
    border-radius: var(--radius-sm); transition: background 0.2s;
    display: flex; align-items: center; gap: 4px;
}
.back-btn:hover { background: rgba(255,255,255,0.2); }
.player-title { color: #fff; font-size: 14px; margin-left: 12px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
.player-page video, .player-page audio { width: 100%; flex: 1; object-fit: contain; }
.player-page audio { margin: auto; width: 88%; max-width: 480px; }

/* 画廊导航 */
.gallery-nav {
    position: absolute; top: 50%; transform: translateY(-50%); z-index: 10;
    background: rgba(0,0,0,0.45); border: 1px solid rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.9);
    width: 46px; height: 46px; border-radius: 50%;
    font-size: 26px; cursor: pointer; display: flex; align-items: center;
    justify-content: center; transition: background 0.2s, border-color 0.2s;
    -webkit-tap-highlight-color: transparent;
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
}
.gallery-nav:hover { background: rgba(0,0,0,0.65); border-color: rgba(108,140,255,0.3); }
.gallery-nav:active { background: rgba(108,140,255,0.3); transform: translateY(-50%) scale(0.95); }
.gallery-prev { left: 10px; }
.gallery-next { right: 10px; }

/* 倍速控制 */
.speed-bar {
    position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%); z-index: 10;
    display: flex; gap: 4px; padding: 4px;
    background: rgba(0,0,0,0.55); border-radius: 20px;
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.08);
}
.speed-btn {
    padding: 5px 12px; border: none; border-radius: 16px;
    background: transparent; color: rgba(255,255,255,0.7);
    font-size: 12px; cursor: pointer; transition: background 0.15s, color 0.15s;
    font-weight: 500; white-space: nowrap;
}
.speed-btn:hover { color: #fff; }
.speed-btn.active { background: var(--accent); color: #fff; }

/* 阅读器 */
.reader-page { position: fixed; inset: 0; background: #1a1612; z-index: 200; display: flex; flex-direction: column; }
.reader-header { display: flex; align-items: center; padding: 12px 16px; background: #221e18; flex-shrink: 0; border-bottom: 1px solid #332e26; }
.reader-header .back-btn { color: #e8ddd0; background: rgba(255,255,255,0.06); }
.reader-header .player-title { color: #e8ddd0; }
.reader-content {
    flex: 1; overflow-y: auto; padding: 24px 20px;
    font-size: 16px; line-height: 1.9; color: #d4c8b8;
    white-space: pre-wrap; word-break: break-word;
    font-family: 'Noto Serif SC', 'SimSun', Georgia, serif;
}
.reader-content img { max-width: 100%; border-radius: 8px; }

/* 管理后台 */
.admin-wrap { max-width: 640px; margin: 0 auto; padding: 16px; }
.admin-card {
    background: var(--surface); border-radius: var(--radius); padding: 20px;
    margin-bottom: 14px; border: 1px solid rgba(255,255,255,0.04);
    animation: fadeUp 0.35s ease-out both;
}
.admin-card:nth-child(2) { animation-delay: 0.05s; }
.admin-card:nth-child(3) { animation-delay: 0.1s; }
.admin-card h2 { font-size: 14px; color: var(--text2); margin-bottom: 16px; font-weight: 500; letter-spacing: 0.3px; }
.share-item {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 0; border-bottom: 1px solid var(--border);
    transition: background 0.15s; border-radius: var(--radius-sm);
}
.share-item:hover { background: var(--accent-bg); }
.share-item:last-child { border-bottom: none; }
.share-name { font-size: 14px; color: var(--text); font-weight: 500; }
.share-path { font-size: 11px; color: var(--text3); margin-top: 3px; word-break: break-all; font-family: 'SF Mono', 'Cascadia Code', monospace; }
.share-del {
    background: rgba(248,113,113,0.08); border: none; color: var(--red);
    padding: 8px 16px; border-radius: var(--radius-sm); font-size: 12px;
    min-height: 44px; cursor: pointer; flex-shrink: 0;
    transition: background 0.2s; font-weight: 500;
}
.share-del:hover { background: rgba(248,113,113,0.18); }
.msg { padding: 12px 16px; border-radius: var(--radius-sm); font-size: 13px; margin-bottom: 14px; display: none; font-weight: 500; }
.msg-ok { background: rgba(74,222,128,0.1); color: var(--green); border: 1px solid rgba(74,222,128,0.2); }
.msg-err { background: rgba(248,113,113,0.1); color: var(--red); border: 1px solid rgba(248,113,113,0.2); }
.stats { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.stat-card {
    background: var(--surface); border-radius: var(--radius); padding: 16px 18px;
    border: 1px solid rgba(255,255,255,0.04); flex: 1; min-width: 140px;
    transition: border-color 0.2s;
}
.stat-card:hover { border-color: rgba(108,140,255,0.15); }
.stat-num { font-size: 22px; color: var(--accent); font-weight: 700; letter-spacing: -0.5px; font-variant-numeric: tabular-nums; }
.stat-label { font-size: 12px; color: var(--text3); margin-top: 4px; }

/* 登录页 */
.login-wrap {
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background: var(--bg); position: relative; overflow: hidden;
}
.login-wrap::before {
    content: ''; position: absolute; top: -40%; left: -20%; width: 80%; height: 80%;
    background: radial-gradient(circle, rgba(108,140,255,0.07) 0%, transparent 60%);
    animation: pulse 8s ease-in-out infinite;
}
.login-wrap::after {
    content: ''; position: absolute; bottom: -30%; right: -15%; width: 60%; height: 60%;
    background: radial-gradient(circle, rgba(74,222,128,0.05) 0%, transparent 60%);
    animation: pulse 8s ease-in-out 4s infinite;
}
.login-box {
    background: var(--surface); border-radius: 20px; padding: 44px 32px;
    width: 90%; max-width: 360px; border: 1px solid rgba(255,255,255,0.06);
    box-shadow: 0 24px 80px rgba(0,0,0,0.6), 0 0 60px rgba(108,140,255,0.04);
    text-align: center; position: relative; z-index: 1; animation: fadeUp 0.5s ease-out;
}
.login-box h2 { font-size: 22px; color: #fff; margin-bottom: 6px; font-weight: 700; letter-spacing: -0.5px; }
.login-box p { font-size: 13px; color: var(--text3); margin-bottom: 28px; }
.login-input {
    width: 100%; padding: 14px 18px; border-radius: var(--radius);
    border: 1px solid var(--border); background: var(--bg); color: #fff;
    font-size: 20px; text-align: center; letter-spacing: 10px;
    outline: none; transition: border-color 0.2s, box-shadow 0.2s;
}
.login-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(108,140,255,0.15), 0 0 30px rgba(108,140,255,0.06); }
.login-input::placeholder { letter-spacing: normal; font-size: 13px; color: var(--text3); }
.login-btn {
    width: 100%; padding: 14px; border-radius: var(--radius); border: none;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: #fff; font-size: 15px; font-weight: 600;
    cursor: pointer; margin-top: 16px; transition: transform 0.15s, box-shadow 0.2s;
}
.login-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 24px rgba(108,140,255,0.35); }
.login-btn:active { transform: translateY(0); }
.login-err { color: var(--red); font-size: 13px; margin-top: 14px; display: none; }

/* 网格视图 */
.file-list.grid-view {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 10px; padding: 10px 14px 90px;
}
.file-list.grid-view .file-item {
    flex-direction: column; padding: 0; margin-bottom: 0;
    overflow: hidden; position: relative;
}
.file-list.grid-view .file-item-main {
    flex-direction: column; padding: 0; width: 100%;
}
.file-list.grid-view .thumb-img {
    width: 100%; height: 120px; margin-right: 0; border-radius: 0;
    border-bottom: 1px solid var(--border);
}
.file-list.grid-view .file-item .icon {
    width: 100%; height: 120px; margin-right: 0; border-radius: 0;
    font-size: 36px; border-bottom: 1px solid var(--border);
}
.file-list.grid-view .file-info {
    padding: 8px 10px; width: 100%;
}
.file-list.grid-view .file-name {
    white-space: normal; font-size: 12px; line-height: 1.3;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.file-list.grid-view .file-meta { font-size: 11px; margin-top: 2px; }
.file-list.grid-view .dl-btn {
    position: absolute; top: 4px; right: 4px; z-index: 5;
    width: 32px; height: 32px; background: rgba(0,0,0,0.5);
    color: #fff; opacity: 0; transition: opacity 0.2s;
    backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
}
.file-list.grid-view .file-item:hover .dl-btn { opacity: 1; }
.file-list.grid-view .dl-btn-del { right: 40px; }
.view-toggle {
    display: inline-flex; align-items: center; gap: 2px;
    padding: 4px; border-radius: var(--radius-sm);
    background: var(--surface3); margin-left: auto;
}
.view-btn {
    padding: 4px 8px; border: none; border-radius: 6px;
    background: transparent; color: var(--text3); cursor: pointer;
    font-size: 16px; display: flex; align-items: center;
    transition: background 0.15s, color 0.15s;
}
.view-btn:hover { color: var(--text); }
.view-btn.active { background: var(--accent); color: #000; }

/* 多选模式 */
.file-item .select-check {
    display: none; width: 20px; height: 20px; border-radius: 4px;
    border: 2px solid var(--border); flex-shrink: 0; margin-right: 8px;
    cursor: pointer; appearance: none; -webkit-appearance: none;
    transition: background 0.15s, border-color 0.15s;
    position: relative;
}
.file-item .select-check:checked {
    background: var(--accent); border-color: var(--accent);
}
.file-item .select-check:checked::after {
    content: ''; position: absolute; top: 2px; left: 5px;
    width: 6px; height: 10px; border: 2px solid #fff;
    border-top: none; border-left: none; transform: rotate(45deg);
}
.select-mode .select-check { display: inline-block; }
.select-mode .file-item.selected { background: var(--accent-bg); border-color: rgba(108,140,255,0.2); }
.select-mode .file-item-main { pointer-events: none; }
.batch-bar {
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 110;
    background: var(--surface2); border-top: 1px solid var(--border);
    padding: 10px 16px; display: none; align-items: center; gap: 12px;
    box-shadow: 0 -4px 16px rgba(0,0,0,0.3);
}
.batch-bar.show { display: flex; }
.batch-btn {
    padding: 8px 18px; border-radius: var(--radius-sm); border: none;
    font-size: 13px; font-weight: 500; cursor: pointer;
    transition: background 0.15s;
}
.batch-btn-dl { background: var(--accent); color: #fff; }
.batch-btn-dl:hover { background: var(--accent2); }
.batch-btn-del { background: rgba(248,113,113,0.15); color: var(--red); }
.batch-btn-del:hover { background: rgba(248,113,113,0.25); }
.batch-btn-cancel { background: var(--surface3); color: var(--text2); }
.batch-btn-cancel:hover { background: var(--border); }
.batch-count { font-size: 13px; color: var(--text2); flex: 1; }

/* Toast 提示 */
.toast {
    position: fixed; top: 16px; left: 50%; transform: translateX(-50%) translateY(-80px);
    z-index: 500; padding: 10px 20px; border-radius: var(--radius-sm);
    font-size: 13px; font-weight: 500; color: #fff; opacity: 0;
    transition: transform 0.3s ease, opacity 0.3s ease;
    pointer-events: none; max-width: 90%; text-align: center;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}
.toast.show { transform: translateX(-50%) translateY(0); opacity: 1; }
.toast-ok { background: rgba(74,222,128,0.9); }
.toast-err { background: rgba(248,113,113,0.9); }
.toast-info { background: rgba(108,140,255,0.9); }

/* 桌面端适配 */
@media (min-width: 768px) {
    .file-list { max-width: 960px; margin: 0 auto; padding: 12px 20px 90px; }
    .search-box, .sort-bar { max-width: 960px; margin: 0 auto; }
    .breadcrumb { max-width: 960px; margin: 0 auto; border-left: 1px solid var(--border); border-right: 1px solid var(--border); }
    .file-item { padding: 6px 16px; }
    .admin-wrap { max-width: 720px; }
}
@media (min-width: 1200px) {
    .file-list { max-width: 1100px; }
    .search-box, .sort-bar, .breadcrumb { max-width: 1100px; }
}
"""

PICKER_CSS = """
.picker-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
    z-index: 300; display: none; align-items: center; justify-content: center;
}
.picker-overlay.show { display: flex; animation: fadeIn 0.2s ease-out; }
.picker-box {
    background: var(--surface); border-radius: 18px; width: 92%; max-width: 520px;
    max-height: 80vh; display: flex; flex-direction: column;
    border: 1px solid var(--border); box-shadow: 0 24px 80px rgba(0,0,0,0.6);
    animation: fadeUp 0.3s ease-out;
}
.picker-header {
    padding: 18px 20px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between; flex-shrink: 0;
}
.picker-header h3 { font-size: 16px; color: #fff; font-weight: 600; }
.picker-close {
    background: var(--surface3); border: none; color: var(--text3);
    font-size: 18px; cursor: pointer; padding: 8px 14px; border-radius: var(--radius-sm);
    transition: all 0.2s; line-height: 1;
}
.picker-close:hover { background: var(--border); color: #fff; }
.picker-path {
    padding: 10px 20px; font-size: 12px; color: var(--accent);
    background: var(--bg); border-bottom: 1px solid var(--border);
    word-break: break-all; flex-shrink: 0;
    display: flex; align-items: center; gap: 6px;
    font-family: 'SF Mono', 'Cascadia Code', monospace;
}
.picker-path .crumb { cursor: pointer; transition: opacity 0.15s; }
.picker-path .crumb:hover { opacity: 0.7; }
.picker-path .sep { color: var(--text3); }
.picker-list { flex: 1; overflow-y: auto; padding: 6px 8px; }
.picker-item {
    display: flex; align-items: center; padding: 10px 14px;
    cursor: pointer; transition: all 0.15s;
    border-radius: var(--radius-sm); margin-bottom: 2px;
}
.picker-item:hover { background: var(--accent-bg); }
.picker-item .pi-icon {
    width: 36px; height: 36px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    margin-right: 12px; flex-shrink: 0; font-size: 17px;
}
.pi-icon-drive { background: linear-gradient(135deg, #2a1a3a, #3a2a4a); color: #ce93d8; }
.pi-icon-folder { background: linear-gradient(135deg, #1a2a5c, #1a3a6c); color: #6c8cff; }
.pi-name { font-size: 14px; color: var(--text); font-weight: 500; }
.pi-sub { font-size: 11px; color: var(--text3); margin-top: 1px; font-family: 'SF Mono', 'Cascadia Code', monospace; }
.picker-footer {
    padding: 14px 20px; border-top: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
    flex-shrink: 0; gap: 10px;
}
.picker-selected {
    flex: 1; font-size: 12px; color: var(--text3); overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap;
}
.picker-confirm {
    padding: 10px 22px; border-radius: var(--radius-sm); border: none;
    background: var(--accent); color: #fff; font-size: 13px;
    cursor: pointer; transition: all 0.2s; white-space: nowrap; font-weight: 600;
}
.picker-confirm:hover { background: var(--accent2); }
.picker-confirm:disabled { opacity: 0.3; cursor: default; }
.picker-loading { padding: 40px; text-align: center; color: var(--text3); font-size: 13px; }
.picker-empty { padding: 40px; text-align: center; color: var(--text3); font-size: 13px; }
.pick-btn {
    padding: 14px 28px; border-radius: var(--radius); border: none;
    background: var(--accent); color: #fff; font-size: 14px; font-weight: 600;
    cursor: pointer; transition: all 0.2s; width: 100%;
}
.pick-btn:hover { background: var(--accent2); transform: translateY(-1px); box-shadow: 0 6px 20px rgba(108,140,255,0.25); }
.pick-btn:active { transform: scale(0.98); }
"""

# ─── JS ───────────────────────────────────────────────────────────────────────

UPLOAD_JS = """
const shareIdx = __SHARE_IDX__;
const curPath = '__CUR_PATH__';
function filterFiles(q) {
    q = q.toLowerCase().trim();
    var cb=document.getElementById('searchClear');
    if(cb) cb.style.display=q?'block':'none';
    document.querySelectorAll('.file-item').forEach(el => {
        var matchType = !_filterType || el.dataset.type === _filterType;
        var matchSearch = !q || (el.dataset.name||'').includes(q);
        if (matchType && matchSearch) {
            el.style.removeProperty('display');
        } else {
            el.style.setProperty('display', 'none', 'important');
        }
    });
}
function formatBytes(b) {
    if (b < 1024) return b + ' B';
    if (b < 1048576) return (b/1024).toFixed(1) + ' KB';
    if (b < 1073741824) return (b/1048576).toFixed(1) + ' MB';
    return (b/1073741824).toFixed(2) + ' GB';
}
async function uploadFiles(files) {
    if (!files.length) return;
    const prog = document.getElementById('uploadProgress');
    const fill = document.getElementById('progressFill');
    const text = document.getElementById('progressText');
    const name = document.getElementById('progressName');
    prog.style.display = 'block';
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        name.textContent = files.length > 1 ? `(${i+1}/${files.length}) ${file.name}` : file.name;
        const fd = new FormData();
        fd.append('file', file);
        fd.append('share', shareIdx);
        fd.append('path', curPath);
        try {
            await new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/upload', true);
                xhr.upload.onprogress = e => {
                    if (e.lengthComputable) {
                        fill.style.width = Math.round(e.loaded/e.total*100) + '%';
                        text.textContent = formatBytes(e.loaded)+' / '+formatBytes(e.total)+' ('+Math.round(e.loaded/e.total*100)+'%)';
                    }
                };
                xhr.onload = () => xhr.status === 200 ? resolve() : reject(new Error(xhr.responseText));
                xhr.onerror = () => reject(new Error('网络错误'));
                xhr.send(fd);
            });
        } catch (e) {
            name.textContent = '上传失败: ' + e.message;
        }
    }
    text.textContent = '全部完成';
    fill.style.width = '100%';
    setTimeout(() => { prog.style.display='none'; location.reload(); }, 1200);
}
function showToast(msg,type){
  var t=document.createElement('div');
  t.className='toast toast-'+(type||'info');
  t.textContent=msg;
  document.body.appendChild(t);
  requestAnimationFrame(function(){t.classList.add('show');});
  setTimeout(function(){t.classList.remove('show');setTimeout(function(){t.remove();},300);},2500);
}
function deleteFile(e,share,path,btn){
  e.preventDefault(); e.stopPropagation();
  if(!confirm('确定删除此文件？此操作不可恢复。')) return;
  var row=btn.closest('.file-item');
  fetch('/api/file?share='+share+'&path='+encodeURIComponent(path),{method:'DELETE'})
    .then(r=>r.json()).then(d=>{
      if(d.ok){ row.style.transition='opacity 0.3s,transform 0.3s'; row.style.opacity='0'; row.style.transform='translateX(40px)'; setTimeout(function(){row.remove();},300); }
      else showToast(d.msg||'删除失败','err');
    }).catch(function(){ showToast('网络错误','err'); });
}
// 拖拽上传
(function(){
  var overlay=document.getElementById('dropOverlay');
  var dragCount=0;
  document.addEventListener('dragenter',function(e){ e.preventDefault(); dragCount++; if(dragCount===1) overlay.style.display='flex'; });
  document.addEventListener('dragleave',function(e){ e.preventDefault(); dragCount--; if(dragCount<=0){ dragCount=0; overlay.style.display='none'; } });
  document.addEventListener('dragover',function(e){ e.preventDefault(); });
  document.addEventListener('drop',function(e){
    e.preventDefault(); dragCount=0; overlay.style.display='none';
    if(e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
  });
})();
var _sortKey='name',_sortAsc=true;
function sortFiles(key,btn){
  if(_sortKey===key){_sortAsc=!_sortAsc;}else{_sortKey=key;_sortAsc=true;}
  document.querySelectorAll('.sort-btn').forEach(function(b){b.classList.remove('active');});
  if(btn) btn.classList.add('active');
  var list=document.getElementById('fileList');
  var items=Array.from(list.querySelectorAll('.file-item'));
  var folders=items.filter(function(el){return el.dataset.type==='folder';});
  var files=items.filter(function(el){return el.dataset.type!=='folder';});
  function cmp(a,b){
    var va,vb;
    if(key==='name'){va=(a.dataset.name||'').toLowerCase();vb=(b.dataset.name||'').toLowerCase();return _sortAsc?va.localeCompare(vb):vb.localeCompare(va);}
    if(key==='size'){va=parseFloat(a.dataset.size||'0')||0;vb=parseFloat(b.dataset.size||'0')||0;return _sortAsc?va-vb:vb-va;}
    if(key==='mtime'){va=parseFloat(a.dataset.mtime||'0')||0;vb=parseFloat(b.dataset.mtime||'0')||0;return _sortAsc?va-vb:vb-va;}
    return 0;
  }
  folders.sort(cmp);
  files.sort(cmp);
  folders.concat(files).forEach(function(el,i){el.style.animationDelay=(i*0.025)+'s';list.appendChild(el);});
}
var _filterType='';
function filterType(type,btn){
  _filterType=type;
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  if(btn) btn.classList.add('active');
  var q=(document.getElementById('searchInput').value||'').toLowerCase().trim();
  document.querySelectorAll('.file-item').forEach(function(el){
    var matchType=!type||el.dataset.type===type;
    var matchSearch=!q||(el.dataset.name||'').includes(q);
    if(matchType&&matchSearch){el.style.removeProperty('display');}else{el.style.setProperty('display','none','important');}
  });
}
function setView(mode){
  var list=document.getElementById('fileList');
  var lb=document.getElementById('viewList'),gb=document.getElementById('viewGrid');
  if(mode==='grid'){
    list.classList.add('grid-view');
    gb.classList.add('active');lb.classList.remove('active');
    localStorage.setItem('viewMode','grid');
  }else{
    list.classList.remove('grid-view');
    lb.classList.add('active');gb.classList.remove('active');
    localStorage.setItem('viewMode','list');
  }
}
// 恢复上次视图模式
(function(){
  var saved=localStorage.getItem('viewMode');
  if(saved==='grid') setView('grid');
})();
// 记住当前浏览位置
(function(){
  var m=location.search.match(/share=(\\d+)/);
  if(m) localStorage.setItem('lastPath_'+m[1], location.search);
})();
// 键盘导航
(function(){
  var focusIdx=-1;
  function getItems(){return Array.from(document.querySelectorAll('.file-item:not([style*="display: none"])'));}
  function setFocus(idx){
    var items=getItems();
    if(idx<0||idx>=items.length) return;
    items.forEach(function(el){el.style.outline='';el.style.outlineOffset='';});
    focusIdx=idx;
    items[focusIdx].style.outline='2px solid var(--accent)';
    items[focusIdx].style.outlineOffset='-2px';
    items[focusIdx].scrollIntoView({block:'nearest'});
  }
  document.addEventListener('keydown',function(e){
    if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA') return;
    if(_selectMode) return;
    var items=getItems();
    if(!items.length) return;
    if(e.key==='ArrowDown'){e.preventDefault();setFocus(Math.min(focusIdx+1,items.length-1));}
    if(e.key==='ArrowUp'){e.preventDefault();setFocus(Math.max(focusIdx-1,0));}
    if(e.key==='Enter'&&focusIdx>=0){
      e.preventDefault();
      var link=items[focusIdx].querySelector('a.file-item-main');
      if(link) window.location.href=link.href;
    }
    if(e.key==='Backspace'){
      e.preventDefault();
      var backBtn=document.querySelector('.topbar .back-btn');
      if(backBtn) window.location.href=backBtn.href;
    }
  });
})();
// 多选批量操作
var _selectMode=false;
function onItemClick(e,el){
  if(!_selectMode) return;
  e.preventDefault(); e.stopPropagation();
  var cb=el.querySelector('.select-check');
  if(cb){ cb.checked=!cb.checked; el.classList.toggle('selected',cb.checked); updateBatchBar(); }
}
function toggleSelectMode(){
  _selectMode=!_selectMode;
  document.body.classList.toggle('select-mode',_selectMode);
  var btn=document.getElementById('selectModeBtn');
  if(btn) btn.textContent=_selectMode?'取消多选':'多选';
  if(!_selectMode){
    document.querySelectorAll('.select-check').forEach(function(c){c.checked=false;});
    document.querySelectorAll('.file-item').forEach(function(el){el.classList.remove('selected');});
  }
  updateBatchBar();
}
function toggleSelect(cb){
  var item=cb.closest('.file-item');
  if(item) item.classList.toggle('selected',cb.checked);
  updateBatchBar();
}
function updateBatchBar(){
  var count=document.querySelectorAll('.select-check:checked').length;
  var bar=document.getElementById('batchBar');
  var cnt=document.getElementById('batchCount');
  if(count>0){bar.classList.add('show');cnt.textContent='已选 '+count+' 个';}
  else{bar.classList.remove('show');}
}
function getSelectedFiles(){
  var files=[];
  document.querySelectorAll('.select-check:checked').forEach(function(cb){
    var item=cb.closest('.file-item');
    if(item && item.dataset.type!=='folder'){
      files.push({path:item.dataset.path,name:item.dataset.name,type:item.dataset.type});
    }
  });
  return files;
}
function batchDownload(){
  var files=getSelectedFiles();
  if(!files.length){showToast('请先选择文件','err');return;}
  files.forEach(function(f){
    var a=document.createElement('a');
    a.href='/raw/'+__SHARE_IDX__+'/'+encodeURIComponent(f.path)+'?download=1';
    a.download=f.name;
    document.body.appendChild(a);a.click();a.remove();
  });
}
function batchDelete(){
  var files=getSelectedFiles();
  if(!files.length){showToast('请先选择文件','err');return;}
  if(!confirm('确定删除选中的 '+files.length+' 个文件？此操作不可恢复。'))return;
  var done=0,failed=0;
  files.forEach(function(f){
    fetch('/api/file?share='+__SHARE_IDX__+'&path='+encodeURIComponent(f.path),{method:'DELETE'})
      .then(function(r){return r.json();}).then(function(d){
        if(d.ok){done++;var el=document.querySelector('[data-path="'+CSS.escape(f.path)+'"]');if(el){el.style.transition='opacity 0.3s';el.style.opacity='0';setTimeout(function(){el.remove();},300);}}
        else{failed++;}
        if(done+failed===files.length){
          toggleSelectMode();
          if(failed) showToast('删除完成，'+failed+' 个失败','err'); else showToast('删除完成','ok');
        }
      }).catch(function(){failed++;if(done+failed===files.length){toggleSelectMode();showToast('删除完成，'+failed+' 个失败','err');}});
  });
}
"""

PICKER_JS = """
let pickPath = '';
function showMsg(text, ok) {
    const m = document.getElementById('msg');
    m.textContent = text;
    m.className = 'msg ' + (ok ? 'msg-ok' : 'msg-err');
    m.style.display = 'block';
    setTimeout(() => m.style.display = 'none', 3000);
}
async function removeShare(idx) {
    if (!confirm('确定移除此共享目录？（不会删除原文件）')) return;
    try {
        const r = await fetch('/api/shares/' + idx, {method: 'DELETE'});
        const data = await r.json();
        if (data.ok) {
            showMsg('已移除', true);
            // 直接从 DOM 移除该项，不用跳转
            const el = document.getElementById('share-' + idx);
            if (el) el.remove();
            // 更新统计数字
            const items = document.querySelectorAll('.share-item');
            document.querySelector('.stat-num').textContent = items.length;
            // 如果列表空了，显示提示
            if (items.length === 0) {
                document.getElementById('shareList').innerHTML = '<div style="padding:30px;text-align:center;color:var(--text3);font-size:13px;">暂无共享目录，点击下方按钮添加</div>';
            }
        }
    } catch(e) { showMsg('网络错误', false); }
}
function openPicker() {
    pickPath = '';
    document.getElementById('pickerOverlay').classList.add('show');
    loadPicker('');
}
function closePicker() {
    document.getElementById('pickerOverlay').classList.remove('show');
}
function renderCrumbs() {
    const el = document.getElementById('pickerPath');
    if (!pickPath) { el.innerHTML = '<span style="color:var(--text3)">此电脑</span>'; return; }
    let html = '<span class="crumb" onclick="navCrumb(-1)">此电脑</span>';
    const parts = pickPath.replace(/\\\\/g, '/').split('/').filter(Boolean);
    for (let i = 0; i < parts.length; i++) {
        html += '<span class="sep"> / </span><span class="crumb" onclick="navCrumb('+i+')">'+parts[i]+'</span>';
    }
    el.innerHTML = html;
}
function navCrumb(depth) {
    if (depth < 0) { pickPath = ''; loadPicker(''); return; }
    const parts = pickPath.replace(/\\\\/g, '/').split('/').filter(Boolean);
    pickPath = parts.slice(0, depth + 1).join('/');
    if (/^[A-Za-z]:$/.test(parts[0])) pickPath = parts[0] + '\\\\' + parts.slice(1, depth + 1).join('\\\\');
    loadPicker(pickPath);
}
async function loadPicker(path) {
    const list = document.getElementById('pickerList');
    list.innerHTML = '<div class="picker-loading">加载中...</div>';
    renderCrumbs();
    document.getElementById('pickerConfirm').disabled = true;
    document.getElementById('pickerSelected').textContent = '点击文件夹进入，点击右侧按钮添加共享';
    try {
        const r = await fetch('/api/browse?path=' + encodeURIComponent(path));
        const data = await r.json();
        if (!data.ok) { list.innerHTML = '<div class="picker-empty">'+(data.msg||'加载失败')+'</div>'; return; }
        if (!data.items.length) { list.innerHTML = '<div class="picker-empty">此目录为空或无子文件夹</div>'; return; }
        let html = '';
        for (const item of data.items) {
            const iconCls = item.drive ? 'pi-icon-drive' : 'pi-icon-folder';
            const icon = item.drive ? 'storage' : 'folder';
            const sub = item.drive ? item.path : '';
            html += '<div class="picker-item" onclick="enterFolder(\\''+item.path.replace(/\\\\/g, '\\\\\\\\')+'\\')">'
                + '<div class="pi-icon '+iconCls+'"><span class="material-symbols-outlined">'+icon+'</span></div>'
                + '<div><div class="pi-name">'+item.name+'</div>'
                + (sub ? '<div class="pi-sub">'+sub+'</div>' : '')
                + '</div></div>';
        }
        list.innerHTML = html;
    } catch(e) { list.innerHTML = '<div class="picker-empty">网络错误</div>'; }
}
function enterFolder(path) {
    pickPath = path;
    loadPicker(path);
    document.getElementById('pickerConfirm').disabled = false;
    document.getElementById('pickerSelected').textContent = path;
}
async function confirmPick() {
    if (!pickPath) return;
    try {
        const r = await fetch('/api/shares', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: pickPath})
        });
        const data = await r.json();
        if (data.ok) {
            closePicker();
            showMsg('添加成功: ' + pickPath, true);
            // 重新加载页面获取最新列表
            setTimeout(() => location.replace('/admin'), 300);
        } else { showMsg(data.msg || '添加失败', false); }
    } catch(e) { showMsg('网络错误', false); }
}
document.getElementById('pickerOverlay').addEventListener('click', e => {
    if (e.target === e.currentTarget) closePicker();
});
"""


# ─── 页面构建 ─────────────────────────────────────────────────────────────────

FAVICON = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect rx='20' width='100' height='100' fill='%236c8cff'/><polygon points='40,25 40,75 78,50' fill='white'/></svg>"


def page_shell(title: str, body: str, extra_css: str = '', extra_head: str = '') -> str:
    safe_title = html_mod.escape(title)
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0c0d14">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="/favicon.svg">
<title>{safe_title}</title>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet">
{extra_head}
<style>{BASE_CSS}{extra_css}</style>
</head>
<body>{body}
</body>
</html>'''


def build_login_html(error: str = '') -> str:
    safe_error = html_mod.escape(error) if error else ''
    err = f'<div class="login-err" style="display:block">{safe_error}</div>' if error else '<div class="login-err" id="err"></div>'
    body = f'''
<div class="login-wrap">
    <div class="login-box">
        <h2>Media Server</h2>
        <p>输入密码访问局域网媒体库</p>
        <form method="POST" action="/login">
            <input class="login-input" type="password" name="password" placeholder="访问密码"
                   autofocus autocomplete="off" maxlength="20">
            <label style="display:flex;align-items:center;gap:6px;margin-top:12px;font-size:12px;color:var(--text3);cursor:pointer">
                <input type="checkbox" name="remember" value="1" style="width:16px;height:16px;accent-color:var(--accent)"> 记住密码（30天免登录）
            </label>
            <button class="login-btn" type="submit">进入</button>
        </form>
        {err}
    </div>
</div>'''
    return page_shell('登录 - Media Server', body)


def build_home_html(shares: list[dict]) -> str:
    items = ''
    for i, s in enumerate(shares):
        safe_name = html_mod.escape(s['name'])
        safe_path = html_mod.escape(s['path'])
        items += f'''
        <a class="file-item animate-in" style="animation-delay:{i*0.04}s" href="/?share={i}">
            <div class="icon icon-folder"><span class="material-symbols-outlined">folder_special</span></div>
            <div class="file-info">
                <div class="file-name">{safe_name}</div>
                <div class="file-meta">{safe_path}</div>
            </div>
        </a>'''
    if not items:
        items = '<div class="empty">还没有共享目录<br><br><a href="/admin" style="color:var(--accent)">去管理后台添加</a></div>'
    body = f'''
<div class="topbar">
    <h1>Media Server</h1>
    <div class="topbar-right">
        <a href="/admin">管理后台</a>
        <a href="/logout">退出</a>
    </div>
</div>
<div class="file-list">{items}</div>
<div id="recentArea" style="display:none;max-width:960px;margin:0 auto;padding:0 14px 90px">
    <div style="font-size:13px;color:var(--text3);padding:12px 0 8px;font-weight:500">最近文件</div>
    <div id="recentList"></div>
</div>
<script>
document.querySelectorAll('.file-item[href*="share="]').forEach(function(a){{
  var m=a.href.match(/share=(\\d+)/);
  if(m){{ var saved=localStorage.getItem('lastPath_'+m[1]); if(saved) a.href='/'+saved; }}
}});
fetch('/api/recent?limit=15').then(function(r){{return r.json();}}).then(function(d){{
  if(!d.ok||!d.files||!d.files.length) return;
  var area=document.getElementById('recentArea');
  var list=document.getElementById('recentList');
  var icons={{folder:'folder',video:'movie',audio:'music_note',image:'image',text:'description',file:'insert_drive_file'}};
  var html='';
  d.files.forEach(function(f,i){{
    var icon=icons[f.type]||'insert_drive_file';
    var size=f.size<1024?f.size+' B':f.size<1048576?(f.size/1024).toFixed(1)+' KB':f.size<1073741824?(f.size/1048576).toFixed(1)+' MB':(f.size/1073741824).toFixed(2)+' GB';
    var href='/play/'+f.share_idx+'/'+encodeURIComponent(f.path);
    html+='<a class="file-item animate-in" style="animation-delay:'+i*0.03+'s" href="'+href+'">';
    html+='<div class="icon icon-'+f.type+'"><span class="material-symbols-outlined">'+icon+'</span></div>';
    html+='<div class="file-info"><div class="file-name">'+f.name+'</div>';
    html+='<div class="file-meta">'+size+'</div></div></a>';
  }});
  list.innerHTML=html;
  area.style.display='block';
}});
</script>'''
    return page_shell('Media Server', body)


def build_browse_html(share_idx: int, share_name: str, rel_path: str, entries: list) -> str:
    safe_share_name = html_mod.escape(share_name)
    parts = [p for p in rel_path.split('/') if p]
    dir_count = sum(1 for e in entries if e[2])
    file_count = len(entries) - dir_count
    count_text = f'  <span style="color:var(--text3);font-size:11px;margin-left:8px">{dir_count} 个文件夹, {file_count} 个文件</span>' if entries else ''
    breadcrumb = f'<a href="/">首页</a> / <a href="/?share={share_idx}">{safe_share_name}</a>{count_text}'
    cum = ''
    for p in parts:
        cum += '/' + quote(p)
        safe_p = html_mod.escape(p)
        breadcrumb += f' / <a href="/?share={share_idx}&path={quote(cum, safe="/")}">{safe_p}</a>'

    dirs = sorted([e for e in entries if e[2]], key=lambda x: x[0].lower())
    files = sorted([e for e in entries if not e[2]], key=lambda x: x[0].lower())

    file_items = ''
    for idx, (name, size, is_dir, mtime) in enumerate(dirs + files):
        icon = get_file_icon(name, is_dir)
        ftype = get_file_type(name, is_dir)
        icon_cls = f'icon-{ftype}' if ftype != 'folder' else 'icon-folder'
        full_path = rel_path + '/' + name if rel_path else name
        if is_dir:
            href = f'/?share={share_idx}&path={quote(full_path, safe="/")}'
            meta = '文件夹'
            dl_btn = ''
        else:
            href = f'/play/{share_idx}/{quote(full_path, safe="/")}'
            from datetime import datetime
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d') if mtime else ''
            meta = f'{format_size(size)}  {date_str}' if date_str else format_size(size)
            dl_url = f'/raw/{share_idx}/{quote(full_path, safe="/")}?download=1'
            dl_btn = f'<a class="dl-btn" href="{dl_url}" title="下载"><span class="material-symbols-outlined">download</span></a><button class="dl-btn dl-btn-del" title="删除" onclick="deleteFile(event,\'{share_idx}\',\'{html_mod.escape(full_path)}\',this)"><span class="material-symbols-outlined">delete</span></button>'

        if ftype == 'video':
            thumb_url = f'/thumb/{share_idx}/{quote(full_path, safe="/")}'
            media_html = f'''<img class="thumb-img" src="{thumb_url}" loading="lazy"
                onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
                <div class="icon {icon_cls}" style="display:none"><span class="material-symbols-outlined">{icon}</span></div>'''
        elif ftype == 'image':
            thumb_url = f'/thumb/{share_idx}/{quote(full_path, safe="/")}'
            media_html = f'''<img class="thumb-img" src="{thumb_url}" loading="lazy"
                onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
                <div class="icon {icon_cls}" style="display:none"><span class="material-symbols-outlined">{icon}</span></div>'''
        else:
            media_html = f'<div class="icon {icon_cls}"><span class="material-symbols-outlined">{icon}</span></div>'

        # XSS 防护：文件名和 data-name 属性必须转义
        safe_name = html_mod.escape(name)
        safe_data_name = html_mod.escape(name.lower())
        file_items += f'''
        <div class="file-item animate-in" style="animation-delay:{idx*0.025}s" data-type="{ftype}" data-name="{safe_data_name}" data-mtime="{mtime}" data-size="{size}" data-path="{html_mod.escape(full_path)}" onclick="onItemClick(event,this)">
            <input type="checkbox" class="select-check">
            <a class="file-item-main" href="{href}">
                {media_html}
                <div class="file-info">
                    <div class="file-name">{safe_name}</div>
                    <div class="file-meta">{meta}</div>
                </div>
            </a>
            {dl_btn}
        </div>'''
    if not (dirs + files):
        file_items = '<div class="empty">空文件夹</div>'

    cur_path = quote(rel_path, safe='/') if rel_path else ''
    js = UPLOAD_JS.replace('__SHARE_IDX__', str(share_idx)).replace('__CUR_PATH__', cur_path)

    # 返回按钮：子目录返回上级，根目录返回首页
    if rel_path:
        parent_path = str(Path(rel_path).parent)
        back_href = f'/?share={share_idx}&path={quote(parent_path, safe="/")}' if parent_path and parent_path != '.' else f'/?share={share_idx}'
    else:
        back_href = '/'
    body = f'''
<div class="topbar">
    <a class="back-btn" href="{back_href}" style="margin-right:8px;padding:6px 10px"><span class="material-symbols-outlined" style="font-size:20px">arrow_back</span></a>
    <h1 style="flex:1">{safe_share_name}</h1>
    <div class="topbar-right"><a href="/admin">管理</a><a href="/logout">退出</a></div>
</div>
<div id="loadBar" style="position:fixed;top:0;left:0;right:0;height:3px;z-index:200;overflow:hidden"><div style="height:100%;width:30%;background:linear-gradient(90deg,transparent,var(--accent),transparent);animation:loadSlide 1s ease-in-out infinite"></div></div>
<div class="breadcrumb">{breadcrumb}</div>
<div class="search-box" style="position:relative">
    <input class="search-input" type="text" placeholder="搜索文件..." id="searchInput"
           oninput="filterFiles(this.value)" style="padding-right:36px">
    <button id="searchClear" onclick="document.getElementById('searchInput').value='';filterFiles('');this.style.display='none'" style="display:none;position:absolute;right:22px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--text3);cursor:pointer;font-size:18px;padding:4px">&times;</button>
</div>
<div class="sort-bar">
    <span class="sort-lbl">排序</span>
    <button class="sort-btn active" data-key="name" onclick="sortFiles('name',this)">名称</button>
    <button class="sort-btn" data-key="size" onclick="sortFiles('size',this)">大小</button>
    <button class="sort-btn" data-key="mtime" onclick="sortFiles('mtime',this)">时间</button>
    <span class="sort-lbl" style="margin-left:8px">筛选</span>
    <button class="filter-btn active" onclick="filterType('',this)">全部</button>
    <button class="filter-btn" onclick="filterType('video',this)">视频</button>
    <button class="filter-btn" onclick="filterType('image',this)">图片</button>
    <button class="filter-btn" onclick="filterType('audio',this)">音频</button>
    <div class="view-toggle">
        <button class="view-btn active" id="viewList" onclick="setView('list')" title="列表"><span class="material-symbols-outlined" style="font-size:18px">view_list</span></button>
        <button class="view-btn" id="viewGrid" onclick="setView('grid')" title="网格"><span class="material-symbols-outlined" style="font-size:18px">grid_view</span></button>
    </div>
</div>
<div class="file-list" id="fileList">{file_items}</div>
<div class="upload-bar">
    <label class="upload-btn" for="fileInput" id="uploadLabel">上传文件到当前目录（点击或拖拽）</label>
    <input type="file" id="fileInput" multiple onchange="uploadFiles(this.files)">
    <button class="upload-btn" style="flex:0 0 auto;padding:12px 16px;border-style:solid" onclick="toggleSelectMode()" id="selectModeBtn">多选</button>
</div>
<div class="batch-bar" id="batchBar">
    <span class="batch-count" id="batchCount">已选 0 个</span>
    <button class="batch-btn batch-btn-dl" onclick="batchDownload()">下载</button>
    <button class="batch-btn batch-btn-del" onclick="batchDelete()">删除</button>
    <button class="batch-btn batch-btn-cancel" onclick="toggleSelectMode()">取消</button>
</div>
<div id="dropOverlay" style="display:none;position:fixed;inset:0;z-index:150;background:rgba(108,140,255,0.12);border:3px dashed var(--accent);pointer-events:none;align-items:center;justify-content:center">
    <div style="text-align:center;color:var(--accent)"><span class="material-symbols-outlined" style="font-size:56px">cloud_upload</span><p style="font-size:16px;font-weight:600;margin-top:8px">松开上传文件</p></div>
</div>
<div class="upload-progress" id="uploadProgress">
    <div class="progress-name" id="progressName"></div>
    <div class="progress-text" id="progressText">准备中...</div>
    <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
</div>
<script>{js}</script>
<script>window.addEventListener('load',function(){{var lb=document.getElementById('loadBar');if(lb)lb.style.display='none';}});</script>'''
    return page_shell(f'{safe_share_name} - Media Server', body)


def build_player_html(title: str, file_url: str, file_type: str, back_href: str = '/', gallery: list = None, video_list: list = None) -> str:
    safe_title = html_mod.escape(title)
    dl_url = file_url + ('&' if '?' in file_url else '?') + 'download=1'
    transcode_url = file_url + ('&' if '?' in file_url else '?') + 'transcode=1'
    if file_type == 'video':
        # ArtPlayer 播放器配置
        art_cfg = (
            f"url:'{file_url}',"
            f"title:'{safe_title}',"
            "autoplay:true,autoPlayback:false,hotkey:true,pip:true,"
            "fullscreen:true,fullscreenWeb:false,setting:true,flip:true,"
            "playbackRate:true,aspectRatio:true,screenshot:true,"
            "miniProgressBar:true,playsInline:true,mutex:true,"
            "fastForward:true,lock:true,gesture:true"
        )
        # 上下集自动连播 JS
        video_nav_js = ''
        if video_list and len(video_list) > 1:
            video_json = json.dumps(video_list, ensure_ascii=False)
            cur_vid = next((i for i, v in enumerate(video_list) if v['url'] == file_url), 0)
            video_nav_js = f'''
var vids={video_json};var vidx={cur_vid};
function vidNav(d){{var n=vidx+d;if(n>=0&&n<vids.length){{vidx=n;art.switchUrl(vids[n].url);art.title=vids[n].name;
  document.getElementById('vidInfo').textContent=(vidx+1)+'/'+vids.length;
  document.getElementById('vidPrev').style.display=vidx>0?'':'none';
  document.getElementById('vidNext').style.display=vidx<vids.length-1?'':'none';}}}}
art.on('video:ended',function(){{if(vidx<vids.length-1) vidNav(1);}});
document.addEventListener('keydown',function(e){{
  if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA') return;
  if(e.key==='[') vidNav(-1);
  if(e.key===']') vidNav(1);
}});'''

        content = f'''<div id="artContainer" style="width:100%;flex:1"></div>
            <div id="fallback" style="display:none;flex-direction:column;align-items:center;justify-content:center;color:#aaa;gap:16px">
                <span class="material-symbols-outlined" style="font-size:48px;color:#f87171">error</span>
                <p style="font-size:14px" id="errMsg">播放失败</p>
                <div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center">
                  <a href="{transcode_url}" style="padding:12px 28px;background:#4ade80;color:#000;border-radius:10px;font-size:14px;text-decoration:none;font-weight:600">转码播放</a>
                  <a href="{dl_url}" style="padding:12px 28px;background:#6c8cff;color:#fff;border-radius:10px;font-size:14px;text-decoration:none;font-weight:600">下载</a>
                </div>
            </div>
            <script>
            var art=new Artplayer({{{art_cfg},container:'#artContainer'}});
            var pk='vp_'+location.pathname,ps=localStorage.getItem(pk);
            if(ps) art.seek=parseFloat(ps);
            var vol=localStorage.getItem('vol');if(vol) art.volume=parseFloat(vol);
            var lt=0;
            art.on('video:timeupdate',function(){{if(art.currentTime-lt>3){{localStorage.setItem(pk,art.currentTime);lt=art.currentTime;}}}});
            art.on('video:ended',function(){{localStorage.removeItem(pk);}});
            art.on('video:volumechange',function(){{localStorage.setItem('vol',art.volume);}});
            art.on('error',function(){{
              art.destroy();
              document.getElementById('artContainer').style.display='none';
              document.getElementById('fallback').style.display='flex';
            }});
            {video_nav_js}
            </script>'''
    elif file_type == 'audio':
        # ArtPlayer 音频配置（禁用视频专属功能）
        art_cfg = (
            f"url:'{file_url}',"
            f"title:'{safe_title}',"
            "autoplay:true,autoPlayback:false,hotkey:true,pip:false,"
            "fullscreen:false,fullscreenWeb:false,setting:true,flip:false,"
            "playbackRate:true,aspectRatio:false,screenshot:false,"
            "miniProgressBar:true,playsInline:true,mutex:true,"
            "fastForward:false,lock:false,gesture:false"
        )
        content = f'''<div id="artContainer" style="width:100%;flex:1"></div>
            <div id="fallback" style="display:none;flex-direction:column;align-items:center;justify-content:center;color:#aaa;gap:16px">
                <span class="material-symbols-outlined" style="font-size:48px;color:#f87171">error</span>
                <p style="font-size:14px" id="errMsg">播放失败</p>
                <div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center">
                  <a href="{transcode_url}" style="padding:12px 28px;background:#4ade80;color:#000;border-radius:10px;font-size:14px;text-decoration:none;font-weight:600">转码播放</a>
                  <a href="{dl_url}" style="padding:12px 28px;background:#6c8cff;color:#fff;border-radius:10px;font-size:14px;text-decoration:none;font-weight:600">下载</a>
                </div>
            </div>
            <script>
            var art=new Artplayer({{{art_cfg},container:'#artContainer'}});
            var pk='vp_'+location.pathname,ps=localStorage.getItem(pk);
            if(ps) art.seek=parseFloat(ps);
            var vol=localStorage.getItem('vol');if(vol) art.volume=parseFloat(vol);
            var lt=0;
            art.on('video:timeupdate',function(){{if(art.currentTime-lt>3){{localStorage.setItem(pk,art.currentTime);lt=art.currentTime;}}}});
            art.on('video:ended',function(){{localStorage.removeItem(pk);}});
            art.on('video:volumechange',function(){{localStorage.setItem('vol',art.volume);}});
            art.on('error',function(){{
              art.destroy();
              document.getElementById('artContainer').style.display='none';
              document.getElementById('fallback').style.display='flex';
            }});
            </script>'''
    elif file_type == 'image':
        gallery_json = json.dumps(gallery or [], ensure_ascii=False)
        content = f'''<div id="galleryWrap" style="flex:1;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden">
            <button id="gPrev" class="gallery-nav gallery-prev" onclick="gShow(cur-1)" style="display:none">&#8249;</button>
            <img id="galleryImg" src="{file_url}" style="max-width:100%;max-height:100%;object-fit:contain;border-radius:8px;user-select:none;-webkit-user-drag:none"
                 onerror="this.style.display='none';this.parentElement.innerHTML='<div style=\\'text-align:center;color:#aaa\\'><span class=\\'material-symbols-outlined\\' style=\\'font-size:48px\\'>broken_image</span><p>图片加载失败</p></div>'">
            <button id="gNext" class="gallery-nav gallery-next" onclick="gShow(cur+1)" style="display:none">&#8250;</button>
        </div>
        <script>
        var images={gallery_json};
        var cur=images.findIndex(function(i){{return i.url==='{file_url}'}});
        if(cur<0) cur=0;
        function gShow(i){{
          if(i<0||i>=images.length) return;
          cur=i;
          var img=document.getElementById('galleryImg');
          img.style.display='';
          img.src=images[cur].url;
          var t=images[cur].name;
          document.getElementById('galleryTitle').textContent=(cur+1)+'/'+images.length+' '+t;
          document.getElementById('gPrev').style.display=cur>0?'':'none';
          document.getElementById('gNext').style.display=cur<images.length-1?'':'none';
          // 预加载前后各一张
          if(cur>0){{var p=new Image();p.src=images[cur-1].url;}}
          if(cur<images.length-1){{var n=new Image();n.src=images[cur+1].url;}}
        }}
        if(images.length>1){{
          document.getElementById('gPrev').style.display=cur>0?'':'none';
          document.getElementById('gNext').style.display=cur<images.length-1?'':'none';
          document.addEventListener('keydown',function(e){{
            if(e.key==='ArrowLeft') gShow(cur-1);
            if(e.key==='ArrowRight') gShow(cur+1);
          }});
          var tx=0;
          document.addEventListener('touchstart',function(e){{tx=e.touches[0].clientX;}});
          document.addEventListener('touchend',function(e){{
            var dx=e.changedTouches[0].clientX-tx;
            if(Math.abs(dx)>50){{dx<0?gShow(cur+1):gShow(cur-1);}}
          }});
        }}
        </script>'''
    else:
        content = '<div class="reader-content" id="rc">加载中...</div>'

    if file_type in ('video', 'audio', 'image'):
        gallery_title = safe_title
        if gallery and len(gallery) > 1:
            cur_idx = next((i for i, g in enumerate(gallery) if g['url'] == file_url), 0)
            gallery_title = f'{cur_idx + 1}/{len(gallery)} {safe_title}'
        # 视频上下集导航 HTML（JS 逻辑在各类型 content 中处理）
        video_nav = ''
        if video_list and len(video_list) > 1:
            cur_vid = next((i for i, v in enumerate(video_list) if v['url'] == file_url), 0)
            video_nav = f'''
<div class="speed-bar" id="videoNav" style="bottom:60px">
    <button class="speed-btn" id="vidPrev" onclick="vidNav(-1)" style="display:{'inline-block' if cur_vid > 0 else 'none'}">&#9664; 上一集</button>
    <span style="color:rgba(255,255,255,0.7);font-size:12px;padding:0 8px" id="vidInfo">{cur_vid+1}/{len(video_list)}</span>
    <button class="speed-btn" id="vidNext" onclick="vidNav(1)" style="display:{'inline-block' if cur_vid < len(video_list)-1 else 'none'}">下一集 &#9654;</button>
</div>'''
        body = f'''
<div class="player-page">
    <div class="player-header">
        <a class="back-btn" href="{back_href}"><span class="material-symbols-outlined" style="font-size:18px">arrow_back</span></a>
        <a class="back-btn" href="{dl_url}" title="下载"><span class="material-symbols-outlined" style="font-size:18px">download</span></a>
        <span class="player-title" id="galleryTitle">{gallery_title}</span>
    </div>
    {content}
    {video_nav}
</div>'''
        extra_head = ''
        if file_type in ('video', 'audio'):
            extra_head = '<script src="https://cdn.jsdelivr.net/npm/artplayer@5/dist/artplayer.js"></script>'
        return page_shell(safe_title, body, 'body{background:#000;}', extra_head=extra_head)
    else:
        reader_css = """
.read-progress { position:fixed; top:0; left:0; right:0; height:3px; z-index:300; background:var(--surface3); }
.read-progress-fill { height:100%; background:linear-gradient(90deg,var(--accent),var(--green)); width:0%; transition:width 0.15s; }
.txt-wrap { display:flex; height:100vh; padding-top:3px; background:#1a1612; }
.txt-toc { width:260px; flex-shrink:0; background:var(--surface); border-right:1px solid var(--border);
  display:flex; flex-direction:column; overflow:hidden; }
.txt-toc.hide { display:none; }
.txt-toc-header { padding:12px 16px; font-size:13px; font-weight:600; color:var(--text2);
  border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; }
.txt-toc-filter { width:100%; padding:6px 12px; border:none; border-bottom:1px solid var(--border);
  background:var(--bg); color:var(--text); font-size:12px; outline:none; }
.txt-toc-filter::placeholder { color:var(--text3); }
.txt-toc-list { flex:1; overflow-y:auto; padding:6px 0; }
.txt-toc-item { padding:8px 16px; font-size:12px; color:var(--text); cursor:pointer;
  border-left:3px solid transparent; transition:background 0.1s,border-color 0.1s; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis; }
.txt-toc-item:hover { background:var(--accent-bg); }
.txt-toc-item.active { border-left-color:var(--accent); background:var(--accent-bg); color:var(--accent); }
.txt-main { flex:1; display:flex; flex-direction:column; min-width:0; }
.txt-header { display:flex; align-items:center; padding:10px 16px; background:var(--glass);
  backdrop-filter:blur(20px); border-bottom:1px solid var(--border); gap:8px; flex-shrink:0; }
.txt-content { flex:1; overflow-y:auto; padding:24px 20px; font-size:16px; line-height:1.9;
  color:var(--text); white-space:pre-wrap; word-break:break-word;
  font-family:'Noto Serif SC','SimSun',Georgia,serif; contain:layout style; }
.txt-content .chapter-mark { scroll-margin-top:20px; }
.txt-content .search-hl { background:rgba(250,204,21,0.35); color:inherit; border-radius:2px; }
.txt-content .search-hl.active { background:rgba(250,204,21,0.7); }
.txt-search-bar { display:flex; align-items:center; gap:6px; padding:6px 12px; background:var(--surface2);
  border-bottom:1px solid var(--border); flex-shrink:0; }
.txt-search-bar input { flex:1; padding:6px 10px; border:1px solid var(--border); border-radius:6px;
  background:var(--bg); color:var(--text); font-size:13px; outline:none; }
.txt-search-bar input:focus { border-color:var(--accent); }
.txt-search-bar button { padding:5px 10px; border:1px solid var(--border); border-radius:6px;
  background:var(--surface); color:var(--text); font-size:12px; cursor:pointer; white-space:nowrap; }
.txt-search-bar button:hover { background:var(--accent-bg); border-color:var(--accent); color:var(--accent); }
.txt-search-bar .search-count { font-size:11px; color:var(--text3); min-width:50px; text-align:center; }
.txt-search-bar.hidden { display:none; }
.txt-bottom-bar { position:fixed; bottom:0; left:0; right:0; z-index:300; background:var(--glass);
  backdrop-filter:blur(20px); border-top:1px solid var(--border); padding:10px 20px; display:flex;
  align-items:center; gap:12px; }
.txt-slider { flex:1; -webkit-appearance:none; appearance:none; height:6px; border-radius:3px;
  background:var(--surface3); outline:none; }
.txt-slider::-webkit-slider-thumb { -webkit-appearance:none; width:18px; height:18px;
  border-radius:50%; background:var(--accent); cursor:pointer; }
.txt-pct-label { font-size:12px; color:var(--text2); min-width:36px; text-align:center; }
.toc-toggle { background:var(--surface2); border:1px solid var(--border); color:var(--text);
  padding:6px 10px; border-radius:var(--radius-sm); cursor:pointer; font-size:18px; }
.search-toggle { background:var(--surface2); border:1px solid var(--border); color:var(--text);
  padding:6px 10px; border-radius:var(--radius-sm); cursor:pointer; font-size:18px; }
"""
        body = f'''
<div class="read-progress"><div class="read-progress-fill" id="readFill"></div></div>
<div class="txt-wrap">
    <div class="txt-toc hide" id="tocPanel">
        <div class="txt-toc-header">目录 <span style="cursor:pointer" onclick="toggleToc()">&times;</span></div>
        <input class="txt-toc-filter" id="tocFilter" placeholder="过滤章节..." oninput="filterToc(this.value)">
        <div class="txt-toc-list" id="tocList"><div style="padding:20px;color:var(--text3);text-align:center;font-size:12px">加载中...</div></div>
    </div>
    <div class="txt-main">
        <div class="txt-header">
            <a class="back-btn" href="{back_href}"><span class="material-symbols-outlined" style="font-size:18px">arrow_back</span></a>
            <button class="toc-toggle" onclick="toggleToc()">☰</button>
            <button class="search-toggle" onclick="toggleSearch()">🔍</button>
            <span class="player-title" style="margin-left:0">{safe_title}</span>
        </div>
        <div class="txt-search-bar hidden" id="searchBar">
            <input id="searchInput" placeholder="搜索内容..." onkeydown="if(event.key==='Enter')doSearch()">
            <button onclick="doSearch()">搜索</button>
            <button onclick="navMatch(-1)">▲</button>
            <button onclick="navMatch(1)">▼</button>
            <span class="search-count" id="searchCount"></span>
            <button onclick="toggleSearch()">✕</button>
        </div>
        <div class="txt-content" id="rc">加载中...</div>
    </div>
</div>
<div class="txt-bottom-bar">
    <span class="txt-pct-label" id="pctLabel">0%</span>
    <input type="range" class="txt-slider" id="progressSlider" min="0" max="100" value="0">
    <span class="txt-pct-label" id="pctRight">100%</span>
</div>
<script>
const rc=document.getElementById('rc'), fill=document.getElementById('readFill');
const slider=document.getElementById('progressSlider'), pctLabel=document.getElementById('pctLabel');
const storageKey='txt_{file_url}';
let chapters=[], rawText='', isSliderDrag=false, ticking=false;
let searchMatches=[], searchIdx=-1, curQuery='';
let totalLines=0, maxScroll=0, lastSliderTs=0;

fetch("{file_url}").then(r=>r.text()).then(t=>{{
  rawText=t;
  totalLines=t.split('\\n').length;
  chapters=parseChapters(t);
  renderContent();
  renderToc();
  const saved=localStorage.getItem(storageKey);
  if(saved) rc.scrollTop=parseInt(saved);
  maxScroll=rc.scrollHeight-rc.clientHeight;
  updateProgress();
}}).catch(e=>rc.textContent='加载失败: '+e.message);

function parseChapters(text){{
  const lines=text.split('\\n');
  const re=/^(第[一二三四五六七八九十百千万零〇\\d]+[章回节卷篇]|Chapter\\s+\\d+|CHAPTER\\s+\\d+|卷[一二三四五六七八九十百千万零〇\\d]+|【.+?】|==+.*==+|───+|\\*\\*\\*+|---\\s*分隔线)/;
  const result=[];
  for(let i=0;i<lines.length;i++){{
    if(re.test(lines[i].trim())){{
      result.push({{line:i, title:lines[i].trim().substring(0,40)}});
    }}
  }}
  return result;
}}

function renderToc(){{
  const list=document.getElementById('tocList');
  if(chapters.length===0){{
    list.innerHTML='<div style="padding:20px;color:var(--text3);text-align:center;font-size:12px">未检测到章节</div>';
    return;
  }}
  list.innerHTML=chapters.map((c,i)=>'<div class="txt-toc-item" data-idx="'+i+'" onclick="jumpChapter('+i+')">'+escHtml(c.title)+'</div>').join('');
}}

function escHtml(s){{ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}

function renderContent(highlight){{
  if(!highlight){{ rc.textContent=rawText; return; }}
  const q=highlight.toLowerCase();
  const lines=rawText.split('\\n');
  const out=[];
  for(let i=0;i<lines.length;i++){{
    const lo=lines[i].toLowerCase();
    let pos=0, found=lo.indexOf(q), lineHtml='';
    while(found!==-1){{
      lineHtml+=escHtml(lines[i].substring(pos,found));
      lineHtml+='<span class="search-hl" data-line="'+i+'">'+escHtml(lines[i].substring(found,found+q.length))+'</span>';
      pos=found+q.length;
      found=lo.indexOf(q,pos);
    }}
    lineHtml+=escHtml(lines[i].substring(pos));
    out.push(lineHtml);
  }}
  rc.innerHTML=out.join('\\n');
}}

function toggleToc(){{
  document.getElementById('tocPanel').classList.toggle('hide');
}}

function filterToc(q){{
  q=q.toLowerCase();
  document.querySelectorAll('.txt-toc-item').forEach(el=>{{
    el.style.display=(!q||el.textContent.toLowerCase().includes(q))?'':'none';
  }});
}}

function jumpChapter(idx){{
  if(idx<0||idx>=chapters.length) return;
  const line=chapters[idx].line;
  const ratio=line/totalLines;
  rc.scrollTop=Math.floor(ratio*(rc.scrollHeight-rc.clientHeight));
  localStorage.setItem(storageKey,rc.scrollTop);
  updateProgress();
}}


function toggleSearch(){{
  const bar=document.getElementById('searchBar');
  bar.classList.toggle('hidden');
  if(!bar.classList.contains('hidden')){{
    document.getElementById('searchInput').focus();
  }} else {{
    searchMatches=[]; searchIdx=-1; curQuery='';
    document.getElementById('searchCount').textContent='';
    document.getElementById('searchInput').value='';
    const st=rc.scrollTop; renderContent(); rc.scrollTop=st;
  }}
}}

function doSearch(){{
  const q=document.getElementById('searchInput').value.trim();
  if(!q){{
    searchMatches=[]; searchIdx=-1; curQuery='';
    document.getElementById('searchCount').textContent='';
    const st=rc.scrollTop; renderContent(); rc.scrollTop=st;
    return;
  }}
  curQuery=q;
  const st=rc.scrollTop;
  renderContent(q);
  rc.scrollTop=st;
  const hl=rc.querySelectorAll('.search-hl');
  searchMatches=[]; searchIdx=-1;
  if(hl.length>0){{
    searchIdx=0;
    hl[0].classList.add('active');
    hl[0].scrollIntoView({{block:'center'}});
    document.getElementById('searchCount').textContent='1/'+hl.length;
  }} else {{
    document.getElementById('searchCount').textContent='无结果';
  }}
}}

function navMatch(dir){{
  const hl=rc.querySelectorAll('.search-hl');
  if(!hl.length) return;
  hl.forEach(s=>s.classList.remove('active'));
  searchIdx=(searchIdx+dir+hl.length)%hl.length;
  hl[searchIdx].classList.add('active');
  hl[searchIdx].scrollIntoView({{block:'center'}});
  document.getElementById('searchCount').textContent=(searchIdx+1)+'/'+hl.length;
}}

function updateProgress(){{
  if(isSliderDrag) return;
  maxScroll=rc.scrollHeight-rc.clientHeight;
  const p=maxScroll>0?Math.round(rc.scrollTop/maxScroll*100):0;
  fill.style.width=p+'%'; pctLabel.textContent=p+'%';
  slider.value=p;
  localStorage.setItem(storageKey,rc.scrollTop);
  if(chapters.length>0){{
    const ratio=rc.scrollTop/(rc.scrollHeight||1);
    const scrollLine=Math.floor(ratio*totalLines);
    let active=0;
    for(let i=0;i<chapters.length;i++){{
      if(chapters[i].line<=scrollLine) active=i;
    }}
    document.querySelectorAll('.txt-toc-item').forEach((el,i)=>el.classList.toggle('active',i===active));
  }}
}}

rc.addEventListener('scroll',function(){{
  if(isSliderDrag) return;
  if(!ticking){{
    requestAnimationFrame(function(){{
      updateProgress();
      ticking=false;
    }});
    ticking=true;
  }}
}});

slider.addEventListener('input',function(){{
  isSliderDrag=true;
  const v=this.value;
  fill.style.width=v+'%';
  pctLabel.textContent=v+'%';
  const now=Date.now();
  if(now-lastSliderTs>50){{
    lastSliderTs=now;
    rc.scrollTop=maxScroll*v/100;
  }}
}});
slider.addEventListener('change',function(){{
  isSliderDrag=false;
  maxScroll=rc.scrollHeight-rc.clientHeight;
  rc.scrollTop=maxScroll*this.value/100;
  localStorage.setItem(storageKey,rc.scrollTop);
}});
window.addEventListener('resize',function(){{ maxScroll=rc.scrollHeight-rc.clientHeight; }});
</script>'''
        return page_shell(safe_title, body, reader_css)


def build_epub_reader_html(title: str, share_idx: int, file_path: str, back_href: str = '/') -> str:
    safe_title = html_mod.escape(title)
    api_url = f'/api/epub/{share_idx}/{quote(file_path, safe="/")}'

    epub_css = """
.read-progress { position:fixed; top:0; left:0; right:0; height:3px; z-index:300; background:var(--surface3); }
.read-progress-fill { height:100%; background:linear-gradient(90deg,var(--accent),var(--green)); width:0%; transition:width 0.15s; }
.epub-wrap { display:flex; height:100vh; padding-top:3px; }
.epub-toc { width:260px; flex-shrink:0; background:var(--surface); border-right:1px solid var(--border);
  display:flex; flex-direction:column; overflow:hidden; }
.epub-toc.hide { display:none; }
.epub-toc-header { padding:12px 16px; font-size:13px; font-weight:600; color:var(--text2);
  border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; }
.epub-toc-list { flex:1; overflow-y:auto; padding:6px 0; }
.epub-toc-item { padding:10px 16px; font-size:13px; color:var(--text); cursor:pointer;
  border-left:3px solid transparent; transition:all 0.15s; }
.epub-toc-item:hover { background:var(--accent-bg); }
.epub-toc-item.active { border-left-color:var(--accent); background:var(--accent-bg); color:var(--accent); }
.epub-main { flex:1; display:flex; flex-direction:column; min-width:0; }
.epub-header { display:flex; align-items:center; padding:10px 16px; background:var(--glass);
  backdrop-filter:blur(20px); border-bottom:1px solid var(--border); gap:8px; flex-shrink:0; }
.epub-content { flex:1; overflow-y:auto; padding:24px 20px; font-size:16px; line-height:1.9;
  color:var(--text); font-family:'Noto Serif SC','SimSun',Georgia,serif; }
.epub-content p { margin-bottom:1em; }
.epub-nav { display:flex; gap:8px; padding:12px 16px; border-top:1px solid var(--border);
  background:var(--surface); flex-shrink:0; }
.epub-nav button { flex:1; padding:10px; border-radius:var(--radius-sm); border:1px solid var(--border);
  background:var(--surface2); color:var(--text); font-size:13px; cursor:pointer; transition:all 0.2s; }
.epub-nav button:hover { background:var(--accent-bg); border-color:var(--accent); color:var(--accent); }
.epub-nav button:disabled { opacity:0.3; cursor:default; }
.read-pct { position:fixed; bottom:60px; right:16px; z-index:300; background:var(--surface2);
  border:1px solid var(--border); border-radius:20px; padding:6px 14px; font-size:12px;
  color:var(--text2); backdrop-filter:blur(10px); }
.toc-toggle { background:var(--surface2); border:1px solid var(--border); color:var(--text);
  padding:6px 10px; border-radius:var(--radius-sm); cursor:pointer; font-size:18px; }
"""
    body = f'''
<div class="read-progress"><div class="read-progress-fill" id="readFill"></div></div>
<div class="epub-wrap">
    <div class="epub-toc hide" id="tocPanel">
        <div class="epub-toc-header">目录 <span style="cursor:pointer" onclick="toggleToc()">&times;</span></div>
        <div class="epub-toc-list" id="tocList"></div>
    </div>
    <div class="epub-main">
        <div class="epub-header">
            <a class="back-btn" href="{back_href}"><span class="material-symbols-outlined" style="font-size:18px">arrow_back</span></a>
            <button class="toc-toggle" onclick="toggleToc()">☰</button>
            <span class="player-title" id="epubTitle" style="margin-left:0">{safe_title}</span>
        </div>
        <div class="epub-content" id="epubContent">加载中...</div>
        <div class="epub-nav">
            <button id="prevBtn" onclick="goChapter(cur-1)" disabled>上一章</button>
            <span style="display:flex;align-items:center;font-size:12px;color:var(--text3);padding:0 8px" id="chInfo"></span>
            <button id="nextBtn" onclick="goChapter(cur+1)" disabled>下一章</button>
        </div>
    </div>
</div>
<div class="read-pct" id="readPct">0%</div>
<script>
let chapters=[], cur=0;
const content=document.getElementById('epubContent'), fill=document.getElementById('readFill'), pct=document.getElementById('readPct');
const storageKey='epub_{file_path}';

fetch("{api_url}").then(r=>r.json()).then(data=>{{
  if(!data.ok){{ content.textContent='加载失败: '+data.msg; return; }}
  chapters=data.chapters;
  renderToc();
  const saved=localStorage.getItem(storageKey);
  goChapter(saved?parseInt(saved):0);
}}).catch(e=>content.textContent='加载失败: '+e.message);

function renderToc(){{
  const list=document.getElementById('tocList');
  list.innerHTML=chapters.map((c,i)=>'<div class="epub-toc-item" onclick="goChapter('+i+')">'+c.title+'</div>').join('');
}}
function toggleToc(){{
  document.getElementById('tocPanel').classList.toggle('hide');
}}
function goChapter(n){{
  if(n<0||n>=chapters.length) return;
  cur=n; content.scrollTop=0;
  content.textContent=chapters[n].content;
  document.getElementById('chInfo').textContent=(n+1)+'/'+chapters.length;
  document.getElementById('prevBtn').disabled=n===0;
  document.getElementById('nextBtn').disabled=n===chapters.length-1;
  document.querySelectorAll('.epub-toc-item').forEach((el,i)=>el.classList.toggle('active',i===n));
  localStorage.setItem(storageKey,n);
  updateProgress();
}}
function updateProgress(){{
  const h=content.scrollHeight-content.clientHeight;
  const p=h>0?Math.round(content.scrollTop/h*100):0;
  fill.style.width=p+'%'; pct.textContent=p+'%';
}}
content.addEventListener('scroll',updateProgress);
</script>'''
    return page_shell(safe_title, body, 'body{background:#1a1612;}' + epub_css)


def build_pdf_reader_html(title: str, share_idx: int, file_path: str, back_href: str = '/') -> str:
    safe_title = html_mod.escape(title)
    api_base = f'/api/pdf/{share_idx}/{quote(file_path, safe="/")}'

    pdf_css = """
.pdf-wrap { position:fixed; inset:0; display:flex; flex-direction:column; background:#1a1612; z-index:200; }
.pdf-header { display:flex; align-items:center; padding:10px 16px; background:var(--glass);
  backdrop-filter:blur(20px); border-bottom:1px solid var(--border); gap:8px; flex-shrink:0; }
.pdf-content { flex:1; overflow:auto; display:flex; justify-content:center; padding:16px; }
.pdf-page-img { max-width:100%; max-height:100%; object-fit:contain; border-radius:4px; box-shadow:0 4px 20px rgba(0,0,0,0.4); }
.pdf-nav { display:flex; align-items:center; gap:10px; padding:10px 16px; background:var(--surface);
  border-top:1px solid var(--border); flex-shrink:0; }
.pdf-nav button { padding:8px 16px; border-radius:var(--radius-sm); border:1px solid var(--border);
  background:var(--surface2); color:var(--text); font-size:13px; cursor:pointer; transition:all 0.2s; }
.pdf-nav button:hover { background:var(--accent-bg); border-color:var(--accent); color:var(--accent); }
.pdf-nav button:disabled { opacity:0.3; cursor:default; }
.pdf-page-input { width:60px; text-align:center; padding:8px; border-radius:var(--radius-sm);
  border:1px solid var(--border); background:var(--bg); color:var(--text); font-size:14px; outline:none; }
.pdf-page-input:focus { border-color:var(--accent); }
.pdf-total { font-size:13px; color:var(--text3); }
"""
    body = f'''
<div class="pdf-wrap">
    <div class="pdf-header">
        <a class="back-btn" href="{back_href}"><span class="material-symbols-outlined" style="font-size:18px">arrow_back</span>返回</a>
        <span class="player-title" style="margin-left:0">{safe_title}</span>
    </div>
    <div class="pdf-content" id="pdfContent">
        <img class="pdf-page-img" id="pdfImg" src="{api_base}?page=0" alt="PDF page">
    </div>
    <div class="pdf-nav">
        <button id="prevPage" onclick="goPage(cur-1)" disabled>上一页</button>
        <input class="pdf-page-input" id="pageInput" type="number" value="1" min="1" onchange="goPage(parseInt(this.value)-1)">
        <span class="pdf-total" id="pageTotal">/ ?</span>
        <button id="nextPage" onclick="goPage(cur+1)">下一页</button>
    </div>
</div>
<script>
let cur=0, total=0;
const img=document.getElementById('pdfImg');
const apiBase="{api_base}";

function goPage(n){{
  if(n<0||n>=total) return;
  cur=n;
  img.src=apiBase+'?page='+n;
  document.getElementById('pageInput').value=n+1;
  document.getElementById('prevPage').disabled=n===0;
  document.getElementById('nextPage').disabled=n===total-1;
}}

img.onload=function(){{
  if(!total){{
    const h=this.naturalHeight;
    total=Math.max(1, Math.round(h/100));
  }}
}};

fetch(apiBase+'?page=0').then(r=>{{
  const t=r.headers.get('X-Total-Pages');
  if(t) total=parseInt(t);
  document.getElementById('pageTotal').textContent='/ '+total;
  goPage(0);
}});

img.onerror=function(){{
  this.style.display='none';
  document.getElementById('pdfContent').innerHTML='<div style="color:var(--text3);padding:40px">PDF 加载失败</div>';
}};
</script>'''
    return page_shell(safe_title, body, 'body{background:#1a1612;}' + pdf_css)


def build_admin_html(shares: list[dict], local_ip: str, port: int) -> str:
    share_items = ''
    for i, s in enumerate(shares):
        safe_name = html_mod.escape(s['name'])
        safe_path = html_mod.escape(s['path'])
        share_items += f'''
        <div class="share-item" id="share-{i}">
            <a href="/?share={i}" style="flex:1;min-width:0;text-decoration:none;color:inherit">
                <div class="share-name">{safe_name}</div>
                <div class="share-path">{safe_path}</div>
            </a>
            <button class="share-del" onclick="event.preventDefault();event.stopPropagation();removeShare({i})">移除</button>
        </div>'''
    if not share_items:
        share_items = '<div style="padding:30px;text-align:center;color:var(--text3);font-size:13px;">暂无共享目录，点击下方按钮添加</div>'

    body = f'''
<div class="topbar">
    <h1>管理后台</h1>
    <div class="topbar-right"><a href="/">返回首页</a><a href="/logout">退出</a></div>
</div>
<div class="admin-wrap">
    <div class="stats" id="statsArea">
        <div class="stat-card">
            <div class="stat-num">{len(shares)}</div>
            <div class="stat-label">共享目录</div>
        </div>
        <div class="stat-card" style="text-align:center">
            <div class="stat-num" style="font-size:15px">http://{local_ip}:{port}</div>
            <div class="stat-label">手机访问地址</div>
            <div style="margin-top:10px"><img src="https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=http://{local_ip}:{port}&bgcolor=0c0d14&color=6c8cff" width="140" height="140" style="border-radius:8px" alt="扫码访问"></div>
            <div style="font-size:11px;color:var(--text3);margin-top:6px">手机扫码直接访问</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" id="statUptime">-</div>
            <div class="stat-label">运行时长</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" id="statThumbs">-</div>
            <div class="stat-label">缩略图缓存</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" id="statOnline">-</div>
            <div class="stat-label">在线设备</div>
        </div>
    </div>
    <div class="admin-card">
        <h2>共享目录管理</h2>
        <div id="shareList">{share_items}</div>
    </div>
    <div class="admin-card">
        <h2>磁盘用量</h2>
        <div id="diskArea" style="font-size:13px;color:var(--text3)">加载中...</div>
    </div>
    <div class="admin-card">
        <h2>添加共享目录</h2>
        <div id="msg" class="msg"></div>
        <button class="pick-btn" onclick="openPicker()">选择文件夹</button>
    </div>
    <div class="admin-card">
        <h2>修改密码</h2>
        <div id="pwMsg" class="msg"></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:end">
            <div style="flex:1;min-width:120px"><label style="font-size:12px;color:var(--text3);display:block;margin-bottom:4px">当前密码</label><input id="oldPw" type="password" style="width:100%;padding:10px 12px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;outline:none"></div>
            <div style="flex:1;min-width:120px"><label style="font-size:12px;color:var(--text3);display:block;margin-bottom:4px">新密码</label><input id="newPw" type="password" style="width:100%;padding:10px 12px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;outline:none"></div>
            <button class="pick-btn" onclick="changePassword()" style="margin-bottom:0">确认修改</button>
        </div>
    </div>
    <div class="admin-card">
        <h2>缓存管理</h2>
        <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
            <span style="font-size:13px;color:var(--text2)">缩略图缓存: <b id="cacheSize">-</b></span>
            <button class="share-del" onclick="clearThumbs()">清理缓存</button>
        </div>
    </div>
    <div class="admin-card">
        <h2>使用说明</h2>
        <div style="font-size:13px;color:var(--text3);line-height:2;">
            <p>1. 点击"选择文件夹"，浏览电脑目录并添加共享</p>
            <p>2. 手机浏览器打开 <b style="color:var(--accent)">http://{local_ip}:{port}</b></p>
            <p>3. 点击共享目录即可浏览、播放、上传</p>
            <p>4. 视频支持拖拽进度条、倍速播放、键盘快捷键</p>
            <p>5. 浏览页支持拖拽文件上传</p>
        </div>
    </div>
</div>
<div class="picker-overlay" id="pickerOverlay">
    <div class="picker-box">
        <div class="picker-header">
            <h3>选择文件夹</h3>
            <button class="picker-close" onclick="closePicker()">&times;</button>
        </div>
        <div class="picker-path" id="pickerPath"></div>
        <div class="picker-list" id="pickerList">
            <div class="picker-loading">加载中...</div>
        </div>
        <div class="picker-footer">
            <span class="picker-selected" id="pickerSelected">点击文件夹进入，点击右侧按钮添加共享</span>
            <button class="picker-confirm" id="pickerConfirm" disabled onclick="confirmPick()">添加此文件夹</button>
        </div>
    </div>
</div>
<script>
function showToast(msg,type){{var t=document.createElement('div');t.className='toast toast-'+(type||'info');t.textContent=msg;document.body.appendChild(t);requestAnimationFrame(function(){{t.classList.add('show');}});setTimeout(function(){{t.classList.remove('show');setTimeout(function(){{t.remove();}},300);}},2500);}}
fetch('/api/stats').then(function(r){{return r.json();}}).then(function(d){{
  if(!d.ok) return;
  document.getElementById('statUptime').textContent=d.uptime;
  document.getElementById('statThumbs').textContent=d.thumb_count+' 个';
  document.getElementById('statOnline').textContent=d.online_count+' 台';
  document.getElementById('cacheSize').textContent=d.thumb_size;
  var html='';
  (d.disks||[]).forEach(function(dk){{
    html+='<div style="margin-bottom:12px;padding:10px 12px;background:var(--surface2);border-radius:var(--radius-sm)">';
    html+='<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span style="color:var(--text);font-weight:500">'+dk.name+'</span><span style="color:var(--text3)">'+dk.used+' / '+dk.total+'</span></div>';
    html+='<div style="height:6px;background:var(--surface3);border-radius:3px;overflow:hidden"><div style="height:100%;width:'+dk.pct+'%;background:'+(dk.pct>90?'var(--red)':dk.pct>70?'var(--orange)':'var(--accent)')+';border-radius:3px"></div></div>';
    html+='<div style="font-size:11px;color:var(--text3);margin-top:4px">剩余 '+dk.free+' ('+dk.pct+'% 已用)</div></div>';
  }});
  document.getElementById('diskArea').innerHTML=html||'<span style="color:var(--text3)">无共享目录</span>';
}});
function changePassword(){{
  var o=document.getElementById('oldPw').value,n=document.getElementById('newPw').value;
  var msg=document.getElementById('pwMsg');
  if(!o||!n){{msg.className='msg msg-err';msg.textContent='请填写完整';msg.style.display='block';return;}}
  fetch('/api/password',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{old:o,new:n}})}})
    .then(function(r){{return r.json();}}).then(function(d){{
      if(d.ok){{msg.className='msg msg-ok';msg.textContent='密码已修改';msg.style.display='block';document.getElementById('oldPw').value='';document.getElementById('newPw').value='';}}
      else{{msg.className='msg msg-err';msg.textContent=d.msg||'修改失败';msg.style.display='block';}}
    }});
}}
function clearThumbs(){{
  if(!confirm('确定清理所有缩略图缓存？')) return;
  fetch('/api/clear-thumbs',{{method:'POST'}}).then(function(r){{return r.json();}}).then(function(d){{
    if(d.ok){{document.getElementById('cacheSize').textContent='0 B';document.getElementById('statThumbs').textContent='0 个';showToast('已清理 '+d.count+' 个缓存文件','ok');}}
  }});
}}
</script>
<script>{PICKER_JS}</script>'''
    return page_shell('管理后台 - Media Server', body, PICKER_CSS)


def build_error_html(status: int, message: str) -> str:
    """
    生成深色主题的错误页面 HTML。

    Args:
        status: HTTP 状态码（400/403/404/500 等）
        message: 错误描述信息

    Returns:
        完整的 HTML 错误页面字符串
    """
    icons = {400: 'warning', 403: 'lock', 404: 'search_off', 500: 'error'}
    icon = icons.get(status, 'error')
    colors = {400: '#fb923c', 403: '#f87171', 404: '#6c8cff', 500: '#f87171'}
    color = colors.get(status, '#f87171')
    safe_msg = html_mod.escape(message)
    body = f'''
<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px">
    <div style="text-align:center;max-width:400px">
        <span class="material-symbols-outlined" style="font-size:72px;color:{color};opacity:0.8">{icon}</span>
        <div style="font-size:64px;font-weight:700;color:var(--text);margin:12px 0;letter-spacing:-2px">{status}</div>
        <p style="font-size:15px;color:var(--text2);margin-bottom:28px;line-height:1.6">{safe_msg}</p>
        <a href="/" style="display:inline-block;padding:10px 28px;background:var(--accent);color:#fff;border-radius:var(--radius);font-size:14px;font-weight:500;transition:background 0.2s">返回首页</a>
    </div>
</div>'''
    return page_shell(f'{status} - Media Server', body)
