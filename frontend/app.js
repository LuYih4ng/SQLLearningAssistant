document.addEventListener('DOMContentLoaded', () => {
   // --- 全局状态和常量 ---
    const API_BASE_URL = 'http://127.0.0.1:8000';
    let state = {
        token: localStorage.getItem('sql_token'),
        user: null,
        currentMode: null, // 'explain', 'test', 'daily'
        currentQuestionId: null, // 用于能力测试和每日一题
    };

    if (!state.token) {
        window.location.href = 'login.html';
        return;
    }

    // --- DOM 元素获取 ---
    const chatBox = document.getElementById('chat-box');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const explainBtn = document.getElementById('explain-btn');
    const testBtn = document.getElementById('test-btn');
    const dailyBtn = document.getElementById('daily-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const changePasswordBtn = document.getElementById('change-password-btn');
    const usernameDisplay = document.getElementById('username-display');
    const pointsDisplay = document.getElementById('points-display');
    const schemaDisplay = document.getElementById('schema-display');
    const leaderboardDisplay = document.getElementById('leaderboard-display');
    const llmSelect = document.getElementById('llm-select');

    // --- API 调用封装 ---
    async function apiCall(endpoint, method = 'GET', body = null) {
        const headers = { 'Content-Type': 'application/json' };
        if (state.token) {
            headers['Authorization'] = `Bearer ${state.token}`;
        }
        const options = { method, headers };
        if (body) {
            options.body = JSON.stringify(body);
        }
        try {
            const response = await fetch(API_BASE_URL + endpoint, options);
            if (response.status === 401) {
                handleLogout();
                return;
            }
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            if (response.status === 204) return null;
            return await response.json();
        } catch (error) {
            console.error('API Call Error:', error);
            throw error;
        }
    }

    // --- UI 渲染函数 ---
    function appendMessage(sender, content, type = 'text') {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', sender);
        if (type === 'html') {
            messageDiv.innerHTML = content;
        } else {
            const p = document.createElement('p');
            p.textContent = content;
            messageDiv.appendChild(p);
        }
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function updateUserInfo() {
        if (state.user) {
            usernameDisplay.textContent = state.user.username;
            pointsDisplay.textContent = state.user.points;
        }
    }

    async function updateLeaderboard() {
        try {
            const leaderboard = await apiCall('/daily/leaderboard');
            if (!leaderboard) return;
            leaderboardDisplay.innerHTML = leaderboard.map(entry =>
                `<p>${entry.rank}. ${entry.username} - ${entry.points}分</p>`
            ).join('');
        } catch (error) {
            leaderboardDisplay.innerHTML = '<p>无法加载排行榜。</p>';
        }
    }

    // 【修改】现在这个函数可以被动态调用来更新表结构
    function updateSchemaDisplay(schemaText) {
        schemaDisplay.textContent = schemaText;
    }

    async function fetchAndDisplaySchema() {
        try {
            const schema = await apiCall('/test/schema');
            if (!schema) return;
            schemaDisplay.textContent = schema;
        } catch (error) {
            schemaDisplay.textContent = '无法加载表结构。';
        }
    }

    // --- 业务逻辑和事件处理 ---
    async function initializeApp() {
        try {
            state.user = await apiCall('/auth/users/me');
            if (state.user) {
                updateUserInfo();
                updateLeaderboard();
                appendMessage('system', `你好, ${state.user.username}！请选择一个功能开始学习。`);
            }
        } catch (error) {
            handleLogout();
        }
    }

    function handleLogout() {
        localStorage.removeItem('sql_token');
        window.location.href = 'login.html';
    }
    logoutBtn.addEventListener('click', handleLogout);
    changePasswordBtn.addEventListener('click', () => { window.location.href = 'change-password.html'; });

    function setMode(mode) {
        state.currentMode = mode;
        const buttons = [explainBtn, testBtn, dailyBtn];
        buttons.forEach(btn => btn.classList.remove('active'));

        state.currentQuestionId = null; // 切换模式时重置题目状态
        updateSchemaDisplay('请先抽取题目'); // 重置表结构显示

        if (mode === 'explain') {
            explainBtn.classList.add('active');
            chatInput.placeholder = '输入你想了解的SQL知识点...';
        } else if (mode === 'test') {
            testBtn.classList.add('active');
            chatInput.placeholder = '输入想练习的知识点 (用逗号分隔), 然后点击发送来抽取题目...';
        } else if (mode === 'daily') {
            dailyBtn.classList.add('active');
            chatInput.placeholder = '点击下方按钮获取每日一题, 然后在此输入SQL答案...';
        }
    }

    explainBtn.addEventListener('click', () => setMode('explain'));
    testBtn.addEventListener('click', () => setMode('test'));
    dailyBtn.addEventListener('click', async () => {
        setMode('daily');
        appendMessage('bot', '正在获取每日一题...');
        try {
            const question = await apiCall('/daily/question');
            if(!question) return;
            // 每日一题现在没有setup_sql，所以不清空
            state.currentQuestionId = question.id; // 注意：这里是daily_question的ID
            appendMessage('system', `题目: ${question.title}\n\n${question.question_text}`);
        } catch (error) {
            appendMessage('bot', `获取每日一题失败: ${error.message}`);
        }
    });

    sendBtn.addEventListener('click', async () => {
        const input = chatInput.value.trim();
        if (!input) return;
        if (!state.currentMode) {
            appendMessage('bot', '请先选择一个功能模式。');
            return;
        }
        appendMessage('user', input);
        chatInput.value = '';
        try {
            switch (state.currentMode) {
                case 'explain':
                    await handleExplain(input);
                    break;
                case 'test':
                    // 【新逻辑】根据是否有题目ID，决定是抽题还是提交答案
                    state.currentQuestionId ? await handleTestSubmit(input) : await handleTestGetQuestion(input);
                    break;
                case 'daily':
                    state.currentQuestionId ? await handleDailySubmit(input) : appendMessage('bot', '请先点击"每日一题"按钮获取题目。');
                    break;
            }
        } catch (error) {
            appendMessage('bot', `操作失败: ${error.message}`);
        }
    });

    async function handleExplain(topic) {
        const selectedLlm = llmSelect.value;
        appendMessage('bot', `正在用 ${selectedLlm} 查询关于 "${topic}" 的解释...`);

        const botMessageDiv = document.createElement('div');
        botMessageDiv.classList.add('chat-message', 'bot');
        const contentP = document.createElement('p');
        botMessageDiv.appendChild(contentP);
        chatBox.appendChild(botMessageDiv);

        let fullContent = '';
        try {
            const response = await fetch(API_BASE_URL + '/chat/explain', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.token}`
                },
                body: JSON.stringify({ topic, llm_provider: selectedLlm })
            });
            if (!response.ok) throw new Error(`服务器错误: ${response.status}`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                fullContent += chunk;
                contentP.textContent = fullContent;
                chatBox.scrollTop = chatBox.scrollHeight;
            }
            contentP.innerHTML = marked.parse(fullContent);
        } catch (error) {
            contentP.textContent = `请求失败: ${error.message}`;
        }
    }

    // 【新】处理抽取能力测试题目的逻辑
    async function handleTestGetQuestion(topicsInput) {
        appendMessage('bot', `正在根据知识点 "${topicsInput}" 从题库中抽取题目...`);
        const topics = topicsInput.split(',').map(t => t.trim());
        try {
            const response = await apiCall('/test/get-question', 'POST', { topics });
            if (response) {
                state.currentQuestionId = response.question_id;
                appendMessage('system', `题目: ${response.title}\n\n${response.question_text}`);
                updateSchemaDisplay(response.setup_sql); // 动态更新表结构
                chatInput.placeholder = '题目已加载，请在此输入你的SQL答案...';
            }
        } catch (error) {
            appendMessage('bot', `抽题失败: ${error.message}`);
        }
    }

    // 【新】处理能力测试答案提交的逻辑
    async function handleTestSubmit(sql) {
        appendMessage('bot', `正在评测你的SQL答案...`);
        const body = {
            question_id: state.currentQuestionId,
            user_sql: sql,
        };
        try {
            const response = await apiCall('/test/submit-answer', 'POST', body);
            if (response) {
                let content = `<h4>评测结果: ${response.message}</h4>`;
                // 新逻辑下，总是有分析结果
                content += `<p><strong>AI导师分析:</strong></p><pre>${response.analysis}</pre>`;
                appendMessage('bot', content, 'html');
            }
        } catch (error) {
            appendMessage('bot', `评测失败: ${error.message}`);
        } finally {
            // 评测结束后，重置状态，准备下一轮
            state.currentQuestionId = null;
            updateSchemaDisplay('请先抽取题目');
            chatInput.placeholder = '输入想练习的知识点, 然后点击发送来抽取题目...';
        }
    }

    async function handleTestGenerate(topicsInput) {
        const selectedLlm = llmSelect.value;
        appendMessage('bot', `正在根据知识点 "${topicsInput}" 生成题目...`);
        const topics = topicsInput.split(',').map(t => t.trim());
        const response = await apiCall('/test/generate-question', 'POST', { topics, llm_provider: selectedLlm });
        if (response) {
            state.currentQuestionId = response.question_id;
            appendMessage('system', `题目: ${response.question_text}`);
            chatInput.placeholder = '请在此输入你的SQL答案...';
        }
    }

    async function handleTestSubmit(sql) {
        const selectedLlm = llmSelect.value;
        appendMessage('bot', `正在评测你的SQL答案...`);
        const body = {
            question_id: state.currentQuestionId,
            user_sql: sql,
            llm_provider: selectedLlm
        };
        const response = await apiCall('/test/submit-answer', 'POST', body);
        if (response) {
            let content = `<h4>评测结果: ${response.message}</h4>`;
            if (response.analysis) {
                content += `<p><strong>AI导师分析:</strong></p><pre>${response.analysis}</pre>`;
            }
            appendMessage('bot', content, 'html');
        }
        state.currentQuestionId = null;
        chatInput.placeholder = '输入要测试的知识点 (用逗号分隔)...';
    }

    // 【修改】处理每日一题答案提交的逻辑
    async function handleDailySubmit(sql) {
        appendMessage('bot', `正在提交每日一题答案...`);
        const body = { daily_question_id: state.currentQuestionId, user_sql: sql };
        try {
            const response = await apiCall('/daily/submit', 'POST', body);
            if (response) {
                appendMessage('bot', response.message);
                if (response.status === 'correct' || response.status === 'already_solved') {
                    state.currentQuestionId = null; // 答对或已答过，则不能再提交
                    if (response.status === 'correct') {
                        state.user = await apiCall('/auth/users/me');
                        updateUserInfo();
                        updateLeaderboard();
                    }
                }
            }
        } catch(error) {
             appendMessage('bot', `提交失败: ${error.message}`);
        }
    }

    // --- 初始化 App ---
    initializeApp();
});
