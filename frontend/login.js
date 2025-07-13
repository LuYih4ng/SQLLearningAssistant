document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    const API_BASE_URL = 'http://127.0.0.1:8000';

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginError.textContent = '';
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        try {
            // 第一步：获取token
            const tokenResponse = await fetch(API_BASE_URL + '/auth/token', {
                method: 'POST',
                body: formData,
            });
            if (!tokenResponse.ok) throw new Error('用户名或密码错误');
            const tokenData = await tokenResponse.json();
            const token = tokenData.access_token;
            localStorage.setItem('sql_token', token);

            // 第二步：使用token获取用户信息，以判断是否为管理员
            const userResponse = await fetch(API_BASE_URL + '/auth/users/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!userResponse.ok) throw new Error('无法获取用户信息');
            const userData = await userResponse.json();

            // 第三步：根据is_admin字段进行跳转
            if (userData.is_admin) {
                window.location.href = 'admin.html'; // 管理员跳转到admin.html
            } else {
                window.location.href = 'index.html'; // 普通用户跳转到index.html
            }

        } catch (error) {
            loginError.textContent = error.message;
        }
    });
});
