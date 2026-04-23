document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('orderForm');
    const textArea = document.getElementById('textContent');
    const wordFileInput = document.getElementById('wordFileInput');
    const wordCountSpan = document.getElementById('wordCountDisplay');
    const priceSpan = document.getElementById('pricePreview');
    const deadlineSelect = document.getElementById('deadlineSelect');
    const paperCountInput = document.getElementById('paperCountInput');
    const submitBtn = document.getElementById('submitBtn');
    const modal = document.getElementById('successModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const accountListDiv = document.getElementById('accountList');

    // AI 元素
    const aiToggle = document.getElementById('aiToggleBtn');
    const aiPanel = document.getElementById('aiChatPanel');
    const aiClose = document.getElementById('aiCloseBtn');
    const aiSend = document.getElementById('aiSendBtn');
    const aiInput = document.getElementById('aiInput');
    const chatMessages = document.getElementById('chatMessages');

    function countWords(str) {
        const matches = str.match(/[^\s]/g);
        return matches ? matches.length : 0;
    }

    function calculateAmount(wordCount, deadline, paperCount) {
        const writingFee = wordCount / 333;
        let urgency = 1.0;
        if (deadline === '1天内') urgency = 2.5;
        else if (deadline === '3天内') urgency = 1.25;
        let paperFee = (paperCount && paperCount > 0) ? paperCount * 0.5 : wordCount / 2000;
        return writingFee * urgency + paperFee;
    }

    function updateStats() {
        const text = textArea.value;
        const wordCount = countWords(text);
        wordCountSpan.textContent = wordCount;
        const deadline = deadlineSelect.value;
        const paperCount = paperCountInput.value ? parseInt(paperCountInput.value) : 0;
        const amount = calculateAmount(wordCount, deadline, paperCount);
        priceSpan.textContent = `¥${amount.toFixed(2)}`;
    }

    textArea.addEventListener('input', updateStats);
    deadlineSelect.addEventListener('change', updateStats);
    paperCountInput.addEventListener('input', updateStats);

    wordFileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('word_file', file);
        submitBtn.disabled = true;
        submitBtn.textContent = '提取中...';
        fetch('/api/extract-word', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.text) {
                textArea.value = data.text;
                updateStats();
            } else {
                alert('提取失败：' + (data.error || '未知错误'));
            }
        })
        .catch(err => alert('请求出错：' + err))
        .finally(() => {
            submitBtn.disabled = false;
            submitBtn.textContent = '提交订单';
        });
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(form);
        submitBtn.disabled = true;
        submitBtn.textContent = '提交中...';

        fetch('/api/submit', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                let html = '';
                data.accounts.forEach(acc => {
                    html += `<div class="flex justify-between items-center py-1 border-b border-stone-200 last:border-0">
                        <span class="text-stone-600 text-sm">${acc.label}</span>
                        <span class="font-medium text-stone-800 cursor-pointer hover:text-emerald-600 transition" onclick="navigator.clipboard.writeText('${acc.value}').then(()=>alert('已复制：${acc.value}'))">${acc.value}</span>
                    </div>`;
                });
                accountListDiv.innerHTML = html;
                modal.classList.remove('hidden');
                form.reset();
                updateStats();
            } else {
                alert('提交失败：' + (data.error || '未知错误'));
            }
        })
        .catch(err => alert('请求出错：' + err))
        .finally(() => {
            submitBtn.disabled = false;
            submitBtn.textContent = '提交订单';
        });
    });

    closeModalBtn.addEventListener('click', () => modal.classList.add('hidden'));

    // AI 交互
    aiToggle.addEventListener('click', () => aiPanel.classList.toggle('hidden'));
    aiClose.addEventListener('click', () => aiPanel.classList.add('hidden'));

    function addAIMessage(content, isUser = false) {
        const div = document.createElement('div');
        div.className = isUser ? 'bg-blue-50 p-2 rounded-lg text-stone-700' : 'bg-emerald-50 p-2 rounded-lg text-stone-600';
        div.textContent = content;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    aiSend.addEventListener('click', function() {
        const prompt = aiInput.value.trim();
        if (!prompt) return;
        addAIMessage(prompt, true);
        aiInput.value = '';
        addAIMessage('思考中...');
        fetch('/api/ai/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt: prompt})
        })
        .then(res => res.json())
        .then(data => {
            chatMessages.removeChild(chatMessages.lastChild);
            if (data.reply) {
                addAIMessage(data.reply);
            } else {
                addAIMessage('AI 暂时无法回应：' + (data.error || ''));
            }
        })
        .catch(err => {
            chatMessages.removeChild(chatMessages.lastChild);
            addAIMessage('请求失败：' + err);
        });
    });

    aiInput.addEventListener('keypress', (e) => { if(e.key === 'Enter') aiSend.click(); });

    updateStats();
});