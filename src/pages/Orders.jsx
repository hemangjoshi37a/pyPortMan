import { useState } from 'react';
import OrdersTable from '../components/OrdersTable';
import { orders, gttOrders } from '../data/mockData';

export default function Orders() {
  const [activeTab, setActiveTab] = useState('pending');
  const [showNewOrderForm, setShowNewOrderForm] = useState(false);
  const [formData, setFormData] = useState({
    symbol: '',
    qty: '',
    price: '',
    type: 'LIMIT',
    side: 'BUY',
    account: 'ACC001'
  });

  const pendingOrders = orders.filter(o => o.status === 'OPEN' || o.status === 'PENDING');
  const completedOrders = orders.filter(o => o.status === 'COMPLETE');

  const handleSubmitOrder = (e) => {
    e.preventDefault();
    console.log('Placing order:', formData);
    setShowNewOrderForm(false);
    setFormData({ symbol: '', qty: '', price: '', type: 'LIMIT', side: 'BUY', account: 'ACC001' });
  };

  return (
    <div className="orders-page">
      <div className="page-header">
        <h1>Orders</h1>
        <button
          className="btn-primary"
          onClick={() => setShowNewOrderForm(true)}
        >
          + New Order
        </button>
      </div>

      <div className="orders-tabs">
        <button
          className={`tab ${activeTab === 'pending' ? 'active' : ''}`}
          onClick={() => setActiveTab('pending')}
        >
          Pending Orders ({pendingOrders.length})
        </button>
        <button
          className={`tab ${activeTab === 'gtt' ? 'active' : ''}`}
          onClick={() => setActiveTab('gtt')}
        >
          GTT Orders ({gttOrders.length})
        </button>
        <button
          className={`tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          Order History ({completedOrders.length})
        </button>
      </div>

      <div className="orders-content">
        {activeTab === 'pending' && (
          <div>
            <h3>Pending Orders</h3>
            <OrdersTable orders={pendingOrders} />
          </div>
        )}

        {activeTab === 'gtt' && (
          <div>
            <h3>GTT Orders</h3>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Account</th>
                    <th>Stock</th>
                    <th>Qty</th>
                    <th>Buy@</th>
                    <th>Sell@</th>
                    <th>Stop Loss</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {gttOrders.map(gtt => {
                    const date = new Date(gtt.createdAt);
                    const dateStr = date.toLocaleDateString('en-IN', {
                      day: '2-digit',
                      month: 'short'
                    });

                    return (
                      <tr key={gtt.id}>
                        <td>{gtt.id}</td>
                        <td>{gtt.accountId}</td>
                        <td>{gtt.symbol}</td>
                        <td>{gtt.qty}</td>
                        <td>{gtt.buyPrice}</td>
                        <td>{gtt.sellPrice}</td>
                        <td>{gtt.stopLoss}</td>
                        <td>
                          <span className={`badge status-${gtt.status.toLowerCase()}`}>
                            {gtt.status}
                          </span>
                        </td>
                        <td>{dateStr}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div>
            <h3>Order History</h3>
            <OrdersTable orders={completedOrders} />
          </div>
        )}
      </div>

      {showNewOrderForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Place New Order</h2>
              <button
                className="btn-close"
                onClick={() => setShowNewOrderForm(false)}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleSubmitOrder} className="order-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Stock Symbol</label>
                  <input
                    type="text"
                    value={formData.symbol}
                    onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                    placeholder="RELIANCE"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Quantity</label>
                  <input
                    type="number"
                    value={formData.qty}
                    onChange={(e) => setFormData({ ...formData, qty: e.target.value })}
                    placeholder="10"
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Order Type</label>
                  <select
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                    required
                  >
                    <option value="LIMIT">LIMIT</option>
                    <option value="MARKET">MARKET</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Side</label>
                  <select
                    value={formData.side}
                    onChange={(e) => setFormData({ ...formData, side: e.target.value })}
                    required
                  >
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Price</label>
                  <input
                    type="number"
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                    placeholder="100.00"
                    step="0.05"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Account</label>
                  <select
                    value={formData.account}
                    onChange={(e) => setFormData({ ...formData, account: e.target.value })}
                    required
                  >
                    <option value="ACC001">Main Account</option>
                    <option value="ACC002">Wife Account</option>
                    <option value="ACC003">HUF Account</option>
                  </select>
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowNewOrderForm(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Place Order
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
