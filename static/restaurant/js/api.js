// static/js/api.js
const BASE_URL = '/api'; // Relative to your Django server

// Token management
export function setTokens(access, refresh) {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
}

export function getAccessToken() {
    return localStorage.getItem('access_token');
}

// Enhanced fetch with token refresh
export async function authFetch(url, options = {}) {
    const finalUrl = url.startsWith('/') ? `${BASE_URL}${url}` : url;
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };
    
    const accessToken = getAccessToken();
    if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    let response = await fetch(finalUrl, {
        ...options,
        headers,
    });
    
    // Handle token refresh
    if (response.status === 401) {
        const newToken = await refreshToken();
        if (newToken) {
            headers['Authorization'] = `Bearer ${newToken}`;
            response = await fetch(finalUrl, {
                ...options,
                headers,
            });
        }
    }
    
    return response;
}

async function refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return null;
    
    try {
        const response = await fetch(`${BASE_URL}/token/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: refreshToken }),
        });
        
        if (response.ok) {
            const data = await response.json();
            setTokens(data.access, data.refresh);
            return data.access;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
    }
    return null;
}