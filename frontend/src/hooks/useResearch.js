import { useState, useCallback } from 'react';

export const useResearch = () => {
    const [socket, setSocket] = useState(null);
    const [sessionId, setSessionId] = useState(null);
    const [status, setStatus] = useState('idle'); // idle, planning, researching, synthesising, publishing, completed, error
    const [agents, setAgents] = useState({
        orchestrator: { status: 'pending', message: '', icon: '🎯' },
        planner: { status: 'pending', message: '', icon: '📝' },
        web_agent: { status: 'pending', message: '', icon: '🌐' },
        academic_agent: { status: 'pending', message: '', icon: '📚' },
        doc_agent: { status: 'pending', message: '', icon: '⚙️' },
        citation_agent: { status: 'pending', message: '', icon: '📍' },
        aggregator: { status: 'pending', message: '', icon: '📥' },
        synthesizer: { status: 'pending', message: '', icon: '🧠' },
        publisher: { status: 'pending', message: '', icon: '📊' }
    });
    const [logs, setLogs] = useState([]);
    const [report, setReport] = useState(null);
    const [plan, setPlan] = useState(null);
    // sections: array of {index, key, title, content} — populated by section_ready WS events
    const [sections, setSections] = useState([]);
    const [messages, setMessages] = useState([
        { role: 'assistant', content: "Hello! I'm Yukti, your advanced research orchestrator. Enter a topic to begin." }
    ]);

    const connect = useCallback((query) => {
        // Reset section state for new run
        setSections([]);

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/research`;

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            ws.send(JSON.stringify({
                action: 'research',
                query,
                citation_style: 'APA'
            }));
            setStatus('planning');
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            switch (data.type) {
                case 'session':
                    setSessionId(data.session_id);
                    break;
                case 'progress': {
                    setAgents(prev => ({
                        ...prev,
                        [data.agent]: { ...prev[data.agent], status: data.status, message: data.message }
                    }));
                    setLogs(prev => [...prev, {
                        agent: data.agent,
                        status: data.status,
                        message: data.message,
                        timestamp: data.timestamp || new Date().toISOString()
                    }]);
                    if (data.agent === 'orchestrator' && data.status === 'step') {
                        const msg = data.message || '';
                        if (msg.includes('Step 1')) setStatus('planning');
                        else if (msg.includes('Step 2') || msg.includes('Step 3')) setStatus('researching');
                        else if (msg.includes('Step 4')) setStatus('synthesising');
                        else if (msg.includes('Step 5')) setStatus('publishing');
                    }
                    if (data.agent === 'planner' && data.status === 'completed') {
                        try {
                            const jsonStr = data.message.match(/\{.*\}/s)[0];
                            setPlan(JSON.parse(jsonStr));
                        } catch {
                            // Failed to parse plan JSON
                        }
                    }
                    break;
                }
                case 'section_ready': {
                    // Append new section (avoid duplicates by key)
                    const sec = data.section;
                    if (sec) {
                        setSections(prev => {
                            const already = prev.find(s => s.key === sec.key);
                            if (already) return prev;
                            return [...prev, sec];
                        });
                    }
                    break;
                }
                case 'result':
                    setReport(data.data);
                    setStatus('completed');
                    break;
                case 'chat_response':
                    setMessages(prev => [...prev, { role: 'assistant', content: data.message }]);
                    break;
                case 'error':
                    setStatus('error');
                    break;
            }
        };

        ws.onclose = () => setSocket(null);
        setSocket(ws);
    }, []);

    const sendMessage = (content) => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: 'chat', message: content }));
            setMessages(prev => [...prev, { role: 'user', content }]);
        }
    };

    return { connect, sendMessage, status, agents, logs, report, plan, sections, setSections, messages, sessionId };
};
