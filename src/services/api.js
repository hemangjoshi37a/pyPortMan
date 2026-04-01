/**
 * Centralized API Service Layer for pyPortMan
 * All API calls to the FastAPI backend are handled here
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Helper function to handle API responses
 * @param {Response} response - Fetch response object
 * @returns {Promise<any>} - Parsed JSON data
 * @throws {Error} - HTTP error or 401 token expired
 */
async function handleResponse(response) {
  if (response.status === 401) {
    throw new Error('TOKEN_EXPIRED');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  return response.json();
}

/**
 * Helper function to make API requests
 * @param {string} endpoint - API endpoint path
 * @param {Object} options - Fetch options
 * @returns {Promise<any>} - Parsed JSON data
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, { ...defaultOptions, ...options });
    return await handleResponse(response);
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') {
      throw error;
    }
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

// ==================== ACCOUNTS ====================

/**
 * Get all accounts
 * @returns {Promise<Array>} - List of accounts
 */
export async function getAccounts() {
  try {
    return await apiRequest('/accounts');
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Add a new account
 * @param {Object} data - Account data { name, account_id, api_key, api_secret }
 * @returns {Promise<Object>} - Created account
 */
export async function addAccount(data) {
  try {
    return await apiRequest('/accounts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Update an account
 * @param {number} id - Account ID
 * @param {Object} data - Account update data
 * @returns {Promise<Object>} - Updated account
 */
export async function updateAccount(id, data) {
  try {
    return await apiRequest(`/accounts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Delete an account
 * @param {number} id - Account ID
 * @returns {Promise<void>}
 */
export async function deleteAccount(id) {
  try {
    await apiRequest(`/accounts/${id}`, {
      method: 'DELETE',
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Get Zerodha login URL for an account
 * @param {number} accountId - Account ID
 * @returns {Promise<Object>} - { login_url }
 */
export async function getLoginUrl(accountId) {
  try {
    return await apiRequest(`/accounts/${accountId}/token-url`);
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

// ==================== HOLDINGS ====================

/**
 * Get all holdings from all accounts
 * @returns {Promise<Array>} - List of holdings
 */
export async function getHoldings() {
  try {
    return await apiRequest('/holdings');
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Get holdings for a specific account
 * @param {number} accountId - Account ID
 * @returns {Promise<Array>} - List of holdings
 */
export async function getHoldingsByAccount(accountId) {
  try {
    return await apiRequest(`/holdings/${accountId}`);
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Refresh holdings from Zerodha API
 * @param {number} accountId - Account ID
 * @returns {Promise<Object>} - { message }
 */
export async function refreshHoldings(accountId) {
  try {
    return await apiRequest(`/holdings/refresh?account_id=${accountId}`, {
      method: 'POST',
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

// ==================== POSITIONS ====================

/**
 * Get all positions from all accounts
 * @returns {Promise<Array>} - List of positions
 */
export async function getPositions() {
  try {
    return await apiRequest('/positions');
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Get positions for a specific account
 * @param {number} accountId - Account ID
 * @returns {Promise<Array>} - List of positions
 */
export async function getPositionsByAccount(accountId) {
  try {
    return await apiRequest(`/positions/${accountId}`);
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Square off a single position
 * @param {number} accountId - Account ID
 * @param {Object} params - { tradingsymbol, exchange, order_type, product }
 * @returns {Promise<Object>} - Result
 */
export async function squareoffPosition(accountId, params) {
  try {
    return await apiRequest(`/positions/squareoff?account_id=${accountId}`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Square off all positions for an account
 * @param {number} accountId - Account ID
 * @returns {Promise<Object>} - { results }
 */
export async function squareoffAll(accountId) {
  try {
    return await apiRequest(`/positions/${accountId}/squareoff-all`, {
      method: 'POST',
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

// ==================== ORDERS ====================

/**
 * Get all orders from all accounts
 * @returns {Promise<Array>} - List of orders
 */
export async function getOrders() {
  try {
    return await apiRequest('/orders');
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Get orders for a specific account
 * @param {number} accountId - Account ID
 * @returns {Promise<Array>} - List of orders
 */
export async function getOrdersByAccount(accountId) {
  try {
    return await apiRequest(`/orders/${accountId}`);
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Place a new order
 * @param {number} accountId - Account ID
 * @param {Object} params - Order parameters
 * @returns {Promise<Object>} - Result
 */
export async function placeOrder(accountId, params) {
  try {
    return await apiRequest(`/orders?account_id=${accountId}`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Cancel an order
 * @param {string} orderId - Order ID
 * @param {number} accountId - Account ID
 * @returns {Promise<Object>} - { message }
 */
export async function cancelOrder(orderId, accountId) {
  try {
    return await apiRequest(`/orders/${orderId}?account_id=${accountId}`, {
      method: 'DELETE',
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

// ==================== STATS ====================

/**
 * Get portfolio summary
 * @returns {Promise<Object>} - { total_value, investment_value, day_pnl, day_pnl_percent, holdings_count, positions_count, accounts_count }
 */
export async function getSummary() {
  try {
    return await apiRequest('/stats/summary');
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return {
      total_value: 0,
      investment_value: 0,
      day_pnl: 0,
      day_pnl_percent: 0,
      holdings_count: 0,
      positions_count: 0,
      accounts_count: 0,
    };
  }
}

/**
 * Get equity curve data
 * @param {number} days - Number of days (default: 30)
 * @returns {Promise<Array>} - Array of { date, total_value, day_pnl, day_pnl_percent }
 */
export async function getEquityData(days = 30) {
  try {
    return await apiRequest(`/stats/equity?days=${days}`);
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Get portfolio allocation
 * @returns {Promise<Array>} - Array of { stock, value, percentage }
 */
export async function getAllocation() {
  try {
    return await apiRequest('/stats/allocation');
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Get top gainers
 * @param {number} limit - Number of stocks (default: 5)
 * @returns {Promise<Array>} - Array of { stock, pnl, pnl_percent, current_value }
 */
export async function getTopGainers(limit = 5) {
  try {
    return await apiRequest(`/stats/top-gainers?limit=${limit}`);
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Get top losers
 * @param {number} limit - Number of stocks (default: 5)
 * @returns {Promise<Array>} - Array of { stock, pnl, pnl_percent, current_value }
 */
export async function getTopLosers(limit = 5) {
  try {
    return await apiRequest(`/stats/top-losers?limit=${limit}`);
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

// ==================== AUTH ====================

/**
 * Get login URL for authentication
 * @param {number} accountId - Account ID
 * @returns {Promise<Object>} - { login_url }
 */
export async function getAuthLoginUrl(accountId) {
  try {
    return await apiRequest(`/auth/login-url/${accountId}`);
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Handle auth callback after Zerodha login
 * @param {Object} data - { account_id, request_token }
 * @returns {Promise<Object>} - { message }
 */
export async function handleAuthCallback(data) {
  try {
    return await apiRequest('/auth/callback', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

// ==================== GTT ORDERS ====================

/**
 * Get all GTT orders from all accounts
 * @returns {Promise<Array>} - List of GTT orders
 */
export async function getGTTOrders() {
  try {
    return await apiRequest('/gtt');
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Get GTT orders for a specific account
 * @param {number} accountId - Account ID
 * @returns {Promise<Array>} - List of GTT orders
 */
export async function getGTTOrdersByAccount(accountId) {
  try {
    return await apiRequest(`/gtt/${accountId}`);
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return [];
  }
}

/**
 * Get GTT summary
 * @returns {Promise<Object>} - GTT summary
 */
export async function getGTTSummary() {
  try {
    return await apiRequest('/gtt/summary');
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    return {
      total_orders: 0,
      active_orders: 0,
      triggered_orders: 0,
      cancelled_orders: 0,
      expired_orders: 0,
      accounts_covered: 0,
      estimated_capital: 0,
    };
  }
}

/**
 * Place a single GTT order
 * @param {number} accountId - Account ID
 * @param {Object} params - GTT parameters
 * @returns {Promise<Object>} - Result
 */
export async function placeGTT(accountId, params) {
  try {
    return await apiRequest(`/gtt?account_id=${accountId}`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Place GTT for all accounts
 * @param {Array} stockList - List of stocks
 * @returns {Promise<Object>} - Result
 */
export async function placeGTTAllAccounts(stockList) {
  try {
    return await apiRequest('/gtt/bulk-all-accounts', {
      method: 'POST',
      body: JSON.stringify({ stock_list: stockList }),
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Place bulk GTT orders for one account
 * @param {number} accountId - Account ID
 * @param {Array} stockList - List of stocks
 * @returns {Promise<Object>} - Result
 */
export async function placeBulkGTT(accountId, stockList) {
  try {
    return await apiRequest(`/gtt/bulk?account_id=${accountId}`, {
      method: 'POST',
      body: JSON.stringify({ stock_list: stockList }),
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Modify a GTT order
 * @param {string} gttId - GTT ID
 * @param {number} accountId - Account ID
 * @param {Object} params - Update parameters
 * @returns {Promise<Object>} - Result
 */
export async function modifyGTT(gttId, accountId, params) {
  try {
    return await apiRequest(`/gtt/${gttId}?account_id=${accountId}`, {
      method: 'PUT',
      body: JSON.stringify(params),
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Delete a GTT order
 * @param {string} gttId - GTT ID
 * @param {number} accountId - Account ID
 * @returns {Promise<Object>} - { message }
 */
export async function deleteGTT(gttId, accountId) {
  try {
    return await apiRequest(`/gtt/${gttId}?account_id=${accountId}`, {
      method: 'DELETE',
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Sync GTT status from Zerodha
 * @param {number} accountId - Account ID (optional)
 * @returns {Promise<Object>} - Result
 */
export async function syncGTTStatus(accountId = null) {
  try {
    const url = accountId ? `/gtt/sync?account_id=${accountId}` : '/gtt/sync';
    return await apiRequest(url, {
      method: 'POST',
    });
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

/**
 * Import GTT from Excel file
 * @param {File} file - Excel file
 * @param {number} accountId - Account ID (optional)
 * @param {boolean} allAccounts - Place for all accounts
 * @returns {Promise<Object>} - Result
 */
export async function importGTTFromExcel(file, accountId = null, allAccounts = false) {
  try {
    const formData = new FormData();
    formData.append('file', file);

    let url = '/gtt/import-excel';
    const params = new URLSearchParams();
    if (accountId) params.append('account_id', accountId);
    if (allAccounts) params.append('all_accounts', 'true');
    if (params.toString()) url += `?${params.toString()}`;

    const response = await fetch(`${API_BASE_URL}${url}`, {
      method: 'POST',
      body: formData,
    });

    return await handleResponse(response);
  } catch (error) {
    if (error.message === 'TOKEN_EXPIRED') throw error;
    throw error;
  }
}

// ==================== HEALTH ====================

/**
 * Check backend health
 * @returns {Promise<Object>} - { status, timestamp, scheduler_running }
 */
export async function checkHealth() {
  try {
    return await apiRequest('/health');
  } catch (error) {
    return {
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      scheduler_running: false,
    };
  }
}

// ==================== UTILITIES ====================

/**
 * Check if market is currently open (9:15 AM - 3:30 PM IST, weekdays)
 * @returns {boolean} - True if market is open
 */
export function isMarketOpen() {
  const now = new Date();
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const day = ist.getDay(); // 0=Sun, 6=Sat
  if (day === 0 || day === 6) return false;
  const hours = ist.getHours();
  const mins = ist.getMinutes();
  const time = hours * 100 + mins;
  return time >= 915 && time <= 1530;
}

/**
 * Format Indian currency
 * @param {number} amount - Amount to format
 * @returns {string} - Formatted string
 */
export function formatIndianCurrency(amount) {
  if (amount === null || amount === undefined) return '₹0';
  if (amount >= 10000000) {
    return `₹${(amount / 10000000).toFixed(2)} Cr`;
  } else if (amount >= 100000) {
    return `₹${(amount / 100000).toFixed(2)} L`;
  } else if (amount >= 1000) {
    return `₹${(amount / 1000).toFixed(2)} K`;
  }
  return `₹${amount.toFixed(2)}`;
}

/**
 * Format number with Indian notation
 * @param {number} amount - Amount to format
 * @returns {string} - Formatted string
 */
export function formatNumber(amount) {
  if (amount === null || amount === undefined) return '0';
  if (amount >= 10000000) {
    return `${(amount / 10000000).toFixed(2)} Cr`;
  } else if (amount >= 100000) {
    return `${(amount / 100000).toFixed(2)} L`;
  } else if (amount >= 1000) {
    return `${(amount / 1000).toFixed(2)} K`;
  }
  return amount.toLocaleString('en-IN');
}

/**
 * Format percentage
 * @param {number} value - Percentage value
 * @returns {string} - Formatted string
 */
export function formatPercent(value) {
  if (value === null || value === undefined) return '0%';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export default {
  // Accounts
  getAccounts,
  addAccount,
  updateAccount,
  deleteAccount,
  getLoginUrl,

  // Holdings
  getHoldings,
  getHoldingsByAccount,
  refreshHoldings,

  // Positions
  getPositions,
  getPositionsByAccount,
  squareoffPosition,
  squareoffAll,

  // Orders
  getOrders,
  getOrdersByAccount,
  placeOrder,
  cancelOrder,

  // Stats
  getSummary,
  getEquityData,
  getAllocation,
  getTopGainers,
  getTopLosers,

  // Auth
  getAuthLoginUrl,
  handleAuthCallback,

  // Health
  checkHealth,

  // Utilities
  isMarketOpen,
  formatIndianCurrency,
  formatNumber,
  formatPercent,
};
