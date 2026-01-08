/**
 * Service Worker for Expense Tracker PWA
 * Handles offline caching and background sync
 */

const CACHE_NAME = 'expense-tracker-v1';
const STATIC_CACHE = 'expense-tracker-static-v1';

// Files to cache for offline use
const STATIC_FILES = [
    '/',
    '/static/index.html',
    '/static/styles.css',
    '/static/app.js',
    '/manifest.json',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
    console.log('Service Worker installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('Caching static files...');
                return cache.addAll(STATIC_FILES).catch((error) => {
                    console.warn('Failed to cache some files:', error);
                    // Don't fail installation if some files don't cache
                    return Promise.resolve();
                });
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => name !== STATIC_CACHE && name !== CACHE_NAME)
                        .map((name) => caches.delete(name))
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Handle API requests differently - network first, then cache
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Clone the response before caching
                    const responseClone = response.clone();
                    
                    // Cache successful GET responses
                    if (response.status === 200) {
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    
                    return response;
                })
                .catch(() => {
                    // Network failed, try cache
                    return caches.match(request)
                        .then((response) => {
                            return response || new Response(
                                JSON.stringify({ error: 'Offline and no cached data' }),
                                {
                                    status: 503,
                                    headers: { 'Content-Type': 'application/json' }
                                }
                            );
                        });
                })
        );
        return;
    }
    
    // For static files - cache first, then network
    event.respondWith(
        caches.match(request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    // Return cached version and update cache in background
                    fetch(request)
                        .then((response) => {
                            if (response.status === 200) {
                                caches.open(STATIC_CACHE).then((cache) => {
                                    cache.put(request, response);
                                });
                            }
                        })
                        .catch(() => {
                            // Network error, ignore
                        });
                    
                    return cachedResponse;
                }
                
                // Not in cache, fetch from network
                return fetch(request)
                    .then((response) => {
                        // Cache successful responses
                        if (response.status === 200) {
                            const responseClone = response.clone();
                            caches.open(STATIC_CACHE).then((cache) => {
                                cache.put(request, responseClone);
                            });
                        }
                        return response;
                    })
                    .catch((error) => {
                        console.error('Fetch failed:', error);
                        
                        // Return offline page or error
                        return new Response('Offline', {
                            status: 503,
                            statusText: 'Service Unavailable'
                        });
                    });
            })
    );
});

// Background sync event - sync queued expenses
self.addEventListener('sync', (event) => {
    console.log('Background sync triggered:', event.tag);
    
    if (event.tag === 'sync-expenses') {
        event.waitUntil(syncExpenses());
    }
});

/**
 * Sync queued expenses to server
 * This is called by the sync event when network is available
 */
async function syncExpenses() {
    try {
        console.log('Syncing expenses in background...');
        
        // Open IndexedDB
        const db = await openDB();
        const transaction = db.transaction(['queuedExpenses'], 'readonly');
        const store = transaction.objectStore('queuedExpenses');
        const queued = await getAll(store);
        
        console.log(`Found ${queued.length} expenses to sync`);
        
        // Sync each expense
        for (const item of queued) {
            try {
                const { id, timestamp, ...expense } = item;
                
                const response = await fetch('/api/expenses', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(expense)
                });
                
                if (response.ok) {
                    // Remove from queue
                    const deleteTransaction = db.transaction(['queuedExpenses'], 'readwrite');
                    const deleteStore = deleteTransaction.objectStore('queuedExpenses');
                    await deleteFromStore(deleteStore, id);
                    console.log('Synced expense:', id);
                }
            } catch (error) {
                console.error('Failed to sync expense:', error);
            }
        }
        
        db.close();
        console.log('Background sync complete');
    } catch (error) {
        console.error('Background sync error:', error);
        throw error;
    }
}

/**
 * Helper: Open IndexedDB
 */
function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('ExpenseTrackerDB', 1);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

/**
 * Helper: Get all items from store
 */
function getAll(store) {
    return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

/**
 * Helper: Delete item from store
 */
function deleteFromStore(store, id) {
    return new Promise((resolve, reject) => {
        const request = store.delete(id);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

// Message event - handle messages from clients
self.addEventListener('message', (event) => {
    console.log('Service Worker received message:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'SYNC_NOW') {
        syncExpenses()
            .then(() => {
                event.ports[0].postMessage({ success: true });
            })
            .catch((error) => {
                event.ports[0].postMessage({ success: false, error: error.message });
            });
    }
});

// Push notification event (for future enhancement)
self.addEventListener('push', (event) => {
    console.log('Push notification received:', event);
    
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Expense Tracker';
    const options = {
        body: data.body || 'New notification',
        icon: '/icon-192.png',
        badge: '/icon-192.png'
    };
    
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

