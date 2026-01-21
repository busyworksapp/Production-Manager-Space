function setAuthToken(token) {
    localStorage.setItem('token', token);
}

function getAuthToken() {
    return localStorage.getItem('token');
}

function removeAuthToken() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
}

function setCurrentUser(user) {
    localStorage.setItem('user', JSON.stringify(user));
}

function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

function isAuthenticated() {
    return !!getAuthToken();
}

function checkPermission(module, action) {
    const user = getCurrentUser();
    if (!user || !user.permissions) {
        return false;
    }
    
    let perms = user.permissions;
    if (typeof perms === 'string') {
        try {
            perms = JSON.parse(perms);
        } catch (e) {
            return false;
        }
    }
    
    if (perms.all) {
        return true;
    }
    
    const modulePerms = perms[module];
    if (!modulePerms) {
        return false;
    }
    
    return modulePerms[action] || modulePerms.all;
}

function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login';
    }
}

function logout() {
    removeAuthToken();
    window.location.href = '/login';
}

async function initAuth() {
    if (!isAuthenticated()) {
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
        return;
    }
    
    // Try to refresh user data from server, but don't log out if it fails
    try {
        const response = await API.auth.getMe();
        if (response && response.success) {
            const userData = response.data;
            // Parse permissions if they're a JSON string
            if (userData.permissions && typeof userData.permissions === 'string') {
                try {
                    userData.permissions = JSON.parse(userData.permissions);
                } catch (e) {
                    console.warn('Failed to parse permissions JSON:', e);
                    userData.permissions = {};
                }
            }
            setCurrentUser(userData);
            window.dispatchEvent(new CustomEvent('user-loaded', { detail: userData }));
        } else {
            // Response is not successful, but keep user logged in with cached data
            console.warn('Failed to refresh user data, using cached data');
            const cachedUser = getCurrentUser();
            if (cachedUser) {
                window.dispatchEvent(new CustomEvent('user-loaded', { detail: cachedUser }));
            }
        }
    } catch (error) {
        // API call failed but user has token, keep them logged in with cached data
        console.warn('Auth refresh error (keeping user logged in):', error);
        const cachedUser = getCurrentUser();
        if (cachedUser) {
            window.dispatchEvent(new CustomEvent('user-loaded', { detail: cachedUser }));
        }
    }
}

if (window.location.pathname !== '/login') {
    requireAuth();
    initAuth();
}
