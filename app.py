import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ============================================================
# إعدادات الصفحة
# ============================================================
st.set_page_config(
    page_title="أداة التحليل المالي",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# الدوال المساعدة
# ============================================================
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_indicators(df):
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['MA100'] = df['Close'].rolling(window=100).mean()

    df['RSI'] = calculate_rsi(df['Close'], 14)

    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']

    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)

    lowest_low = df['Low'].rolling(window=14).min()
    highest_high = df['High'].rolling(window=14).max()
    df['%K'] = 100 * ((df['Close'] - lowest_low) / (highest_high - lowest_low))
    df['%D'] = df['%K'].rolling(window=3).mean()

    df['TR1'] = df['High'] - df['Low']
    df['TR2'] = abs(df['High'] - df['Close'].shift(1))
    df['TR3'] = abs(df['Low'] - df['Close'].shift(1))
    df['TrueRange'] = df[['TR1', 'TR2', 'TR3']].max(axis=1)
    df['ATR'] = df['TrueRange'].rolling(window=14).mean()

    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
    df['Support'] = df['Low'].rolling(window=20).min()
    df['Resistance'] = df['High'].rolling(window=20).max()

    return df

def get_fibonacci_levels(df, lookback=60):
    recent_high = df['High'].iloc[-lookback:].max()
    recent_low = df['Low'].iloc[-lookback:].min()
    diff = recent_high - recent_low
    return {
        '0%': recent_high, '23.6%': recent_high - 0.236 * diff,
        '38.2%': recent_high - 0.382 * diff, '50%': recent_high - 0.5 * diff,
        '61.8%': recent_high - 0.618 * diff, '100%': recent_low
    }

def generate_signals(df):
    df['Signal'] = 0
    df.loc[(df['MACD'] > df['MACD_Signal']) & 
           (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1)) & 
           (df['RSI'] > 30) & (df['RSI'] < 70), 'Signal'] = 1
    df.loc[(df['MACD'] < df['MACD_Signal']) & 
           (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1)) & 
           (df['RSI'] > 70), 'Signal'] = -1
    return df

# ============================================================
# الشريط الجانبي
# ============================================================
st.sidebar.title("⚙️ الإعدادات")

symbol = st.sidebar.text_input("رمز السهم", value="AAPL").upper()

period_options = {
    "1 شهر": "1mo", "3 أشهر": "3mo", "6 أشهر": "6mo",
    "1 سنة": "1y", "2 سنة": "2y", "5 سنوات": "5y"
}
period_name = st.sidebar.selectbox("الفترة", list(period_options.keys()))
period = period_options[period_name]

st.sidebar.markdown("---")
st.sidebar.subheader("📊 المؤشرات")
show_ma = st.sidebar.checkbox("المتوسطات المتحركة", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands", value=True)
show_rsi = st.sidebar.checkbox("RSI", value=True)
show_macd = st.sidebar.checkbox("MACD", value=True)
show_stochastic = st.sidebar.checkbox("Stochastic", value=True)
show_volume = st.sidebar.checkbox("حجم التداول", value=True)
show_atr = st.sidebar.checkbox("ATR", value=True)

st.sidebar.markdown("---")
refresh = st.sidebar.button("🔄 تحديث البيانات", type="primary")

# ============================================================
# العنوان الرئيسي
# ============================================================
st.title("📊 أداة التحليل المالي المتكاملة")
st.markdown("---")

# ============================================================
# جلب البيانات
# ============================================================
try:
    with st.spinner("جاري جلب البيانات..."):
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)

        if df.empty:
            st.error(f"❌ لم يتم العثور على بيانات للرمز: {symbol}")
            st.stop()

        df = calculate_indicators(df)
        df = generate_signals(df)
        fib_levels = get_fibonacci_levels(df)

except Exception as e:
    st.error(f"❌ خطأ: {str(e)}")
    st.stop()

# ============================================================
# معلومات السهم
# ============================================================
col1, col2, col3, col4, col5 = st.columns(5)

current_price = df['Close'].iloc[-1]
prev_close = df['Close'].iloc[-2]
change = current_price - prev_close
change_pct = (change / prev_close) * 100

with col1:
    st.metric(label="السعر الحالي", value=f"${current_price:.2f}",
              delta=f"{change:.2f} ({change_pct:.2f}%)")
with col2:
    st.metric("أعلى سعر اليوم", f"${df['High'].iloc[-1]:.2f}")
with col3:
    st.metric("أدنى سعر اليوم", f"${df['Low'].iloc[-1]:.2f}")
with col4:
    st.metric("حجم التداول", f"{df['Volume'].iloc[-1]:,.0f}")
with col5:
    st.metric("ATR", f"${df['ATR'].iloc[-1]:.2f}")

st.markdown("---")

# ============================================================
# الرسم البياني
# ============================================================
st.subheader("📈 الرسم البياني التفاعلي")

fig = make_subplots(
    rows=6, cols=1, shared_xaxes=True, vertical_spacing=0.02,
    row_heights=[0.4, 0.12, 0.12, 0.12, 0.12, 0.12],
    subplot_titles=("الشموع اليومية", "حجم التداول", "RSI", "MACD", "Stochastic", "ATR")
)

fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    name="الشموع", increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
), row=1, col=1)

if show_ma:
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name="MA5", line=dict(color='blue', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name="MA20", line=dict(color='orange', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], name="MA50", line=dict(color='red', width=1.5)), row=1, col=1)

if show_bb:
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], name="BB Upper", line=dict(color='gray', width=1, dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], name="BB Lower", line=dict(color='gray', width=1, dash='dash')), row=1, col=1)

buy_signals = df[df['Signal'] == 1]
sell_signals = df[df['Signal'] == -1]

if not buy_signals.empty:
    fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Low'] * 0.99,
        mode='markers', marker=dict(symbol='triangle-up', size=15, color='green'), name='شراء'), row=1, col=1)
if not sell_signals.empty:
    fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['High'] * 1.01,
        mode='markers', marker=dict(symbol='triangle-down', size=15, color='red'), name='بيع'), row=1, col=1)

if show_volume:
    colors = ['#26a69a' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ef5350' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color=colors), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Volume_MA20'], name="Volume MA20", line=dict(color='blue', width=1)), row=2, col=1)

if show_rsi:
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='purple', width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

if show_macd:
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="MACD", line=dict(color='blue', width=1.5)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], name="Signal", line=dict(color='red', width=1.5)), row=4, col=1)
    colors_macd = ['#26a69a' if h >= 0 else '#ef5350' for h in df['MACD_Histogram']]
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Histogram'], name="Histogram", marker_color=colors_macd), row=4, col=1)

if show_stochastic:
    fig.add_trace(go.Scatter(x=df.index, y=df['%K'], name="%K", line=dict(color='blue', width=1.5)), row=5, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['%D'], name="%D", line=dict(color='red', width=1.5)), row=5, col=1)
    fig.add_hline(y=80, line_dash="dash", line_color="red", row=5, col=1)
    fig.add_hline(y=20, line_dash="dash", line_color="green", row=5, col=1)

if show_atr:
    fig.add_trace(go.Scatter(x=df.index, y=df['ATR'], name="ATR", line=dict(color='orange', width=1.5), fill='tozeroy'), row=6, col=1)

fig.update_layout(height=1200, showlegend=True, xaxis_rangeslider_visible=False,
                  title_text=f"{symbol} - التحليل الفني الشامل", title_x=0.5, template="plotly_white")
fig.update_xaxes(rangeslider_visible=False)

st.plotly_chart(fig, use_container_width=True)

# ============================================================
# ملخص التحليل
# ============================================================
st.markdown("---")
st.subheader("📊 ملخص التحليل")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📈 المتوسطات المتحركة")
    ma_data = {"MA5": df['MA5'].iloc[-1], "MA10": df['MA10'].iloc[-1],
               "MA20": df['MA20'].iloc[-1], "MA50": df['MA50'].iloc[-1], "MA100": df['MA100'].iloc[-1]}
    for name, value in ma_data.items():
        if not np.isnan(value):
            status = "✅" if current_price > value else "❌"
            st.write(f"{status} **{name}**: ${value:.2f}")

with col2:
    st.markdown("### 📊 المؤشرات")
    rsi_val = df['RSI'].iloc[-1]
    macd_val = df['MACD'].iloc[-1]
    macd_sig = df['MACD_Signal'].iloc[-1]
    stoch_k = df['%K'].iloc[-1]
    st.write(f"**RSI**: {rsi_val:.2f}")
    st.write(f"**MACD**: {macd_val:.4f}")
    st.write(f"**Signal**: {macd_sig:.4f}")
    st.write(f"**Stochastic**: {stoch_k:.2f}")

with col3:
    st.markdown("### 📊 فيبوناتشي")
    for level, price in fib_levels.items():
        st.write(f"**{level}**: ${price:.2f}")

# ============================================================
# إدارة المخاطر
# ============================================================
st.markdown("---")
st.subheader("⚠️ إدارة المخاطر")

support = df['Support'].iloc[-1]
resistance = df['Resistance'].iloc[-1]
risk = current_price - support
reward = resistance - current_price
rr_ratio = reward / risk if risk > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Stop Loss", f"${support:.2f}")
col2.metric("Take Profit", f"${resistance:.2f}")
col3.metric("المخاطرة", f"${risk:.2f}")
col4.metric("Risk/Reward", f"{rr_ratio:.2f}", 
            delta="✅ جيد" if rr_ratio >= 2 else "⚠️ مقبول" if rr_ratio >= 1 else "❌ سيئ")

# ============================================================
# التقييم النهائي
# ============================================================
st.markdown("---")
st.subheader("🎯 التقييم النهائي")

bullish = sum([
    current_price > df['MA20'].iloc[-1],
    current_price > df['MA50'].iloc[-1],
    macd_val > macd_sig,
    30 < rsi_val < 70,
    current_price < df['BB_Lower'].iloc[-1] * 1.02,
    stoch_k < 20
])

bearish = sum([
    current_price < df['MA20'].iloc[-1],
    current_price < df['MA50'].iloc[-1],
    macd_val < macd_sig,
    rsi_val > 70,
    current_price > df['BB_Upper'].iloc[-1] * 0.98,
    stoch_k > 80
])

if bullish > bearish + 1:
    final, color = "✅ صاعد بقوة", "green"
elif bullish > bearish:
    final, color = "⚠️ مائل للصعود", "lightgreen"
elif bearish > bullish + 1:
    final, color = "❌ هابط بقوة", "red"
elif bearish > bullish:
    final, color = "⚠️ مائل للهبوط", "orange"
else:
    final, color = "⚖️ متذبذب/محايد", "gray"

st.markdown(f"<h2 style='text-align: center; color: {color};'>{final}</h2>", unsafe_allow_html=True)
st.write(f"إشارات صاعدة: {bullish} | إشارات هابطة: {bearish}")

st.markdown("---")
st.warning("⚠️ هذا تحليل تعليمي فقط، ليس توصية شراء/بيع!")

with st.expander("📋 عرض البيانات الخام"):
    st.dataframe(df.tail(20))
