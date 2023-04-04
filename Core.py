from binance.client import Client
from binance.enums import *
import time

# API anahtarları
api_key = ''
api_secret = ''

# Binance API istemcisine bağlanma
client = Client(api_key, api_secret)

# İşlem çifti
symbol = 'CFXBUSD'

# ZeroMACD parametreleri
fast_length = 12
slow_length = 26
signal_length = 9

# Geçmiş kline'ları alma
def get_historical_klines(interval):
    klines = client.get_historical_klines(symbol, interval, "1 gün önce UTC")
    return klines

# ZeroMACD hesaplama
def calculate_zeromacd(klines):
    # Kline'lardan kapanış fiyatlarını ayırın
    close_prices = []
    for kline in klines:
        close_prices.append(float(kline[4]))
    # Hızlı uzunluk için EMA hesaplayın
    ema_fast = sum(close_prices[-fast_length:]) / fast_length
    multiplier_fast = 2 / (fast_length + 1)
    for i in range(fast_length + 1, len(close_prices) + 1):
        ema_fast = (close_prices[i - 1] - ema_fast) * multiplier_fast + ema_fast
    # Yavaş uzunluk için EMA hesaplayın
    ema_slow = sum(close_prices[-slow_length:]) / slow_length
    multiplier_slow = 2 / (slow_length + 1)
    for i in range(slow_length + 1, len(close_prices) + 1):
        ema_slow = (close_prices[i - 1] - ema_slow) * multiplier_slow + ema_slow
    # MACD'yi hesaplamak için EMA'ları birbirinden çıkarın
    macd = ema_fast - ema_slow
    # Sinyal çizgisi için MACD'nin EMA'sını hesaplayın
    ema_signal = macd
    multiplier_signal = 2 / (signal_length + 1)
    for i in range(signal_length + 1, len(close_prices) + 1):
        ema_signal = (macd - ema_signal) * multiplier_signal + ema_signal
    # ZeroMACD'yi elde etmek için MACD'nin EMA'sından MACD'yi çıkarın
    zeromacd = macd - ema_signal
    return zeromacd

# Mevcut hesap bakiyesini alma
def get_balance(asset):
    balance = client.get_asset_balance(asset=asset)
    return float(balance['free'])

# Limitli alım emri verme
def limit_buy(quantity, price):
    order = client.create_order(
        symbol=symbol,
        side=SIDE_BUY,
        type=ORDER_TYPE_LIMIT,
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=quantity,
        price=price)
    return order['orderId']

# Limitli satım emri verme
def limit_sell(quantity, price):
    order = client.create_order(
        symbol=symbol,
        side=SIDE_SELL,
        type=ORDER_TYPE_LIMIT,
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=quantity,
        price=price)
    return order['orderId']

# OCO satış emri verme
def oco_sell(quantity, limit_price, stop_price):
    order = client.create_oco_order(
        symbol=symbol,
        side=SIDE_SELL,
        quantity=quantity,
        price=limit_price,
        stopPrice=stop_price,
        stopLimitPrice=stop_price,
        stopLimitTimeInForce=TIME_IN_FORCE_GTC)
    return order

# Tüm siparişleri iptal etme
def cancel_all_orders():
    open_orders = client.get_open_orders(symbol=symbol)
    for order in open_orders:
        client.cancel_order(symbol=symbol, orderId=order['orderId'])
    print("Tüm açık emirler iptal edildi.")

# Ana döngü
while True:
    try:
        # Geçmiş kline'ları alma
        klines_15m = get_historical_klines(KLINE_INTERVAL_15MINUTE)
        # ZeroMACD hesapla
        zeromacd = calculate_zeromacd(klines_15m)
        # Alım sinyali için kontrol et
        if zeromacd > 0:
            # Hesap bakiyesini alma
            busd_balance = get_balance('BUSD')
            # Mevcut BUSD'ye göre alım miktarını hesapla
            quantity = round(busd_balance / float(klines_15m[-1][4]))
            # Limitli alım emri ver
            limit_price = round(float(klines_15m[-1][4]) * 1.01, 2)
            order_id = limit_buy(quantity, limit_price)
            # Emrin doldurulmasını bekle
            while True:
                time.sleep(5)
                order = client.get_order(symbol=symbol, orderId=order_id)
                if order['status'] == 'FILLED':
                    # Satış fiyatlarını hesapla
                    limit_price = round(float(klines_15m[-1][4]) * 1.02, 2)
                    stop_price = round(float(klines_15m[-1][4]) * 0.99, 2)
                    # OCO satış emri ver
                    oco_sell(quantity, limit_price, stop_price)
                    break
        # Satış sinyali için kontrol et
        elif zeromacd < 0:
            # Tüm siparişleri iptal et
            cancel_all_orders()
            # Hesap bakiyesini alma
            cfx_balance = get_balance('CFX')
            # Limitli satış emri ver
            limit_price = round(float(klines_15m[-1][4]) * 0.98, 2)
            order_id = limit_sell(cfx_balance, limit_price)
        # Tekrar kontrol etmek için 15 dakika bekle
        print('Sistem Hesapladı.')
        time.sleep(0.5)
    except Exception as e:
        print(e)
