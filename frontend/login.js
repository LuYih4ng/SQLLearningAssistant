document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    const API_BASE_URL = 'http://127.0.0.1:8000';

    // 如果已有token，先清除，确保每次都通过登录流程判断
    if (localStorage.getItem('sql_token')) {
        localStorage.removeItem('sql_token');
    }

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
            if (!tokenResponse.ok) {
                const errorData = await tokenResponse.json();
                throw new Error(errorData.detail || '用户名或密码错误');
            }
            const tokenData = await tokenResponse.json();
            const token = tokenData.access_token;
            localStorage.setItem('sql_token', token);

            // 第二步：使用token获取用户信息
            const userResponse = await fetch(API_BASE_URL + '/auth/users/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!userResponse.ok) {
                throw new Error('无法获取用户信息');
            }
            const userData = await userResponse.json();

            // --- 【重要调试代码】 ---
            // 在浏览器开发者工具的控制台(Console)中查看返回的用户信息
            console.log("获取到的用户信息 (User Data):", userData);
            console.log("is_admin 字段的值:", userData.is_admin);
            console.log("is_admin 字段的类型:", typeof userData.is_admin);
            // -------------------------

            // 第三步：根据 is_admin 字段进行跳转
            if (userData.is_admin === true) { // 严格判断是否为布尔值 true
                console.log("判断为管理员，正在跳转到 admin.html...");
                window.location.href = 'admin.html';
            } else {
                console.log("判断为普通用户，正在跳转到 index.html...");
                window.location.href = 'index.html';
            }

        } catch (error) {
            loginError.textContent = error.message;
        }
    });
});
