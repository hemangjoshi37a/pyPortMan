import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  getGTTOrders,
  getGTTSummary,
  placeGTT,
  placeGTTAllAccounts,
  modifyGTT,
  deleteGTT,
  syncGTTStatus,
  importGTTFromExcel,
  getAccounts,
} from '../services/api';

export default function GTTOrders() {
  const [gttOrders, setGttOrders] = useState([]);
  const [summary, setSummary] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedAccount, setSelectedAccount] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [showAddForm, setShowAddForm] = useState(false);
  const [showBulkImport, setShowBulkImport] = useState(false);
  const [showModifyModal, setShowModifyModal] = useState(false);
  const [selectedGTT, setSelectedGTT] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    stock: '',
    exchange: 'NSE',
    qty: 1,
    buy_price: 0,
    target_price: 0,
    sl_price: 0,
    allocation_pct: 0,
  });

  // Modify form state
  const [modifyData, setModifyData] = useState({
    target_price: 0,
    sl_price: 0,
    qty: 1,
    buy_price: 0,
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [ordersData, summaryData, accountsData] = await Promise.all([
        getGTTOrders(),
        getGTTSummary(),
        getAccounts(),
      ]);
      setGttOrders(ordersData);
      setSummary(summaryData);
      setAccounts(accountsData);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      await syncGTTStatus();
      await fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handlePlaceGTT = async (forAllAccounts = false) => {
    try {
      if (forAllAccounts) {
        await placeGTTAllAccounts([formData]);
      } else {
        const accountId = accounts[0]?.id;
        if (!accountId) {
          setError('No account available');
          return;
        }
        await placeGTT(accountId, formData);
      }
      setShowAddForm(false);
      setFormData({
        stock: '',
        exchange: 'NSE',
        qty: 1,
        buy_price: 0,
        target_price: 0,
        sl_price: 0,
        allocation_pct: 0,
      });
      await fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleModifyGTT = async () => {
    try {
      await modifyGTT(selectedGTT.gtt_id, selectedGTT.account_id, modifyData);
      setShowModifyModal(false);
      await fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteGTT = async (gttId, accountId) => {
    if (!window.confirm('Are you sure you want to delete this GTT order?')) {
      return;
    }
    try {
      await deleteGTT(gttId, accountId);
      await fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleFileUpload = async (file, forAllAccounts = false) => {
    try {
      setUploading(true);
      const result = await importGTTFromExcel(file, null, forAllAccounts);
      if (result.stock_list) {
        setPreviewData(result);
      } else {
        setPreviewData(null);
        await fetchData();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleConfirmImport = async (forAllAccounts = false) => {
    if (!previewData) return;
    try {
      setUploading(true);
      const file = document.getElementById('excel-file').files[0];
      await importGTTFromExcel(file, null, forAllAccounts);
      setPreviewData(null);
      setShowBulkImport(false);
      await fetchData();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const downloadTemplate = () => {
    const template = [
      ['Symbol', 'Allocation%', 'Buy Price', 'Target Price', 'Stop Loss', 'Exchange', 'Qty'],
      ['RELIANCE', 10, 2800, 2920, 2750, 'NSE', 5],
      ['TCS', 8, 3800, 3950, 3720, 'NSE', 3],
      ['INFY', 7, 1480, 1550, 1440, 'NSE', 8],
      ['HDFCBANK', 12, 1650, 1720, 1610, 'NSE', 6],
      ['SBIN', 5, 750, 800, 720, 'NSE', 15],
    ];

    let csv = template.map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'gtt_template.csv';
    a.click();
  };

  const openModifyModal = (gtt) => {
    setSelectedGTT(gtt);
    setModifyData({
      target_price: gtt.target_price,
      sl_price: gtt.sl_price,
      qty: gtt.qty,
      buy_price: gtt.buy_price,
    });
    setShowModifyModal(true);
  };

  const filteredOrders = gttOrders.filter((order) => {
    if (selectedAccount !== 'all' && order.account_id !== parseInt(selectedAccount)) {
      return false;
    }
    if (selectedStatus !== 'all' && order.status !== selectedStatus) {
      return false;
    }
    return true;
  });

  const getStatusColor = (status) => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-green-100 text-green-800';
      case 'TRIGGERED':
        return 'bg-yellow-100 text-yellow-800';
      case 'CANCELLED':
        return 'bg-red-100 text-red-800';
      case 'EXPIRED':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getAccountName = (accountId) => {
    const account = accounts.find((a) => a.id === accountId);
    return account ? account.name : `Account ${accountId}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="gtt-orders-page">
      <div className="page-header">
        <h1 className="page-title">GTT Orders</h1>
        <p className="page-subtitle">Good Till Triggered Orders - Set and forget your trades</p>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="close-btn">×</button>
        </div>
      )}

      {/* Summary Bar */}
      {summary && (
        <div className="summary-bar">
          <div className="summary-item">
            <span className="summary-label">Active GTT Orders</span>
            <span className="summary-value">{summary.active_orders}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Accounts Covered</span>
            <span className="summary-value">{summary.accounts_covered}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Estimated Capital</span>
            <span className="summary-value">₹{(summary.estimated_capital / 100000).toFixed(2)} L</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Triggered</span>
            <span className="summary-value">{summary.triggered_orders}</span>
          </div>
          <button onClick={handleSync} className="sync-btn">
            <span>🔄</span> Sync Status
          </button>
        </div>
      )}

      {/* Action Buttons */}
      <div className="action-bar">
        <button onClick={() => setShowAddForm(!showAddForm)} className="btn btn-primary">
          <span>➕</span> Add GTT Order
        </button>
        <button onClick={() => setShowBulkImport(!showBulkImport)} className="btn btn-secondary">
          <span>📥</span> Bulk Import
        </button>
        <button onClick={downloadTemplate} className="btn btn-outline">
          <span>📋</span> Download Template
        </button>
      </div>

      {/* Add GTT Form */}
      {showAddForm && (
        <div className="form-card">
          <h3 className="form-title">Add New GTT Order</h3>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Stock Symbol</label>
              <input
                type="text"
                className="form-input"
                value={formData.stock}
                onChange={(e) => setFormData({ ...formData, stock: e.target.value.toUpperCase() })}
                placeholder="RELIANCE"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Exchange</label>
              <select
                className="form-select"
                value={formData.exchange}
                onChange={(e) => setFormData({ ...formData, exchange: e.target.value })}
              >
                <option value="NSE">NSE</option>
                <option value="BSE">BSE</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Quantity</label>
              <input
                type="number"
                className="form-input"
                value={formData.qty}
                onChange={(e) => setFormData({ ...formData, qty: parseInt(e.target.value) || 0 })}
                min="1"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Buy Price (Trigger)</label>
              <input
                type="number"
                className="form-input"
                value={formData.buy_price}
                onChange={(e) => setFormData({ ...formData, buy_price: parseFloat(e.target.value) || 0 })}
                step="0.05"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Target Price</label>
              <input
                type="number"
                className="form-input"
                value={formData.target_price}
                onChange={(e) => setFormData({ ...formData, target_price: parseFloat(e.target.value) || 0 })}
                step="0.05"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Stop Loss</label>
              <input
                type="number"
                className="form-input"
                value={formData.sl_price}
                onChange={(e) => setFormData({ ...formData, sl_price: parseFloat(e.target.value) || 0 })}
                step="0.05"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Allocation %</label>
              <input
                type="number"
                className="form-input"
                value={formData.allocation_pct}
                onChange={(e) => setFormData({ ...formData, allocation_pct: parseFloat(e.target.value) || 0 })}
                step="0.1"
                min="0"
                max="100"
              />
            </div>
          </div>
          <div className="form-actions">
            <button
              onClick={() => handlePlaceGTT(false)}
              className="btn btn-primary"
              disabled={!formData.stock || formData.qty <= 0}
            >
              Place for Current Account
            </button>
            <button
              onClick={() => handlePlaceGTT(true)}
              className="btn btn-indigo"
              disabled={!formData.stock || formData.qty <= 0}
            >
              ⚡ Place for ALL Accounts
            </button>
            <button onClick={() => setShowAddForm(false)} className="btn btn-outline">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Bulk Import Section */}
      {showBulkImport && (
        <div className="form-card">
          <h3 className="form-title">Bulk Import GTT Orders</h3>
          <div className="upload-area">
            <input
              type="file"
              id="excel-file"
              accept=".xlsx,.xls,.csv"
              onChange={(e) => handleFileUpload(e.target.files[0], false)}
              className="file-input"
            />
            <p className="upload-hint">Upload Excel/CSV file with columns: Symbol, Allocation%, Buy Price, Target Price, Stop Loss, Exchange, Qty</p>
          </div>

          {previewData && (
            <div className="preview-section">
              <h4 className="preview-title">Preview ({previewData.count} stocks)</h4>
              <div className="preview-table">
                <table>
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Qty</th>
                      <th>Buy Price</th>
                      <th>Target</th>
                      <th>SL</th>
                      <th>Allocation %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewData.stock_list.slice(0, 5).map((stock, idx) => (
                      <tr key={idx}>
                        <td>{stock.stock}</td>
                        <td>{stock.qty}</td>
                        <td>₹{stock.buy_price}</td>
                        <td>₹{stock.target_price}</td>
                        <td>₹{stock.sl_price}</td>
                        <td>{stock.allocation_pct}%</td>
                      </tr>
                    ))}
                    {previewData.stock_list.length > 5 && (
                      <tr>
                        <td colSpan="6" className="text-center">
                          ... and {previewData.stock_list.length - 5} more
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="preview-actions">
                <button
                  onClick={() => handleConfirmImport(false)}
                  className="btn btn-primary"
                  disabled={uploading}
                >
                  {uploading ? 'Placing...' : 'Place for Current Account'}
                </button>
                <button
                  onClick={() => handleConfirmImport(true)}
                  className="btn btn-indigo"
                  disabled={uploading}
                >
                  {uploading ? 'Placing...' : '⚡ Place for ALL Accounts'}
                </button>
                <button onClick={() => setPreviewData(null)} className="btn btn-outline">
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="filters-bar">
        <div className="filter-group">
          <label className="filter-label">Account:</label>
          <select
            className="filter-select"
            value={selectedAccount}
            onChange={(e) => setSelectedAccount(e.target.value)}
          >
            <option value="all">All Accounts</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label className="filter-label">Status:</label>
          <select
            className="filter-select"
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="ACTIVE">Active</option>
            <option value="TRIGGERED">Triggered</option>
            <option value="CANCELLED">Cancelled</option>
            <option value="EXPIRED">Expired</option>
          </select>
        </div>
      </div>

      {/* GTT Orders Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Account</th>
              <th>Stock</th>
              <th>Exchange</th>
              <th>Qty</th>
              <th>Buy Price</th>
              <th>Target</th>
              <th>SL</th>
              <th>Allocation %</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.length === 0 ? (
              <tr>
                <td colSpan="11" className="text-center">
                  No GTT orders found
                </td>
              </tr>
            ) : (
              filteredOrders.map((order) => (
                <tr key={order.id}>
                  <td>{getAccountName(order.account_id)}</td>
                  <td className="font-semibold">{order.stock}</td>
                  <td>{order.exchange}</td>
                  <td>{order.qty}</td>
                  <td>₹{order.buy_price}</td>
                  <td className="text-green-600">₹{order.target_price}</td>
                  <td className="text-red-600">₹{order.sl_price}</td>
                  <td>{order.allocation_pct}%</td>
                  <td>
                    <span className={`status-badge ${getStatusColor(order.status)}`}>
                      {order.status}
                    </span>
                  </td>
                  <td>{new Date(order.created_at).toLocaleDateString()}</td>
                  <td>
                    <div className="action-buttons">
                      {order.status === 'ACTIVE' && (
                        <>
                          <button
                            onClick={() => openModifyModal(order)}
                            className="btn-icon btn-edit"
                            title="Edit"
                          >
                            ✏️
                          </button>
                          <button
                            onClick={() => handleDeleteGTT(order.gtt_id, order.account_id)}
                            className="btn-icon btn-delete"
                            title="Delete"
                          >
                            🗑️
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modify GTT Modal */}
      {showModifyModal && selectedGTT && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Modify GTT Order</h3>
              <button onClick={() => setShowModifyModal(false)} className="modal-close">×</button>
            </div>
            <div className="modal-body">
              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">Stock</label>
                  <input type="text" className="form-input" value={selectedGTT.stock} disabled />
                </div>
                <div className="form-group">
                  <label className="form-label">Quantity</label>
                  <input
                    type="number"
                    className="form-input"
                    value={modifyData.qty}
                    onChange={(e) => setModifyData({ ...modifyData, qty: parseInt(e.target.value) || 0 })}
                    min="1"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Buy Price</label>
                  <input
                    type="number"
                    className="form-input"
                    value={modifyData.buy_price}
                    onChange={(e) => setModifyData({ ...modifyData, buy_price: parseFloat(e.target.value) || 0 })}
                    step="0.05"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Target Price</label>
                  <input
                    type="number"
                    className="form-input"
                    value={modifyData.target_price}
                    onChange={(e) => setModifyData({ ...modifyData, target_price: parseFloat(e.target.value) || 0 })}
                    step="0.05"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Stop Loss</label>
                  <input
                    type="number"
                    className="form-input"
                    value={modifyData.sl_price}
                    onChange={(e) => setModifyData({ ...modifyData, sl_price: parseFloat(e.target.value) || 0 })}
                    step="0.05"
                  />
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button onClick={handleModifyGTT} className="btn btn-primary">
                Save Changes
              </button>
              <button onClick={() => setShowModifyModal(false)} className="btn btn-outline">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
