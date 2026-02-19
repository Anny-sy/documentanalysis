// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
    });
});

// Helper functions
function showLoading(id) {
    document.getElementById(id).classList.remove('hidden');
}

function hideLoading(id) {
    document.getElementById(id).classList.add('hidden');
}

function formatMarkdown(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

// Query functionality
document.getElementById('query-btn').addEventListener('click', async () => {
    const question = document.getElementById('question-input').value.trim();
    if (!question) return;

    showLoading('query-loading');
    document.getElementById('query-result').classList.add('hidden');

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        document.getElementById('answer-content').innerHTML = formatMarkdown(data.answer);
        document.getElementById('token-stats').textContent = 
            `${data.token_stats.original} → ${data.token_stats.compressed} tokens (${data.token_stats.savings_percent.toFixed(1)}% saved)`;

        const sourcesList = document.getElementById('sources-list');
        sourcesList.innerHTML = '';
        data.sources.slice(0, 5).forEach(source => {
            const meta = source.metadata || {};
            const li = document.createElement('li');
            li.textContent = `${meta.case_name || 'Unknown'}${meta.section ? ' - ' + meta.section : ''}`;
            sourcesList.appendChild(li);
        });

        document.getElementById('query-result').classList.remove('hidden');
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        hideLoading('query-loading');
    }
});

// Upload functionality
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');

uploadArea.addEventListener('click', () => fileInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--primary)';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = 'var(--border)';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--border)';
    const files = e.dataTransfer.files;
    if (files.length) handleUpload(files[0]);
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleUpload(e.target.files[0]);
});

async function handleUpload(file) {
    showLoading('upload-loading');
    document.getElementById('upload-result').classList.add('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        const resultDiv = document.getElementById('upload-result');

        if (data.success) {
            resultDiv.innerHTML = `
                <div class="success-message">
                    <strong>Upload Successful!</strong><br>
                    File: ${data.filename}<br>
                    Case: ${data.case_name || 'Unknown'}<br>
                    Chunks created: ${data.chunks_created}
                </div>
            `;
        } else {
            resultDiv.innerHTML = `<div class="error-message">Upload failed</div>`;
        }
        resultDiv.classList.remove('hidden');
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        hideLoading('upload-loading');
    }
}

// Analyze case functionality
document.getElementById('analyze-btn').addEventListener('click', async () => {
    const caseName = document.getElementById('case-name-input').value.trim();
    if (!caseName) return;

    showLoading('analyze-loading');
    document.getElementById('analyze-result').classList.add('hidden');

    try {
        const formData = new FormData();
        formData.append('case_name', caseName);

        const response = await fetch('/api/analyze-case', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        document.getElementById('analyze-answer').innerHTML = formatMarkdown(data.answer);
        document.getElementById('analyze-token-stats').textContent = 
            `${data.token_stats.original} → ${data.token_stats.compressed} tokens (${data.token_stats.savings_percent.toFixed(1)}% saved)`;

        document.getElementById('analyze-result').classList.remove('hidden');
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        hideLoading('analyze-loading');
    }
});

// Compare cases functionality
document.getElementById('compare-btn').addEventListener('click', async () => {
    const case1 = document.getElementById('case1-input').value.trim();
    const case2 = document.getElementById('case2-input').value.trim();
    if (!case1 || !case2) return;

    showLoading('compare-loading');
    document.getElementById('compare-result').classList.add('hidden');

    try {
        const formData = new FormData();
        formData.append('case1', case1);
        formData.append('case2', case2);

        const response = await fetch('/api/compare-cases', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        document.getElementById('compare-answer').innerHTML = formatMarkdown(data.answer);
        document.getElementById('compare-token-stats').textContent = 
            `${data.token_stats.original} → ${data.token_stats.compressed} tokens (${data.token_stats.savings_percent.toFixed(1)}% saved)`;

        document.getElementById('compare-result').classList.remove('hidden');
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        hideLoading('compare-loading');
    }
});

// Stats functionality
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        document.getElementById('stat-name').textContent = data.collection_name || '-';
        document.getElementById('stat-count').textContent = data.document_count || '0';
        document.getElementById('stat-path').textContent = data.persist_directory || '-';
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

document.getElementById('refresh-stats').addEventListener('click', loadStats);

// Load stats on page load and when stats tab is clicked
document.querySelector('[data-tab="stats"]').addEventListener('click', loadStats);
loadStats();
