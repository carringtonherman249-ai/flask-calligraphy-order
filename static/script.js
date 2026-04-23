document.addEventListener('DOMContentLoaded', function() {
    // 元素引用
    const form = document.getElementById('orderForm');
    const textArea = document.getElementById('textContent');
    const wordFileInput = document.getElementById('wordFileInput');
    const wordCountSpan = document.getElementById('wordCountDisplay');
    const priceSpan = document.getElementById('pricePreview');
    const deadlineSelect = document.getElementById('deadlineSelect');
    const paperCountInput = document.getElementById('paperCountInput');
    const submitBtn = document.getElementById('submitBtn');
    const modal = document.getElementById('successModal');
    const qrImage = document.getElementById('qrCodeImage');
    const closeModalBtn = document.getElementById('closeModalBtn');

    // AI 面板元素
    const aiToggle = document.getElementById('aiToggleBtn');
    const aiPanel = document.getElementById('aiChatPanel');
    const aiClose = document.getElementById('aiCloseBtn');
    const aiSend = document.getElementById('aiSendBtn');
    const aiInput = document.getElementById('aiInput');
    const chatMessages = document.getElementById('chatMessages');

    // 字数统计与金额计算
    function updateStats() {
        const text = textArea.value;
        const wordCount = countWords(text);
        wordCountSpan.textContent = wordCount;

        const deadline = deadlineSelect.value;
        const paperCount = paperCountInput.value ? parseInt(paperCountInput.value) : 0;
        const amount = calculateAmount(wordCount, deadline, paperCount);
        priceSpan.textContent = `¥${amount.toFixed(2)}`;
    }

    function countWords(str) {
        // 匹配非空白字符
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

    textArea.addEventListener('input', updateStats);
    deadlineSelect.addEventListener('change', updateStats);
    paperCountInput.addEventListener('input', updateStats);

    // Word 文件上传处理（提取文字）
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

    // 后端需要补充 Word 提取接口，稍后添加

    // 表单提交
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
                qrImage.src = 'data:image/png;base64,' + data.qr_code;
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

    // AI 助手交互
    aiToggle.addEventListener('click', () => aiPanel.classList.toggle('hidden'));
    aiClose.addEventListener('click', () => aiPanel.classList.add('hidden'));

    function addAIMessage(content, isUser = false) {
        const div = document.createElement('div');
        div.className = isUser ? 'bg-blue-50 p-2 rounded-lg text-stone-700 self-end' : 'bg-emerald-50 p-2 rounded-lg text-stone-600';
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

    // 初始化统计
    updateStats();
});