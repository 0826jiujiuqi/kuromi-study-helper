function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function request(url, options = {}) {
    return fetch(url, options)
        .then(res => {
            if (!res.ok) {
                return res.json().catch(() => {
                    throw new Error('HTTP ' + res.status + ' 错误');
                }).then(data => {
                    throw new Error(data.message || '请求失败: HTTP ' + res.status);
                });
            }
            return res.json();
        });
}

function loadPlan() {
    request('/api/plan')
        .then(data => {
            if (data.status === 'success') {
                document.getElementById('plan-content').innerText = data.plan_text;
            } else {
                document.getElementById('plan-content').innerText = '加载计划失败: ' + data.message;
            }
        })
        .catch(err => document.getElementById('plan-content').innerText = '请求失败: ' + err.message);
}

document.getElementById('btn-sleep').addEventListener('click', function() {
    const btn = this;
    if (btn.disabled) return;
    const bed_time = document.getElementById('bed-time').value.trim();
    const nap_start = document.getElementById('nap-start').value.trim();
    const nap_duration = document.getElementById('nap-duration').value.trim();
    if (!bed_time || !nap_start || !nap_duration) {
        alert('请完整填写睡眠信息');
        return;
    }
    btn.disabled = true;
    request('/api/sleep', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({bed_time, nap_start, nap_duration: parseInt(nap_duration)})
    })
    .then(data => {
        alert(data.message);
        document.getElementById('wake-recommend').innerText = '⏰ 起床: ' + data.wake_recommend;
        document.getElementById('nap-recommend').innerText = '🌙 午休起: ' + data.nap_end_recommend;
        loadPlan();
    })
    .catch(err => alert('提交失败: ' + err.message))
    .finally(() => btn.disabled = false);
});



document.getElementById('btn-mark-complete').addEventListener('click', function() {
    const btn = this;
    if (btn.disabled) return;
    btn.disabled = true;
    request('/api/mark_complete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({rate: 1.0})
    })
    .then(data => {
        alert(data.message);
        loadPlan();
    })
    .catch(err => alert('操作失败: ' + err.message))
    .finally(() => btn.disabled = false);
});

document.getElementById('btn-sleep').addEventListener('click', function() {
    const btn = this;
    if (btn.disabled) return;
    const bed_time = document.getElementById('bed-time').value.trim();
    const wake_time = document.getElementById('wake-time').value.trim();
    const nap_duration = document.getElementById('nap-duration').value.trim();
    if (!bed_time || !wake_time || !nap_duration) {
        alert('请完整填写睡眠信息');
        return;
    }
    btn.disabled = true;
    request('/api/sleep', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({bed_time, wake_time, nap_duration: parseInt(nap_duration)})
    })
    .then(data => {
        alert(data.message);
        loadPlan();
    })
    .catch(err => alert('提交失败: ' + err.message))
    .finally(() => btn.disabled = false);
});

document.getElementById('btn-state').addEventListener('click', function() {
    const state = document.getElementById('state-input').value.trim();
    if (!state) return;
    request('/api/state', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({state})
    })
    .then(data => {
        document.getElementById('state-feedback').innerText = '建议：' + (data.advice || '');
        loadPlan();
    })
    .catch(err => document.getElementById('state-feedback').innerText = '提交失败: ' + err.message);
});

document.getElementById('btn-add-task').addEventListener('click', function() {
    const btn = this;
    if (btn.disabled) return;
    const subject = document.getElementById('task-subject').value.trim();
    const phase = document.getElementById('task-phase').value.trim();
    const desc = document.getElementById('task-desc').value.trim();
    const plan_date = document.getElementById('task-date').value;
    if (!subject || !phase || !desc || !plan_date) {
        alert('请完整填写任务信息');
        return;
    }
    btn.disabled = true;
    request('/api/task', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({subject, phase, description: desc, plan_date})
    })
    .then(data => {
        alert(data.message);
        loadTasks();
        loadPlan();
        document.getElementById('task-subject').value = '';
        document.getElementById('task-phase').value = '';
        document.getElementById('task-desc').value = '';
        document.getElementById('task-date').value = '';
    })
    .catch(err => alert('添加失败: ' + err.message))
    .finally(() => btn.disabled = false);
});

function loadTasks() {
    request('/api/tasks')
        .then(tasks => {
            let html = '<ul class="list-group">';
            tasks.forEach(t => {
                html += `<li class="list-group-item d-flex justify-content-between align-items-center task-item-kuromi">
                    <span class="task-info">${escapeHtml(t.subject)} - ${escapeHtml(t.description)} (${escapeHtml(t.plan_date)}) [${escapeHtml(t.status)}]</span>
                    <span>
                        ${t.status !== '已完成' ? `<button class="btn btn-sm btn-success" onclick="completeTask(${t.id})">完成</button>` : ''}
                        <button class="btn btn-sm btn-danger" onclick="deleteTask(${t.id})">删除</button>
                    </span>
                </li>`;
            });
            html += '</ul>';
            document.getElementById('task-list').innerHTML = html;
        })
        .catch(err => document.getElementById('task-list').innerText = '加载失败: ' + err.message);
}

window.completeTask = function(id) {
    request(`/api/task/${id}/complete`, {method: 'POST'})
        .then(() => loadTasks())
        .catch(err => alert('操作失败: ' + err.message));
};
window.deleteTask = function(id) {
    if (!confirm('确认删除该任务？')) return;
    request(`/api/task/${id}`, {method: 'DELETE'})
        .then(() => loadTasks())
        .catch(err => alert('删除失败: ' + err.message));
};

document.getElementById('btn-import-doc').addEventListener('click', function() {
    const btn = this;
    if (btn.disabled) return;
    const fileInput = document.getElementById('file-input');
    if (fileInput.files.length === 0) {
        alert('请选择一个文件');
        return;
    }
    btn.disabled = true;
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    request('/api/import_document', {
        method: 'POST',
        body: formData
    })
    .then(data => {
        document.getElementById('import-feedback').innerText = data.message;
        loadPlan();
    })
    .catch(err => document.getElementById('import-feedback').innerText = '导入失败: ' + err.message)
    .finally(() => btn.disabled = false);
});

document.getElementById('btn-import-kp').addEventListener('click', function() {
    const btn = this;
    if (btn.disabled) return;
    const fileInput = document.getElementById('file-input');
    if (fileInput.files.length === 0) {
        alert('请选择一个文件');
        return;
    }
    btn.disabled = true;
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('replace', 'true');
    request('/api/import_knowledge', {
        method: 'POST',
        body: formData
    })
    .then(data => {
        document.getElementById('import-feedback').innerText = data.message;
        loadPlan();
    })
    .catch(err => document.getElementById('import-feedback').innerText = '导入失败: ' + err.message)
    .finally(() => btn.disabled = false);
});

document.getElementById('btn-history').addEventListener('click', function() {
    const oldModal = document.getElementById('historyModal');
    if (oldModal) {
        const modalInstance = bootstrap.Modal.getInstance(oldModal);
        if (modalInstance) modalInstance.dispose();
        oldModal.remove();
    }
    request('/api/history')
        .then(events => {
            let html = '<div class="modal fade" id="historyModal" tabindex="-1"><div class="modal-dialog modal-dialog-scrollable"><div class="modal-content"><div class="modal-header"><h5>历史记录</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><ul class="list-group">';
            events.forEach(e => {
                html += `<li class="list-group-item d-flex justify-content-between">
                    <span>${escapeHtml(e.date)} ${escapeHtml(e.subject)} ${escapeHtml(e.topic)} ${escapeHtml(e.activity)} ${escapeHtml(e.duration)}分</span>
                    <button class="btn btn-sm btn-danger" onclick="deleteEvent(${e.id})">删除</button>
                </li>`;
            });
            html += '</ul></div></div></div></div>';
            document.body.insertAdjacentHTML('beforeend', html);
            const myModal = new bootstrap.Modal(document.getElementById('historyModal'));
            myModal.show();
        })
        .catch(err => alert('加载历史失败: ' + err.message));
});

window.deleteEvent = function(id) {
    if (!confirm('确认删除该条记录？')) return;
    request(`/api/event/${id}`, {method: 'DELETE'})
        .then(() => {
            const modalEl = document.getElementById('historyModal');
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            if (modalInstance) modalInstance.hide();
            loadPlan();
        })
        .catch(err => alert('删除失败: ' + err.message));
};

document.getElementById('btn-train').addEventListener('click', function() {
    const btn = this;
    if (btn.disabled) return;
    btn.disabled = true;
    request('/api/train', {method: 'POST'})
        .then(data => alert(data.message))
        .catch(err => alert('操作失败: ' + err.message))
        .finally(() => btn.disabled = false);
});

document.getElementById('btn-clear').addEventListener('click', function() {
    if (!confirm('确定要清空所有数据吗？')) return;
    request('/api/clear_all', {method: 'POST'})
        .then(data => alert(data.message))
        .catch(err => alert('操作失败: ' + err.message));
});

document.getElementById('btn-update-plan').addEventListener('click', loadPlan);
document.getElementById('btn-report').addEventListener('click', loadPlan);

loadPlan();
loadTasks();
