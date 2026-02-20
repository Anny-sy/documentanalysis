// API Base URL (change this if deploying to a different server)
const API_BASE_URL = '';

// Helper functions
function showLoading(id) {
    document.getElementById(id).classList.remove('hidden');
}

function hideLoading(id) {
    document.getElementById(id).classList.add('hidden');
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    element.innerHTML = `<div class="error-message"><strong>Error:</strong> ${message}</div>`;
    element.classList.remove('hidden');
}

function formatMarkdown(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
    });
});

// Query functionality
document.getElementById('query-btn').addEventListener('click', async () => {
    const question = document.getElementById('question-input').value.trim();
    if (!question) {
        alert('Please enter a question');
        return;
    }

    showLoading('query-loading');
    document.getElementById('query-result').classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE_URL}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        document.getElementById('answer-content').innerHTML = formatMarkdown(data.answer);
        document.getElementById('token-stats').textContent = 
            `${data.token_stats.original} → ${data.token_stats.compressed} tokens (${data.token_stats.savings_percent.toFixed(1)}% saved)`;

        const sourcesList = document.getElementById('sources-list');
        sourcesList.innerHTML = '';
        if (data.sources && data.sources.length > 0) {
            data.sources.slice(0, 5).forEach(source => {
                const meta = source.metadata || {};
                const li = document.createElement('li');
                li.textContent = `${meta.case_name || 'Unknown'}${meta.section ? ' - ' + meta.section : ''}`;
                sourcesList.appendChild(li);
            });
        } else {
            sourcesList.innerHTML = '<li>No sources found</li>';
        }

        document.getElementById('query-result').classList.remove('hidden');
    } catch (error) {
        console.error('Query error:', error);
        showError('query-result', error.message || 'Failed to get answer. Please try again.');
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
        const response = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Upload failed: ${response.status}`);
        }

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
        console.error('Upload error:', error);
        showError('upload-result', error.message || 'Failed to upload file. Please try again.');
    } finally {
        hideLoading('upload-loading');
    }
}

// Analyze case functionality
document.getElementById('analyze-btn').addEventListener('click', async () => {
    const caseName = document.getElementById('case-name-input').value.trim();
    if (!caseName) {
        alert('Please enter a case name');
        return;
    }

    showLoading('analyze-loading');
    document.getElementById('analyze-result').classList.add('hidden');

    try {
        const formData = new FormData();
        formData.append('case_name', caseName);

        const response = await fetch(`${API_BASE_URL}/api/analyze-case`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        document.getElementById('analyze-answer').innerHTML = formatMarkdown(data.answer);
        document.getElementById('analyze-token-stats').textContent = 
            `${data.token_stats.original} → ${data.token_stats.compressed} tokens (${data.token_stats.savings_percent.toFixed(1)}% saved)`;

        document.getElementById('analyze-result').classList.remove('hidden');
    } catch (error) {
        console.error('Analyze error:', error);
        showError('analyze-result', error.message || 'Failed to analyze case. Please try again.');
    } finally {
        hideLoading('analyze-loading');
    }
});

// Compare cases functionality
document.getElementById('compare-btn').addEventListener('click', async () => {
    const case1 = document.getElementById('case1-input').value.trim();
    const case2 = document.getElementById('case2-input').value.trim();
    if (!case1 || !case2) {
        alert('Please enter both case names');
        return;
    }

    showLoading('compare-loading');
    document.getElementById('compare-result').classList.add('hidden');

    try {
        const formData = new FormData();
        formData.append('case1', case1);
        formData.append('case2', case2);

        const response = await fetch(`${API_BASE_URL}/api/compare-cases`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        document.getElementById('compare-answer').innerHTML = formatMarkdown(data.answer);
        document.getElementById('compare-token-stats').textContent = 
            `${data.token_stats.original} → ${data.token_stats.compressed} tokens (${data.token_stats.savings_percent.toFixed(1)}% saved)`;

        document.getElementById('compare-result').classList.remove('hidden');
    } catch (error) {
        console.error('Compare error:', error);
        showError('compare-result', error.message || 'Failed to compare cases. Please try again.');
    } finally {
        hideLoading('compare-loading');
    }
});

// Stats functionality
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();

        document.getElementById('stat-name').textContent = data.collection_name || '-';
        document.getElementById('stat-count').textContent = data.document_count || '0';
        document.getElementById('stat-path').textContent = data.persist_directory || '-';
    } catch (error) {
        console.error('Failed to load stats:', error);
        document.getElementById('stat-name').textContent = 'Error loading';
        document.getElementById('stat-count').textContent = '-';
        document.getElementById('stat-path').textContent = '-';
    }
}

document.getElementById('refresh-stats').addEventListener('click', loadStats);

// Load stats on page load and when stats tab is clicked
document.querySelector('[data-tab="stats"]').addEventListener('click', loadStats);
loadStats();
