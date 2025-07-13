document.addEventListener('DOMContentLoaded', () => {
    const changePasswordForm = document.getElementById('change-password-form');
    const messageElement = document.getElementById('change-password-message');
    const backBtn = document.getElementById('back-btn');
    const API_BASE_URL = 'http://127.0.0.1:8000';
    const token = localStorage.getItem('sql_token');

    // 如果未登录，直接返回登录页
    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    changePasswordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        messageElement.textContent = '';
        messageElement.className = 'message';

        const old_password = document.getElementById('old-password').value;
        const new_password = document.getElementById('new-password').value;
        const confirm_new_password = document.getElementById('confirm-new-password').value;

        if (new_password !== confirm_new_password) {
            messageElement.textContent = '两次输入的新密码不一致！';
            messageElement.classList.add('error-message');
            return;
        }

        try {
            const response = await fetch(API_BASE_URL + '/auth/users/me/password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ old_password, new_password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || '修改失败，请稍后再试');
            }

            messageElement.textContent = '密码修改成功！';
            messageElement.classList.add('success-message');
            changePasswordForm.reset(); // 清空表单

        } catch (error) {
            messageElement.textContent = error.message;
            messageElement.classList.add('error-message');
        }
    });

    // 返回按钮的功能
    backBtn.addEventListener('click', () => {
        // 返回到上一页
        history.back();
    });
});
