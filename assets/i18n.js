/**
 * assets/i18n.js - KyteView 官方網站中英雙語字典與切換引擎
 */

const TRANSLATIONS = {
    zh_TW: {
        "page.title": "KyteView - 為 Windows 打造的次世代極速檔案預覽神器 | 媲美 macOS QuickLook",
        
        "top.badge": "v1.5.2 正式版",
        "top.announcement": "KyteView 釋出：全新多國語言 (繁中/英文) 即時切換、各檔案類型全域國際化支援！",

        "nav.brand_sub": "QUICK PREVIEW UTILITY",
        "nav.features": "核心特色",
        "nav.formats": "支援格式",
        "nav.compare": "強大對比",
        "nav.shortcuts": "快捷鍵",
        "nav.pricing": "授權方案",
        "nav.guide": "操作指南",
        "nav.suite": "Kyte 全系列",
        "nav.faq": "常見問答",
        "nav.download": "免費下載",

        "hero.badge": "為 Windows 10 / 11 深度打造 · 毫秒級快速預覽神器",
        "hero.title_pre": "選中檔案，按一下空白鍵",
        "hero.title_post": "內容秒開，工作流絕不卡頓",
        "hero.desc": "不再為了確認內容反覆開啟笨重肥大的微軟 Office 或外部播放器。<br class='hidden sm:inline'>按一下 <kbd class='px-2 py-1 rounded bg-slate-800 border border-slate-700 font-mono-code text-brand-300 font-bold text-sm shadow'>Space</kbd> 瞬間彈出，具備智慧避讓與側邊釘選，為高效專業工作者而生。",
        "hero.btn_installer": "立即下載 Windows 安裝檔 (v1.5.2)",
        "hero.btn_portable": "免安裝綠色版 (.zip)",
        "hero.btn_features": "探索全部殺手級功能",
        "hero.trial_note": "免費下載試用 (14 天全功能暢享) · 零門檻無綁卡 · 開箱即用",

        "mock.badge": "真實操作實錄",
        "mock.filename_demo": "Windows 檔案總管連續秒開實測",
        "mock.filesize_demo": "· 實機錄影 · 20 秒無冷場",
        "mock.pin_title": "釘選模式 (Tab)",
        "mock.tab_label": "切換展示：",
        "mock.tab_demo": "🎬 實機秒開實錄 (Demo)",
        "mock.tab_pptx": "簡報 .pptx",
        "mock.tab_code": "程式碼 .py",
        "mock.tab_archive": "壓縮包 .zip",
        "mock.tab_table": "試算表 .xlsx",
        "mock.video_tip": "檔案總管按 Space 鍵連續預覽 · 毫秒級切換",
        "mock.video_pause": "點擊畫面暫停 / 播放",

        "feat.tag": "WHY KYTEVIEW",
        "feat.title": "為 Windows 量身訂製的極致預覽",
        "feat.desc": "不僅是把 macOS QuickLook 搬到 Windows，更加入「單檔抽出」、「智慧避讓」、「側邊釘選」等諸多原版沒有的殺手級功能。",
        
        "feat.f1_title": "50ms 內極速瞬開",
        "feat.f1_desc": "僅讀取必要的中繼檔頭與 Central Directory，不消耗多餘記憶體，毫秒級秒開毫不猶豫。",
        "feat.f1_tag": "零感延遲 · 極致流暢",

        "feat.f2_title": "智慧避讓偏移",
        "feat.f2_desc": "自動探測檔案總管視窗座標與最大化狀態，視窗自動偏移至對側，絕不遮擋目前選取清單。",
        "feat.f2_tag": "視線無阻 · 效率倍增",

        "feat.f3_title": "側邊釘選模式 (Tab)",
        "feat.f3_desc": "按下 Tab 鍵瞬間將預覽視窗固定於螢幕右側 1/3，搭配上下方向鍵快速連續檢閱大量文件。",
        "feat.f3_tag": "Split View · 連續瀏覽",

        "feat.f4_title": "單檔直接拖曳抽出",
        "feat.f4_desc": "在 ZIP/7Z/RAR 樹狀圖中選取某個檔案，按住滑鼠左鍵直接拖到桌面！自動解壓，告別整包解壓縮。",
        "feat.f4_tag": "Drag & Drop Extract",

        "feat.f5_title": "PPTX 簡報免裝 Office",
        "feat.f5_desc": "2~5ms 封面全彩預覽秒開！支援多頁投影片大綱要點瀏覽、16:9 比例畫布與底部翻頁膠囊。",
        "feat.f5_tag": "專屬 16:9 比例畫布",

        "feat.f6_title": "微軟原生 GPU 影音硬解",
        "feat.f6_desc": "調用微軟 Media Foundation 硬體解碼，零外部大型解碼套件依賴，4K 影片毫秒秒開且 CPU 佔用近乎 0。",
        "feat.f6_tag": "WMF 硬體加速",

        "feat.f7_title": "長按微透機制 (Peek)",
        "feat.f7_desc": "預覽期間長按 Alt 或 Ctrl 鍵，視窗瞬間呈現 15% 半透明，直接穿透看清底層被遮住的內容。",
        "feat.f7_tag": "半透明看穿背景",

        "feat.f8_title": "Windows 11 Mica 毛玻璃",
        "feat.f8_desc": "調用 Windows 原生 DWM 屬性呈現 Mica/Acrylic 頂級材質，完美自適應深色與淺色風格。",
        "feat.f8_tag": "沉浸式微圓角邊框",

        "fmt.tag": "FORMAT SUPPORT",
        "fmt.title": "支援幾乎所有日常工作檔案",
        "fmt.desc": "原生高速解析，不必為了瞄一眼內容啟動肥大軟體。",
        "fmt.pptx": "簡報投影片",
        "fmt.docx": "Word 文件",
        "fmt.xlsx": "試算表格",
        "fmt.zip": "壓縮封裝",
        "fmt.code": "程式代碼",
        "fmt.code_sub": ".py, .js, .cpp 50+種",
        "fmt.pdf": "PDF / 電子書",

        "cmp.tag": "COMPARISON",
        "cmp.title": "為什麼選擇 KyteView？",
        "cmp.desc": "與 Windows 內建預覽窗格及原版 macOS QuickLook 深度對比",
        "cmp.col_dim": "功能比較維度",
        "cmp.col_kv": "KyteView (本軟體)",
        "cmp.col_win": "Windows 原生預覽窗格",
        "cmp.col_mac": "macOS 原版 QuickLook",
        "cmp.r1_title": "開啟速度",
        "cmp.r1_kv": "⚡ < 50ms 秒開瞬彈",
        "cmp.r1_win": "1~3 秒 (經常載入卡頓)",
        "cmp.r1_mac": "約 100~200ms",
        "cmp.r2_title": "壓縮檔單檔直接拖曳抽出",
        "cmp.r2_kv": "✅ 支援 (直接拖到桌面)",
        "cmp.r2_win": "❌ 不支援",
        "cmp.r2_mac": "❌ 不支援 (僅能檢視)",
        "cmp.r3_title": "視窗智慧避讓偏移",
        "cmp.r3_kv": "✅ 自動靠向對側不擋清單",
        "cmp.r3_win": "固定於右側佔用空間",
        "cmp.r3_mac": "居中遮擋當前檔案",
        "cmp.r4_title": "側邊分割釘選模式 (Tab)",
        "cmp.r4_kv": "✅ 支援 (右側 1/3 固定)",
        "cmp.r4_win": "❌ 無彈性",
        "cmp.r4_mac": "❌ 需手動調整視窗",
        "cmp.r5_title": "PPTX 簡報免裝 Office",
        "cmp.r5_kv": "✅ 封面瞬開 + 大綱翻頁",
        "cmp.r5_win": "需安裝完整 MS Office",
        "cmp.r5_mac": "內建支援 (Keynote引擎)",
        "cmp.r6_title": "長按微透機制 (Peek)",
        "cmp.r6_kv": "✅ 長按 Alt/Ctrl 15% 半透明",
        "cmp.r6_win": "❌ 不支援",
        "cmp.r6_mac": "❌ 不支援",

        "sc.tag": "SHORTCUTS",
        "sc.title": "行雲流水的鍵盤操作",
        "sc.desc": "雙手不離鍵盤，極致掌握所有預覽狀態。",
        "sc.toggle": "開啟 / 關閉預覽",
        "sc.pin": "側邊釘選模式",
        "sc.peek": "看穿底層視窗",
        "sc.peek_key": "長按 Alt/Ctrl",

        "price.tag": "PRICING & LICENSING",
        "price.title": "簡單透明，買斷無訂閱負擔",
        "price.desc": "所有版本皆享完整隱私安全與離線本機極速體驗，拒絕繁瑣年費訂閱。",
        
        "price.t1_badge": "零門檻試用",
        "price.t1_title": "免費下載體驗",
        "price.t1_desc": "下載即刻體驗，14 天全功能暢享，無需綁卡、無廣告干擾。",
        "price.t1_period": "/ 14 天全功能暢享",
        "price.t1_f1": "<b>毫秒級快速預覽</b>（Space 鍵秒開秒關）",
        "price.t1_f2": "<b>14 天全功能解鎖</b>：體驗 Word 官方高保真向量預覽",
        "price.t1_f3": "<b>14 天全功能解鎖</b>：體驗壓縮包單檔直接拖曳抽出",
        "price.t1_f4": "<b>14 天全功能解鎖</b>：Win11 Mica 毛玻璃、側邊釘選與透視",
        "price.t1_f5": "圖片全螢幕、4K 影音 GPU 硬解播放與代碼語法著色",
        "price.t1_f6": "試用期滿後<b>溫和降級</b>（保留日常必備預覽，工作流不中斷）",
        "price.t1_btn": "免費下載試用 (v1.5.2)",

        "price.t2_badge_top": "早鳥特惠 · 限量發售",
        "price.t2_badge_rec": "推薦旗艦",
        "price.t2_title": "個人終身專業版",
        "price.t2_desc": "一次買斷終身使用，<b>預設提供 2 台裝置授權</b>，個人公私設備全包辦。",
        "price.t2_tag_perpetual": "買斷永久",
        "price.t2_f1": "<b>1 組序號同時啟用 2 台裝置</b>（一桌機一筆電，全場包辦）",
        "price.t2_f2": "<b>換機零後顧之憂</b>：舊電腦隨時一鍵移轉解綁，終身有效",
        "price.t2_f3": "<b>Word 官方引擎高保真向量預覽</b>（表格排版 100% 零跑版）",
        "price.t2_f4": "<b>壓縮檔單檔直接拖曳抽出</b>（無需整包解壓，直拖桌面複製）",
        "price.t2_f5": "<b>Win11 Mica 毛玻璃材質、側邊釘選分割與微透機制</b>",
        "price.t2_f6": "<b>享有一年內免費維護與 Bug 修復</b>（若未來 OS 大型改版需重構，新版另行販售）",
        "price.t2_btn": "立即取得早鳥序號 (NT$ 299 終身買斷)",
        "price.bundle_btn": "選購 Kyte Suite 旗艦三合一套裝 (All-in-One)",
        "price.t2_sub1": "離線安全無後門",
        "price.t2_sub2": "支援自主換機移轉",

        "faq.title": "常見問題解答",
        "faq.q1": "KyteView 支援哪些 Windows 作業系統？",
        "faq.a1": "KyteView 專為 64 位元 Windows 10 (1809 以上) 與最新 Windows 11 深度設計，完美原生支援深色模式（Dark Mode）、淺色模式以及 Windows 11 Mica / Acrylic 毛玻璃半透明材質。",
        "faq.q2": "預覽 Word 或 PowerPoint 需要在電腦安裝微軟 Office 嗎？",
        "faq.a2": "完全不需要！KyteView 採用純原生輕量解析引擎，PPTX 透過內嵌縮圖 2~5ms 秒開並支援多頁大綱條列；DOCX 透過純 Python 輕量轉標準 HTML 渲染，即使電腦完全沒有安裝 Office 也能流暢秒開。",
        "faq.q3": "防毒軟體或 Windows Defender 是否會誤報？",
        "faq.a3": "由於 KyteView 使用 Windows 底層低階鍵盤鉤子（Low-Level Keyboard Hook）監聽檔案總管中的空白鍵（Space），部分防毒軟體首次執行時可能會出現提示。KyteView 為純本地端離線運作工具，絕不連網傳輸您的任何個人檔案，請安心點擊允許。",
        "faq.q4": "本軟體授權規範為何？商業使用需要購買嗎？",
        "faq.a4": "本專案原始碼採用 Personal & Non-Commercial License，僅供個人學習、研究與檢閱用途。未經授權禁止任何形式之商業用途、轉售或重新散布。商業使用或官方封裝版本請向原作者取得正式授權。",
        "faq.q5": "一次性買斷的維護期與後續更新政策是什麼？",
        "faq.a5": "本商品為一次性買斷，享有一年內免費維護與 Bug 修復。若未來作業系統大型改版（如 Windows 升級）導致軟體需重構，新版本將另行販售。",

        "footer.slogan": "— Windows 次世代極速檔案預覽神器",
        "footer.features": "特色功能",
        "footer.guide": "操作指南",
        "footer.shortcuts": "操作快捷鍵",
        "footer.terms": "服務條款",
        "footer.privacy": "隱私權政策",
        "footer.license": "授權條款 (License)",
        "footer.support": "技術支援",
        "footer.contact": "技術支援與售後聯絡：<a href=\"mailto:support@aisming.com?subject=%5B%E5%95%8F%E9%A1%8C%E5%9B%9E%E5%A0%B1%5D%20KyteView%20%E4%BD%BF%E7%94%A8%E8%AB%AE%E8%A9%A2\" class=\"text-brand-400 hover:underline font-semibold\">support@aisming.com</a> · 全年無休客服信箱"
    },

    en_US: {
        "page.title": "KyteView - Next-Gen Instant File Preview Utility for Windows | Best QuickLook Alternative",
        
        "top.badge": "v1.5.2 Official",
        "top.announcement": "KyteView Released: Brand-new multi-language (Traditional Chinese & English) support!",

        "nav.brand_sub": "QUICK PREVIEW UTILITY",
        "nav.features": "Features",
        "nav.formats": "Formats",
        "nav.compare": "Comparison",
        "nav.shortcuts": "Shortcuts",
        "nav.pricing": "Pricing",
        "nav.guide": "User Guide",
        "nav.suite": "Kyte Suite",
        "nav.faq": "FAQ",
        "nav.download": "Free Download",

        "hero.badge": "Engineered for Windows 10 & 11 · Millisecond Instant Preview",
        "hero.title_pre": "Select Any File, Press Spacebar,",
        "hero.title_post": "Instant Preview with Zero Friction",
        "hero.desc": "Never wait for bulky Microsoft Office or external media players again.<br class='hidden sm:inline'>Press <kbd class='px-2 py-1 rounded bg-slate-800 border border-slate-700 font-mono-code text-brand-300 font-bold text-sm shadow'>Space</kbd> for instant popups with smart offset positioning and side-dock pinning.",
        "hero.btn_installer": "Download Windows Setup (v1.5.2)",
        "hero.btn_portable": "Portable .zip Edition",
        "hero.btn_features": "Explore Killer Features",
        "hero.trial_note": "Free 14-day full trial · No credit card required · Ready out of the box",

        "mock.badge": "Real Demo Recording",
        "mock.filename_demo": "Windows Explorer Instant Preview Demo",
        "mock.filesize_demo": "· Real Recording · 20s Action",
        "mock.pin_title": "Pin to Side (Tab)",
        "mock.tab_label": "Switch Demo:",
        "mock.tab_demo": "🎬 Live Demo (Video)",
        "mock.tab_pptx": "Presentation .pptx",
        "mock.tab_code": "Code .py",
        "mock.tab_archive": "Archive .zip",
        "mock.tab_table": "Spreadsheet .xlsx",
        "mock.video_tip": "Press Space in Explorer for continuous previews · Millisecond switching",
        "mock.video_pause": "Click video to Pause / Play",

        "feat.tag": "WHY KYTEVIEW",
        "feat.title": "Tailor-Made Instant Preview for Windows",
        "feat.desc": "Beyond simply porting macOS QuickLook to Windows, KyteView introduces killer capabilities like Drag & Drop Extraction, Smart Offsetting, and Side Pinning.",
        
        "feat.f1_title": "Sub-50ms Instant Launch",
        "feat.f1_desc": "Reads only essential metadata headers and central directories, consuming minimal RAM with true millisecond speed.",
        "feat.f1_tag": "Zero Latency · Ultimate Smoothness",

        "feat.f2_title": "Smart Offsetting",
        "feat.f2_desc": "Detects Explorer coordinates and automatically shifts the preview window to the opposite side, never obscuring file lists.",
        "feat.f2_tag": "Unblocked View · 2x Efficiency",

        "feat.f3_title": "Side Pinning Mode (Tab)",
        "feat.f3_desc": "Press Tab to lock the preview to the right third of your screen. Browse dozens of files sequentially with arrow keys.",
        "feat.f3_tag": "Split View · Fast Navigation",

        "feat.f4_title": "Drag & Drop Extraction",
        "feat.f4_desc": "Select any single file inside a ZIP, 7Z, or RAR tree and drag it straight to your desktop. Auto-extracted without unzipping all.",
        "feat.f4_tag": "Drag & Drop Extract",

        "feat.f5_title": "PPTX Without Office Installed",
        "feat.f5_desc": "Full-color cover preview in 2~5ms! Features multi-slide outline viewing, dedicated 16:9 canvas, and page navigation capsules.",
        "feat.f5_tag": "Dedicated 16:9 Canvas",

        "feat.f6_title": "Native GPU Video Decoding",
        "feat.f6_desc": "Leverages Windows Media Foundation hardware acceleration with zero external dependencies. 4K video opens instantly at ~0% CPU load.",
        "feat.f6_tag": "WMF Hardware Accelerated",

        "feat.f7_title": "Hold to Peek (Translucency)",
        "feat.f7_desc": "Hold Alt or Ctrl during preview to turn the window 15% translucent, letting you see obscured windows underneath seamlessly.",
        "feat.f7_tag": "Translucent Background Peek",

        "feat.f8_title": "Windows 11 Mica Aesthetics",
        "feat.f8_desc": "Applies native Windows DWM Mica & Acrylic materials, adapting elegantly to both system dark and light modes.",
        "feat.f8_tag": "Immersive Rounded Borders",

        "fmt.tag": "FORMAT SUPPORT",
        "fmt.title": "Supports Nearly All Daily Work Files",
        "fmt.desc": "Native fast parsing—no need to launch heavy apps just for a quick peek.",
        "fmt.pptx": "Presentations",
        "fmt.docx": "Word Docs",
        "fmt.xlsx": "Spreadsheets",
        "fmt.zip": "Archives",
        "fmt.code": "Source Code",
        "fmt.code_sub": ".py, .js, .cpp 50+ languages",
        "fmt.pdf": "PDF & eBooks",

        "cmp.tag": "COMPARISON",
        "cmp.title": "Why Choose KyteView?",
        "cmp.desc": "In-depth comparison with Windows Explorer Preview Pane and native macOS QuickLook",
        "cmp.col_dim": "Comparison Matrix",
        "cmp.col_kv": "KyteView",
        "cmp.col_win": "Windows Preview Pane",
        "cmp.col_mac": "macOS QuickLook",
        "cmp.r1_title": "Launch Speed",
        "cmp.r1_kv": "⚡ < 50ms Instant Popup",
        "cmp.r1_win": "1~3s (Frequent stutter)",
        "cmp.r1_mac": "~100~200ms",
        "cmp.r2_title": "Single File Drag Extract",
        "cmp.r2_kv": "✅ Yes (Drag direct to desktop)",
        "cmp.r2_win": "❌ No",
        "cmp.r2_mac": "❌ No (View only)",
        "cmp.r3_title": "Smart Window Offset",
        "cmp.r3_kv": "✅ Auto shifts opposite side",
        "cmp.r3_win": "Fixed on right pane",
        "cmp.r3_mac": "Centered over files",
        "cmp.r4_title": "Side Pinning Mode (Tab)",
        "cmp.r4_kv": "✅ Yes (Right 1/3 fixed)",
        "cmp.r4_win": "❌ Inflexible",
        "cmp.r4_mac": "❌ Manual resize needed",
        "cmp.r5_title": "PPTX Without Office",
        "cmp.r5_kv": "✅ Cover instant + outlines",
        "cmp.r5_win": "Requires MS Office installed",
        "cmp.r5_mac": "Built-in (Keynote engine)",
        "cmp.r6_title": "Hold to Peek (Translucent)",
        "cmp.r6_kv": "✅ Hold Alt/Ctrl 15% transparent",
        "cmp.r6_win": "❌ No",
        "cmp.r6_mac": "❌ No",

        "sc.tag": "SHORTCUTS",
        "sc.title": "Fluid Keyboard Control",
        "sc.desc": "Keep your hands on the keyboard for total preview mastery.",
        "sc.toggle": "Toggle Preview On/Off",
        "sc.pin": "Side Pinning Mode",
        "sc.peek": "Peek Through Windows",
        "sc.peek_key": "Hold Alt / Ctrl",

        "price.tag": "PRICING & LICENSING",
        "price.title": "Transparent & Fair, No Subscriptions",
        "price.desc": "All tiers feature full privacy and offline local speed. Zero recurring annual fees.",
        
        "price.t1_badge": "Risk-Free Trial",
        "price.t1_title": "Free Download",
        "price.t1_desc": "Immediate download, 14 days of full feature access, no card required, no ads.",
        "price.t1_period": "/ 14-Day Free Access",
        "price.t1_f1": "<b>Sub-50ms instant preview</b> (Spacebar toggle)",
        "price.t1_f2": "<b>14-day Pro unlock</b>: Official Word high-fidelity vector previews",
        "price.t1_f3": "<b>14-day Pro unlock</b>: Single file drag-and-drop extraction from archives",
        "price.t1_f4": "<b>14-day Pro unlock</b>: Win11 Mica, side pinning & peek translucent mode",
        "price.t1_f5": "Fullscreen images, 4K GPU video playback & syntax highlighting",
        "price.t1_f6": "Gentle graceful fallback after trial (essential previews preserved)",
        "price.t1_btn": "Download Free Trial (v1.5.2)",

        "price.t2_badge_top": "Early Bird · Limited Offer",
        "price.t2_badge_rec": "Recommended Pro",
        "price.t2_title": "Personal Lifetime Pro",
        "price.t2_desc": "One-time purchase for lifetime use. <b>Includes 2 concurrent device activations</b>.",
        "price.t2_tag_perpetual": "Perpetual License",
        "price.t2_f1": "<b>1 license activates 2 devices concurrently</b> (desktop & laptop covered)",
        "price.t2_f2": "<b>Hassle-free PC transfer</b>: One-click unbind and transfer anytime",
        "price.t2_f3": "<b>Word high-fidelity vector preview</b> (zero table layout shift)",
        "price.t2_f4": "<b>Drag & drop single file extraction</b> (extract direct to desktop)",
        "price.t2_f5": "<b>Win11 Mica material, side pinning & peek translucency</b>",
        "price.t2_f6": "<b>Includes 1 year of free maintenance & bug fixes</b> (major OS rewrites sold separately)",
        "price.t2_btn": "Get Early Bird License (NT$ 299 Lifetime)",
        "price.bundle_btn": "Get Kyte Suite Trio (All-in-One Bundle)",
        "price.t2_sub1": "100% Offline Safe",
        "price.t2_sub2": "Self-Serve Device Transfer",

        "faq.title": "Frequently Asked Questions",
        "faq.q1": "Which Windows versions are supported?",
        "faq.a1": "KyteView is engineered specifically for 64-bit Windows 10 (version 1809+) and Windows 11, with full native support for Dark Mode, Light Mode, and Windows 11 Mica / Acrylic transparency.",
        "faq.q2": "Do I need Microsoft Office installed to preview Word or PowerPoint?",
        "faq.a2": "Not at all! KyteView uses a native lightweight parsing engine. PPTX loads covers in 2~5ms with outline viewing, and DOCX is rendered via pure lightweight engines—no Office installation needed.",
        "faq.q3": "Will Windows Defender or antivirus software flag KyteView?",
        "faq.a3": "Because KyteView uses low-level keyboard hooks to detect Spacebar presses inside File Explorer, some antivirus tools may prompt initially. KyteView runs 100% locally and never transmits your data. Please click Allow.",
        "faq.q4": "What are the licensing terms? Can I use it commercially?",
        "faq.a4": "The open repository uses a Personal & Non-Commercial License. For commercial deployment or pre-packaged enterprise binaries, please acquire an official commercial license from the author.",
        "faq.q5": "What is the maintenance period and update policy for perpetual purchases?",
        "faq.a5": "Licenses are one-time perpetual purchases including one year of free maintenance and bug fixes. If future major operating system overhauls (such as major Windows version upgrades) necessitate substantial software refactoring, new major releases will be sold separately.",

        "footer.slogan": "— Next-Gen Instant File Preview Utility for Windows",
        "footer.features": "Features",
        "footer.guide": "User Guide",
        "footer.shortcuts": "Shortcuts",
        "footer.terms": "Terms of Service",
        "footer.privacy": "Privacy Policy",
        "footer.license": "License",
        "footer.support": "Technical Support",
        "footer.contact": "Support & Inquiries: <a href=\"mailto:support@aisming.com?subject=%5BInquiry%5D%20KyteView%20Support\" class=\"text-brand-400 hover:underline font-semibold\">support@aisming.com</a> · 24/7 Customer Service"
    }
};

let currentLang = 'zh_TW';

function getInitialLanguage() {
    const saved = localStorage.getItem('kyte_view_lang');
    if (saved && (saved === 'zh_TW' || saved === 'en_US')) {
        return saved;
    }
    const sysLang = navigator.language || navigator.userLanguage || '';
    if (sysLang.toLowerCase().includes('zh')) {
        return 'zh_TW';
    }
    return 'en_US';
}

function applyLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('kyte_view_lang', lang);
    document.documentElement.lang = lang === 'zh_TW' ? 'zh-TW' : 'en';

    const dict = TRANSLATIONS[lang] || TRANSLATIONS.zh_TW;

    if (dict["page.title"]) {
        document.title = dict["page.title"];
    }

    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) {
            el.innerHTML = dict[key];
        }
    });

    // 智能切換操作指南目標網址
    const guideLinks = document.querySelectorAll('a[href="guide.html"], a[href="guide_en.html"]');
    guideLinks.forEach(a => {
        a.href = lang === 'en_US' ? 'guide_en.html' : 'guide.html';
    });

    const langBtnText = document.getElementById('lang-btn-text');
    if (langBtnText) {
        langBtnText.textContent = lang === 'zh_TW' ? 'EN' : '繁中';
    }

    // 同步更新 Mockup 視圖中目前 tab 的標題
    if (typeof currentMockTab !== 'undefined' && typeof switchMockTab === 'function') {
        switchMockTab(currentMockTab);
    }
}

function toggleLanguage() {
    const nextLang = currentLang === 'zh_TW' ? 'en_US' : 'zh_TW';
    applyLanguage(nextLang);
}

document.addEventListener('DOMContentLoaded', () => {
    const initial = getInitialLanguage();
    applyLanguage(initial);

    const toggleBtn = document.getElementById('lang-toggle-btn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleLanguage);
    }
});
