document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-input');
    const resultsGrid = document.getElementById('results-grid');
    const loading = document.getElementById('loading');
    const statusMessage = document.getElementById('status-message');
    const universityFilter = document.getElementById('university-filter');
    const courseFilter = document.getElementById('course-filter');
    const typeFilter = document.getElementById('type-filter');

    let debounceTimer;

    // Load metadata on start
    loadMetadata();

    // Search input listener
    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();
        
        if (query.length < 2 && !universityFilter.value && !typeFilter.value) {
            resultsGrid.innerHTML = '';
            if (query.length === 0) {
                // Show empty state or recent
                resultsGrid.innerHTML = '<div class="card" style="text-align: center; grid-column: 1/-1;"><p style="color: var(--text-secondary);">Type to start searching your PDF database...</p></div>';
            }
            return;
        }

        debounceTimer = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    // Filter listeners
    [typeFilter].forEach(filter => {
        filter.addEventListener('change', () => {
            const query = searchInput.value.trim();
            if (query.length >= 2 || universityFilter.value || typeFilter.value) {
                performSearch(query);
            } else {
                resultsGrid.innerHTML = '<div class="card" style="text-align: center; grid-column: 1/-1;"><p style="color: var(--text-secondary);">Type to start searching your PDF database...</p></div>';
            }
        });
    });
    
    universityFilter.addEventListener('change', () => {
        if (universityFilter.value) {
            loadCourses(universityFilter.value);
        } else {
            courseFilter.innerHTML = '<option value="">All Courses</option>';
            courseFilter.disabled = true;
        }
        
        const query = searchInput.value.trim();
        if (query.length >= 2 || universityFilter.value || typeFilter.value) {
            performSearch(query);
        } else {
            resultsGrid.innerHTML = '<div class="card" style="text-align: center; grid-column: 1/-1;"><p style="color: var(--text-secondary);">Type to start searching your PDF database...</p></div>';
        }
    });

    courseFilter.addEventListener('change', async () => {
        if (!courseFilter.value) return;
        
        // Find course details
        const selectedOption = courseFilter.options[courseFilter.selectedIndex];
        const courseData = {
            title: selectedOption.textContent,
            filename: courseFilter.value,
            university: universityFilter.value,
            snippet: selectedOption.dataset.snippet
        };
        
        openModal(courseData);
        // Reset the dropdown so it can be clicked again
        courseFilter.value = '';
    });

    // Auto-sync on page load
    async function autoSync() {
        try {
            console.log('Starting auto-sync...');
            const response = await fetch('/api/parse', {
                method: 'POST'
            });
            const data = await response.json();
            if (data.success) {
                console.log('Sync started in background.');
                // Refresh metadata once sync starts
                setTimeout(loadMetadata, 2000);
            }
        } catch (error) {
            console.error('Auto-sync failed:', error);
        }
    }
    
    autoSync();

    async function performSearch(query) {
        try {
            loading.classList.remove('hidden');
            resultsGrid.innerHTML = '';
            
            const u = encodeURIComponent(universityFilter.value);
            const t = encodeURIComponent(typeFilter.value);
            const q = encodeURIComponent(query);
            
            const response = await fetch(`/api/search?q=${q}&university=${u}&doc_type=${t}`);
            const results = await response.json();
            
            loading.classList.add('hidden');
            
            if (results.length === 0) {
                resultsGrid.innerHTML = `
                    <div class="card" style="text-align: center; grid-column: 1/-1;">
                        <i class="fas fa-search" style="font-size: 3rem; color: var(--text-secondary); margin-bottom: 1rem; opacity: 0.5;"></i>
                        <h3 class="card-title">No results found</h3>
                        <p style="color: var(--text-secondary); margin-top: 0.5rem;">Try adjusting your search terms or sync new PDFs.</p>
                    </div>
                `;
                return;
            }
            
            renderResults(results, query);
            
        } catch (error) {
            loading.classList.add('hidden');
            resultsGrid.innerHTML = `
                <div class="card" style="text-align: center; grid-column: 1/-1; border-color: rgba(239, 68, 68, 0.3);">
                    <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #f87171; margin-bottom: 1rem; opacity: 0.8;"></i>
                    <h3 class="card-title" style="color: #f87171;">Connection Error</h3>
                    <p style="color: var(--text-secondary); margin-top: 0.5rem;">Could not connect to the search engine server. Is it running?</p>
                </div>
            `;
        }
    }

    function renderResults(results, query) {
        resultsGrid.innerHTML = '';
        
        results.forEach(result => {
            const card = document.createElement('div');
            card.className = 'card';
            
            // Highlight search terms in snippet
            let snippet = result.snippet || '';
            if (query) {
                const regex = new RegExp(`(${query.replace(/[.*+?^$\/{}()|[\\]\\\\]/g, '\\\\$&')})`, 'gi');
                snippet = snippet.replace(regex, '<mark>$1</mark>');
            }
            
            // Format snippet to look cleaner (remove excessive newlines)
            snippet = snippet.replace(/\\n+/g, ' ').substring(0, 200) + '...';
            
            card.innerHTML = `
                <div class="card-header">
                    <div class="card-icon">
                        <i class="fas fa-file-pdf"></i>
                    </div>
                    <div>
                        <div class="card-tags">
                            ${result.university && result.university !== 'Uncategorized' ? `<span class="tag tag-university"><i class="fas fa-university"></i> ${escapeHtml(result.university)}</span>` : ''}
                            ${result.doc_type && result.doc_type !== 'Other' ? `<span class="tag tag-doctype"><i class="fas fa-tag"></i> ${escapeHtml(result.doc_type)}</span>` : ''}
                        </div>
                        <h3 class="card-title">${escapeHtml(result.title)}</h3>
                        <div class="card-filename">
                            <i class="fas fa-file-alt"></i> ${escapeHtml(result.filename)}
                        </div>
                    </div>
                </div>
                
                <div class="card-snippet">
                    ${snippet}
                </div>
                
                <div class="card-footer">
                    <span style="font-size: 0.875rem; color: var(--text-secondary);">
                        <i class="fas fa-database"></i> Database Match
                    </span>
                    <button class="btn-secondary" onclick="window.open('/pdfs/${result.filename.split('/').map(encodeURIComponent).join('/')}', '_blank')">
                        View Document
                    </button>
                </div>
            `;
            
            resultsGrid.appendChild(card);
        });
    }

    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = type === 'error' ? 'error' : '';
        statusMessage.classList.remove('hidden');
        
        setTimeout(() => {
            statusMessage.classList.add('hidden');
        }, 5000);
    }
    
    function escapeHtml(unsafe) {
        return (unsafe || '').toString()
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }
    
    async function loadMetadata() {
        try {
            const response = await fetch('/api/metadata');
            const data = await response.json();
            
            // Clear existing options except the first "All..." option
            universityFilter.innerHTML = '<option value="">All Universities</option>';
            typeFilter.innerHTML = '<option value="">All Document Types</option>';
            
            data.universities.forEach(u => {
                const option = document.createElement('option');
                option.value = u;
                option.textContent = u;
                universityFilter.appendChild(option);
            });
            
            data.doc_types.forEach(d => {
                const option = document.createElement('option');
                option.value = d;
                option.textContent = d;
                typeFilter.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load metadata', error);
        }
    }
    
    // Modal Logic
    const modal = document.getElementById('course-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const modalOverlay = document.querySelector('.modal-overlay');
    
    closeModalBtn.addEventListener('click', () => modal.classList.add('hidden'));
    modalOverlay.addEventListener('click', () => modal.classList.add('hidden'));
    
    async function openModal(course) {
        document.getElementById('modal-title').textContent = course.title;
        document.getElementById('modal-university').innerHTML = `<i class="fas fa-university"></i> ${escapeHtml(course.university)}`;
        document.getElementById('modal-snippet').innerHTML = course.snippet || 'No description available.';
        
        const viewBtn = document.getElementById('modal-view-brochure');
        viewBtn.onclick = () => window.open('/pdfs/' + course.filename.split('/').map(encodeURIComponent).join('/'), '_blank');
        
        // Fetch fees
        const feesContainer = document.getElementById('modal-fees-container');
        feesContainer.innerHTML = '<div class="spinner"></div>';
        modal.classList.remove('hidden');
        
        try {
            const response = await fetch(`/api/fees/${encodeURIComponent(course.university)}`);
            const fees = await response.json();
            
            feesContainer.innerHTML = '';
            if (fees.length === 0) {
                feesContainer.innerHTML = '<p class="fees-description">No specific fee structures found for this university.</p>';
            } else {
                fees.forEach(fee => {
                    const card = document.createElement('div');
                    card.className = 'fee-card';
                    card.innerHTML = `
                        <div class="fee-title"><i class="fas fa-file-invoice-dollar"></i> ${escapeHtml(fee.title)}</div>
                        <button class="btn-fee" onclick="window.open('/pdfs/${fee.filename.split('/').map(encodeURIComponent).join('/')}', '_blank')">View</button>
                    `;
                    feesContainer.appendChild(card);
                });
            }
        } catch (error) {
            feesContainer.innerHTML = '<p class="fees-description" style="color: #ef4444;">Failed to load fees.</p>';
        }
    }
    
    async function loadCourses(university) {
        try {
            courseFilter.disabled = true;
            courseFilter.innerHTML = '<option value="">Loading courses...</option>';
            
            const response = await fetch(`/api/courses/${encodeURIComponent(university)}`);
            const courses = await response.json();
            
            courseFilter.innerHTML = '<option value="">All Courses</option>';
            
            if (courses.length > 0) {
                courseFilter.disabled = false;
                courses.forEach(c => {
                    const option = document.createElement('option');
                    option.value = c.filename;
                    option.textContent = c.title;
                    option.dataset.snippet = c.snippet;
                    courseFilter.appendChild(option);
                });
            }
        } catch (error) {
            console.error("Failed to load courses", error);
            courseFilter.innerHTML = '<option value="">All Courses</option>';
        }
    }
    
    // Initial empty state
    resultsGrid.innerHTML = '<div class="card" style="text-align: center; grid-column: 1/-1;"><p style="color: var(--text-secondary);">Type to start searching your PDF database...</p></div>';
});
