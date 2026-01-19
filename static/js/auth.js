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
    
    if (user.permissions.all) {
        return true;
    }
    
    const modulePerms = user.permissions[module];
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
    
    try {
        const response = await API.auth.getMe();
        if (response.success) {
            setCurrentUser(response.data);
        } else {
            logout();
        }
    } catch (error) {
        console.error('Auth initialization failed:', error);
        logout();
    }
}

if (window.location.pathname !== '/login') {
    requireAuth();
    initAuth();
}
