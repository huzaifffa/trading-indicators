from flask import Flask, render_template, request
import yfinance as yf
import plotly.graph_objs as go
from datetime import datetime, timedelta
import numpy as np

app = Flask(__name__)

# Define available tickers, time periods, and intervals
tickers = ['BTC-USD', 'ETH-USD', 'AAPL', 'GOOGL', 'MSFT']
time_periods = {'30 days': 30, '60 days': 60, '100 days': 100, '200 days': 200}
intervals = ['1d', '1wk', '1mo']

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Get user inputs
        ticker = request.form["ticker"]
        days = int(request.form["time_period"])
        interval = request.form["interval"]

        # Checkbox indicators
        calc_supertrend = 'supertrend' in request.form
        calc_macd = 'macd' in request.form
        calc_ma = 'ma' in request.form

        # Fetch historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval)

        # Calculate indicators based on user selection
        buy_signal = sell_signal = None
        if calc_supertrend:
            data['High-Low'] = data['High'] - data['Low']
            data['High-Prev Close'] = np.abs(data['High'] - data['Close'].shift(1))
            data['Low-Prev Close'] = np.abs(data['Low'] - data['Close'].shift(1))
            data['TR'] = data[['High-Low', 'High-Prev Close', 'Low-Prev Close']].max(axis=1)
            data['ATR'] = data['TR'].rolling(window=10).mean()

            data['Up'] = data['Close'] - (3.0 * data['ATR'])  # Default multiplier = 3.0
            data['Dn'] = data['Close'] + (3.0 * data['ATR'])

            data['Supertrend'] = np.nan
            data['Trend'] = 1

            for i in range(1, len(data)):
                if data['Close'][i] > data['Supertrend'][i - 1]:
                    data['Supertrend'][i] = max(data['Up'][i], data['Supertrend'][i - 1])
                else:
                    data['Supertrend'][i] = min(data['Dn'][i], data['Supertrend'][i - 1])

                data['Trend'][i] = 1 if data['Close'][i] > data['Supertrend'][i] else -1

            # Buy and sell signals
            buy_signal = (data['Trend'] == 1) & (data['Trend'].shift(1) == -1)
            sell_signal = (data['Trend'] == -1) & (data['Trend'].shift(1) == 1)

        if calc_macd:
            data['EMA12'] = data['Close'].ewm(span=12, adjust=False).mean()
            data['EMA26'] = data['Close'].ewm(span=26, adjust=False).mean()
            data['MACD'] = data['EMA12'] - data['EMA26']
            data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
            data['MACD Histogram'] = data['MACD'] - data['Signal']

        if calc_ma:
            data['MA9'] = data['Close'].rolling(window=9).mean()
            data['MA26'] = data['Close'].rolling(window=26).mean()

        # Create chart
        fig_data = []

        # Candlestick chart
        fig_data.append(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='Price'
        ))

        # Add indicators if they were selected
        if calc_supertrend:
            fig_data.append(go.Scatter(
                x=data.index,
                y=data['Supertrend'],
                mode='lines',
                name='Supertrend',
                line=dict(color='cyan')
            ))

            # Buy and sell signal markers
            fig_data.append(go.Scatter(
                x=data.index[buy_signal],
                y=data['Close'][buy_signal],
                mode='markers',
                name='Buy Signal',
                marker=dict(color='green', size=10, symbol='triangle-up')
            ))
            fig_data.append(go.Scatter(
                x=data.index[sell_signal],
                y=data['Close'][sell_signal],
                mode='markers',
                name='Sell Signal',
                marker=dict(color='red', size=10, symbol='triangle-down')
            ))

        if calc_macd:
            fig_data.append(go.Scatter(x=data.index, y=data['MACD'], mode='lines', name='MACD Line', line=dict(color='green')))
            fig_data.append(go.Scatter(x=data.index, y=data['Signal'], mode='lines', name='Signal Line', line=dict(color='orange')))
            fig_data.append(go.Bar(x=data.index, y=data['MACD Histogram'], name='MACD Histogram', marker=dict(color='red')))

        if calc_ma:
            fig_data.append(go.Scatter(x=data.index, y=data['MA9'], mode='lines', name='9-Day MA', line=dict(color='blue')))
            fig_data.append(go.Scatter(x=data.index, y=data['MA26'], mode='lines', name='26-Day MA', line=dict(color='purple')))

        # Create the figure
        fig = go.Figure(data=fig_data)
        fig.update_layout(title=f"{ticker} Price with Indicators and Buy/Sell Signals", xaxis_title="Date", yaxis_title="Price", xaxis_rangeslider_visible=False)

        # Render the chart in the browser
        graph_html = fig.to_html(full_html=False)
        return render_template("index.html", tickers=tickers, time_periods=time_periods, intervals=intervals, graph=graph_html)

    # Initial load
    return render_template("index.html", tickers=tickers, time_periods=time_periods, intervals=intervals, graph=None)

if __name__ == "__main__":
    app.run(debug=True, port=8000)
