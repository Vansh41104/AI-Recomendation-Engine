async function searchRecommendations() {
    const queryInput = document.getElementById('queryInput');
    const searchBtn = document.getElementById('searchBtn');
    const errorMessage = document.getElementById('errorMessage');
    const resultsSection = document.getElementById('resultsSection');
    const loadingSection = document.getElementById('loadingSection');
    const emptyState = document.getElementById('emptyState');
    
    const query = queryInput.value.trim();
    
    if (query.length < 3) {
        showError('Please enter at least 3 characters to search.');
        return;
    }
    
    errorMessage.style.display = 'none';
    resultsSection.style.display = 'none';
    emptyState.style.display = 'none';
    loadingSection.style.display = 'block';
    
    searchBtn.disabled = true;
    searchBtn.querySelector('.btn-text').textContent = 'Searching...';
    
    try {
        const response = await fetch('/api/recommend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch recommendations');
        }
        
        const data = await response.json();
        
        loadingSection.style.display = 'none';
        displayResults(data.recommended_assessments);
        addToHistory(query);
        
    } catch (error) {
        loadingSection.style.display = 'none';
        emptyState.style.display = 'block';
        showError(`Error: ${error.message}`);
    } finally {
        searchBtn.disabled = false;
        searchBtn.querySelector('.btn-text').textContent = 'Get Recommendations';
    }
}

function displayResults(assessments) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsContainer = document.getElementById('resultsContainer');
    
    if (!assessments || assessments.length === 0) {
        resultsContainer.innerHTML = '<p>No recommendations found. Try adjusting your search query.</p>';
        resultsSection.style.display = 'block';
        return;
    }
    
    resultsContainer.innerHTML = assessments.map((assessment, index) => `
        <div class="assessment-card">
            <div class="assessment-header">
                <div class="assessment-name">${escapeHtml(assessment.name)}</div>
                <div class="assessment-number">#${index + 1}</div>
            </div>
            
            <div class="assessment-description">
                ${escapeHtml(assessment.description)}
            </div>
            
            <div class="assessment-details">
                <div class="detail-item">
                    <span class="icon">⏱️</span>
                    <div>
                        <div class="label">Duration</div>
                        <div class="value">${escapeHtml(assessment.duration)}</div>
                    </div>
                </div>
                
                <div class="detail-item">
                    <span class="icon">${assessment.adaptive_support === 'Yes' ? '✅' : '❌'}</span>
                    <div>
                        <div class="label">Adaptive</div>
                        <div class="value">${assessment.adaptive_support}</div>
                    </div>
                </div>
                
                <div class="detail-item">
                    <span class="icon">${assessment.remote_support === 'Yes' ? '🌐' : '🏢'}</span>
                    <div>
                        <div class="label">Remote</div>
                        <div class="value">${assessment.remote_support}</div>
                    </div>
                </div>
            </div>
            
            ${assessment.test_type && assessment.test_type.length > 0 ? `
            <div class="test-types">
                <div class="test-types-label">
                    <span>📋</span>
                    Test Types:
                </div>
                <div class="test-type-tags">
                    ${assessment.test_type.map(type => `
                        <span class="test-type-tag">${escapeHtml(type)}</span>
                    `).join('')}
                </div>
            </div>
            ` : ''}
            
            ${assessment.url ? `
                <a href="${escapeHtml(assessment.url)}" target="_blank" class="assessment-link">
                    View Assessment →
                </a>
            ` : ''}
        </div>
    `).join('');
    
    resultsSection.style.display = 'block';
}

function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function addToHistory(query) {
    const history = getHistory();
    const filtered = history.filter(q => q !== query);
    filtered.unshift(query);
    const updated = filtered.slice(0, 5);
    localStorage.setItem('queryHistory', JSON.stringify(updated));
    displayHistory();
}

function getHistory() {
    try {
        return JSON.parse(localStorage.getItem('queryHistory') || '[]');
    } catch {
        return [];
    }
}

function displayHistory() {
    const history = getHistory();
    const historySection = document.getElementById('queryHistory');
    const historyContainer = document.getElementById('historyContainer');
    
    if (history.length === 0) {
        historySection.style.display = 'none';
        return;
    }
    
    historyContainer.innerHTML = history.map(query => `
        <div class="history-item" onclick="loadQuery('${escapeHtml(query).replace(/'/g, "\\'")}')">
            ${escapeHtml(query)}
        </div>
    `).join('');
    
    historySection.style.display = 'block';
}

function loadQuery(query) {
    document.getElementById('queryInput').value = query;
    searchRecommendations();
}

document.getElementById('queryInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        searchRecommendations();
    }
});

window.addEventListener('load', function() {
    document.getElementById('queryInput').focus();
    displayHistory();
});
