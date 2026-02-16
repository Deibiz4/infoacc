import json
import sys
import os
import time

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️ yfinance no instalado. Validación limitada a chequeos lógicos.")

def validate_prices(file_path):
    print(f"🔍 Validando y filtrando precios en: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ Error: Archivo {file_path} no encontrado.")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            signals = json.load(f)
    except Exception as e:
        print(f"❌ Error leyendo JSON: {e}")
        return False

    valid_signals = []
    signals_removed = False

    # First pass: Logical checks
    pre_filtered_signals = []
    for signal in signals:
        ticker = signal.get('ticker', 'UNKNOWN')
        entry = signal.get('entry_price', 0)
        stop = signal.get('stop_loss', 0)
        
        # Regla 1: Precio = 0
        if entry == 0 or stop == 0:
            print(f"🗑️ Eliminando señal {ticker}: Precio o Stop es 0.00")
            signals_removed = True
            continue 
            
        pre_filtered_signals.append(signal)

    # Second pass: Real Market Check (if available)
    final_signals = []
    tickers_to_check = [s.get('ticker') for s in pre_filtered_signals if s.get('ticker') != 'UNKNOWN']
    
    current_prices = {}
    if YFINANCE_AVAILABLE and tickers_to_check:
        print(f"☁️ Verificando con Mercado Real (yfinance): {tickers_to_check}")
        try:
            data = yf.download(tickers_to_check, period="1d", progress=False)['Close']
            
            if len(tickers_to_check) == 1:
                last_price = data.iloc[-1].item() if not data.empty else None
                if last_price:
                    current_prices[tickers_to_check[0]] = last_price
            else:
                 if not data.empty:
                    last_row = data.iloc[-1]
                    for t in tickers_to_check:
                        if t in last_row:
                            current_prices[t] = last_row[t]
        except Exception as e:
            print(f"⚠️ Error conectando con YFinance: {e}. Se omitirá chequeo de mercado (Fallback).")

    for signal in pre_filtered_signals:
        ticker = signal.get('ticker')
        entry = signal.get('entry_price')
        
        is_valid = True
        
        if YFINANCE_AVAILABLE and ticker in current_prices:
            market_price = current_prices[ticker]
            if entry > 0 and market_price > 0:
                diff_pct = abs(market_price - entry) / market_price
                
                # Desviación > 15% elimina la señal
                if diff_pct > 0.15:
                    print(f"🗑️ Eliminando señal {ticker}: Precio Señal (${entry}) difiere {diff_pct:.1%} de Mercado (${market_price:.2f})")
                    is_valid = False
                    signals_removed = True
                elif diff_pct > 0.05:
                     print(f"⚠️ Advertencia {ticker}: Desviación del {diff_pct:.1%}")

        if is_valid:
            final_signals.append(signal)

    # Save changes if any signals were removed
    if signals_removed:
        print("💾 Guardando señales filtradas...")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(final_signals, f, indent=4)
        except Exception as e:
            print(f"❌ Error guardando JSON: {e}")
            return False

    if not final_signals:
        print("\n❌ CRÍTICO: No quedan señales válidas después del filtrado.")
        return False

    print(f"\n✅ Validación completada. {len(final_signals)} señales válidas.")
    return True

if __name__ == "__main__":
    signals_file = "d:/Docker/infoacc/data/signals.json"
    if validate_prices(signals_file):
        sys.exit(0)
    else:
        sys.exit(1)
