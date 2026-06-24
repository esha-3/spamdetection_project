// API base URL
const API_URL = 'http://127.0.0.1:8000/api';

// Realistic sample messages for quick testing
const SAMPLES = {
  safe: "Hey! Just wanted to check if you're still free for coffee this afternoon? Let me know, I'll be around campus till 4pm.",
  spam: "URGENT! Your mobile number has won a £1,500 cash prize. Call 09061701461 now to claim! Code: KL341. Valid 12 hrs only."
};

// On Page Load
document.addEventListener('DOMContentLoaded', () => {
  // Setup textarea character counter
  const textarea = document.getElementById('sms-input');
  const counter = document.getElementById('char-counter');
  
  textarea.addEventListener('input', () => {
    const len = textarea.value.length;
    counter.textContent = `${len} / 800 characters`;
  });

  // Load initial statistics and scanning logs
  refreshDashboard();
});

// Load quick-test sample messages
function loadSample(type) {
  const textarea = document.getElementById('sms-input');
  textarea.value = SAMPLES[type];
  
  // Trigger input event to update char counter
  textarea.dispatchEvent(new Event('input'));
  showToast(`Loaded ${type} sample message`, 'success');
}

// Clear textarea input
function clearInput() {
  const textarea = document.getElementById('sms-input');
  textarea.value = '';
  textarea.dispatchEvent(new Event('input'));
  document.getElementById('result-box').classList.add('hidden');
}

// Refresh stats and logs
async function refreshDashboard() {
  await Promise.all([
    loadStats(),
    loadHistory()
  ]);
}

// Fetch and render summary stats
async function loadStats() {
  try {
    const res = await fetch(`${API_URL}/stats/`);
    if (!res.ok) throw new Error();
    const data = await res.json();

    document.getElementById('stat-total').textContent = data.total_count;
    document.getElementById('stat-spam').textContent = data.spam_count;
    document.getElementById('stat-ratio').textContent = `${data.spam_rate}%`;
  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

// Fetch and render historical scans
async function loadHistory() {
  const historyList = document.getElementById('history-list');
  const emptyState = document.getElementById('empty-state');
  const logCount = document.getElementById('log-count');

  try {
    const res = await fetch(`${API_URL}/history/`);
    if (!res.ok) throw new Error();
    const data = await res.json();

    // Update count label
    logCount.textContent = `${data.length} recorded`;

    if (data.length === 0) {
      emptyState.classList.remove('hidden');
      // Clear any items other than empty state
      const items = historyList.querySelectorAll('.history-item');
      items.forEach(el => el.remove());
      return;
    }

    emptyState.classList.add('hidden');

    // Create set of current element IDs to avoid full re-rendering and keep UI smooth
    const existingItems = historyList.querySelectorAll('.history-item');
    const existingIds = Array.from(existingItems).map(el => parseInt(el.dataset.id));
    const newIds = data.map(item => item.id);

    // Remove items that are no longer in the fetched list
    existingItems.forEach(el => {
      const id = parseInt(el.dataset.id);
      if (!newIds.includes(id)) {
        el.remove();
      }
    });

    // Render/Insert items
    data.forEach((item, index) => {
      let itemEl = historyList.querySelector(`.history-item[data-id="${item.id}"]`);
      
      const timeStr = formatRelativeTime(item.created_at);
      const isSpam = item.verdict === 'spam';
      const verdictLabel = isSpam ? 'SPAM' : 'SAFE';
      const badgeClass = isSpam ? 'spam' : 'safe';

      if (!itemEl) {
        // Create new item element
        itemEl = document.createElement('div');
        itemEl.className = 'history-item';
        itemEl.dataset.id = item.id;
        
        // Quick inspection on item click
        itemEl.addEventListener('click', (e) => {
          // If clicked the delete button, do nothing
          if (e.target.closest('.btn-delete')) return;
          loadMessageToScanner(item);
        });

        // Insert into proper order
        if (index === 0) {
          historyList.insertBefore(itemEl, historyList.firstChild);
        } else {
          historyList.appendChild(itemEl);
        }
      }

      // Update contents
      itemEl.innerHTML = `
        <div class="history-content">
          <div class="history-header">
            <span class="badge-mini ${badgeClass}">${verdictLabel}</span>
            <span class="history-time">${timeStr}</span>
          </div>
          <p class="history-text" title="${item.message_text}">${item.message_text}</p>
        </div>
        <button class="btn-delete" title="Delete scan" onclick="deleteHistoryItem(${item.id}, event)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      `;
    });

  } catch (err) {
    console.error('Failed to load history:', err);
  }
}

// Load a historical log item back into the scanner and show result
function loadMessageToScanner(record) {
  const textarea = document.getElementById('sms-input');
  textarea.value = record.message_text;
  textarea.dispatchEvent(new Event('input'));

  displayResult(record);
  showToast("Loaded audit details", "success");
}

// Run spam classifier on user input
async function checkSpam() {
  const textarea = document.getElementById('sms-input');
  const message = textarea.value.trim();

  if (!message) {
    showToast('Please input or paste a message to analyze.', 'error');
    return;
  }

  // Show loading state
  const btn = document.getElementById('check-btn');
  btn.disabled = true;
  btn.querySelector('span').textContent = 'Running diagnostics...';

  // Clear previous outputs
  document.getElementById('result-box').classList.add('hidden');
  document.getElementById('error-box').classList.add('hidden');

  try {
    const res = await fetch(`${API_URL}/check/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: message })
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.error || 'Server error.');
    }

    const data = await res.json();
    
    // Render the output with animations
    displayResult(data);
    
    // Refresh stats and history list
    refreshDashboard();
    
    showToast("Audit completed successfully!", "success");

  } catch (err) {
    console.error(err);
    const errorBox = document.getElementById('error-box');
    document.getElementById('error-message').textContent = err.message || 'Unable to connect to diagnostic server. Please verify Django is running.';
    errorBox.classList.remove('hidden');
    showToast("Analysis failed.", "error");
  } finally {
    btn.disabled = false;
    btn.querySelector('span').textContent = 'Analyze Message';
  }
}

// Renders the API output inside the results card
function displayResult(data) {
  const resultBox = document.getElementById('result-box');
  
  // Set result card class to 'spam', 'safe', or 'unknown'
  resultBox.className = `glass-card result-card ${data.verdict}`;

  // Set text labels
  const verdictEl = document.getElementById('verdict');
  if (data.verdict === 'spam') {
    verdictEl.textContent = '🚨 SPAM';
  } else if (data.verdict === 'safe') {
    verdictEl.textContent = '✅ SAFE';
  } else {
    verdictEl.textContent = '❓ UNCERTAIN';
  }

  document.getElementById('confidence-percentage').textContent = `${Math.round(data.confidence)}%`;
  document.getElementById('explanation').textContent = data.explanation;

  // Animate the radial gauge
  const progressCircle = document.getElementById('gauge-progress');
  const circumference = 264; // 2 * pi * 42 = 263.89
  const offset = circumference - (data.confidence / 100) * circumference;
  
  // Apply the offset stroke
  progressCircle.style.strokeDashoffset = offset;

  // Reveal result card
  resultBox.classList.remove('hidden');
}

// Delete historical record
async function deleteHistoryItem(id, event) {
  if (event) event.stopPropagation(); // Avoid triggering item click

  try {
    const res = await fetch(`${API_URL}/history/${id}/`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error();

    showToast("Log entry deleted", "success");
    refreshDashboard();

    // If currently showing this result in the result card, hide it
    const resultBox = document.getElementById('result-box');
    if (!resultBox.classList.contains('hidden')) {
      // Check if current text matches
      const currentInput = document.getElementById('sms-input').value.trim();
      // Let's just hide the result box for safety
      resultBox.classList.add('hidden');
    }
  } catch (err) {
    showToast("Failed to delete log entry", "error");
  }
}

// Helper to format ISO timestamp to relative string (e.g., "5 mins ago")
function formatRelativeTime(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);

  if (diffSec < 10) return 'Just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

// Toast Notifications System
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  // Icon based on type
  const icon = type === 'success' ? 
    `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"></path></svg>` : 
    `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;

  toast.innerHTML = `${icon} <span>${message}</span>`;
  container.appendChild(toast);

  // Auto-remove toast
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}