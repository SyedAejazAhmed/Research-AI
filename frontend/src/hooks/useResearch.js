import { useState, useEffect, useCallback, useRef } from 'react';

export const useResearch = () => {
    const [socket, setSocket] = useState(null);
    const [sessionId, setSessionId] = useState(null);
    const [status, setStatus] = useState('idle'); // idle, planning, researching, synthesising, completed, error
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
    const [report, setReport] = useState(null);
    const [plan, setPlan] = useState(null);
    const [messages, setMessages] = useState([
        { role: 'assistant', content: "Hello! I'm Yukti, your advanced research orchestrator. Enter a topic to begin." }
    ]);

    const connect = useCallback((query) => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Always use current host — Vite proxy forwards /ws → backend in dev,
        // and in production the backend serves on the same host.
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
                case 'progress':
                    setAgents(prev => ({
                        ...prev,
                        [data.agent]: { ...prev[data.agent], status: data.status, message: data.message }
                    }));

                    if (data.agent === 'planner' && data.status === 'completed') {
                        try {
                            const jsonStr = data.message.match(/\{.*\}/s)[0];
                            setPlan(JSON.parse(jsonStr));
                        } catch (e) { }
                    }
                    break;
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

    return { connect, sendMessage, status, agents, report, plan, messages, sessionId };
};
