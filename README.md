# pyPortMan 📊💼

![GitHub stars](https://img.shields.io/github/stars/hemangjoshi37a/pyPortMan?style=social)
![GitHub forks](https://img.shields.io/github/forks/hemangjoshi37a/pyPortMan?style=social)
![GitHub issues](https://img.shields.io/github/issues/hemangjoshi37a/pyPortMan)
![GitHub license](https://img.shields.io/github/license/hemangjoshi37a/pyPortMan)

![pyPortMan Logo](https://user-images.githubusercontent.com/12392345/125978523-eb21fa0b-e1c0-4af9-920e-4a418e273f26.png)

> Python Zerodha Multi-Account Portfolio Management Software (Jupyter Notebook)

pyPortMan is a powerful tool designed to help you manage multiple Zerodha trading accounts effortlessly. With automated GTT (Good Till Triggered) order placement and portfolio tracking, it's perfect for traders and investors looking to streamline their workflow.

## 🚀 Features

- 📈 Multi-account management
- 🤖 Automated GTT order placement
- 📊 Real-time portfolio tracking
- 💹 Percentage-based allocation across accounts
- 📱 Telegram integration for alerts

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
   - Add your Zerodha credentials for each account

## 🏃‍♂️ Quick Start

1. Start the Jupyter Notebook:
   ```bash
   jupyter notebook hjOpenTerminal.ipynb
   ```

2. Configure your stock list:
   - Open `stocks.xlsx`
   - Add the stocks you want to trade

3. Run all cells in `hjOpenTerminal.ipynb`

4. Monitor your portfolio and GTT orders in real-time!

## 📖 How It Works

1. **Initial Setup**: The software reads your Zerodha authentication details and stock list from Excel files.
2. **GTT Placement**: It automatically places GTT orders based on the specifications in your stock list.
3. **Buy-Sell Cycle**:
   - Initial GTT buy orders are placed.
   - When a buy order is triggered, a corresponding sell GTT is placed.
   - Stocks are bought and sold based on the percentage allocation set in the Excel file.

## 🔧 Advanced Usage

### Customizing Allocations

In `stocks.xlsx`, you can set custom percentage allocations for each stock. For example:

| Symbol | Percent | Buy Price | Sell Price |
|--------|---------|-----------|------------|
| RELIANCE | 10 | 2000 | 2100 |

This will allocate 10% of the available funds in each account for RELIANCE stock.

### Telegram Alerts

To set up Telegram alerts:
1. Create a Telegram bot and get the API key
2. Add your Telegram chat ID and bot API key to `config.py`

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [Zerodha Kite API](https://kite.trade/)
- [Jugaad Trader](https://github.com/jugaad-py/jugaad-trader)

## 💬 Get in Touch

- 📧 Email: [hemangjoshi37a@gmail.com](mailto:hemangjoshi37a@gmail.com)
- 📱 Telegram: [+919409077371](https://t.me/+919409077371)
- 💼 Place a custom order on [Fiverr](https://www.fiverr.com/share/7KpVd1)
- 📢 Join our [Telegram Stock Market Tips](https://t.me/joinchat/Xad-Dry-GlI2MGFl)

## 💖 Support the Project

If you find this project helpful, consider supporting us:

[![PayPal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=5JXC8VRCSUZWJ)

Your support helps us maintain and improve pyPortMan!
