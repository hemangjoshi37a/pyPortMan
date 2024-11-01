# pyPortMan 📊💼

<p align="center">
  <img src="https://user-images.githubusercontent.com/12392345/125978523-eb21fa0b-e1c0-4af9-920e-4a418e273f26.png" alt="pyPortMan Logo" width="200">
</p>

![GitHub stars](https://img.shields.io/github/stars/hemangjoshi37a/pyPortMan?style=social)
![GitHub forks](https://img.shields.io/github/forks/hemangjoshi37a/pyPortMan?style=social)
![GitHub issues](https://img.shields.io/github/issues/hemangjoshi37a/pyPortMan)
![GitHub license](https://img.shields.io/github/license/hemangjoshi37a/pyPortMan)

> Python Zerodha Multi-Account Portfolio Management Software (Jupyter Notebook)

pyPortMan is a powerful tool designed to help you manage multiple Zerodha trading accounts effortlessly. With automated GTT (Good Till Triggered) order placement and portfolio tracking, it's perfect for traders and investors looking to streamline their workflow and optimize their trading strategies across multiple accounts.

## 🌟 Key Features

- 📈 Multi-account management for Zerodha
- 🤖 Automated GTT order placement
- 📊 Real-time portfolio tracking across all accounts
- 💹 Percentage-based allocation for each stock
- 📱 Telegram integration for instant alerts
- 🔒 Secure handling of account credentials
- 📉 Risk management through automated stop-loss and target orders

## 🛠️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hemangjoshi37a/pyPortMan.git
   cd pyPortMan
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Zerodha authentication:
   - Open `auth_info.xlsx`
   - Add your Zerodha credentials for each account (User ID, Password, PIN, API Key if applicable)
   - Ensure you keep this file secure and do not share it

## 🏃‍♂️ Quick Start

1. Start the Jupyter Notebook:
   ```bash
   jupyter notebook hjOpenTerminal.ipynb
   ```

2. Configure your stock list:
   - Open `stocks.xlsx`
   - Add the stocks you want to trade, including Symbol, Percentage Allocation, Buy Price, Sell Price, and Stop Loss

3. Run all cells in `hjOpenTerminal.ipynb`

4. Monitor your portfolio and GTT orders in real-time through the Jupyter Notebook interface!

## 📖 How It Works

1. **Initial Setup**: 
   - The software securely reads your Zerodha authentication details from `auth_info.xlsx`.
   - It loads your trading preferences and stock list from `stocks.xlsx`.

2. **GTT Placement**: 
   - Based on your specifications, pyPortMan automatically places GTT orders for each stock across all accounts.

3. **Buy-Sell Cycle**:
   - Initial GTT buy orders are placed at your specified prices.
   - When a buy order is triggered, a corresponding sell GTT is automatically placed.
   - All transactions respect the percentage allocation you've set for each stock and account.

4. **Real-Time Monitoring**:
   - The Jupyter Notebook interface provides live updates on your portfolio status, open orders, and account balances.

## 🔧 Advanced Usage

### Customizing Allocations

In `stocks.xlsx`, you can set custom percentage allocations for each stock. For example:

| Symbol | Percent | Buy Price | Sell Price | Stop Loss |
|--------|---------|-----------|------------|-----------|
| RELIANCE | 10 | 2000 | 2100 | 1950 |

This will allocate 10% of the available funds in each account for RELIANCE stock, with a buy order at 2000, a sell target at 2100, and a stop loss at 1950.

### Risk Management

pyPortMan allows you to set stop-loss orders alongside your target sell orders. This helps in automating your risk management strategy across all accounts.

### Telegram Alerts

To set up Telegram alerts:
1. Create a Telegram bot and obtain the API key
2. Add your Telegram chat ID and bot API key to `config.py`
3. Customize alert preferences in the configuration file

## 🔍 Troubleshooting

- **Authentication Issues**: Ensure your Zerodha credentials in `auth_info.xlsx` are correct and up-to-date.
- **Order Placement Failures**: Check your account balance and stock list for any discrepancies.
- **Jupyter Notebook Errors**: Make sure all required libraries are installed and up-to-date.

## 🤝 Contributing

We welcome contributions to improve pyPortMan! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more details on how to submit pull requests, report issues, or suggest enhancements.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [Zerodha Kite API](https://kite.trade/) for providing the trading interface
- [Jugaad Trader](https://github.com/jugaad-py/jugaad-trader) for inspiration and some code foundations

## 📫 How to reach me | Contact Information
<div align="center">
  <a href="https://hjlabs.in/"><img height="36" src="https://cdn.simpleicons.org/similarweb"/></a>
  <a href="https://wa.me/917016525813"><img height="36" src="https://cdn.simpleicons.org/WhatsApp"/></a>
  <a href="https://t.me/hjlabs"><img height="36" src="https://cdn.simpleicons.org/telegram"/></a>
  <a href="mailto:hemangjoshi37a@gmail.com"><img height="36" src="https://cdn.simpleicons.org/Gmail"/></a> 
  <a href="https://www.linkedin.com/in/hemang-joshi-046746aa"><img height="36" src="https://cdn.simpleicons.org/LinkedIn"/></a>
  <a href="https://www.facebook.com/hemangjoshi37"><img height="36" src="https://cdn.simpleicons.org/facebook"/></a>
  <a href="https://twitter.com/HemangJ81509525"><img height="36" src="https://cdn.simpleicons.org/Twitter"/></a>
  <a href="https://www.tumblr.com/blog/hemangjoshi37a-blog"><img height="36" src="https://cdn.simpleicons.org/tumblr"/></a>
  <a href="https://stackoverflow.com/users/8090050/hemang-joshi"><img height="36" src="https://cdn.simpleicons.org/StackOverflow"/></a>
  <a href="https://www.instagram.com/hemangjoshi37"><img height="36" src="https://cdn.simpleicons.org/Instagram"/></a>
  <a href="https://in.pinterest.com/hemangjoshi37a"><img height="36" src="https://cdn.simpleicons.org/Pinterest"/></a> 
  <a href="http://hemangjoshi.blogspot.com"><img height="36" src="https://cdn.simpleicons.org/Blogger"/></a>
  <a href="https://gitlab.com/hemangjoshi37a"><img height="36" src="https://cdn.simpleicons.org/gitlab"/></a>
</div>

## 📫 Try Our Algo Trading Platform hjAlgos

Ready to elevate your trading strategy? 

<a href="https://hjalgos.hjlabs.in" style="
    display: inline-block;
    padding: 12px 24px;
    background-color: #2563EB;
    color: #FFFFFF;
    text-decoration: none;
    border-radius: 8px;
    font-weight: bold;
    font-size: 16px;
    transition: background-color 0.3s, transform 0.3s;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
">
    Try Our AlgoTrading Platform
</a>

## 💖 Support the Project

If you find pyPortMan helpful for your trading activities, consider supporting the project:

[![PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=5JXC8VRCSUZWJ)

Your support helps us maintain and improve pyPortMan, ensuring it remains a valuable tool for the trading community!
