import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import Holdings from './pages/Holdings';
import Orders from './pages/Orders';
import Positions from './pages/Positions';
import GTTOrders from './pages/GTTOrders';
import Settings from './pages/Settings';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <div className="sidebar">
          <Sidebar />
        </div>
        <div className="main-content">
          <TopBar />
          <div className="page-content">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/accounts" element={<Accounts />} />
              <Route path="/holdings" element={<Holdings />} />
              <Route path="/orders" element={<Orders />} />
              <Route path="/gtt" element={<GTTOrders />} />
              <Route path="/positions" element={<Positions />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </div>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
