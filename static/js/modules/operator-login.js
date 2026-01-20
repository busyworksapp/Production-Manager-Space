class OperatorLogin {
    constructor() {
        this.init();
    }

    init() {
        this.attachEventListeners();
    }

    attachEventListeners() {
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }

        const employeeNumberInput = document.getElementById('employeeNumber');
        if (employeeNumberInput) {
            employeeNumberInput.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^0-9]/g, '');
            });
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        
        const employeeNumber = document.getElementById('employeeNumber').value.trim();
        const loginBtn = document.getElementById('loginBtn');
        const errorMessage = document.getElementById('errorMessage');
        
        if (!employeeNumber) {
            this.showError('Please enter your employee number');
            return;
        }
        
        loginBtn.disabled = true;
        loginBtn.textContent = 'Logging in...';
        errorMessage.style.display = 'none';
        
        try {
            const response = await fetch('/api/operator/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    employee_number: employeeNumber
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                localStorage.setItem('auth_token', data.data.token);
                localStorage.setItem('user', JSON.stringify({
                    id: data.data.employee.id,
                    name: data.data.employee.name,
                    employee_type: data.data.employee.employee_type,
                    department_id: data.data.employee.department_id,
                    department_name: data.data.employee.department_name,
                    role: 'operator'
                }));
                
                window.location.href = '/operator/dashboard';
            } else {
                this.showError(data.message || 'Login failed. Please check your employee number.');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError('Unable to connect to the server. Please try again.');
        } finally {
            loginBtn.disabled = false;
            loginBtn.textContent = 'Login';
        }
    }

    showError(message) {
        const errorDiv = document.getElementById('errorMessage');
        errorDiv.className = 'alert alert-danger';
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new OperatorLogin());
} else {
    new OperatorLogin();
}
