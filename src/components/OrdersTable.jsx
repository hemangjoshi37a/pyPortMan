import { formatIndianCurrency, formatNumber } from '../data/mockData';

export default function OrdersTable({ orders, showFilters = true }) {
  const getStatusBadgeClass = (status) => {
    switch (status.toLowerCase()) {
      case 'complete':
        return 'status-complete';
      case 'pending':
        return 'status-pending';
      case 'open':
        return 'status-open';
      default:
        return 'status-default';
    }
  };

  const getTypeBadgeClass = (type) => {
    switch (type.toLowerCase()) {
      case 'buy':
        return 'type-buy';
      case 'sell':
        return 'type-sell';
      default:
        return 'type-default';
    }
  };

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Account</th>
            <th>Stock</th>
            <th>Type</th>
            <th>Side</th>
            <th>Qty</th>
            <th>Price</th>
            <th>Status</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => {
            const date = new Date(order.timestamp);
            const timeStr = date.toLocaleTimeString('en-IN', {
              hour: '2-digit',
              minute: '2-digit',
              hour12: false
            });

            return (
              <tr key={order.id}>
                <td>{order.id}</td>
                <td>{order.accountId}</td>
                <td>{order.symbol}</td>
                <td>{order.type}</td>
                <td>
                  <span className={`badge ${getTypeBadgeClass(order.side)}`}>
                    {order.side}
                  </span>
                </td>
                <td>{formatNumber(order.qty)}</td>
                <td>{formatIndianCurrency(order.price)}</td>
                <td>
                  <span className={`badge ${getStatusBadgeClass(order.status)}`}>
                    {order.status}
                  </span>
                </td>
                <td>{timeStr}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
