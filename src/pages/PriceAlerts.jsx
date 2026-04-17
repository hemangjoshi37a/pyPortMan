import { useState, useEffect, useCallback } from 'react';
import LoadingSpinner from '../components/LoadingSpinner';
import { formatIndianCurrency } from '../services/api';
import {
  getAccounts,
  getPriceAlerts,
  getPriceAlertSummary,
  createPriceAlert,
  updatePriceAlert,
  deletePriceAlert
} from '../services/api';

export default function PriceAlerts() {
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState('all');
  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filterStatus, setFilterStatus] = useState('ACTIVE');

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' or 'edit'
  const [formData, setFormData] = useState({
    id: null,
    stock: '',
    exchange: 'NSE',
    alert_type: 'ABOVE',
    target_price: '',
    repeat: false,
    repeat_interval: 24,
    account_id: ''
  });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Fetch Accounts
  useEffect(() => {
    getAccounts().then(data => {
      setAccounts(data);
      if (data.length > 0 && selectedAccountId === 'all') {
        // keep 'all' 
      }
    });
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const accId = selectedAccountId === 'all' ? null : selectedAccountId;
      const [alertsData, summaryData] = await Promise.all([
        getPriceAlerts(accId, filterStatus),
        getPriceAlertSummary(accId)
      ]);
      setAlerts(alertsData);
      setSummary(summaryData);
    } catch (err) {
      console.error('Error fetching alerts:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedAccountId, filterStatus]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Modal handlers
  const openCreateModal = () => {
    setFormData({
      id: null,
      stock: '',
      exchange: 'NSE',
      alert_type: 'ABOVE',
      target_price: '',
      repeat: false,
      repeat_interval: 24,
      account_id: selectedAccountId === 'all' ? (accounts[0]?.id || '') : selectedAccountId
    });
    setModalMode('create');
    setFormError('');
    setShowModal(true);
  };

  const openEditModal = (alert) => {
    setFormData({
      id: alert.id,
      stock: alert.stock,
      exchange: alert.exchange,
      alert_type: alert.alert_type,
      target_price: alert.target_price,
      repeat: alert.repeat,
      repeat_interval: alert.repeat_interval,
      account_id: alert.account_id
    });
    setModalMode('edit');
    setFormError('');
    setShowModal(true);
  };

  const handleCloseModal = () => setShowModal(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.stock || !formData.target_price || !formData.account_id) {
      setFormError('Please fill in all required fields');
      return;
    }

    setSubmitting(true);
    setFormError('');

    try {
      const payload = {
        stock: formData.stock.toUpperCase(),
        exchange: formData.exchange,
        alert_type: formData.alert_type,
        target_price: parseFloat(formData.target_price),
        repeat: formData.repeat,
        repeat_interval: parseInt(formData.repeat_interval, 10)
      };

      if (modalMode === 'create') {
        await createPriceAlert(formData.account_id, payload);
      } else {
        await updatePriceAlert(formData.id, payload);
      }
      setShowModal(false);
      fetchData(); // Refresh list
    } catch (err) {
      setFormError(err.message || 'Failed to save alert');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this alert?')) {
      try {
        await deletePriceAlert(id);
        fetchData();
      } catch (err) {
        console.error('Delete failed:', err);
        alert(err.message || 'Failed to delete alert');
      }
    }
  };

  const handleToggleStatus = async (alert) => {
    try {
      const newStatus = alert.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
      await updatePriceAlert(alert.id, { status: newStatus });
      fetchData();
    } catch (err) {
      alert(err.message || 'Failed to update alert status');
    }
  };

  // Determine distance to alert
  const getAlertProgress = (current, target, type) => {
    if (!current || !target) return 0;
    // rough visual approximation
    const diff = Math.abs(current - target);
    const pct = (diff / target) * 100;
    if (pct > 20) return 0;
    if (pct === 0) return 100;
    return Math.max(0, 100 - (pct * 5)); // 20% away = 0 progress
  };

  if (loading && alerts.length === 0) {
    return (
      <div className="alerts-page">
        <LoadingSpinner size="large" text="Loading price alerts..." />
      </div>
    );
  }

  return (
    <div className="alerts-page">
      <div className="alerts-header">
        <div>
          <h1>🔔 Price Alerts</h1>
          <p className="description">Get notified when stocks cross your target prices</p>
        </div>
        <div className="alerts-actions">
          <select 
            value={selectedAccountId} 
            onChange={(e) => setSelectedAccountId(e.target.value)}
            className="select-input"
          >
            <option value="all">All Accounts</option>
            {accounts.map(acc => (
              <option key={acc.id} value={acc.id}>{acc.name}</option>
            ))}
          </select>
          <button className="btn btn-primary" onClick={openCreateModal}>
            + New Alert
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="alerts-summary-grid">
          <div className="summary-card">
            <div className="summary-title">Active Alerts</div>
            <div className="summary-value active-text">{summary.active}</div>
          </div>
          <div className="summary-card">
            <div className="summary-title">Triggered Today</div>
            <div className="summary-value triggered-text">{summary.triggered}</div>
          </div>
          <div className="summary-card">
            <div className="summary-title">Completed</div>
            <div className="summary-value">{summary.completed}</div>
          </div>
          <div className="summary-card">
            <div className="summary-title">Total Alerts</div>
            <div className="summary-value">{summary.total}</div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="dashboard-card">
        <div className="card-header">
          <h2>Your Alerts</h2>
          <div className="tab-buttons">
            {['ACTIVE', 'TRIGGERED', 'PAUSED', 'COMPLETED'].map(status => (
              <button 
                key={status}
                className={`tab-btn ${filterStatus === status ? 'active' : ''}`}
                onClick={() => setFilterStatus(status)}
              >
                {status}
              </button>
            ))}
          </div>
        </div>

        <div className="card-body">
          {loading ? (
            <div style={{ padding: '40px 0', textAlign: 'center' }}>
              <LoadingSpinner size="small" />
            </div>
          ) : alerts.length > 0 ? (
            <div className="table-responsive">
              <table className="alerts-table">
                <thead>
                  <tr>
                    <th>Stock</th>
                    <th>Condition</th>
                    <th>Target</th>
                    <th>Current</th>
                    <th>Progress</th>
                    <th>Status</th>
                    <th>Settings</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.map(alert => {
                    const isAbove = alert.alert_type === 'ABOVE';
                    const progress = getAlertProgress(alert.current_price, alert.target_price, alert.alert_type);
                    
                    return (
                      <tr key={alert.id} className={alert.status === 'TRIGGERED' ? 'row-triggered' : ''}>
                        <td>
                          <div className="stock-symbol">{alert.stock}</div>
                          <div className="stock-exchange">{alert.exchange}</div>
                        </td>
                        <td>
                          <span className={`condition-badge ${isAbove ? 'badge-above' : 'badge-below'}`}>
                            {isAbove ? '≥ ABOVE' : '≤ BELOW'}
                          </span>
                        </td>
                        <td className="price-cell">{formatIndianCurrency(alert.target_price)}</td>
                        <td className="price-cell">{formatIndianCurrency(alert.current_price)}</td>
                        <td>
                          <div className="progress-wrapper">
                            <div className="progress-bar">
                              <div 
                                className={`progress-fill ${isAbove ? 'fill-green' : 'fill-red'}`} 
                                style={{ width: `${progress}%` }}
                              ></div>
                            </div>
                            <span className="progress-text">{Math.round(progress)}%</span>
                          </div>
                        </td>
                        <td>
                          <span className={`status-blob status-${alert.status.toLowerCase()}`}>
                            {alert.status}
                          </span>
                        </td>
                        <td className="settings-cell">
                          {alert.repeat ? (
                            <span className="repeat-badge" title={`Repeats every ${alert.repeat_interval}h`}>
                              🔁 {alert.repeat_interval}h
                            </span>
                          ) : (
                            <span className="once-badge">1️⃣ Once</span>
                          )}
                        </td>
                        <td className="actions-cell">
                          {(alert.status === 'ACTIVE' || alert.status === 'PAUSED') && (
                            <button 
                              className="action-btn" 
                              onClick={() => handleToggleStatus(alert)}
                              title={alert.status === 'ACTIVE' ? "Pause Alert" : "Resume Alert"}
                            >
                              {alert.status === 'ACTIVE' ? '⏸️' : '▶️'}
                            </button>
                          )}
                          <button className="action-btn" onClick={() => openEditModal(alert)} title="Edit">✏️</button>
                          <button className="action-btn delete" onClick={() => handleDelete(alert.id)} title="Delete">🗑️</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔔</div>
              <h3>No {filterStatus.toLowerCase()} alerts found</h3>
              <p>Create a price alert to get notified when stocks reach your targets.</p>
              <button className="btn btn-primary" onClick={openCreateModal} style={{ marginTop: '16px' }}>
                Create First Alert
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Modal for Create/Edit */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>{modalMode === 'create' ? 'Create New Alert' : 'Edit Alert'}</h2>
              <button className="close-btn" onClick={handleCloseModal}>&times;</button>
            </div>
            
            <div className="modal-body">
              {formError && <div className="error-message">{formError}</div>}
              
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label>Account</label>
                  <select 
                    className="form-control"
                    value={formData.account_id}
                    onChange={(e) => setFormData({...formData, account_id: e.target.value})}
                    disabled={modalMode === 'edit'} // Don't allow changing account on edit
                    required
                  >
                    <option value="">Select Account</option>
                    {accounts.map(acc => (
                      <option key={acc.id} value={acc.id}>{acc.name}</option>
                    ))}
                  </select>
                </div>

                <div className="form-row">
                  <div className="form-group" style={{ flex: 2 }}>
                    <label>Stock Symbol</label>
                    <input 
                      type="text" 
                      className="form-control"
                      value={formData.stock}
                      onChange={(e) => setFormData({...formData, stock: e.target.value})}
                      placeholder="e.g. RELIANCE"
                      required
                    />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Exchange</label>
                    <select 
                      className="form-control"
                      value={formData.exchange}
                      onChange={(e) => setFormData({...formData, exchange: e.target.value})}
                    >
                      <option value="NSE">NSE</option>
                      <option value="BSE">BSE</option>
                    </select>
                  </div>
                </div>

                <div className="form-row form-row-align">
                  <div className="form-group">
                    <label>Condition</label>
                    <div className="condition-toggle">
                      <button 
                        type="button"
                        className={`cond-btn ${formData.alert_type === 'ABOVE' ? 'active-above' : ''}`}
                        onClick={() => setFormData({...formData, alert_type: 'ABOVE'})}
                      >
                        Greater Than (≥)
                      </button>
                      <button 
                        type="button"
                        className={`cond-btn ${formData.alert_type === 'BELOW' ? 'active-below' : ''}`}
                        onClick={() => setFormData({...formData, alert_type: 'BELOW'})}
                      >
                        Less Than (≤)
                      </button>
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Target Price (₹)</label>
                    <input 
                      type="number" 
                      step="0.05"
                      className="form-control price-input"
                      value={formData.target_price}
                      onChange={(e) => setFormData({...formData, target_price: e.target.value})}
                      placeholder="0.00"
                      required
                    />
                  </div>
                </div>

                <div className="form-group options-group">
                  <label className="checkbox-label">
                    <input 
                      type="checkbox" 
                      checked={formData.repeat}
                      onChange={(e) => setFormData({...formData, repeat: e.target.checked})}
                    />
                    <span>Repeat this alert</span>
                  </label>
                  
                  {formData.repeat && (
                    <div className="repeat-options" style={{ marginTop: '10px' }}>
                      <label>Cooldown interval (hours):</label>
                      <input 
                        type="number" 
                        min="1"
                        max="720"
                        className="form-control"
                        value={formData.repeat_interval}
                        onChange={(e) => setFormData({...formData, repeat_interval: e.target.value})}
                        style={{ width: '100px', display: 'inline-block', marginLeft: '10px' }}
                      />
                    </div>
                  )}
                </div>

                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={handleCloseModal}>Cancel</button>
                  <button type="submit" className="btn btn-primary" disabled={submitting}>
                    {submitting ? 'Saving...' : 'Save Alert'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
