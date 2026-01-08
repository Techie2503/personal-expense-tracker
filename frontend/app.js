/**
 * Expense Tracker PWA - Main Application
 * Features: Offline-first with IndexedDB, Auto-sync, Charts
 */

// ==================== CONFIGURATION ====================
const API_BASE = window.location.origin + '/api';
const DB_NAME = 'ExpenseTrackerDB';
const DB_VERSION = 1;
const STORE_NAME = 'queuedExpenses';

// ==================== STATE ====================
let db = null;
let currentScreen = 'add';
let currentPage = 0;
let pageSize = 20;
let isOnline = navigator.onLine;
let c1Categories = [];
let c2Categories = [];
let charts = {};
let deferredPrompt = null;

// ==================== INDEXEDDB SETUP ====================
/**
 * Initialize IndexedDB for offline queue
 */
function initDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            db = request.result;
            console.log('IndexedDB initialized');
            resolve(db);
        };
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                const store = db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
                store.createIndex('timestamp', 'timestamp', { unique: false });
                console.log('IndexedDB object store created');
            }
        };
    });
}

/**
 * Add expense to offline queue
 */
function addToQueue(expense) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORE_NAME], 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.add({
            ...expense,
            timestamp: Date.now()
        });
        
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

/**
 * Get all queued expenses
 */
function getQueuedExpenses() {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORE_NAME], 'readonly');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.getAll();
        
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

/**
 * Remove expense from queue
 */
function removeFromQueue(id) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORE_NAME], 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.delete(id);
        
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

// ==================== API FUNCTIONS ====================
/**
 * Generic API fetch with error handling
 */
async function apiFetch(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ==================== SYNC FUNCTIONALITY ====================
/**
 * Sync queued expenses to server
 */
async function syncQueuedExpenses() {
    if (!isOnline) {
        console.log('Offline - cannot sync');
        return { success: false, message: 'Offline' };
    }
    
    try {
        const queued = await getQueuedExpenses();
        console.log(`Syncing ${queued.length} queued expenses...`);
        
        let synced = 0;
        let failed = 0;
        
        for (const item of queued) {
            try {
                // Remove the IndexedDB metadata
                const { id, timestamp, ...expense } = item;
                
                // Post to server
                await apiFetch('/expenses', {
                    method: 'POST',
                    body: JSON.stringify(expense)
                });
                
                // Remove from queue on success
                await removeFromQueue(id);
                synced++;
            } catch (error) {
                console.error('Failed to sync expense:', error);
                failed++;
            }
        }
        
        console.log(`Sync complete: ${synced} synced, ${failed} failed`);
        return { success: true, synced, failed };
    } catch (error) {
        console.error('Sync error:', error);
        return { success: false, message: error.message };
    }
}

/**
 * Auto-sync when coming online
 */
function setupAutoSync() {
    window.addEventListener('online', async () => {
        console.log('Connection restored - auto-syncing...');
        isOnline = true;
        updateOnlineStatus();
        await syncQueuedExpenses();
        await updateQueueStatus();
    });
    
    window.addEventListener('offline', () => {
        console.log('Connection lost');
        isOnline = false;
        updateOnlineStatus();
    });
}

// ==================== UI FUNCTIONS ====================
/**
 * Update online/offline status indicator
 */
function updateOnlineStatus() {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    if (isOnline) {
        indicator.classList.remove('offline');
        statusText.textContent = 'Online';
    } else {
        indicator.classList.add('offline');
        statusText.textContent = 'Offline';
    }
}

/**
 * Show status message
 */
function showStatus(elementId, message, type = 'success') {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `status-message ${type}`;
    element.style.display = 'block';
    
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

/**
 * Switch between screens
 */
function switchScreen(screenName) {
    // Hide all screens
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    
    // Remove active from all tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected screen
    document.getElementById(`${screenName}Screen`).classList.add('active');
    
    // Mark tab as active
    document.querySelector(`[data-screen="${screenName}"]`).classList.add('active');
    
    currentScreen = screenName;
    
    // Load screen data
    loadScreenData(screenName);
}

/**
 * Load data for the current screen
 */
async function loadScreenData(screenName) {
    switch (screenName) {
        case 'add':
            await loadCategories();
            break;
        case 'list':
            await loadExpenses();
            break;
        case 'insights':
            await loadInsights();
            break;
        case 'categories':
            await loadCategoriesManagement();
            break;
        case 'settings':
            await updateQueueStatus();
            break;
    }
}

// ==================== ADD EXPENSE SCREEN ====================
/**
 * Load categories for dropdowns
 */
async function loadCategories() {
    try {
        c1Categories = await apiFetch('/categories');
        
        const c1Select = document.getElementById('expenseC1');
        c1Select.innerHTML = '<option value="">Select category...</option>';
        
        c1Categories
            .filter(cat => cat.active)
            .forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.id;
                option.textContent = cat.name;
                c1Select.appendChild(option);
            });
    } catch (error) {
        console.error('Error loading categories:', error);
        showStatus('formStatus', 'Error loading categories. Using offline mode.', 'warning');
    }
}

/**
 * Load C2 subcategories when C1 is selected
 */
async function loadC2Categories(c1Id) {
    const c2Select = document.getElementById('expenseC2');
    const addC2Btn = document.getElementById('addC2Btn');
    
    if (!c1Id) {
        c2Select.innerHTML = '<option value="">Select C1 first...</option>';
        c2Select.disabled = true;
        addC2Btn.style.display = 'none';
        return;
    }
    
    try {
        c2Categories = await apiFetch(`/categories/${c1Id}/c2`);
        
        c2Select.innerHTML = '<option value="">Select subcategory...</option>';
        c2Categories
            .filter(cat => cat.active)
            .forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.id;
                option.textContent = cat.name;
                c2Select.appendChild(option);
            });
        
        c2Select.disabled = false;
        addC2Btn.style.display = 'block';
    } catch (error) {
        console.error('Error loading C2 categories:', error);
        c2Select.innerHTML = '<option value="">Error loading subcategories</option>';
    }
}

/**
 * Handle expense form submission
 */
async function handleExpenseSubmit(event) {
    event.preventDefault();
    
    // Get the datetime-local value and preserve it as local time
    const dateInput = document.getElementById('expenseDate').value;
    // datetime-local format: "2026-01-08T15:30"
    // We want to send this exact time to the server, not convert to UTC
    const localDate = new Date(dateInput);
    // Create ISO string but treat as local time (don't shift to UTC)
    const dateString = localDate.toISOString();
    
    const formData = {
        date: dateString,
        amount: parseFloat(document.getElementById('expenseAmount').value),
        c1_id: parseInt(document.getElementById('expenseC1').value),
        c2_id: parseInt(document.getElementById('expenseC2').value),
        payment_mode: document.getElementById('paymentMode').value,
        notes: document.getElementById('expenseNotes').value || null,
        person: document.getElementById('expensePerson').value || null,
        need_vs_want: document.getElementById('needVsWant').value || null
    };
    
    try {
        if (isOnline) {
            // Try to post to server
            await apiFetch('/expenses', {
                method: 'POST',
                body: JSON.stringify(formData)
            });
            showStatus('formStatus', '✅ Expense saved successfully!', 'success');
        } else {
            // Queue for later sync
            await addToQueue(formData);
            showStatus('formStatus', '📥 Saved offline. Will sync when online.', 'warning');
        }
        
        // Clear form
        document.getElementById('expenseForm').reset();
        setDefaultDateTime();
        
    } catch (error) {
        console.error('Error saving expense:', error);
        
        // If online save failed, queue it
        try {
            await addToQueue(formData);
            showStatus('formStatus', '⚠️ Saved offline. Server error.', 'warning');
        } catch (dbError) {
            showStatus('formStatus', '❌ Error: ' + error.message, 'error');
        }
    }
}

/**
 * Set default date/time to now
 */
function setDefaultDateTime() {
    const now = new Date();
    const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16);
    document.getElementById('expenseDate').value = localDateTime;
}

// ==================== EXPENSES LIST SCREEN ====================
/**
 * Load and display expenses
 */
async function loadExpenses() {
    const listContainer = document.getElementById('expensesList');
    listContainer.innerHTML = '<div class="loading">Loading expenses...</div>';
    
    try {
        const params = new URLSearchParams({
            limit: pageSize,
            offset: currentPage * pageSize
        });
        
        // Add date filters if set
        const startDate = document.getElementById('filterStartDate').value;
        const endDate = document.getElementById('filterEndDate').value;
        
        if (startDate) {
            params.append('start_date', new Date(startDate).toISOString());
        }
        if (endDate) {
            params.append('end_date', new Date(endDate).toISOString());
        }
        
        const data = await apiFetch(`/expenses?${params}`);
        
        // Get category names for display
        const c1Map = {};
        const c2Map = {};
        
        const allC1 = await apiFetch('/categories');
        allC1.forEach(cat => c1Map[cat.id] = cat.name);
        
        // Load all C2 for each C1
        for (const c1 of allC1) {
            const c2List = await apiFetch(`/categories/${c1.id}/c2`);
            c2List.forEach(cat => c2Map[cat.id] = cat.name);
        }
        
        if (data.expenses.length === 0) {
            listContainer.innerHTML = '<p class="loading">No expenses found.</p>';
            return;
        }
        
        listContainer.innerHTML = '';
        data.expenses.forEach(expense => {
            const item = document.createElement('div');
            item.className = 'expense-item';
            
            const date = new Date(expense.date).toLocaleString();
            
            item.innerHTML = `
                <div class="expense-header">
                    <div class="expense-amount">₹${expense.amount.toFixed(2)}</div>
                    <div class="expense-date">${date}</div>
                </div>
                <div class="expense-details">
                    <span class="expense-category">${c1Map[expense.c1_id] || 'Unknown'}</span>
                    <span class="expense-subcategory">${c2Map[expense.c2_id] || 'Unknown'}</span>
                </div>
                <div class="expense-details">
                    <strong>Payment:</strong> ${expense.payment_mode}
                    ${expense.person ? `<br><strong>Person:</strong> ${expense.person}` : ''}
                    ${expense.need_vs_want ? `<br><strong>Type:</strong> ${expense.need_vs_want}` : ''}
                </div>
                ${expense.notes ? `<div class="expense-notes">${expense.notes}</div>` : ''}
                <div class="expense-actions">
                    <button class="btn btn-sm btn-danger" onclick="deleteExpense(${expense.id})">Delete</button>
                </div>
            `;
            
            listContainer.appendChild(item);
        });
        
        // Update pagination
        document.getElementById('pageInfo').textContent = 
            `Page ${currentPage + 1} (${data.expenses.length} of ${data.total})`;
        document.getElementById('prevPageBtn').disabled = currentPage === 0;
        document.getElementById('nextPageBtn').disabled = 
            (currentPage + 1) * pageSize >= data.total;
        
    } catch (error) {
        console.error('Error loading expenses:', error);
        listContainer.innerHTML = '<p class="loading">Error loading expenses. Check connection.</p>';
    }
}

/**
 * Delete expense
 */
async function deleteExpense(id) {
    if (!confirm('Delete this expense?')) return;
    
    try {
        await apiFetch(`/expenses/${id}`, { method: 'DELETE' });
        showStatus('formStatus', 'Expense deleted', 'success');
        await loadExpenses();
    } catch (error) {
        alert('Error deleting expense: ' + error.message);
    }
}

/**
 * Download expenses as CSV
 */
async function downloadExpensesCSV() {
    try {
        // Get all expenses (up to 10000 to capture everything)
        const params = new URLSearchParams({
            limit: 10000,
            offset: 0
        });
        
        // Add date filters if set
        const startDate = document.getElementById('filterStartDate').value;
        const endDate = document.getElementById('filterEndDate').value;
        
        if (startDate) {
            params.append('start_date', new Date(startDate).toISOString());
        }
        if (endDate) {
            params.append('end_date', new Date(endDate).toISOString());
        }
        
        const data = await apiFetch(`/expenses?${params}`);
        
        if (!data.expenses || data.expenses.length === 0) {
            alert('No expenses to download');
            return;
        }
        
        // Get category names
        const c1Map = {};
        const c2Map = {};
        
        const allC1 = await apiFetch('/categories');
        allC1.forEach(cat => c1Map[cat.id] = cat.name);
        
        for (const c1 of allC1) {
            const c2List = await apiFetch(`/categories/${c1.id}/c2`);
            c2List.forEach(cat => c2Map[cat.id] = cat.name);
        }
        
        // Create CSV content
        const headers = ['Date', 'Amount', 'Category (C1)', 'Subcategory (C2)', 'Payment Mode', 'Person', 'Need vs Want', 'Notes'];
        let csvContent = headers.join(',') + '\n';
        
        data.expenses.forEach(expense => {
            const date = new Date(expense.date).toLocaleString();
            const amount = expense.amount.toFixed(2);
            const c1 = c1Map[expense.c1_id] || 'Unknown';
            const c2 = c2Map[expense.c2_id] || 'Unknown';
            const paymentMode = expense.payment_mode || '';
            const person = expense.person || '';
            const needVsWant = expense.need_vs_want || '';
            const notes = (expense.notes || '').replace(/"/g, '""'); // Escape quotes
            
            const row = [
                `"${date}"`,
                amount,
                `"${c1}"`,
                `"${c2}"`,
                `"${paymentMode}"`,
                `"${person}"`,
                `"${needVsWant}"`,
                `"${notes}"`
            ];
            
            csvContent += row.join(',') + '\n';
        });
        
        // Create download link
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.setAttribute('href', url);
        link.setAttribute('download', `expenses_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        console.log(`Downloaded ${data.expenses.length} expenses as CSV`);
    } catch (error) {
        console.error('Error downloading CSV:', error);
        const errorMsg = error.message || error.toString() || 'Unknown error occurred';
        alert('Error downloading CSV: ' + errorMsg);
    }
}

// ==================== INSIGHTS SCREEN ====================
/**
 * Get date filter parameters for insights
 */
function getInsightsDateParams() {
    const params = new URLSearchParams();
    const startDate = document.getElementById('insightsStartDate').value;
    const endDate = document.getElementById('insightsEndDate').value;
    
    if (startDate) {
        params.append('start_date', new Date(startDate).toISOString());
    }
    if (endDate) {
        params.append('end_date', new Date(endDate).toISOString());
    }
    
    return params.toString();
}

/**
 * Load all insights and charts
 */
async function loadInsights() {
    await Promise.all([
        loadMonthlyChart(),
        loadC1Chart(),
        loadC2Chart(),
        loadTopExpenses(),
        populateC1FilterForCharts()
    ]);
}

/**
 * Load monthly trend chart
 */
async function loadMonthlyChart() {
    try {
        const dateParams = getInsightsDateParams();
        const data = await apiFetch(`/insights/monthly${dateParams ? '?' + dateParams : ''}`);
        
        const ctx = document.getElementById('monthlyChart');
        
        // Destroy existing chart
        if (charts.monthly) {
            charts.monthly.destroy();
        }
        
        charts.monthly = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.month),
                datasets: [{
                    label: 'Monthly Spending (₹)',
                    data: data.map(d => d.total),
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: true }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => '₹' + value.toLocaleString()
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading monthly chart:', error);
    }
}

/**
 * Load C1 distribution pie chart
 */
async function loadC1Chart() {
    try {
        const dateParams = getInsightsDateParams();
        const data = await apiFetch(`/insights/c1-distribution${dateParams ? '?' + dateParams : ''}`);
        
        const ctx = document.getElementById('c1Chart');
        
        if (charts.c1) {
            charts.c1.destroy();
        }
        
        const colors = [
            '#4CAF50', '#2196F3', '#FF9800', '#E91E63', '#9C27B0',
            '#00BCD4', '#FFEB3B', '#795548', '#607D8B', '#F44336'
        ];
        
        charts.c1 = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.map(d => d.c1_name),
                datasets: [{
                    data: data.map(d => d.total),
                    backgroundColor: colors
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    } catch (error) {
        console.error('Error loading C1 chart:', error);
    }
}

/**
 * Load C2 breakdown bar chart
 */
async function loadC2Chart(c1Id = null) {
    try {
        const dateParams = getInsightsDateParams();
        let url = '/insights/c2-breakdown?';
        if (c1Id) url += `c1_id=${c1Id}&`;
        if (dateParams) url += dateParams;
        // Remove trailing & or ?
        url = url.replace(/[&?]$/, '');
        
        const data = await apiFetch(url);
        
        const ctx = document.getElementById('c2Chart');
        
        if (charts.c2) {
            charts.c2.destroy();
        }
        
        charts.c2 = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.c2_name),
                datasets: [{
                    label: 'Spending (₹)',
                    data: data.map(d => d.total),
                    backgroundColor: '#2196F3'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => '₹' + value.toLocaleString()
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading C2 chart:', error);
    }
}

/**
 * Load top expenses
 */
async function loadTopExpenses() {
    const container = document.getElementById('topExpensesList');
    container.innerHTML = '<div class="loading">Loading...</div>';
    
    try {
        const expenses = await apiFetch('/expenses/top?limit=10');
        
        // Handle both array response and empty response
        if (!Array.isArray(expenses) || expenses.length === 0) {
            container.innerHTML = '<p class="empty-state">No expenses available yet.</p>';
            return;
        }
        
        // Get category names
        const c1Map = {};
        const c2Map = {};
        
        const allC1 = await apiFetch('/categories');
        allC1.forEach(cat => c1Map[cat.id] = cat.name);
        
        for (const c1 of allC1) {
            const c2List = await apiFetch(`/categories/${c1.id}/c2`);
            c2List.forEach(cat => c2Map[cat.id] = cat.name);
        }
        
        container.innerHTML = '';
        expenses.forEach((expense, index) => {
            const item = document.createElement('div');
            item.className = 'top-expense-item';
            
            item.innerHTML = `
                <div class="top-expense-rank">#${index + 1}</div>
                <div class="top-expense-details">
                    <div><strong>${c1Map[expense.c1_id]}</strong> → ${c2Map[expense.c2_id]}</div>
                    <div style="font-size: 0.9rem; color: #666;">
                        ${new Date(expense.date).toLocaleDateString()} - ${expense.payment_mode}
                    </div>
                    ${expense.notes ? `<div style="font-size: 0.85rem; color: #999;">${expense.notes}</div>` : ''}
                </div>
                <div class="top-expense-amount">₹${expense.amount.toFixed(2)}</div>
            `;
            
            container.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading top expenses:', error);
        // For any error, show empty state with friendly message
        container.innerHTML = '<p class="empty-state">No expenses available yet.</p>';
    }
}

/**
 * Populate C1 filter dropdown for charts
 */
async function populateC1FilterForCharts() {
    try {
        const categories = await apiFetch('/categories');
        const select = document.getElementById('c1FilterChart');
        
        select.innerHTML = '<option value="">All Categories</option>';
        categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = cat.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading C1 filter:', error);
    }
}

// ==================== CATEGORIES MANAGEMENT SCREEN ====================
/**
 * Load categories management UI
 */
async function loadCategoriesManagement() {
    const container = document.getElementById('categoriesList');
    container.innerHTML = '<div class="loading">Loading categories...</div>';
    
    try {
        const categories = await apiFetch('/categories');
        
        container.innerHTML = '';
        
        for (const c1 of categories) {
            const c2List = await apiFetch(`/categories/${c1.id}/c2`);
            
            const item = document.createElement('div');
            item.className = 'category-item';
            
            const statusClass = c1.active ? 'active' : 'inactive';
            const statusText = c1.active ? 'Active' : 'Inactive';
            
            item.innerHTML = `
                <div class="category-header">
                    <div class="category-name">${c1.name}</div>
                    <div class="category-status ${statusClass}">${statusText}</div>
                </div>
                <div class="category-actions">
                    <button class="btn btn-sm btn-secondary" onclick="toggleC1Active(${c1.id}, ${!c1.active})">
                        ${c1.active ? 'Deactivate' : 'Activate'}
                    </button>
                </div>
                <div class="subcategories">
                    <h4 style="font-size: 0.9rem; margin-bottom: 0.5rem;">Subcategories:</h4>
                    <div id="c2-list-${c1.id}">
                        ${c2List.map(c2 => `
                            <div class="subcategory-item">
                                <span>${c2.name} ${!c2.active ? '(Inactive)' : ''}</span>
                                <button class="btn btn-sm btn-secondary" onclick="toggleC2Active(${c2.id}, ${!c2.active})">
                                    ${c2.active ? 'Deactivate' : 'Activate'}
                                </button>
                            </div>
                        `).join('')}
                    </div>
                    <div class="add-c2-form">
                        <input type="text" id="new-c2-${c1.id}" placeholder="New subcategory name">
                        <button class="btn btn-sm btn-primary" onclick="addNewC2(${c1.id})">Add C2</button>
                    </div>
                </div>
            `;
            
            container.appendChild(item);
        }
    } catch (error) {
        console.error('Error loading categories:', error);
        container.innerHTML = '<p class="loading">Error loading categories.</p>';
    }
}

/**
 * Add new C1 category
 */
async function addNewC1() {
    const nameInput = document.getElementById('newC1Name');
    const name = nameInput.value.trim();
    
    if (!name) {
        alert('Please enter a category name');
        return;
    }
    
    try {
        await apiFetch('/categories', {
            method: 'POST',
            body: JSON.stringify({ name })
        });
        
        nameInput.value = '';
        await loadCategoriesManagement();
    } catch (error) {
        alert('Error adding category: ' + error.message);
    }
}

/**
 * Toggle C1 active status
 */
async function toggleC1Active(id, active) {
    try {
        await apiFetch(`/categories/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ active })
        });
        
        await loadCategoriesManagement();
    } catch (error) {
        alert('Error updating category: ' + error.message);
    }
}

/**
 * Add new C2 subcategory
 */
async function addNewC2(c1Id) {
    const nameInput = document.getElementById(`new-c2-${c1Id}`);
    const name = nameInput.value.trim();
    
    if (!name) {
        alert('Please enter a subcategory name');
        return;
    }
    
    try {
        await apiFetch(`/categories/${c1Id}/c2`, {
            method: 'POST',
            body: JSON.stringify({ name })
        });
        
        nameInput.value = '';
        await loadCategoriesManagement();
    } catch (error) {
        alert('Error adding subcategory: ' + error.message);
    }
}

/**
 * Toggle C2 active status
 */
async function toggleC2Active(id, active) {
    try {
        await apiFetch(`/categories/c2/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ active })
        });
        
        await loadCategoriesManagement();
    } catch (error) {
        alert('Error updating subcategory: ' + error.message);
    }
}

// ==================== SETTINGS SCREEN ====================
/**
 * Update queue status display
 */
async function updateQueueStatus() {
    try {
        const queued = await getQueuedExpenses();
        const statusEl = document.getElementById('queueStatus');
        
        if (queued.length === 0) {
            statusEl.textContent = '✅ No pending expenses. Everything synced!';
        } else {
            statusEl.textContent = `📥 ${queued.length} expense(s) waiting to sync`;
        }
    } catch (error) {
        console.error('Error checking queue:', error);
        document.getElementById('queueStatus').textContent = 'Error checking queue';
    }
}

/**
 * Manual sync button handler
 */
async function handleManualSync() {
    const resultEl = document.getElementById('syncResult');
    resultEl.textContent = 'Syncing...';
    resultEl.className = 'status-message';
    resultEl.style.display = 'block';
    
    const result = await syncQueuedExpenses();
    
    if (result.success) {
        if (result.synced === 0) {
            resultEl.textContent = '✅ Nothing to sync!';
            resultEl.className = 'status-message success';
        } else {
            resultEl.textContent = `✅ Synced ${result.synced} expense(s)!`;
            resultEl.className = 'status-message success';
        }
    } else {
        resultEl.textContent = `❌ Sync failed: ${result.message || 'Unknown error'}`;
        resultEl.className = 'status-message error';
    }
    
    await updateQueueStatus();
}

// ==================== PWA INSTALL ====================
/**
 * Setup PWA install prompt
 */
function setupPWAInstall() {
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        
        const installBtn = document.getElementById('installBtn');
        installBtn.style.display = 'block';
        document.getElementById('installStatus').textContent = 'Ready to install!';
    });
    
    document.getElementById('installBtn').addEventListener('click', async () => {
        if (!deferredPrompt) return;
        
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        
        if (outcome === 'accepted') {
            document.getElementById('installStatus').textContent = 'App installed! ✅';
        }
        
        deferredPrompt = null;
        document.getElementById('installBtn').style.display = 'none';
    });
    
    window.addEventListener('appinstalled', () => {
        console.log('PWA installed successfully');
        deferredPrompt = null;
    });
}

// ==================== SERVICE WORKER REGISTRATION ====================
/**
 * Register service worker
 */
async function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        try {
            const registration = await navigator.serviceWorker.register('/service-worker.js');
            console.log('Service Worker registered:', registration);
            
            // Listen for updates
            registration.addEventListener('updatefound', () => {
                console.log('Service Worker update found');
            });
        } catch (error) {
            console.error('Service Worker registration failed:', error);
        }
    }
}

// ==================== INITIALIZATION ====================
/**
 * Initialize app
 */
async function initApp() {
    console.log('Initializing Expense Tracker...');
    
    // Initialize IndexedDB
    await initDB();
    
    // Register service worker
    await registerServiceWorker();
    
    // Setup auto-sync
    setupAutoSync();
    
    // Setup PWA install
    setupPWAInstall();
    
    // Update online status
    updateOnlineStatus();
    
    // Set default date/time
    setDefaultDateTime();
    
    // Load initial screen data
    await loadScreenData('add');
    
    // Try to sync queued expenses on startup
    if (isOnline) {
        syncQueuedExpenses();
    }
    
    console.log('App initialized successfully');
}

// ==================== EVENT LISTENERS ====================
document.addEventListener('DOMContentLoaded', () => {
    // Navigation tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            switchScreen(tab.dataset.screen);
        });
    });
    
    // Expense form
    document.getElementById('expenseForm').addEventListener('submit', handleExpenseSubmit);
    document.getElementById('clearFormBtn').addEventListener('click', () => {
        document.getElementById('expenseForm').reset();
        setDefaultDateTime();
    });
    
    // C1 category change -> load C2
    document.getElementById('expenseC1').addEventListener('change', (e) => {
        loadC2Categories(e.target.value);
    });
    
    // Add C2 button (opens modal)
    document.getElementById('addC2Btn').addEventListener('click', () => {
        document.getElementById('addC2Modal').classList.add('active');
    });
    
    // Add C2 modal close
    document.getElementById('closeC2Modal').addEventListener('click', () => {
        document.getElementById('addC2Modal').classList.remove('active');
    });
    
    document.getElementById('cancelC2Btn').addEventListener('click', () => {
        document.getElementById('addC2Modal').classList.remove('active');
    });
    
    // Add C2 form submit
    document.getElementById('addC2Form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const c1Id = document.getElementById('expenseC1').value;
        const name = document.getElementById('newC2Name').value.trim();
        
        if (!name || !c1Id) return;
        
        try {
            const newC2 = await apiFetch(`/categories/${c1Id}/c2`, {
                method: 'POST',
                body: JSON.stringify({ name })
            });
            
            // Reload C2 and select the new one
            await loadC2Categories(c1Id);
            document.getElementById('expenseC2').value = newC2.id;
            
            // Close modal and clear form
            document.getElementById('addC2Modal').classList.remove('active');
            document.getElementById('newC2Name').value = '';
        } catch (error) {
            alert('Error adding subcategory: ' + error.message);
        }
    });
    
    // Expenses list pagination
    document.getElementById('prevPageBtn').addEventListener('click', () => {
        if (currentPage > 0) {
            currentPage--;
            loadExpenses();
        }
    });
    
    document.getElementById('nextPageBtn').addEventListener('click', () => {
        currentPage++;
        loadExpenses();
    });
    
    // Download CSV button
    document.getElementById('downloadCsvBtn').addEventListener('click', downloadExpensesCSV);
    
    // Expenses list filters
    document.getElementById('applyFilterBtn').addEventListener('click', () => {
        currentPage = 0;
        loadExpenses();
    });
    
    document.getElementById('clearFilterBtn').addEventListener('click', () => {
        document.getElementById('filterStartDate').value = '';
        document.getElementById('filterEndDate').value = '';
        currentPage = 0;
        loadExpenses();
    });
    
    // C1 category management
    document.getElementById('addC1Form').addEventListener('submit', (e) => {
        e.preventDefault();
        addNewC1();
    });
    
    // Chart filter
    document.getElementById('c1FilterChart').addEventListener('change', (e) => {
        const c1Id = e.target.value;
        loadC2Chart(c1Id || null);
    });
    
    // Insights date filters
    document.getElementById('applyInsightsFilterBtn').addEventListener('click', () => {
        loadInsights();
    });
    
    document.getElementById('clearInsightsFilterBtn').addEventListener('click', () => {
        document.getElementById('insightsStartDate').value = '';
        document.getElementById('insightsEndDate').value = '';
        loadInsights();
    });
    
    // Settings sync button
    document.getElementById('syncNowBtn').addEventListener('click', handleManualSync);
    
    // Initialize app
    initApp();
});

