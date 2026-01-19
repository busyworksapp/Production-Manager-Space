class LoginPage {
    constructor() {
        this.init();
    }

    init() {
        if (this.checkExistingAuth()) {
            window.location.href = '/dashboard';
            return;
        }

        this.attachEventListeners();
    }

    checkExistingAuth() {
        return !!localStorage.getItem('token');
    }

    attachEventListeners() {
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }
    }

    async handleLogin(e) {
        e.preventDefault();

        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorDiv = document.getElementById('loginError');

        errorDiv.classList.add('hidden');

        try {
            const response = await API.auth.login({ username, password });

            if (response.success) {
                localStorage.setItem('token', response.data.token);
                localStorage.setItem('user', JSON.stringify(response.data.user));
                window.location.href = '/dashboard';
            }
        } catch (error) {
            errorDiv.textContent = error.message || 'Invalid username or password';
            errorDiv.classList.remove('hidden');
        }
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new LoginPage());
} else {
    new LoginPage();
}
