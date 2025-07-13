document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('register-form');
    const registerError = document.getElementById('register-error');
    const API_BASE_URL = 'http://127.0.0.1:8000';

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        registerError.textContent = '';

        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;

        if (password !== confirmPassword) {
            registerError.textContent = '两次输入的密码不一致！';
            return;
        }

        try {
            const response = await fetch(API_BASE_URL + '/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '注册失败，请稍后再试');
            }

            // 注册成功
            alert('注册成功！现在将跳转到登录页面。');
            window.location.href = 'login.html';

        } catch (error) {
            registerError.textContent = error.message;
        }
    });
});
