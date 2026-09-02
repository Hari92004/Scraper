/**
 * ScrapeAI - Frontend Controller Logic
 * Universal Web Scraper + Hugging Face RAG AI
 */

// Global State
const state = {
    currentData: null,
    activeTab: 'tab-article',
    hfToken: localStorage.getItem('hf_token') || '',
    modelName: localStorage.getItem('hf_model') || 'Qwen/Qwen2.5-7B-Instruct',
    systemPrompt: localStorage.getItem('hf_system_prompt') || '',
    isScraping: false,
    isChatting: false
};

// DOM References
const dom = {
    // Scraper Form
    scrapeForm: document.getElementById('scrapeForm'),
    urlInput: document.getElementById('urlInput'),
    scrapeBtn: document.getElementById('scrapeBtn'),
    presetPills: document.querySelectorAll('.preset-pill'),
    toggleAdvOptions: document.getElementById('toggleAdvOptions'),
    advancedDrawer: document.getElementById('advancedDrawer'),
    customSelector: document.getElementById('customSelector'),
    progressContainer: document.getElementById('progressContainer'),
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    
    // Stats
    statWords: document.getElementById('statWords'),
    statTables: document.getElementById('statTables'),
    statLinks: document.getElementById('statLinks'),
    statImages: document.getElementById('statImages'),
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
    articleBody: document.getElementById('articleBody'),
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
    hfTokenInput: document.getElementById('hfTokenInput'),
    modelSelect: document.getElementById('modelSelect'),
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
    if (state.hfToken) dom.hfTokenInput.value = state.hfToken;
    if (state.modelName) dom.modelSelect.value = state.modelName;
    if (state.systemPrompt) dom.systemPromptInput.value = state.systemPrompt;
    updateActiveModelBadge();
}

function updateActiveModelBadge() {
    const isTokenSet = Boolean(state.hfToken);
    const shortName = state.modelName.split('/').pop();
    dom.chatActiveModel.textContent = isTokenSet ? `HF: ${shortName}` : 'Offline Mode (Local QA)';
}

// --- EVENT LISTENERS ---
function initEventListeners() {
    // Scraper Form
    dom.scrapeForm.addEventListener('submit', handleScrapeSubmit);

    // Preset Pills
    dom.presetPills.forEach(pill => {
        pill.addEventListener('click', () => {
            dom.urlInput.value = pill.dataset.url;
            dom.scrapeForm.dispatchEvent(new Event('submit'));
        });
    });

    // Toggle Advanced Selector Drawer
    dom.toggleAdvOptions.addEventListener('click', () => {
        dom.advancedDrawer.classList.toggle('open');
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
                document.querySelector('.viewer-card').scrollIntoView({ behavior: 'smooth' });
            } else if (view === 'rag-chat') {
                document.querySelector('.rag-chat-card').scrollIntoView({ behavior: 'smooth' });
            } else if (view === 'dashboard') {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    });

    // Search filter in links
    dom.linkSearch.addEventListener('input', (e) => {
        filterLinks(e.target.value);
    });

    // Copy JSON
    dom.copyJsonBtn.addEventListener('click', () => {
        if (!state.currentData) return;
        navigator.clipboard.writeText(JSON.stringify(state.currentData, null, 2));
        dom.copyJsonBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
        setTimeout(() => {
            dom.copyJsonBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy JSON';
        }, 2000);
    });

    // Export Dropdown
    dom.exportBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dom.exportMenu.classList.toggle('show');
    });

    document.addEventListener('click', () => {
        dom.exportMenu.classList.remove('show');
    });

    dom.exportOpts.forEach(opt => {
        opt.addEventListener('click', () => {
            handleExport(opt.dataset.fmt);
        });
    });

    // Chatbot Form
    dom.chatForm.addEventListener('submit', handleChatSubmit);

    // Suggestion Chips
    dom.suggestionChips.addEventListener('click', (e) => {
        const chip = e.target.closest('.quick-chip');
        if (chip) {
            dom.chatInput.value = chip.dataset.prompt;
            dom.chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // Clear Chat
    dom.clearChatBtn.addEventListener('click', () => {
        dom.chatMessages.innerHTML = `
            <div class="chat-row bot-row">
                <div class="chat-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="chat-speech-bubble">
                    <p>Chat cleared. Ask anything about the active scraped webpage.</p>
                </div>
            </div>
        `;
    });

    // Modal Triggers
    const openSettings = () => openModal(dom.settingsModal);
    const openHistory = () => openHistoryModal();

    if (dom.sidebarSettingsBtn) dom.sidebarSettingsBtn.addEventListener('click', openSettings);
    if (dom.topSettingsTab) dom.topSettingsTab.addEventListener('click', openSettings);
    if (dom.topAiModelsTab) dom.topAiModelsTab.addEventListener('click', openSettings);
    if (dom.chatActiveModel) {
        dom.chatActiveModel.style.cursor = 'pointer';
        dom.chatActiveModel.title = 'Click to configure AI Model & Token';
        dom.chatActiveModel.addEventListener('click', openSettings);
    }
    
    if (dom.sidebarHistoryBtn) dom.sidebarHistoryBtn.addEventListener('click', openHistory);
    if (dom.topHistoryTab) dom.topHistoryTab.addEventListener('click', openHistory);

    if (dom.topDocsTab) {
        dom.topDocsTab.addEventListener('click', () => {
            window.open('https://github.com', '_blank');
        });
    }

    dom.closeSettingsModal.addEventListener('click', () => closeModal(dom.settingsModal));
    dom.cancelSettingsBtn.addEventListener('click', () => closeModal(dom.settingsModal));
    dom.saveSettingsBtn.addEventListener('click', handleSaveSettings);

    dom.closeHistoryModal.addEventListener('click', () => closeModal(dom.historyModal));
}

// --- SCRAPE ACTION ---
async function handleScrapeSubmit(e) {
    e.preventDefault();
    const url = dom.urlInput.value.trim();
    if (!url) return;

    state.isScraping = true;
    setLoadingState(true, "Connecting to target site...");

    try {
        updateProgress(35, "Parsing HTML, metadata, tables, links & images...");
        
        const res = await fetch('/api/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                custom_selector: dom.customSelector.value.trim() || null,
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
        renderScrapedData(data);
        updateProgress(100, "Scraping & Indexing Completed!");

        addBotMessage(`✅ Successfully extracted **${data.metadata.title || data.url}** (${data.stats.word_count} words, ${data.stats.table_count} tables, ${data.stats.link_count} links). Indexed **${data.indexed_chunks || 0} chunks** for RAG search. Ask me anything!`);
    } catch (err) {
        alert(`Scraping Error: ${err.message}`);
        console.error(err);
    } finally {
        setTimeout(() => setLoadingState(false), 500);
    }
}

function setLoadingState(loading, text = '') {
    if (loading) {
        dom.scrapeBtn.disabled = true;
        dom.scrapeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scraping...';
        dom.progressContainer.classList.add('active');
        dom.progressText.textContent = text;
        dom.progressBar.style.width = '20%';
    } else {
        dom.scrapeBtn.disabled = false;
        dom.scrapeBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> <span>Scrape Page</span>';
        dom.progressContainer.classList.remove('active');
        dom.progressBar.style.width = '0%';
    }
}

function updateProgress(percent, text) {
    dom.progressBar.style.width = `${percent}%`;
    dom.progressText.textContent = text;
}

// --- RENDER DATA ---
function renderScrapedData(data) {
    dom.emptyState.style.display = 'none';

    // 4 Stat Cards
    dom.statWords.textContent = (data.stats.word_count || 0).toLocaleString();
    dom.statTables.textContent = data.stats.table_count || 0;
    dom.statLinks.textContent = (data.stats.link_count || 0).toLocaleString();
    dom.statImages.textContent = data.stats.image_count || 0;

    // Badges on tabs
    dom.tableTabBadge.textContent = data.stats.table_count || 0;
    dom.linkTabBadge.textContent = data.stats.link_count || 0;
    dom.imgTabBadge.textContent = data.stats.image_count || 0;

    // Tab 1: Reader View
    dom.articleMetaHeader.style.display = 'block';
    dom.articleTitle.textContent = data.metadata.title || 'Extracted Document';
    dom.articleAuthor.innerHTML = `<i class="fa-solid fa-user"></i> ${data.metadata.author || 'Unknown Author'}`;
    dom.articleSource.innerHTML = `<i class="fa-solid fa-globe"></i> ${new URL(data.url).hostname}`;
    dom.articleDate.innerHTML = `<i class="fa-solid fa-calendar"></i> ${data.article.date || new Date().toLocaleDateString()}`;
    dom.articleBody.textContent = data.article.text || 'No text extracted.';

    // Tab 2: Tables
    renderTables(data.tables);

    // Tab 3: Links
    renderLinks(data.links);

    // Tab 4: Images
    renderImages(data.images);

    // Tab 5: Raw JSON
    dom.jsonCode.textContent = JSON.stringify(data, null, 2);

    switchViewerTab('tab-article');
}

function renderTables(tables) {
    if (!tables || tables.length === 0) {
        dom.tablesContainer.innerHTML = '<p class="tab-empty-msg">No HTML tables found on this webpage.</p>';
        return;
    }

    dom.tablesContainer.innerHTML = tables.map((t, idx) => `
        <div class="custom-table-wrapper">
            <h4 style="padding: 0.65rem 0.9rem; color: var(--accent-cyan); font-size: 0.85rem;">Table #${idx + 1} (${t.row_count} rows, ${t.col_count} columns)</h4>
            <table class="styled-table">
                <thead>
                    <tr>${t.headers.map(h => `<th>${escapeHtml(h)}</th>`).join('')}</tr>
                </thead>
                <tbody>
                    ${t.rows.map(row => `
                        <tr>${row.map(cell => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `).join('');
}

function renderLinks(links) {
    if (!links || links.length === 0) {
        dom.linksList.innerHTML = '<p class="tab-empty-msg">No links extracted.</p>';
        return;
    }

    dom.linksList.innerHTML = links.map(l => `
        <a href="${escapeHtml(l.url)}" target="_blank" rel="noopener noreferrer" class="link-item">
            <span class="link-anchor">${escapeHtml(l.text || l.url)}</span>
            <span class="link-dest">${escapeHtml(l.type)} • ${new URL(l.url).hostname}</span>
        </a>
    `).join('');
}

function filterLinks(query) {
    const q = query.toLowerCase();
    const items = dom.linksList.querySelectorAll('.link-item');
    items.forEach(el => {
        const text = el.textContent.toLowerCase();
        el.style.display = text.includes(q) ? 'flex' : 'none';
    });
}

function renderImages(images) {
    if (!images || images.length === 0) {
        dom.imagesGrid.innerHTML = '<p class="tab-empty-msg">No images found on this page.</p>';
        return;
    }

    dom.imagesGrid.innerHTML = images.map(img => `
        <div class="image-card">
            <img src="${escapeHtml(img.src)}" alt="${escapeHtml(img.alt)}" loading="lazy" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'100\' height=\'100\'><rect width=\'100\' height=\'100\' fill=\'%23111827\'/></svg>'">
            <span class="image-alt" title="${escapeHtml(img.alt)}">${escapeHtml(img.alt || 'Image')}</span>
        </div>
    `).join('');
}

function switchViewerTab(tabId) {
    state.activeTab = tabId;
    dom.vTabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
    });
    dom.tabPanels.forEach(panel => {
        panel.classList.toggle('active', panel.id === tabId);
    });
}

// --- CHAT & RAG ENGINE ---
async function handleChatSubmit(e) {
    e.preventDefault();
    const question = dom.chatInput.value.trim();
    if (!question || state.isChatting) return;

    if (!state.currentData) {
        alert("Please scrape a website URL first before asking questions!");
        return;
    }

    addUserMessage(question);
    dom.chatInput.value = '';
    state.isChatting = true;

    const typingId = addTypingIndicator();

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: question,
                hf_token: state.hfToken || null,
                model_name: state.modelName,
                system_prompt: state.systemPrompt || null
            })
        });

        const data = await res.json();
        removeTypingIndicator(typingId);

        if (data.success) {
            addBotMessage(data.answer, data.citations, data.model_used);
        } else {
            addBotMessage(data.answer || "Unable to get an answer.", []);
        }
    } catch (err) {
        removeTypingIndicator(typingId);
        addBotMessage(`⚠️ Error communicating with AI: ${err.message}`);
    } finally {
        state.isChatting = false;
    }
}

function addUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'chat-row user-row';
    row.innerHTML = `
        <div class="chat-avatar user-avatar-icon"><i class="fa-solid fa-user"></i></div>
        <div class="chat-speech-bubble">${escapeHtml(text)}</div>
    `;
    dom.chatMessages.appendChild(row);
    scrollToBottom();
}

function addBotMessage(text, citations = [], model = null) {
    const row = document.createElement('div');
    row.className = 'chat-row bot-row';

    let citationsHtml = '';
    if (citations && citations.length > 0) {
        citationsHtml = `
            <div class="citations-box">
                <span style="font-size: 0.68rem; color: var(--text-muted);"><i class="fa-solid fa-book-bookmark"></i> Grounded in ${citations.length} chunk(s):</span>
                ${citations.map(c => `
                    <div class="citation-chip">
                        [Chunk #${c.chunk_id} • Score: ${c.score}]
                        <div class="citation-snippet">${escapeHtml(c.snippet)}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    let modelTag = model ? `<div style="font-size:0.65rem; color:var(--accent-cyan); margin-top:0.35rem;"><i class="fa-solid fa-microchip"></i> ${model}</div>` : '';
    const formatted = formatMarkdown(text);

    row.innerHTML = `
        <div class="chat-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="chat-speech-bubble">
            ${formatted}
            ${citationsHtml}
            ${modelTag}
        </div>
    `;
    dom.chatMessages.appendChild(row);
    scrollToBottom();
}

function addTypingIndicator() {
    const id = 'typing_' + Date.now();
    const row = document.createElement('div');
    row.id = id;
    row.className = 'chat-row bot-row';
    row.innerHTML = `
        <div class="chat-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="chat-speech-bubble"><i class="fa-solid fa-circle-notch fa-spin"></i> Retrieving context & generating answer...</div>
    `;
    dom.chatMessages.appendChild(row);
    scrollToBottom();
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

// --- EXPORT HANDLER ---
async function handleExport(format) {
    if (!state.currentData) {
        alert("Please scrape a website URL first before exporting.");
        return;
    }

    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ format: format })
        });

        if (!response.ok) throw new Error("Export failed");

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        
        const ext = format === 'markdown' ? 'md' : format;
        a.download = `scrape_export_${Date.now()}.${ext}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
    } catch (err) {
        alert(`Export failed: ${err.message}`);
    }
}

// --- HISTORY MODAL ---
async function openHistoryModal() {
    openModal(dom.historyModal);
    dom.historyList.innerHTML = '<p class="tab-empty-msg"><i class="fa-solid fa-spinner fa-spin"></i> Loading history...</p>';

    try {
        const res = await fetch('/api/history');
        const data = await res.json();
        const history = data.history || [];

        if (history.length === 0) {
            dom.historyList.innerHTML = '<p class="tab-empty-msg">No previous scrapes saved yet.</p>';
            return;
        }

        dom.historyList.innerHTML = history.map(item => `
            <div class="history-item-row" onclick="loadHistoryItem('${item.url}')">
                <div>
                    <div class="history-item-title">${escapeHtml(item.title || 'Untitled Page')}</div>
                    <div class="history-item-url">${escapeHtml(item.url)}</div>
                </div>
                <div style="font-size:0.75rem; color:var(--accent-cyan); text-align:right;">
                    ${item.word_count || 0} words<br>
                    <span style="color:var(--text-muted); font-size:0.7rem;">${new Date(item.timestamp).toLocaleDateString()}</span>
                </div>
            </div>
        `).join('');
    } catch (err) {
        dom.historyList.innerHTML = '<p class="tab-empty-msg">Failed to load history.</p>';
    }
}

window.loadHistoryItem = function(url) {
    closeModal(dom.historyModal);
    dom.urlInput.value = url;
    dom.scrapeForm.dispatchEvent(new Event('submit'));
};

// --- SETTINGS MODAL ---
function handleSaveSettings() {
    state.hfToken = dom.hfTokenInput.value.trim();
    state.modelName = dom.modelSelect.value;
    state.systemPrompt = dom.systemPromptInput.value.trim();

    localStorage.setItem('hf_token', state.hfToken);
    localStorage.setItem('hf_model', state.modelName);
    localStorage.setItem('hf_system_prompt', state.systemPrompt);

    updateActiveModelBadge();
    closeModal(dom.settingsModal);

    addBotMessage(`⚙️ Settings updated! Model: **${state.modelName}**. Token: **${state.hfToken ? 'Active' : 'Unset (Offline Mode)'}**.`);
}

function openModal(modalEl) {
    modalEl.classList.add('open');
}

function closeModal(modalEl) {
    modalEl.classList.remove('open');
}

// --- HEALTH CHECK ---
async function checkHealth() {
    try {
        const res = await fetch('/api/health');
        if (res.ok) {
            dom.serverStatus.innerHTML = '<span class="status-dot"></span><span class="status-text">Backend Ready</span>';
        }
    } catch (e) {
        dom.serverStatus.innerHTML = '<span class="status-dot" style="background:#f43f5e; box-shadow:0 0 8px #f43f5e;"></span><span class="status-text" style="color:#f43f5e;">Offline</span>';
    }
}

// --- UTILS ---
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function formatMarkdown(text) {
    if (!text) return '';
    let formatted = escapeHtml(text);
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/^\* (.*?)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/(<li>.*?<\/li>)+/g, '<ul style="margin: 0.4rem 0; padding-left: 1.1rem;">$&</ul>');
    formatted = formatted.replace(/\n/g, '<br>');
    return formatted;
}
