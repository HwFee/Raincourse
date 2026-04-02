// 全局状态
let currentUser = null;
let rainAPI = null;
let courses = [];
let currentCourseId = null;
let works = [];
let currentWorkId = null;
let appInitialized = false;
let qrLoginLoading = false;

async function initializeApp() {
    if (appInitialized) return;

    if (!window.pywebview || !window.pywebview.api) {
        console.log('⏳ pywebview API 尚未就绪，等待中...');
        return;
    }

    appInitialized = true;
    console.log('🚀 应用初始化...');
    await loadSavedUsers();
    await checkLoginStatus();
    await loadCoursesForAI();
}

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        initializeApp();
    }, 300);
});

window.addEventListener('pywebviewready', () => {
    console.log('✅ pywebviewready');
    initializeApp();
});

// 加载AI答题页面的课程选项
async function loadCoursesForAI() {
    try {
        if (!currentUser) return;
        
        const result = await pywebview.api.get_courses();
        if (result.success) {
            const select = document.getElementById('select-course');
            
            if (result.courses.length === 0) {
                select.innerHTML = '<option value="">暂无课程</option>';
                return;
            }
            
            select.innerHTML = '<option value="">请选择课程</option>' +
                result.courses.map(course => 
                    `<option value="${course.id || course.classroom_id}">${course.name}</option>`
                ).join('');
        }
    } catch (error) {
        console.error('加载AI课程选项失败:', error);
    }
}

// 导航功能
function navigateTo(page) {
    // 更新导航状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-page="${page}"]`).classList.add('active');

    // 切换页面
    document.querySelectorAll('.page').forEach(p => {
        p.classList.remove('active');
    });
    document.getElementById(`page-${page}`).classList.add('active');

    // 加载页面数据
    switch(page) {
        case 'home':
            loadHomeData();
            break;
        case 'courses':
            loadCourses();
            break;
        case 'files':
            loadFiles('question');
            break;
    }
}

// 首页数据
async function loadHomeData() {
    if (!currentUser) {
        console.log('未登录，无法加载首页数据');
        return;
    }

    try {
        console.log('开始加载首页数据...');
        const coursesData = await pywebview.api.get_courses();
        console.log('课程数据:', coursesData);
        
        if (coursesData.success) {
            document.getElementById('stat-courses').textContent = coursesData.courses.length;
            
            // 自动加载课程列表到首页
            const courseList = document.getElementById('course-list');
            if (courseList && coursesData.courses.length > 0) {
                courseList.innerHTML = coursesData.courses.map((course, index) => `
                    <div class="course-card" onclick="selectCourse(${index})">
                        <div class="course-name">${course.name || course.course_name}</div>
                        <div class="course-info">教师: ${course.teacher || '未知'}</div>
                        <div class="course-info">学生数: ${course.student_count || 0}</div>
                    </div>
                `).join('');
            }
        } else {
            console.error('加载课程失败:', coursesData.message);
            showNotification(coursesData.message, 'error');
        }
    } catch (error) {
        console.error('加载首页数据失败:', error);
        showNotification('加载首页数据失败: ' + error.message, 'error');
    }
}

// 课程列表
async function loadCourses() {
    if (!currentUser) {
        showNotification('请先登录', 'error');
        showLoginModal();
        return;
    }

    try {
        console.log('加载课程列表...');
        const result = await pywebview.api.get_courses();
        console.log('课程结果:', result);
        
        if (result.success) {
            courses = result.courses;
            const courseList = document.getElementById('course-list');
            
            if (courses.length === 0) {
                courseList.innerHTML = '<div class="empty-message">暂无课程</div>';
                return;
            }
            
            courseList.innerHTML = courses.map((course, index) => `
                <div class="course-card" onclick="selectCourse(${index})">
                    <div class="course-name">${course.name || course.course_name}</div>
                    <div class="course-info">教师: ${course.teacher || '未知'}</div>
                    <div class="course-info">学生数: ${course.student_count || 0}</div>
                </div>
            `).join('');
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        console.error('加载课程失败:', error);
        showNotification('加载课程失败: ' + error.message, 'error');
    }
}

// 选择课程
async function selectCourse(index) {
    const course = courses[index];
    currentCourseId = course.classroom_id || course.id;
    
    console.log('选择课程:', course.name, 'ID:', currentCourseId);
    navigateTo('ai-answer');
    document.getElementById('select-course').value = currentCourseId;
    await loadWorksForAI(currentCourseId);
}

// AI答题 - 加载课程
async function loadWorksForAI(courseId) {
    try {
        currentCourseId = courseId || null;
        currentWorkId = null;
        console.log('AI答题 - 加载作业, 课程ID:', courseId);
        const select = document.getElementById('select-work');
        const quickList = document.getElementById('work-quick-list');

        if (!courseId) {
            select.innerHTML = '<option value="">请先选择课程</option>';
            quickList.innerHTML = '';
            return;
        }

        const result = await pywebview.api.get_works(courseId);
        console.log('AI答题 - 作业结果:', result);
        
        if (result.success) {
            works = result.works;
            if (result.works.length === 0) {
                select.innerHTML = '<option value="">该课程暂无作业</option>';
                quickList.innerHTML = '<div class="empty-message compact">当前课程没有可显示的作业</div>';
                return;
            }
            
            select.innerHTML = '<option value="">请选择作业</option>' +
                result.works.map(work => 
                    `<option value="${work.id || work.courseware_id}">${work.title || work.name}</option>`
                ).join('');

            quickList.innerHTML = result.works.map((work, index) => `
                <button class="quick-work-chip" onclick="pickWorkFromQuickList(${index})">
                    <span>${work.title || work.name}</span>
                    <small>${work.status || '未知状态'}</small>
                </button>
            `).join('');
        } else {
            addLog('加载作业失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('加载作业失败:', error);
        addLog('加载作业失败: ' + error.message, 'error');
    }
}

function pickWorkFromQuickList(index) {
    const work = works[index];
    currentWorkId = work.id || work.courseware_id;
    document.getElementById('select-work').value = currentWorkId;
    addLog(`已选择作业: ${work.title || work.name}`, 'info');
}

// 选择作业(AI答题)
function selectWorkForAI(workId) {
    currentWorkId = workId;
}

// 开始AI答题
async function startAIAnswering() {
    if (!currentCourseId || !currentWorkId) {
        addLog('请先选择课程和作业', 'error');
        return;
    }

    // 更新答题状态为正在答题
    updateAnswerStatus('answering');
    
    addLog('开始AI答题...', 'info');
    addLog(`课程ID: ${currentCourseId}`, 'info');
    addLog(`作业ID: ${currentWorkId}`, 'info');

    try {
        const result = await pywebview.api.start_ai_answer(currentCourseId, currentWorkId);
        
        if (result.success) {
            addLog(result.message, 'success');
        } else {
            updateAnswerStatus('idle');
            addLog(result.message, 'error');
        }
    } catch (error) {
        updateAnswerStatus('idle');
        addLog('答题失败: ' + error.message, 'error');
    }
}

// 添加日志
function addLog(message, type = 'info') {
    const logContent = document.getElementById('answer-log');
    const timestamp = new Date().toLocaleTimeString();
    
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;
    entry.textContent = `[${timestamp}] ${message}`;
    
    logContent.appendChild(entry);
    logContent.scrollTop = logContent.scrollHeight;
}

// 清空日志
function clearLog() {
    document.getElementById('answer-log').innerHTML = '';
}

// 文件管理
function switchFileTab(type) {
    document.querySelectorAll('.file-tabs .tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');
    
    loadFiles(type);
}

async function loadFiles(type) {
    try {
        console.log('加载文件列表, 类型:', type);
        const result = await pywebview.api.get_files(type);
        console.log('文件结果:', result);
        
        if (result.success) {
            const fileList = document.getElementById('file-list');
            
            if (result.files.length === 0) {
                fileList.innerHTML = '<div class="empty-message">暂无文件</div>';
                return;
            }
            
            fileList.innerHTML = result.files.map(file => {
                // 根据文件类型决定按钮文字
                const buttonText = file.type === 'export' ? '打开' : '导出';
                const buttonIcon = file.type === 'export' ? '📂' : '📤';
                
                return `
                    <div class="file-item">
                        <div>
                            <div>${file.name}</div>
                            <div class="work-meta">${file.description || ''}</div>
                            <div class="work-meta">${file.raw_name || file.name} | ${file.size} | ${file.date}</div>
                        </div>
                        <button class="btn-secondary" data-path="${file.path}" onclick="exportFile(this.getAttribute('data-path'))">
                            <span>${buttonIcon}</span> ${buttonText}
                        </button>
                    </div>
                `;
            }).join('');
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        console.error('加载文件失败:', error);
        showNotification('加载文件失败: ' + error.message, 'error');
    }
}

// 登录相关
async function loadSavedUsers() {
    try {
        console.log('📋 加载已保存的用户列表...');
        const users = await pywebview.api.get_saved_users();
        console.log('用户列表:', users);
        
        const select = document.getElementById('saved-users');
        
        if (users && users.length > 0) {
            select.innerHTML = '<option value="">请选择用户</option>' +
                users.map(user => `<option value="${user}">${user}</option>`).join('');
            
            console.log(`✅ 找到 ${users.length} 个已保存的用户`);
        } else {
            select.innerHTML = '<option value="">暂无保存的用户</option>';
            console.log('⚠️ 没有找到已保存的用户');
        }
    } catch (error) {
        console.error('❌ 加载用户列表失败:', error);
    }
}

async function loadSavedUser() {
    const username = document.getElementById('saved-users').value;
    if (!username) {
        showNotification('请选择用户', 'error');
        return;
    }

    try {
        const result = await pywebview.api.load_user_session(username);
        
        if (result.success) {
            currentUser = result.username;
            updateLoginStatus();
            closeLoginModal();
            showNotification(result.message, 'success');
            await loadSavedUsers();
            await loadHomeData();
            await loadCoursesForAI();
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('加载失败: ' + error.message, 'error');
    }
}

async function startQRLogin() {
    if (qrLoginLoading) {
        return;
    }

    try {
        qrLoginLoading = true;
        // 清空之前的二维码
        document.getElementById('qr-image').style.display = 'none';
        document.getElementById('qr-code').textContent = '正在生成二维码...';
        
        const result = await pywebview.api.start_qr_login();
        
        if (result.success) {
            showNotification(result.message, 'info');
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('启动登录失败: ' + error.message, 'error');
    } finally {
        qrLoginLoading = false;
    }
}

// 显示二维码(从Python调用)
function showQRCode(qrAscii) {
    document.getElementById('qr-image').style.display = 'none';
    document.getElementById('qr-code').textContent = qrAscii;
}

function showQRCodeImage(src) {
    const image = document.getElementById('qr-image');
    const text = document.getElementById('qr-code');
    image.src = src;
    image.style.display = 'block';
    text.textContent = '';
}

// 处理登录成功(从Python调用)
function handleLoginSuccess(username) {
    currentUser = username;
    updateLoginStatus();
    closeLoginModal();
    showNotification('登录成功: ' + username, 'success');
    loadHomeData();
    loadSavedUsers();
    loadCoursesForAI();
}

// 处理登录失败(从Python调用)
function handleLoginError(error) {
    showNotification('登录失败: ' + error, 'error');
}

// 检查登录状态
async function checkLoginStatus() {
    try {
        const result = await pywebview.api.check_login();
        if (result.logged_in) {
            currentUser = result.username;
            updateLoginStatus();
            await loadHomeData();
        } else {
            // 如果未登录，显示登录模态框
            showLoginModal();
        }
    } catch (error) {
        console.log('未登录');
        showLoginModal();
    }
}

// 更新登录状态
function updateLoginStatus() {
    document.getElementById('user-name').textContent = currentUser || '未登录';
    document.getElementById('current-user').textContent = currentUser || '未登录';
}

// 模态框
function showLoginModal() {
    document.getElementById('login-modal').classList.add('active');

    // 如果当前停留在扫码登录标签，打开弹窗后自动拉取二维码
    const activeTab = document.querySelector('.login-tabs .tab.active');
    if (activeTab && activeTab.textContent.includes('扫码')) {
        startQRLogin();
    }
}

function closeLoginModal() {
    document.getElementById('login-modal').classList.remove('active');
}

function switchLoginTab(type) {
    document.querySelectorAll('.login-tabs .tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    document.getElementById('login-saved').style.display = type === 'saved' ? 'block' : 'none';
    document.getElementById('login-qr').style.display = type === 'qr' ? 'block' : 'none';

    // 切换到扫码页后自动请求二维码，无需手动点击刷新
    if (type === 'qr') {
        startQRLogin();
    }
}

// 通知
function showNotification(message, type = 'info') {
    // 简单的通知实现
    console.log(`[${type}] ${message}`);
    addLog(message, type);
}

window.handleBackendLog = function(payload) {
    if (!payload || !payload.message) return;
    addLog(payload.message, payload.type || 'info');
};

// 导出文件
async function exportFile(filePath) {
    try {
        const result = await pywebview.api.export_file(filePath);
        if (result.success) {
            showNotification('导出成功', 'success');
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('导出失败: ' + error.message, 'error');
    }
}

// ==================== 停止答题功能 ====================
let isAnswering = false;

// 停止AI答题
async function stopAIAnswering() {
    if (!isAnswering) {
        addLog('当前没有正在进行的答题任务', 'warning');
        return;
    }

    addLog('正在停止答题...', 'info');
    
    try {
        const result = await pywebview.api.stop_ai_answer();
        
        if (result.success) {
            isAnswering = false;
            updateAnswerStatus('stopped');
            addLog(result.message || '答题已停止', 'success');
        } else {
            addLog(result.message || '停止失败', 'error');
        }
    } catch (error) {
        addLog('停止答题失败: ' + error.message, 'error');
    }
}

// 更新答题状态
function updateAnswerStatus(status) {
    const statusText = document.getElementById('answer-status-text');
    const btnStart = document.getElementById('btn-start-answer');
    const btnStop = document.getElementById('btn-stop-answer');
    
    const statusMap = {
        'idle': { text: '未开始', class: '' },
        'answering': { text: '正在答题...', class: 'answering' },
        'stopped': { text: '已停止', class: 'stopped' },
        'completed': { text: '答题完成', class: 'completed' }
    };
    
    const statusInfo = statusMap[status] || statusMap['idle'];
    statusText.textContent = statusInfo.text;
    statusText.className = 'status-value ' + statusInfo.class;
    
    // 更新按钮显示状态
    if (status === 'answering') {
        isAnswering = true;
        btnStart.style.display = 'none';
        btnStop.style.display = 'inline-block';
    } else {
        isAnswering = false;
        btnStart.style.display = 'inline-block';
        btnStop.style.display = 'none';
    }
}

// 答题完成回调
window.handleAnswerComplete = function(message) {
    updateAnswerStatus('completed');
    addLog(message, 'success');
};

// 答题停止回调
window.handleAnswerStopped = function(message) {
    updateAnswerStatus('stopped');
    addLog(message, 'warning');
};

// 答题错误回调
window.handleAnswerError = function(message) {
    updateAnswerStatus('idle');
    addLog(message, 'error');
};

// ==================== API配置功能 ====================
let currentApiProvider = null;

// 切换设置标签页
function switchSettingsTab(tab) {
    document.querySelectorAll('.settings-tabs .tab').forEach(t => {
        t.classList.remove('active');
    });
    event.target.classList.add('active');
    
    document.getElementById('settings-account').style.display = tab === 'account' ? 'block' : 'none';
    document.getElementById('settings-ai').style.display = tab === 'ai' ? 'block' : 'none';
    document.getElementById('settings-api').style.display = tab === 'api' ? 'block' : 'none';
    
    if (tab === 'api') {
        loadApiProviders();
    }
}

// 加载API服务商列表
async function loadApiProviders() {
    try {
        const result = await pywebview.api.get_all_providers();
        
        if (result.success) {
            renderApiProviders(result.providers, result.current_provider_id);
        }
    } catch (error) {
        console.error('加载API配置失败:', error);
    }
}

// 渲染API服务商列表
function renderApiProviders(providers, currentId) {
    const container = document.getElementById('api-provider-list');
    
    const icons = {
        'minimax_token_plan': '🧩',
        'minimax_official': '🤖',
        'openai': '🌐',
        'anthropic': '🧠',
        'qwen': '☁️',
        'deepseek': '🔍',
        'zhipu': '⚡',
        'doubao': '🫘',
        'siliconflow': '🪨',
        'feishu': '🕊️'
    };
    
    container.innerHTML = providers.map(provider => {
        const isConfigured = !!provider.configured;
        const isUsing = !!provider.is_using;
        const canToggle = isConfigured;
        
        return `
            <div class="api-provider-item">
                <div class="api-provider-info">
                    <div class="api-provider-icon">${icons[provider.id] || '🔌'}</div>
                    <div class="api-provider-details">
                        <h4>${provider.name}</h4>
                        <div class="api-provider-meta">
                            <span>类型: ${provider.api_type}</span>
                            <span class="api-status ${isConfigured ? 'configured' : 'not-configured'}">
                                ${isConfigured ? '✓ 已配置' : '○ 未配置'}
                            </span>
                            ${isUsing ? '<span class="api-status current">★ 正在使用</span>' : '<span class="api-status">○ 未启用</span>'}
                        </div>
                    </div>
                </div>
                <div class="api-provider-actions">
                    <button class="btn-secondary" onclick="showApiConfigModal('${provider.id}')">配置</button>
                    ${isConfigured ? `<button class="btn-secondary" onclick="testApiConnectionById('${provider.id}')">测试</button>` : ''}
                    <label class="switch-inline">
                        <input type="checkbox" ${isUsing ? 'checked' : ''} ${canToggle ? '' : 'disabled'} onchange="toggleProviderEnabled('${provider.id}', this.checked)">
                        <span>${isUsing ? '开' : '关'}</span>
                    </label>
                </div>
            </div>
        `;
    }).join('');
}

// 显示API配置模态框
async function showApiConfigModal(providerId) {
    try {
        const result = await pywebview.api.get_provider_config(providerId);
        
        if (result.success) {
            currentApiProvider = { id: providerId, ...result.config };
            
            document.getElementById('api-config-title').textContent = `配置 ${result.config.name} API`;
            document.getElementById('api-provider-name').value = result.config.name;
            document.getElementById('api-type').value = result.config.api_type;
            document.getElementById('api-key').value = '';
            document.getElementById('api-key').placeholder = result.config.api_key_masked
                ? `已保存: ${result.config.api_key_masked}（留空则不修改）`
                : '请输入API密钥';
            document.getElementById('api-endpoint').value = result.config.base_url || '';
            
            document.getElementById('api-config-modal').classList.add('active');
        }
    } catch (error) {
        showNotification('获取配置失败: ' + error.message, 'error');
    }
}

// 关闭API配置模态框
function closeApiConfigModal() {
    document.getElementById('api-config-modal').classList.remove('active');
    currentApiProvider = null;
}

// 测试API连接
async function testApiConnection() {
    if (!currentApiProvider) return;
    
    const apiKey = document.getElementById('api-key').value;
    const apiEndpoint = document.getElementById('api-endpoint').value;
    
    showNotification('正在测试连接...', 'info');
    
    try {
        // 输入了新key才覆盖；留空则使用已保存key
        if (apiKey) {
            await pywebview.api.set_provider_api_key(
                currentApiProvider.id,
                apiKey,
                apiEndpoint
            );
        }
        
        // 再测试连接
        const result = await pywebview.api.test_api_connection(currentApiProvider.id);
        
        if (result.success) {
            showNotification('连接测试成功！', 'success');
        } else {
            showNotification(result.message || '连接测试失败', 'error');
        }
    } catch (error) {
        showNotification('测试失败: ' + error.message, 'error');
    }
}

// 测试指定服务商的连接
async function testApiConnectionById(providerId) {
    showNotification('正在测试连接...', 'info');
    
    try {
        const result = await pywebview.api.test_api_connection(providerId);
        
        if (result.success) {
            showNotification('连接测试成功！', 'success');
        } else {
            showNotification(result.message || '连接测试失败', 'error');
        }
    } catch (error) {
        showNotification('测试失败: ' + error.message, 'error');
    }
}

// 保存API配置
async function saveApiConfig() {
    if (!currentApiProvider) return;
    
    const apiKey = document.getElementById('api-key').value;
    const apiEndpoint = document.getElementById('api-endpoint').value;
    
    try {
        const result = await pywebview.api.set_provider_api_key(
            currentApiProvider.id,
            apiKey,
            apiEndpoint
        );
        
        if (result.success) {
            // 保存后自动启用当前服务商
            await pywebview.api.set_provider_enabled(currentApiProvider.id, true);
            showNotification('API配置已保存并启用', 'success');
            closeApiConfigModal();
            await loadApiProviders();
        } else {
            showNotification(result.message || '保存失败', 'error');
        }
    } catch (error) {
        showNotification('保存失败: ' + error.message, 'error');
    }
}

// 设置当前使用的API
async function setCurrentApi(providerId) {
    try {
        const result = await pywebview.api.set_current_provider(providerId);
        
        if (result.success) {
            showNotification('已切换API服务商', 'success');
            await loadApiProviders();
        } else {
            showNotification(result.message || '切换失败', 'error');
        }
    } catch (error) {
        showNotification('切换失败: ' + error.message, 'error');
    }
}

async function toggleProviderEnabled(providerId, enabled) {
    try {
        const result = await pywebview.api.set_provider_enabled(providerId, enabled);
        if (result.success) {
            showNotification(enabled ? '已启用，正在使用' : '已停用', 'success');
            await loadApiProviders();
        } else {
            showNotification(result.message || '切换失败', 'error');
            await loadApiProviders();
        }
    } catch (error) {
        showNotification('切换失败: ' + error.message, 'error');
        await loadApiProviders();
    }
}

// ==================== 导出题目功能 ====================
// 显示导出模态框
function showExportModal() {
    // 检查是否已选择课程和作业
    if (!currentCourseId || !currentWorkId) {
        showNotification('请先在AI答题页面选择课程和作业', 'error');
        return;
    }
    document.getElementById('export-modal').classList.add('active');
}

// 关闭导出模态框
function closeExportModal() {
    document.getElementById('export-modal').classList.remove('active');
}

// 导出题目
async function exportQuestions() {
    const format = document.getElementById('export-format').value;
    const filename = document.getElementById('export-filename').value || null;
    
    // 检查是否已选择课程和作业
    if (!currentCourseId || !currentWorkId) {
        showNotification('请先在AI答题页面选择课程和作业', 'error');
        return;
    }
    
    showNotification(`正在从服务器获取题目...`, 'info');
    
    try {
        // 从服务器获取题目数据
        const result = await pywebview.api.export_questions_from_server(
            currentCourseId, 
            currentWorkId, 
            format, 
            filename
        );
        
        if (result.success) {
            showNotification(`导出成功！文件已保存到: ${result.filepath}`, 'success');
            closeExportModal();
        } else {
            showNotification(result.message || '导出失败', 'error');
        }
    } catch (error) {
        showNotification('导出失败: ' + error.message, 'error');
    }
}

// ==================== 初始化 ====================
// 页面加载时初始化答题状态
document.addEventListener('DOMContentLoaded', () => {
    updateAnswerStatus('idle');
});
