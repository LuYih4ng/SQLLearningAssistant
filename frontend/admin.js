document.addEventListener('DOMContentLoaded', () => {
    // --- 全局状态和API封装 ---
    const API_BASE_URL = 'http://127.0.0.1:8000';
    const token = localStorage.getItem('sql_token');

    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    async function apiCall(endpoint, method = 'GET', body = null) {
        const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` };
        const options = { method, headers };
        if (body) options.body = JSON.stringify(body);

        const response = await fetch(API_BASE_URL + endpoint, options);
        if (response.status === 401 || response.status === 403) {
            handleLogout();
            return null;
        }
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'API请求失败');
        }
        return response.json();
    }

    // --- DOM 元素 ---
    const adminUsername = document.getElementById('admin-username');
    const logoutBtn = document.getElementById('logout-btn');
    const changePasswordBtn = document.getElementById('change-password-btn');
    const batchGenerateBtn = document.getElementById('batch-generate-btn');
    const draftListContainer = document.getElementById('draft-list');
    const draftCountSpan = document.getElementById('draft-count');
    const editModal = document.getElementById('edit-modal');
    const closeModalBtn = document.querySelector('.modal-close-btn');
    const updateBtn = document.getElementById('update-btn');
    const publishBtn = document.getElementById('publish-btn');

    // --- 页面初始化 ---
    async function initializeAdminPage() {
        try {
            const user = await apiCall('/auth/users/me');
            if (!user || !user.is_admin) { handleLogout(); return; }
            adminUsername.textContent = user.username;
            loadDrafts();
        } catch (error) { alert('无法加载管理员信息'); }
    }

    // --- 题库管理 ---
    async function loadDrafts() {
        try {
            const drafts = await apiCall('/admin/questions/drafts');
            draftListContainer.innerHTML = '';
            draftCountSpan.textContent = drafts.length;
            drafts.forEach(draft => {
                const draftElement = document.createElement('div');
                draftElement.className = 'draft-item';
                draftElement.innerHTML = `
                    <div class="draft-title">${draft.title}</div>
                    <div class="draft-topics">知识点: ${draft.topics}</div>
                    <button class="edit-draft-btn" data-id="${draft.id}">审核/编辑</button>
                `;
                draftListContainer.appendChild(draftElement);
            });
        } catch (error) { alert('加载草稿列表失败: ' + error.message); }
    }

    batchGenerateBtn.addEventListener('click', async () => {
        const topics = document.getElementById('ai-topics').value.split(',').map(t => t.trim());
        const count = parseInt(document.getElementById('ai-count').value, 10);
        const llm_provider = document.getElementById('ai-llm-provider').value;

        if (!topics.length || !count) { alert('请输入知识点和数量！'); return; }

        batchGenerateBtn.textContent = '生成中...';
        batchGenerateBtn.disabled = true;
        try {
            const response = await apiCall('/admin/questions/batch-generate', 'POST', { topics, count, llm_provider });
            alert(response.message);
            // 稍等片刻后刷新列表
            setTimeout(loadDrafts, 5000);
        } catch (error) {
            alert('请求失败: ' + error.message);
        } finally {
            batchGenerateBtn.textContent = '开始生成';
            batchGenerateBtn.disabled = false;
        }
    });

    draftListContainer.addEventListener('click', async (e) => {
        if (e.target.classList.contains('edit-draft-btn')) {
            const questionId = e.target.dataset.id;
            const draft = (await apiCall('/admin/questions/drafts')).find(d => d.id == questionId);
            if (draft) {
                document.getElementById('edit-question-id').value = draft.id;
                document.getElementById('edit-title').value = draft.title;
                document.getElementById('edit-topics').value = draft.topics;
                document.getElementById('edit-question-text').value = draft.question_text;
                document.getElementById('edit-setup-sql').value = draft.setup_sql;
                document.getElementById('edit-correct-sql').value = draft.correct_sql;
                editModal.style.display = 'flex';
            }
        }
    });

    // --- 模态框逻辑 ---
    closeModalBtn.addEventListener('click', () => editModal.style.display = 'none');

    updateBtn.addEventListener('click', async () => {
        const questionId = document.getElementById('edit-question-id').value;
        const body = {
            title: document.getElementById('edit-title').value,
            topics: document.getElementById('edit-topics').value,
            question_text: document.getElementById('edit-question-text').value,
            setup_sql: document.getElementById('edit-setup-sql').value,
            correct_sql: document.getElementById('edit-correct-sql').value,
        };
        try {
            await apiCall(`/admin/questions/${questionId}`, 'PUT', body);
            alert('保存成功！');
            editModal.style.display = 'none';
            loadDrafts();
        } catch (error) { alert('保存失败: ' + error.message); }
    });

    publishBtn.addEventListener('click', async () => {
        const questionId = document.getElementById('edit-question-id').value;
        if (confirm(`确定要发布题目 #${questionId} 吗？`)) {
            try {
                await apiCall(`/admin/questions/${questionId}/publish`, 'POST');
                alert('发布成功！');
                editModal.style.display = 'none';
                loadDrafts();
            } catch (error) { alert('发布失败: ' + error.message); }
        }
    });


    // --- 登出 ---
    function handleLogout() {
        localStorage.removeItem('sql_token');
        window.location.href = 'login.html';
    }
    logoutBtn.addEventListener('click', handleLogout);

    // 新增: 跳转到修改密码页面
    changePasswordBtn.addEventListener('click', () => {
        window.location.href = 'change-password.html';
    });

    initializeAdminPage();
});
