/**
 * Yukti Research AI - Frontend Logic
 * Handles WebSocket communication, research progress rendering,
 * and chat interactions.
 */

class YuktiApp {
    constructor() {
        this.socket = null;
        this.sessionId = null;
        this.currentQuery = null;
        this.history = [];
        this.agents = [
            { id: 'orchestrator', name: 'Orchestrator', icon: '🎯' },
            { id: 'planner', name: 'Planer Agent', icon: '📝' },
            { id: 'web_agent', name: 'Web Context Agent', icon: '🌐' },
            { id: 'academic_agent', name: 'Academic Research Agent', icon: '📚' },
            { id: 'doc_agent', name: 'Document Processing Agent', icon: '⚙️' },
            { id: 'citation_agent', name: 'Metadata & Citation Agent', icon: '📍' },
            { id: 'aggregator', name: 'Content Aggregator', icon: '📥' },
            { id: 'synthesizer', name: 'Synthesizer Agent', icon: '🧠' },
            { id: 'publisher', name: 'Publisher Agent', icon: '📊' }
        ];

        // UI Elements
        this.elements = {
            searchForm: document.getElementById('search-form'),
            searchInput: document.getElementById('search-input'),
            heroSection: document.getElementById('hero-section'),
            appInterface: document.getElementById('app-interface'),
            agentList: document.getElementById('agent-list'),
            reportContent: document.getElementById('report-content'),
            chatDrawer: document.getElementById('chat-drawer'),
            chatMessages: document.getElementById('chat-messages'),
            chatForm: document.getElementById('chat-form'),
            chatInput: document.getElementById('chat-input'),
            chatToggle: document.getElementById('chat-toggle'),
            headerQuery: document.getElementById('header-query'),
            progressBar: document.querySelector('.progress-fill'),
            exportMd: document.getElementById('export-md'),
            exportHtml: document.getElementById('export-html'),
            exportPdf: document.getElementById('export-pdf'),
            exportLatex: document.getElementById('export-latex'),
            researchMap: document.getElementById('research-map')
        };

        this.init();
    }

    init() {
        this.elements.searchForm.addEventListener('submit', (e) => this.handleSearch(e));
        this.elements.chatForm.addEventListener('submit', (e) => this.handleChat(e));
        this.elements.chatToggle.addEventListener('click', () => this.toggleChat());

        // Handle export buttons
        this.elements.exportMd.addEventListener('click', () => this.handleExport('markdown'));
        this.elements.exportHtml.addEventListener('click', () => this.handleExport('html'));
        this.elements.exportPdf.addEventListener('click', () => this.handleExport('pdf'));
        this.elements.exportLatex.addEventListener('click', () => this.handleExport('latex'));

        // Load examples
        document.querySelectorAll('.tag').forEach(tag => {
            tag.addEventListener('click', () => {
                this.elements.searchInput.value = tag.textContent;
                this.elements.searchForm.dispatchEvent(new Event('submit'));
            });
        });
    }

    async handleSearch(e) {
        e.preventDefault();
        const query = this.elements.searchInput.value.trim();
        if (!query) return;

        this.currentQuery = query;
        this.elements.headerQuery.textContent = query;

        // Show interface, hide hero
        this.elements.heroSection.classList.add('hidden');
        this.elements.appInterface.style.display = 'grid';
        this.elements.progressBar.style.width = '5%';
        this.elements.researchMap.classList.remove('hidden');

        this.resetAgentList();
        this.connectWebSocket(query);
    }

    connectWebSocket(query) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/research`;

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('WebSocket Connected');
            this.socket.send(JSON.stringify({
                action: 'research',
                query: query,
                citation_style: 'APA'
            }));
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.socket.onclose = () => {
            console.log('WebSocket Closed');
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket Error:', error);
            this.showError('Connection error. Please try again.');
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'session':
                this.sessionId = data.session_id;
                this.updateAgentStatus('orchestrator', 'active', 'Initializing research pipeline...');
                break;

            case 'progress':
                this.updateAgentStatus(data.agent, data.status, data.message);
                this.updateOverallProgress();
                break;

            case 'result':
                this.renderReport(data.data);
                this.elements.progressBar.style.width = '100%';
                this.elements.chatToggle.classList.remove('hidden');
                this.updateAgentStatus('orchestrator', 'completed', 'Research complete! 🎉');
                break;

            case 'chat_response':
                this.appendMessage('assistant', data.message);
                break;

            case 'error':
                this.showError(data.message);
                break;
        }
    }

    updateAgentStatus(agentId, status, message) {
        const item = document.getElementById(`agent-${agentId}`);
        if (!item) return;

        item.className = `agent-item ${status}`;
        const msgEl = item.querySelector('.agent-msg');
        if (msgEl) msgEl.textContent = message;

        const badge = item.querySelector('.agent-badge');
        if (badge) {
            badge.textContent = status;
            badge.className = `agent-badge ${status}`;
        }

        // Update Research Map Node
        const mapNode = document.querySelector(`.map-node[data-agent="${agentId}"]`);
        if (mapNode) {
            mapNode.classList.remove('active', 'completed');
            if (status === 'active') mapNode.classList.add('active');
            if (status === 'completed') mapNode.classList.add('completed');
        }

        // Special case: If planner completed, render the plan immediately
        if (agentId === 'planner' && status === 'completed' && message.includes('{')) {
            try {
                // Extract JSON if embedded in message
                const jsonStr = message.match(/\{.*\}/s)[0];
                const plan = JSON.parse(jsonStr);
                this.renderPlan(plan);
            } catch (e) { }
        }

        // Auto-scroll sidebar
        item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    renderPlan(plan) {
        this.elements.reportContent.innerHTML = `
            <div class="plan-viewer animated fadeIn">
                <h3>📝 Research Roadmap: ${plan.title}</h3>
                <p><strong>Scope:</strong> ${plan.abstract_scope}</p>
                <div style="margin-top:1rem">
                    <strong>Key Sub-questions:</strong>
                    <ul class="plan-list">
                        ${plan.sub_questions.map(q => `<li class="plan-item">${q}</li>`).join('')}
                    </ul>
                </div>
                <div style="margin-top:1rem; color: var(--accent); font-size: 0.8rem;">
                    <span class="pulse-msg">Agents are now gathering academic sources for these sections...</span>
                </div>
            </div>
        `;
    }

    resetAgentList() {
        this.elements.agentList.innerHTML = '';
        this.agents.forEach(agent => {
            const div = document.createElement('div');
            div.id = `agent-${agent.id}`;
            div.className = 'agent-item pending';
            div.innerHTML = `
                <div class="agent-header">
                    <span class="agent-name">${agent.icon} ${agent.name}</span>
                    <span class="agent-badge pending">Pending</span>
                </div>
                <div class="agent-msg">Waiting to start...</div>
            `;
            this.elements.agentList.appendChild(div);
        });
    }

    updateOverallProgress() {
        const completed = document.querySelectorAll('.agent-item.completed').length;
        const total = this.agents.length;
        const progress = Math.max(5, (completed / total) * 100);
        this.elements.progressBar.style.width = `${progress}%`;
    }

    renderReport(data) {
        const stats = data.statistics || {};

        let html = `
            <div class="report-viewer animated fadeIn">
                <div class="stat-grid">
                    <div class="stat-card">
                        <div class="stat-value">${stats.academic_sources || 0}</div>
                        <div class="stat-label">Academic Papers</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.verified_dois || 0}</div>
                        <div class="stat-label">Verified DOIs</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.word_count || 0}</div>
                        <div class="stat-label">Word Count</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.duration_seconds || 0}s</div>
                        <div class="stat-label">Research Time</div>
                    </div>
                </div>

                <h1>${data.title}</h1>
                <div class="report-meta">
                    <span>Generated on ${new Date().toLocaleDateString()}</span> | 
                    <span>Session ID: ${this.sessionId}</span>
                </div>

                <div class="report-abstract">
                    <h2>Abstract</h2>
                    <p>${data.abstract}</p>
                </div>

                <div class="report-sections">
                    ${data.sections.map((s, i) => `
                        <div class="report-section">
                            <h2>${i + 1}. ${s.title}</h2>
                            <div class="section-content">${this.formatMarkdown(s.content)}</div>
                        </div>
                    `).join('')}
                </div>

                <div class="report-references">
                    <hr>
                    ${this.formatMarkdown(data.report.split('## References\n')[1] || '## References\nNo references available.')}
                </div>
            </div>
        `;

        this.elements.reportContent.innerHTML = html;
        this.elements.reportContent.scrollTop = 0;
    }

    formatMarkdown(text) {
        if (!text) return '';
        // Basic markdown formatting
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/\[(\d+)\]/g, '<sup class="citation">[$1]</sup>');
    }

    async handleChat(e) {
        e.preventDefault();
        const msg = this.elements.chatInput.value.trim();
        if (!msg) return;

        this.appendMessage('user', msg);
        this.elements.chatInput.value = '';

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                action: 'chat',
                message: msg
            }));
        }
    }

    appendMessage(role, content) {
        const div = document.createElement('div');
        div.className = `message ${role}`;
        div.textContent = content;
        this.elements.chatMessages.appendChild(div);
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    }

    toggleChat() {
        this.elements.chatDrawer.classList.toggle('open');
    }

    handleExport(format) {
        if (!this.sessionId) return;
        window.open(`/api/export/${this.sessionId}/${format}`, '_blank');
    }

    showError(msg) {
        alert(msg);
        this.updateAgentStatus('orchestrator', 'error', msg);
    }
}

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    window.app = new YuktiApp();
});
