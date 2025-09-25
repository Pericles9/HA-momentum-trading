"""
Candlestick Chart Viewer GUI
A modern GUI application for visualizing OHLCV data from TimescaleDB as candlestick charts.

Features:
- Search tickers by symbol
- Browse available tickers in a list
- Interactive candlestick charts with volume
- Date range selection
- Real-time data refresh
- Professional chart styling
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import mplfinance as mpf
    MPLFINANCE_AVAILABLE = True
except ImportError:
    MPLFINANCE_AVAILABLE = False
    print("⚠️  mplfinance not available. Install with: pip install mplfinance")

from src.DB.operations import DatabaseOperations

class CandlestickChartViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("🕯️ Candlestick Chart Viewer - HA Momentum Trading")
        self.root.geometry("1400x800")
        self.root.configure(bg='#2b2b2b')
        
        # Initialize database
        self.db_ops = DatabaseOperations()
        
        # Current data
        self.current_symbol = None
        self.current_data = None
        
        # Style configuration
        self.setup_styles()
        
        # Create GUI
        self.create_widgets()
        
        # Load available tickers
        self.refresh_ticker_list()
    
    def setup_styles(self):
        """Configure modern dark theme styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure dark theme colors
        style.configure('TLabel', background='#2b2b2b', foreground='#ffffff')
        style.configure('TFrame', background='#2b2b2b')
        style.configure('TButton', background='#404040', foreground='#ffffff')
        style.configure('TEntry', background='#404040', foreground='#ffffff')
        style.configure('Treeview', background='#3b3b3b', foreground='#ffffff', selectbackground='#505050')
        style.configure('Treeview.Heading', background='#404040', foreground='#ffffff')
        
    def create_widgets(self):
        """Create and arrange GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left panel for controls
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side='left', fill='y', padx=(0, 10))
        
        # Right panel for chart
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side='right', fill='both', expand=True)
        
        self.create_control_panel(left_panel)
        self.create_chart_panel(right_panel)
    
    def create_control_panel(self, parent):
        """Create the left control panel"""
        # Title
        title_label = ttk.Label(parent, text="📊 Chart Controls", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Search section
        search_frame = ttk.LabelFrame(parent, text="🔍 Search Ticker", padding=10)
        search_frame.pack(fill='x', pady=(0, 10))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, 
                                font=('Arial', 10), width=20)
        search_entry.pack(fill='x')
        search_entry.bind('<Return>', self.search_ticker)
        
        search_btn = ttk.Button(search_frame, text="Search", 
                               command=self.search_ticker)
        search_btn.pack(fill='x', pady=(5, 0))
        
        # Ticker list section
        list_frame = ttk.LabelFrame(parent, text="📋 Available Tickers", padding=10)
        list_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Treeview for ticker list
        columns = ('symbol', 'last_update', 'records')
        self.ticker_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        self.ticker_tree.heading('symbol', text='Symbol')
        self.ticker_tree.heading('last_update', text='Last Update')
        self.ticker_tree.heading('records', text='Records')
        
        self.ticker_tree.column('symbol', width=80)
        self.ticker_tree.column('last_update', width=120)
        self.ticker_tree.column('records', width=80)
        
        # Scrollbar for ticker list
        ticker_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.ticker_tree.yview)
        self.ticker_tree.configure(yscrollcommand=ticker_scrollbar.set)
        
        self.ticker_tree.pack(side='left', fill='both', expand=True)
        ticker_scrollbar.pack(side='right', fill='y')
        
        self.ticker_tree.bind('<Double-1>', self.on_ticker_select)
        
        # Date range section
        date_frame = ttk.LabelFrame(parent, text="📅 Date Range", padding=10)
        date_frame.pack(fill='x', pady=(0, 10))
        
        # Days back selector
        ttk.Label(date_frame, text="Days back:").pack(anchor='w')
        self.days_var = tk.StringVar(value='7')
        days_combo = ttk.Combobox(date_frame, textvariable=self.days_var, 
                                 values=['1', '2', '3', '7', '14', '30', '90'], 
                                 width=18, state='readonly')
        days_combo.pack(fill='x', pady=(2, 10))
        
        # Refresh button
        refresh_btn = ttk.Button(date_frame, text="🔄 Refresh Chart", 
                                command=self.refresh_chart)
        refresh_btn.pack(fill='x')
        
        # Info section
        info_frame = ttk.LabelFrame(parent, text="ℹ️ Current Selection", padding=10)
        info_frame.pack(fill='x')
        
        self.info_label = ttk.Label(info_frame, text="No ticker selected", 
                                   font=('Arial', 9), wraplength=200)
        self.info_label.pack(anchor='w')
    
    def create_chart_panel(self, parent):
        """Create the right chart panel"""
        # Chart title
        chart_title = ttk.Label(parent, text="📈 Candlestick Chart", 
                               font=('Arial', 14, 'bold'))
        chart_title.pack(pady=(0, 10))
        
        # Create matplotlib figure with dark theme
        plt.style.use('dark_background')
        self.fig = Figure(figsize=(12, 8), facecolor='#2b2b2b')
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Initialize with empty chart
        self.show_empty_chart()
    
    def show_empty_chart(self):
        """Show empty chart with instructions"""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.text(0.5, 0.5, '🕯️ Select a ticker to view candlestick chart\n\n' +
                          '• Double-click a ticker from the list\n' +
                          '• Or search for a specific symbol',
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=14, color='#888888')
        ax.set_facecolor('#2b2b2b')
        self.canvas.draw()
    
    def refresh_ticker_list(self):
        """Load and display available tickers"""
        try:
            # Clear existing items
            for item in self.ticker_tree.get_children():
                self.ticker_tree.delete(item)
            
            # Query available tickers
            query = """
                SELECT 
                    symbol,
                    MAX(timestamp) as last_update,
                    COUNT(*) as record_count
                FROM ohlcv_data 
                GROUP BY symbol 
                ORDER BY MAX(timestamp) DESC
            """
            
            result = self.db_ops.execute_query(query)
            
            if result:
                for row in result:
                    symbol, last_update, count = row
                    # Format last update
                    if last_update:
                        last_str = last_update.strftime('%Y-%m-%d %H:%M')
                    else:
                        last_str = 'Unknown'
                    
                    self.ticker_tree.insert('', 'end', values=(symbol, last_str, count))
                
                print(f"✅ Loaded {len(result)} tickers")
            else:
                print("⚠️ No tickers found in database")
                
        except Exception as e:
            print(f"❌ Error loading tickers: {e}")
            messagebox.showerror("Database Error", f"Failed to load tickers: {e}")
    
    def search_ticker(self, event=None):
        """Search for a specific ticker"""
        symbol = self.search_var.get().upper().strip()
        if not symbol:
            return
        
        try:
            # Check if ticker exists
            query = """
                SELECT COUNT(*) FROM ohlcv_data WHERE symbol = %s
            """
            result = self.db_ops.execute_query(query, (symbol,))
            
            if result and result[0][0] > 0:
                self.load_ticker_data(symbol)
            else:
                messagebox.showwarning("Ticker Not Found", 
                                     f"No data found for ticker '{symbol}'")
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            messagebox.showerror("Search Error", f"Failed to search ticker: {e}")
    
    def on_ticker_select(self, event):
        """Handle ticker selection from list"""
        selection = self.ticker_tree.selection()
        if selection:
            item = self.ticker_tree.item(selection[0])
            symbol = item['values'][0]
            self.load_ticker_data(symbol)
    
    def load_ticker_data(self, symbol):
        """Load OHLCV data for a ticker"""
        try:
            days_back = int(self.days_var.get())
            start_date = datetime.now() - timedelta(days=days_back)
            
            print(f"🔍 Loading data for {symbol}, {days_back} days back from {start_date}")
            
            query = """
                SELECT timestamp, open_price, high_price, low_price, close_price, volume
                FROM ohlcv_data 
                WHERE symbol = %s AND timestamp >= %s
                ORDER BY timestamp ASC
            """
            
            result = self.db_ops.execute_query(query, (symbol, start_date))
            
            if result:
                print(f"✅ Found {len(result)} records for {symbol}")
                # Convert to DataFrame
                df = pd.DataFrame(result, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df.set_index('timestamp', inplace=True)
                
                self.current_symbol = symbol
                self.current_data = df
                
                # Update info
                self.update_info_display(symbol, len(df))
                
                # Create chart
                self.create_candlestick_chart(df, symbol)
                
                print(f"✅ Loaded {len(df)} records for {symbol}")
            else:
                print(f"⚠️ No data found for {symbol} in last {days_back} days")
                
                # Try to get any data at all for this symbol
                fallback_query = """
                    SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
                    FROM ohlcv_data 
                    WHERE symbol = %s
                """
                fallback_result = self.db_ops.execute_query(fallback_query, (symbol,))
                
                if fallback_result and fallback_result[0][0] > 0:
                    count, min_date, max_date = fallback_result[0]
                    messagebox.showwarning("No Recent Data", 
                                         f"Symbol '{symbol}' has {count} records, but none in the last {days_back} days.\n" +
                                         f"Data range: {min_date} to {max_date}\n\n" +
                                         f"Try increasing the date range.")
                else:
                    messagebox.showwarning("No Data", f"No data found for {symbol}")
                
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            messagebox.showerror("Data Error", f"Failed to load data for {symbol}: {e}")
    
    def update_info_display(self, symbol, record_count):
        """Update the info display"""
        info_text = f"Symbol: {symbol}\n"
        info_text += f"Records: {record_count}\n"
        info_text += f"Range: {self.days_var.get()} days"
        
        if self.current_data is not None and not self.current_data.empty:
            latest = self.current_data.iloc[-1]
            info_text += f"\n\nLatest Price: ${latest['close']:.2f}"
            info_text += f"\nVolume: {latest['volume']:,.0f}"
        
        self.info_label.config(text=info_text)
    
    def create_candlestick_chart(self, df, symbol):
        """Create candlestick chart with volume"""
        try:
            self.fig.clear()
            
            if MPLFINANCE_AVAILABLE and len(df) > 1:
                # Use mplfinance for professional charts
                self.create_mplfinance_chart(df, symbol)
            else:
                # Fallback to matplotlib
                self.create_matplotlib_chart(df, symbol)
                
            self.canvas.draw()
            
        except Exception as e:
            print(f"❌ Chart creation error: {e}")
            self.show_error_chart(f"Chart Error: {e}")
    
    def create_mplfinance_chart(self, df, symbol):
        """Create chart using mplfinance"""
        # Configure mplfinance style
        mc = mpf.make_marketcolors(up='#00ff88', down='#ff4444', 
                                  edge='inherit', wick={'up':'#00ff88', 'down':'#ff4444'},
                                  volume='#888888')
        s = mpf.make_mpf_style(marketcolors=mc, figcolor='#2b2b2b', 
                              facecolor='#2b2b2b', gridcolor='#444444')
        
        # Create subplots
        ax1 = self.fig.add_subplot(2, 1, 1)  # Price chart
        ax2 = self.fig.add_subplot(2, 1, 2)  # Volume chart
        
        # Plot candlesticks
        mpf.plot(df, type='candle', ax=ax1, volume=ax2, style=s, 
                returnfig=True, figsize=(12, 8))
        
        ax1.set_title(f'{symbol} - Candlestick Chart', color='white', fontsize=14)
        ax1.grid(True, alpha=0.3)
        ax2.set_title('Volume', color='white', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Adjust layout
        self.fig.tight_layout()
    
    def create_matplotlib_chart(self, df, symbol):
        """Fallback matplotlib chart"""
        ax1 = self.fig.add_subplot(2, 1, 1)
        ax2 = self.fig.add_subplot(2, 1, 2)
        
        # Simple line chart for price
        ax1.plot(df.index, df['close'], color='#00ff88', linewidth=2, label='Close Price')
        ax1.fill_between(df.index, df['low'], df['high'], alpha=0.3, color='#00ff88')
        ax1.set_title(f'{symbol} - Price Chart', color='white', fontsize=14)
        ax1.set_ylabel('Price ($)', color='white')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Volume bars
        ax2.bar(df.index, df['volume'], color='#888888', alpha=0.7)
        ax2.set_title('Volume', color='white', fontsize=12)
        ax2.set_ylabel('Volume', color='white')
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis
        ax1.tick_params(colors='white')
        ax2.tick_params(colors='white')
        
        self.fig.tight_layout()
    
    def show_error_chart(self, error_msg):
        """Show error message in chart area"""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.text(0.5, 0.5, f'❌ {error_msg}',
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=12, color='#ff4444')
        ax.set_facecolor('#2b2b2b')
        self.canvas.draw()
    
    def refresh_chart(self):
        """Refresh the current chart"""
        if self.current_symbol:
            self.load_ticker_data(self.current_symbol)
        else:
            messagebox.showinfo("No Selection", "Please select a ticker first")

def main():
    """Main function to run the application"""
    try:
        root = tk.Tk()
        app = CandlestickChartViewer(root)
        
        # Center window
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        print("🚀 Candlestick Chart Viewer started")
        print("📊 Features:")
        print("  • Search tickers by symbol")
        print("  • Browse available tickers")
        print("  • Interactive candlestick charts")
        print("  • Adjustable date ranges")
        print("  • Real-time data refresh")
        
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Application error: {e}")
        messagebox.showerror("Application Error", f"Failed to start application: {e}")

if __name__ == "__main__":
    main()