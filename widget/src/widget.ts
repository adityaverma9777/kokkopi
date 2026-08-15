import { KokkopiClient } from './client';
import { KokkopiUI } from './ui';
import { getSessionId } from './config';

async function init() {
    // Find the script tag that loaded this script
    const scripts = document.getElementsByTagName('script');
    let currentScript = scripts[scripts.length - 1];
    
    // Attempt to find script by data-agent if currentScript isn't right
    for (let i = 0; i < scripts.length; i++) {
        if (scripts[i].getAttribute('data-agent')) {
            currentScript = scripts[i];
            break;
        }
    }

    const agentId = currentScript.getAttribute('data-agent');
    if (!agentId) {
        console.error("Kokkopi Widget: Missing data-agent attribute on script tag.");
        return;
    }

    // Determine base URL from the script src
    let baseUrl = '';
    const src = currentScript.getAttribute('src');
    if (src && src.startsWith('http')) {
        const url = new URL(src);
        baseUrl = `${url.protocol}//${url.host}`;
    } else {
        // Fallback for local testing
        baseUrl = 'http://127.0.0.1:8000';
    }

    try {
        const sessionId = getSessionId();
        const res = await fetch(`${baseUrl}/api/public/agents/${agentId}/config?session_id=${sessionId}`);
        if (!res.ok) {
            console.warn("Kokkopi Widget: Agent is unavailable or invalid.");
            return;
        }

        const config = await res.json();
        const client = new KokkopiClient(baseUrl, config);
        const ui = new KokkopiUI(config, client);
        
        ui.render();
    } catch (e) {
        console.warn("Kokkopi Widget: Failed to load configuration.", e);
    }
}

// Run safely
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
