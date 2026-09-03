/**
 * ScrapeAI - Frontend Controller Logic
 * Universal Web Scraper + Continuous Multi-Site Batching + Proxy Pool + Hugging Face RAG AI
 */

// Global State
const state = {
    mode: 'single', // 'single' | 'batch'
    currentData: null,
    currentBatchData: null,
    activeTab: 'tab-article',
    apiUrl: localStorage.getItem('scraper_api_url') || '',
    hfToken: localStorage.getItem('hf_token') || '',
    modelName: localStorage.getItem('hf_model') || 'Qwen/Qwen2.5-7B-Instruct',
    defaultProxy: localStorage.getItem('default_proxy') || '',
    systemPrompt: localStorage.getItem('hf_system_prompt') || '',
    isScraping: false,
    isChatting: false
};

// Helper for backend API endpoints (supporting split Vercel + Render deployments)
function getApiUrl(path) {
    const base = (state.apiUrl || '').trim().replace(/\/+$/, '');
    if (!base) return path;
    return `${base}${path.startsWith('/') ? path : '/' + path}`;
}

// DOM References
const dom = {
    // Mode Switcher
    modeSingleBtn: document.getElementById('modeSingleBtn'),
    modeBatchBtn: document.getElementById('modeBatchBtn'),
    proxyStatusBadge: document.getElementById('proxyStatusBadge'),
    proxyStatusText: document.getElementById('proxyStatusText'),
    
    // Single Form
    scrapeForm: document.getElementById('scrapeForm'),
    urlInput: document.getElementById('urlInput'),
    scrapeBtn: document.getElementById('scrapeBtn'),
    presetPills: document.querySelectorAll('.preset-pill'),
    toggleAdvOptions: document.getElementById('toggleAdvOptions'),
    advancedDrawer: document.getElementById('advancedDrawer'),
    customSelector: document.getElementById('customSelector'),
    proxyInput: document.getElementById('proxyInput'),
    testProxyBtn: document.getElementById('testProxyBtn'),
    
    // Batch Form
    batchScrapeForm: document.getElementById('batchScrapeForm'),
    batchUrlsInput: document.getElementById('batchUrlsInput'),
    batchProxiesInput: document.getElementById('batchProxiesInput'),
    proxyRotationSelect: document.getElementById('proxyRotationSelect'),
    throttleDelayInput: document.getElementById('throttleDelayInput'),
    delayValLabel: document.getElementById('delayValLabel'),
    loadSampleBatchBtn: document.getElementById('loadSampleBatchBtn'),
    loadTestProxyBtn: document.getElementById('loadTestProxyBtn'),
    testBatchProxyBtn: document.getElementById('testBatchProxyBtn'),
    batchScrapeBtn: document.getElementById('batchScrapeBtn'),

    // Progress Bar
    progressContainer: document.getElementById('progressContainer'),
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    
    // Stats
    statWords: document.getElementById('statWords'),
    statTables: document.getElementById('statTables'),
    statLinks: document.getElementById('statLinks'),
    statImages: document.getElementById('statImages'),
    batchTabBadge: document.getElementById('batchTabBadge'),
    tableTabBadge: document.getElementById('tableTabBadge'),
    linkTabBadge: document.getElementById('linkTabBadge'),
    imgTabBadge: document.getElementById('imgTabBadge'),
    
    // Viewer Tabs & Elements
    vTabs: document.querySelectorAll('.v-tab'),
    tabPanels: document.querySelectorAll('.tab-panel'),
    emptyState: document.getElementById('emptyState'),
    articleMetaHeader: document.getElementById('articleMetaHeader'),
    articleTitle: document.getElementById('articleTitle'),
    articleAuthor: document.getElementById('articleAuthor'),
    articleSource: document.getElementById('articleSource'),
    articleDate: document.getElementById('articleDate'),
    articleProxy: document.getElementById('articleProxy'),
    articleProxyText: document.getElementById('articleProxyText'),
    articleBody: document.getElementById('articleBody'),
    batchContainer: document.getElementById('batchContainer'),
    tablesContainer: document.getElementById('tablesContainer'),
    linksList: document.getElementById('linksList'),
    linkSearch: document.getElementById('linkSearch'),
    imagesGrid: document.getElementById('imagesGrid'),
    jsonCode: document.getElementById('jsonCode'),
    copyJsonBtn: document.getElementById('copyJsonBtn'),
    
    // Export Dropdown
    exportBtn: document.getElementById('exportBtn'),
    exportMenu: document.getElementById('exportMenu'),
    exportOpts: document.querySelectorAll('.export-opt'),
    
    // Chatbot Panel
    chatForm: document.getElementById('chatForm'),
    chatInput: document.getElementById('chatInput'),
    sendBtn: document.getElementById('sendBtn'),
    chatMessages: document.getElementById('chatMessages'),
    clearChatBtn: document.getElementById('clearChatBtn'),
    chatActiveModel: document.getElementById('chatActiveModel'),
    suggestionChips: document.getElementById('suggestionChips'),
    
    // Modals
    settingsModal: document.getElementById('settingsModal'),
    closeSettingsModal: document.getElementById('closeSettingsModal'),
    cancelSettingsBtn: document.getElementById('cancelSettingsBtn'),
    saveSettingsBtn: document.getElementById('saveSettingsBtn'),
    apiUrlInput: document.getElementById('apiUrlInput'),
    hfTokenInput: document.getElementById('hfTokenInput'),
    modelSelect: document.getElementById('modelSelect'),
    defaultProxyInput: document.getElementById('defaultProxyInput'),
    systemPromptInput: document.getElementById('systemPromptInput'),
    
    historyModal: document.getElementById('historyModal'),
    closeHistoryModal: document.getElementById('closeHistoryModal'),
    historyList: document.getElementById('historyList'),
    
    // Nav Triggers
    sidebarSettingsBtn: document.getElementById('sidebarSettingsBtn'),
    sidebarHistoryBtn: document.getElementById('sidebarHistoryBtn'),
    topSettingsTab: document.getElementById('topSettingsTab'),
    topHistoryTab: document.getElementById('topHistoryTab'),
    topAiModelsTab: document.getElementById('topAiModelsTab'),
    topDocsTab: document.getElementById('topDocsTab'),
    serverStatus: document.getElementById('serverStatus'),
    sidebarItems: document.querySelectorAll('.sidebar-item'),
    topTabs: document.querySelectorAll('.top-tab')
};

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    initSettings();
    initEventListeners();
    checkHealth();
});

function initSettings() {
    if (state.apiUrl && dom.apiUrlInput) dom.apiUrlInput.value = state.apiUrl;
    if (state.hfToken) dom.hfTokenInput.value = state.hfToken;
    if (state.modelName) dom.modelSelect.value = state.modelName;
    if (state.defaultProxy) {
        dom.defaultProxyInput.value = state.defaultProxy;
        if (dom.proxyInput) dom.proxyInput.value = state.defaultProxy;
        updateProxyBadge(state.defaultProxy);
    }
    if (state.systemPrompt) dom.systemPromptInput.value = state.systemPrompt;
    updateActiveModelBadge();
}

function updateActiveModelBadge() {
    const isTokenSet = Boolean(state.hfToken);
    const shortName = state.modelName.split('/').pop();
    dom.chatActiveModel.textContent = isTokenSet ? `HF: ${shortName}` : 'Offline Mode (Local QA)';
}

function updateProxyBadge(proxyStr) {
    if (proxyStr && proxyStr.trim()) {
        const masked = proxyStr.length > 25 ? proxyStr.substring(0, 22) + '...' : proxyStr;
        dom.proxyStatusBadge.classList.add('active');
        dom.proxyStatusText.textContent = `Proxy: ${masked}`;
    } else {
        dom.proxyStatusBadge.classList.remove('active');
        dom.proxyStatusText.textContent = 'Direct (No Proxy)';
    }
}

// --- EVENT LISTENERS ---
function initEventListeners() {
    // Mode Switcher
    dom.modeSingleBtn.addEventListener('click', () => switchMode('single'));
    dom.modeBatchBtn.addEventListener('click', () => switchMode('batch'));

    // Single Scraper Form
    dom.scrapeForm.addEventListener('submit', handleSingleScrapeSubmit);

    // Batch Scraper Form
    dom.batchScrapeForm.addEventListener('submit', handleBatchScrapeSubmit);

    // Preset Pills for Single Scraper
    dom.presetPills.forEach(pill => {
        pill.addEventListener('click', () => {
            if (pill.dataset.url) {
                dom.urlInput.value = pill.dataset.url;
                dom.scrapeForm.dispatchEvent(new Event('submit'));
            }
        });
    });

    // Sample Batch Sites Loader
    dom.loadSampleBatchBtn.addEventListener('click', () => {
        dom.batchUrlsInput.value = [
            'https://en.wikipedia.org/wiki/Web_scraping',
            'https://news.ycombinator.com',
            'https://docs.python.org/3/tutorial/'
        ].join('\n');
    });

    // Load Free Test Proxy Preset
    dom.loadTestProxyBtn.addEventListener('click', () => {
        // Preset sample public / test proxy format
        dom.batchProxiesInput.value = [
            'http://127.0.0.1:8080',
            'socks5://127.0.0.1:9050',
            'http://user:pass@gate.smartproxy.com:7000'
        ].join('\n');
        alert('ℹ️ Sample proxy formats added! You can test local Tor (socks5://127.0.0.1:9050) or your own proxies.');
    });

    // Throttle Delay Slider
    dom.throttleDelayInput.addEventListener('input', (e) => {
        dom.delayValLabel.textContent = `${parseFloat(e.target.value).toFixed(1)}s`;
    });

    // Toggle Advanced Drawer in Single Mode
    dom.toggleAdvOptions.addEventListener('click', () => {
        dom.advancedDrawer.classList.toggle('open');
    });

    // Test Proxy Buttons
    dom.testProxyBtn.addEventListener('click', () => testProxyConnection(dom.proxyInput.value.trim()));
    dom.testBatchProxyBtn.addEventListener('click', () => {
        const firstProxy = (dom.batchProxiesInput.value.trim().split(/[\r\n,;]+/)[0] || '').trim();
        testProxyConnection(firstProxy);
    });

    // Viewer Tabs
    dom.vTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            switchViewerTab(tab.dataset.tab);
        });
    });

    // Sidebar navigation clicks
    dom.sidebarItems.forEach(item => {
        item.addEventListener('click', (e) => {
            if (item.id === 'sidebarSettingsBtn' || item.id === 'sidebarHistoryBtn') return;
            dom.sidebarItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            
            const view = item.dataset.view;
            if (view && view.startsWith('tab-')) {
                switchViewerTab(view);
            }
        });
    });

    // Export Menu
    dom.exportBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dom.exportMenu.classList.toggle('open');
    });
    document.addEventListener('click', () => dom.exportMenu.classList.remove('open'));
    
    dom.exportOpts.forEach(btn => {
        btn.addEventListener('click', () => {
            handleExport(btn.dataset.fmt);
            dom.exportMenu.classList.remove('open');
        });
    });

    // Copy JSON
    dom.copyJsonBtn.addEventListener('click', () => {
        const content = dom.jsonCode.textContent;
        navigator.clipboard.writeText(content).then(() => {
            const original = dom.copyJsonBtn.innerHTML;
            dom.copyJsonBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
            setTimeout(() => dom.copyJsonBtn.innerHTML = original, 2000);
        });
    });

    // Link Search Filter
    dom.linkSearch.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const items = dom.linksList.querySelectorAll('.link-item-row');
        items.forEach(it => {
            const text = it.textContent.toLowerCase();
            it.style.display = text.includes(query) ? 'flex' : 'none';
        });
    });

    // Chatbot Submit
    dom.chatForm.addEventListener('submit', handleChatSubmit);
    dom.clearChatBtn.addEventListener('click', clearChatFeed);

    // Suggestion Chips
    dom.suggestionChips.querySelectorAll('.quick-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            dom.chatInput.value = chip.dataset.prompt;
            dom.chatForm.dispatchEvent(new Event('submit'));
        });
    });

    // Modals Handling
    dom.sidebarSettingsBtn.addEventListener('click', () => openModal(dom.settingsModal));
    dom.closeSettingsModal.addEventListener('click', () => closeModal(dom.settingsModal));
    dom.cancelSettingsBtn.addEventListener('click', () => closeModal(dom.settingsModal));
    dom.saveSettingsBtn.addEventListener('click', handleSaveSettings);

    dom.sidebarHistoryBtn.addEventListener('click', () => {
        openModal(dom.historyModal);
        loadHistory();
    });
    dom.closeHistoryModal.addEventListener('click', () => closeModal(dom.historyModal));
}

// --- SWITCH MODE: SINGLE VS BATCH ---
function switchMode(newMode) {
    state.mode = newMode;
    if (newMode === 'single') {
        dom.modeSingleBtn.classList.add('active');
        dom.modeBatchBtn.classList.remove('active');
        dom.scrapeForm.style.display = 'block';
        dom.batchScrapeForm.style.display = 'none';
    } else {
        dom.modeBatchBtn.classList.add('active');
        dom.modeSingleBtn.classList.remove('active');
        dom.scrapeForm.style.display = 'none';
        dom.batchScrapeForm.style.display = 'block';
    }
}

// --- TEST PROXY CONNECTION ---
async function testProxyConnection(proxyUrl) {
    if (!proxyUrl) {
        alert('Please enter a proxy URL to test (e.g. http://127.0.0.1:8080 or socks5://127.0.0.1:9050)');
        return;
    }

    setLoadingState(true, `Testing proxy: ${proxyUrl}...`);
    try {
        const res = await fetch(getApiUrl('/api/proxy/test'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ proxy: proxyUrl })
        });
        const data = await res.json();
        if (data.success) {
            alert(`✅ Proxy Connection Successful!\n\nPublic IP: ${data.ip}\nLatency: ${data.latency_seconds}s\nProxy: ${data.proxy_tested}`);
            updateProxyBadge(proxyUrl);
        } else {
            alert(`❌ Proxy Connection Failed:\n\n${data.error || data.message}`);
        }
    } catch (err) {
        alert(`❌ Network test error: ${err.message}`);
    } finally {
        setLoadingState(false);
    }
}

// --- SINGLE URL SCRAPE ACTION ---
async function handleSingleScrapeSubmit(e) {
    e.preventDefault();
    const url = dom.urlInput.value.trim();
    if (!url) return;

    const proxy = dom.proxyInput ? dom.proxyInput.value.trim() : state.defaultProxy;
    state.isScraping = true;
    setLoadingState(true, proxy ? `Connecting via proxy (${proxy})...` : "Connecting to target site...");

    try {
        updateProgress(35, "Parsing HTML, metadata, tables, links & images...");
        
        const res = await fetch(getApiUrl('/api/scrape'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                custom_selector: dom.customSelector.value.trim() || null,
                proxy: proxy || null,
                hf_token: state.hfToken || null,
                model_name: state.modelName
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Scraping failed');
        }

        updateProgress(80, "Building semantic RAG vector index...");
        const data = await res.json();
        
        state.currentData = data;
        state.currentBatchData = null;
        renderScrapedData(data);
        updateProgress(100, "Scraping & Indexing Completed!");

        const proxyNotice = data.proxy ? ` via Proxy **${data.proxy}**` : '';
        addBotMessage(`✅ Successfully extracted **${data.metadata.title || data.url}**${proxyNotice} (${data.stats.word_count} words, ${data.stats.table_count} tables, ${data.stats.link_count} links). Indexed **${data.indexed_chunks || 0} chunks** for RAG AI. Ask me anything!`);
    } catch (err) {
        alert(`Scraping Error: ${err.message}`);
        console.error(err);
    } finally {
        setTimeout(() => setLoadingState(false), 500);
    }
}

// --- MULTI-SITE CONTINUOUS BATCH SCRAPE ACTION ---
async function handleBatchScrapeSubmit(e) {
    e.preventDefault();
    let urlsRaw = dom.batchUrlsInput.value.trim();
    if (!urlsRaw) {
        // Auto-load 3 standard sample sites if left empty
        urlsRaw = [
            'https://en.wikipedia.org/wiki/Web_scraping',
            'https://news.ycombinator.com',
            'https://docs.python.org/3/tutorial/'
        ].join('\n');
        dom.batchUrlsInput.value = urlsRaw;
    }

    const urls = urlsRaw.split(/[\r\n]+/).map(u => u.trim()).filter(Boolean);
    const proxiesRaw = dom.batchProxiesInput.value.trim();
    const proxies = proxiesRaw ? proxiesRaw.split(/[\r\n,;]+/).map(p => p.trim()).filter(Boolean) : (state.defaultProxy ? [state.defaultProxy] : null);
    const rotation = dom.proxyRotationSelect.value;
    const delay = parseFloat(dom.throttleDelayInput.value) || 0.5;

    state.isScraping = true;
    setLoadingState(true, `Starting continuous batch scrape across ${urls.length} sites...`);
    switchViewerTab('tab-batch');

    try {
        updateProgress(25, `Connecting & scraping ${urls.length} target websites...`);

        const res = await fetch(getApiUrl('/api/scrape/batch'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                urls: urls,
                proxies: proxies && proxies.length > 0 ? proxies : null,
                proxy_rotation: rotation,
                delay_seconds: delay,
                hf_token: state.hfToken || null,
                model_name: state.modelName
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Batch scraping failed');
        }

        updateProgress(85, "Building unified RAG vector index over all websites...");
        const batchData = await res.json();

        state.currentBatchData = batchData;
        state.currentData = null;
        renderBatchData(batchData);
        updateProgress(100, "Continuous Batch Scrape Completed!");

        addBotMessage(`🚀 **Continuous Batch Scraping Completed!**\n\n- Scraped **${batchData.success_count} / ${batchData.total_urls} websites** successfully.\n- Total **${batchData.stats.total_words} words**, **${batchData.stats.total_tables} tables**, **${batchData.stats.total_links} links** extracted.\n- RAG vector search is ready over the combined corpus of all sites. Ask any comparative question!`);
    } catch (err) {
        alert(`Batch Scraping Error: ${err.message}`);
        console.error(err);
    } finally {
        setTimeout(() => setLoadingState(false), 500);
    }
}

// --- RENDER BATCH SCRAPED DATA ---
function renderBatchData(batchData) {
    dom.emptyState.style.display = 'none';

    // Update Stats
    dom.statWords.textContent = (batchData.stats.total_words || 0).toLocaleString();
    dom.statTables.textContent = (batchData.stats.total_tables || 0).toLocaleString();
    dom.statLinks.textContent = (batchData.stats.total_links || 0).toLocaleString();
    dom.statImages.textContent = (batchData.stats.total_images || 0).toLocaleString();
    dom.batchTabBadge.textContent = batchData.total_urls;

    // Render Batch Results Table
    const results = batchData.results || [];
    let html = `
        <div class="batch-summary-banner">
            <div class="batch-summary-stat"><span>Total Sites:</span> <strong>${batchData.total_urls}</strong></div>
            <div class="batch-summary-stat"><span>Success:</span> <strong class="text-green">${batchData.success_count}</strong></div>
            <div class="batch-summary-stat"><span>Failed:</span> <strong class="text-red">${batchData.fail_count}</strong></div>
        </div>
        <div class="table-responsive">
            <table class="styled-data-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Target Website URL</th>
                        <th>Status</th>
                        <th>Proxy Used</th>
                        <th>Words</th>
                        <th>Tables</th>
                        <th>Time</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
    `;

    results.forEach((it, idx) => {
        const isSuccess = it.status === 'success';
        const data = it.data || {};
        const stats = data.stats || {};
        const title = data.metadata?.title || it.url;
        const proxyLabel = it.proxy || 'Direct';

        html += `
            <tr>
                <td>${idx + 1}</td>
                <td>
                    <div class="table-url-title">
                        <strong>${escapeHtml(title)}</strong>
                        <a href="${escapeHtml(it.url)}" target="_blank" class="table-link">${escapeHtml(it.url)} <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                    </div>
                </td>
                <td>
                    <span class="status-chip ${isSuccess ? 'chip-success' : 'chip-fail'}">
                        ${isSuccess ? '<i class="fa-solid fa-check"></i> Scraped' : '<i class="fa-solid fa-xmark"></i> Failed'}
                    </span>
                </td>
                <td><span class="proxy-tag"><i class="fa-solid fa-shield-halved"></i> ${escapeHtml(proxyLabel)}</span></td>
                <td>${(stats.word_count || 0).toLocaleString()}</td>
                <td>${stats.table_count || 0}</td>
                <td>${it.duration}s</td>
                <td>
                    ${isSuccess ? `<button class="view-item-btn" onclick="viewSingleFromBatch(${idx})"><i class="fa-solid fa-eye"></i> View</button>` : `<span class="err-hint" title="${escapeHtml(it.error || '')}">Error</span>`}
                </td>
            </tr>
        `;
    });

    html += `</tbody></table></div>`;
    dom.batchContainer.innerHTML = html;

    // Set JSON code
    dom.jsonCode.textContent = JSON.stringify(batchData, null, 2);

    // Switch to batch tab
    switchViewerTab('tab-batch');
}

// Global helper to view single item from batch
window.viewSingleFromBatch = function(idx) {
    if (state.currentBatchData && state.currentBatchData.results[idx]) {
        const item = state.currentBatchData.results[idx];
        if (item.data) {
            state.currentData = item.data;
            renderScrapedData(item.data);
            switchViewerTab('tab-article');
        }
    }
};

// --- RENDER SINGLE SCRAPED DATA ---
function renderScrapedData(data) {
    dom.emptyState.style.display = 'none';

    // Update Stats
    dom.statWords.textContent = (data.stats.word_count || 0).toLocaleString();
    dom.statTables.textContent = data.stats.table_count || 0;
    dom.statLinks.textContent = data.stats.link_count || 0;
    dom.statImages.textContent = data.stats.image_count || 0;
    
    dom.tableTabBadge.textContent = data.stats.table_count || 0;
    dom.linkTabBadge.textContent = data.stats.link_count || 0;
    dom.imgTabBadge.textContent = data.stats.image_count || 0;

    // 1. Article View
    dom.articleMetaHeader.style.display = 'block';
    dom.articleTitle.textContent = data.article.title || data.metadata.title || "Scraped Content";
    dom.articleAuthor.innerHTML = `<i class="fa-solid fa-user"></i> ${escapeHtml(data.article.author || data.metadata.author || "Unknown")}`;
    dom.articleSource.innerHTML = `<i class="fa-solid fa-globe"></i> ${escapeHtml(data.metadata.site_name || new URL(data.url).hostname)}`;
    dom.articleDate.innerHTML = `<i class="fa-solid fa-calendar"></i> ${escapeHtml(data.article.date || new Date().toLocaleDateString())}`;
    
    if (data.proxy) {
        dom.articleProxy.style.display = 'inline-flex';
        dom.articleProxyText.textContent = `Proxy: ${data.proxy}`;
    } else {
        dom.articleProxy.style.display = 'none';
    }

    dom.articleBody.innerHTML = formatArticleText(data.article.text);

    // 2. Tables View
    renderTables(data.tables);

    // 3. Links View
    renderLinks(data.links);

    // 4. Media View
    renderImages(data.images);

    // 5. JSON Code
    dom.jsonCode.textContent = JSON.stringify(data, null, 2);

    // Switch to Reader View
    switchViewerTab('tab-article');
}

function renderTables(tables) {
    if (!tables || tables.length === 0) {
        dom.tablesContainer.innerHTML = '<p class="tab-empty-msg">No HTML tables found on this webpage.</p>';
        return;
    }

    let html = '';
    tables.forEach(t => {
        html += `
            <div class="extracted-table-card">
                <div class="table-card-header">
                    <h4><i class="fa-solid fa-table-cells"></i> Table #${t.table_index} (${t.row_count} rows, ${t.col_count} cols)</h4>
                </div>
                <div class="table-responsive">
                    <table class="styled-data-table">
                        <thead>
                            <tr>
                                ${t.headers.map(h => `<th>${escapeHtml(h)}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${t.rows.map(row => `
                                <tr>
                                    ${row.map(cell => `<td>${escapeHtml(cell)}</td>`).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    });
    dom.tablesContainer.innerHTML = html;
}

function renderLinks(links) {
    if (!links || links.length === 0) {
        dom.linksList.innerHTML = '<p class="tab-empty-msg">No hyperlinks found.</p>';
        return;
    }

    let html = '';
    links.forEach(l => {
        html += `
            <div class="link-item-row">
                <span class="link-type-pill ${l.type === 'Internal' ? 'pill-internal' : 'pill-external'}">${l.type}</span>
                <span class="link-text-anchor">${escapeHtml(l.text)}</span>
                <a href="${escapeHtml(l.url)}" target="_blank" class="link-url-target" title="${escapeHtml(l.url)}">
                    ${escapeHtml(l.url)} <i class="fa-solid fa-arrow-up-right-from-square"></i>
                </a>
            </div>
        `;
    });
    dom.linksList.innerHTML = html;
}

function renderImages(images) {
    if (!images || images.length === 0) {
        dom.imagesGrid.innerHTML = '<p class="tab-empty-msg">No images detected on this page.</p>';
        return;
    }

    let html = '';
    images.forEach(img => {
        html += `
            <div class="media-card">
                <div class="media-thumb-wrap">
                    <img src="${escapeHtml(img.src)}" alt="${escapeHtml(img.alt)}" loading="lazy" onerror="this.src='https://via.placeholder.com/300x200?text=Image+Unavailable'">
                </div>
                <div class="media-caption">
                    <span class="media-alt-label">${escapeHtml(img.alt || "Image")}</span>
                    <a href="${escapeHtml(img.src)}" target="_blank" class="media-src-link"><i class="fa-solid fa-external-link"></i> Full Image</a>
                </div>
            </div>
        `;
    });
    dom.imagesGrid.innerHTML = html;
}

// --- CHATBOT LOGIC ---
async function handleChatSubmit(e) {
    e.preventDefault();
    const q = dom.chatInput.value.trim();
    if (!q || state.isChatting) return;

    addUserMessage(q);
    dom.chatInput.value = '';
    state.isChatting = true;
    dom.sendBtn.disabled = true;

    const loaderId = addBotLoader();

    try {
        const res = await fetch(getApiUrl('/api/chat'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: q,
                hf_token: state.hfToken || null,
                model_name: state.modelName,
                system_prompt: state.systemPrompt || null
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Chat query failed');
        }

        const data = await res.json();
        removeLoader(loaderId);
        addBotAnswer(data);
    } catch (err) {
        removeLoader(loaderId);
        addBotMessage(`⚠️ Error: ${err.message}`);
    } finally {
        state.isChatting = false;
        dom.sendBtn.disabled = false;
    }
}

function addUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'chat-row user-row';
    row.innerHTML = `
        <div class="chat-speech-bubble user-bubble">
            <p>${escapeHtml(text)}</p>
        </div>
        <div class="chat-avatar user-avatar"><i class="fa-solid fa-user"></i></div>
    `;
    dom.chatMessages.appendChild(row);
    scrollChat();
}

function addBotMessage(text) {
    const row = document.createElement('div');
    row.className = 'chat-row bot-row';
    row.innerHTML = `
        <div class="chat-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="chat-speech-bubble bot-bubble">
            <p>${formatMarkdown(text)}</p>
        </div>
    `;
    dom.chatMessages.appendChild(row);
    scrollChat();
}

function addBotAnswer(data) {
    const row = document.createElement('div');
    row.className = 'chat-row bot-row';
    
    let citationsHtml = '';
    if (data.citations && data.citations.length > 0) {
        citationsHtml = `
            <div class="chat-citations-wrap">
                <span class="citations-header"><i class="fa-solid fa-quote-left"></i> Evidence Chunks (${data.citations.length}):</span>
                <div class="citations-list">
                    ${data.citations.map(c => `
                        <div class="citation-chip" title="${escapeHtml(c.snippet)}">
                            <span class="citation-tag">Chunk #${c.chunk_id}</span>
                            <span class="citation-score">${(c.score * 100).toFixed(0)}% match</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    row.innerHTML = `
        <div class="chat-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="chat-speech-bubble bot-bubble">
            <div class="bot-answer-body">${formatMarkdown(data.answer)}</div>
            ${citationsHtml}
        </div>
    `;
    dom.chatMessages.appendChild(row);
    scrollChat();
}

function addBotLoader() {
    const id = 'loader_' + Date.now();
    const row = document.createElement('div');
    row.className = 'chat-row bot-row';
    row.id = id;
    row.innerHTML = `
        <div class="chat-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="chat-speech-bubble bot-bubble typing-bubble">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
        </div>
    `;
    dom.chatMessages.appendChild(row);
    scrollChat();
    return id;
}

function removeLoader(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function clearChatFeed() {
    dom.chatMessages.innerHTML = `
        <div class="chat-row bot-row">
            <div class="chat-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="chat-speech-bubble">
                <p>👋 Chat reset! Ask any question regarding the active scraped content.</p>
            </div>
        </div>
    `;
}

function scrollChat() {
    dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

// --- EXPORT HANDLER ---
async function handleExport(format) {
    const isBatch = state.mode === 'batch' && state.currentBatchData !== null;
    if (!state.currentData && !state.currentBatchData) {
        alert('Please scrape a URL or run a batch scrape first before exporting.');
        return;
    }

    try {
        const res = await fetch(getApiUrl('/api/export'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ format: format, is_batch: isBatch })
        });

        if (!res.ok) throw new Error('Export generation failed');

        const blob = await res.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `scraped_${isBatch ? 'batch_' : ''}data.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
    } catch (err) {
        alert(`Export Error: ${err.message}`);
    }
}

// --- SETTINGS SAVE ---
function handleSaveSettings() {
    const apiUrl = dom.apiUrlInput ? dom.apiUrlInput.value.trim() : '';
    const token = dom.hfTokenInput.value.trim();
    const model = dom.modelSelect.value;
    const proxy = dom.defaultProxyInput.value.trim();
    const prompt = dom.systemPromptInput.value.trim();

    state.apiUrl = apiUrl;
    state.hfToken = token;
    state.modelName = model;
    state.defaultProxy = proxy;
    state.systemPrompt = prompt;

    localStorage.setItem('scraper_api_url', apiUrl);
    localStorage.setItem('hf_token', token);
    localStorage.setItem('hf_model', model);
    localStorage.setItem('default_proxy', proxy);
    localStorage.setItem('hf_system_prompt', prompt);

    updateActiveModelBadge();
    updateProxyBadge(proxy);
    if (dom.proxyInput) dom.proxyInput.value = proxy;

    closeModal(dom.settingsModal);
    checkHealth();
    alert('Settings saved successfully!');
}

// --- HISTORY LOGIC ---
async function loadHistory() {
    try {
        const res = await fetch(getApiUrl('/api/history'));
        const data = await res.json();
        const list = data.history || [];

        if (list.length === 0) {
            dom.historyList.innerHTML = '<p class="tab-empty-msg">No scrape sessions recorded yet.</p>';
            return;
        }

        let html = '';
        list.forEach(item => {
            html += `
                <div class="history-item-card">
                    <div class="hist-info">
                        <h4>${escapeHtml(item.title || "Untitled")}</h4>
                        <span class="hist-url"><i class="fa-solid fa-link"></i> ${escapeHtml(item.url)}</span>
                        <span class="hist-meta">${new Date(item.timestamp).toLocaleString()} • ${item.word_count} words • ${item.tables_count} tables</span>
                    </div>
                </div>
            `;
        });
        dom.historyList.innerHTML = html;
    } catch (err) {
        dom.historyList.innerHTML = `<p class="tab-empty-msg">Failed to load history: ${err.message}</p>`;
    }
}

// --- UTILITIES ---
function switchViewerTab(tabId) {
    state.activeTab = tabId;
    dom.vTabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tabId));
    dom.tabPanels.forEach(p => p.classList.toggle('active', p.id === tabId));
}

function setLoadingState(loading, text = '') {
    if (loading) {
        dom.scrapeBtn.disabled = true;
        dom.batchScrapeBtn.disabled = true;
        dom.scrapeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scraping...';
        dom.batchScrapeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Batch Scraping...';
        dom.progressContainer.classList.add('active');
        dom.progressText.textContent = text;
        dom.progressBar.style.width = '20%';
    } else {
        dom.scrapeBtn.disabled = false;
        dom.batchScrapeBtn.disabled = false;
        dom.scrapeBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> <span>Scrape Page</span>';
        dom.batchScrapeBtn.innerHTML = '<i class="fa-solid fa-play"></i> <span>Start Continuous Batch Scrape</span>';
        dom.progressContainer.classList.remove('active');
        dom.progressBar.style.width = '0%';
    }
}

function updateProgress(percent, label) {
    dom.progressBar.style.width = `${percent}%`;
    if (label) dom.progressText.textContent = label;
}

function openModal(m) { m.classList.add('open'); }
function closeModal(m) { m.classList.remove('open'); }

async function checkHealth() {
    try {
        const res = await fetch(getApiUrl('/api/health'));
        if (res.ok) {
            dom.serverStatus.classList.add('online');
            dom.serverStatus.querySelector('.status-text').textContent = 'Backend Online';
        }
    } catch {
        dom.serverStatus.classList.remove('online');
        dom.serverStatus.querySelector('.status-text').textContent = 'Backend Offline';
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function formatArticleText(text) {
    if (!text) return '<p class="tab-empty-msg">No article text extracted.</p>';
    const paragraphs = text.split(/\n\s*\n/);
    return paragraphs.map(p => `<p>${escapeHtml(p.trim())}</p>`).join('');
}

function formatMarkdown(text) {
    if (!text) return '';
    let parsed = escapeHtml(text);
    parsed = parsed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    parsed = parsed.replace(/\*(.*?)\*/g, '<em>$1</em>');
    parsed = parsed.replace(/`([^`]+)`/g, '<code>$1</code>');
    parsed = parsed.replace(/\n/g, '<br>');
    return parsed;
}
