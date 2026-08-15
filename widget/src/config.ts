export interface WidgetConfig {
    agent_id: string;
    name: string;
    theme: string;
    primary_color: string;
    position: string;
    greeting: string;
    voice_enabled: boolean;
}

// Generate a random session ID and persist it in sessionStorage
// so refresh doesn't break conversation for the MVP.
export function getSessionId(): string {
    let sid = sessionStorage.getItem('kokkopi_session');
    if (!sid) {
        sid = 'sess_' + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem('kokkopi_session', sid);
    }
    return sid;
}
