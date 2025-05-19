import tkinter as tk
from tkinter import ttk
import threading
import asyncio
import logging

import sys
import os 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.order_book_manager import OrderBookManager
from src.websocket_handler import connect_and_listen

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - [%(name)s:%(threadName)s] - %(message)s')
logger = logging.getLogger(__name__)

class TradingSimulatorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("GoQuant Trade Simulator")
        self.geometry("850x650")

        self.order_book = OrderBookManager()
        self.websocket_thread = None
        self.loop = None
        self.is_connected_with_symbol = False # Flag to track if symbol has been reported

        self.exchange_var = tk.StringVar(value="OKX")
        self.spot_asset_var = tk.StringVar(value="BTC-USDT-SWAP") # This is the symbol we expect
        self.order_type_var = tk.StringVar(value="Market")
        self.quantity_usd_var = tk.StringVar(value="100")
        self.volatility_var = tk.StringVar(value="0.02")
        self.fee_tier_var = tk.StringVar() 

        self.slippage_var = tk.StringVar(value="N/A")
        self.fees_var = tk.StringVar(value="N/A")
        self.market_impact_var = tk.StringVar(value="N/A")
        self.net_cost_var = tk.StringVar(value="N/A")
        self.maker_taker_proportion_var = tk.StringVar(value="N/A")
        self.internal_latency_var = tk.StringVar(value="N/A")
        
        self.timestamp_var = tk.StringVar(value="N/A")
        self.current_best_bid_var = tk.StringVar(value="N/A")
        self.current_best_ask_var = tk.StringVar(value="N/A")
        self.current_spread_var = tk.StringVar(value="N/A")

        self._setup_ui()
        self._start_websocket_connection()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_ui(self):
        # ... (UI setup code remains the same as before) ...
        # Configure main window grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1, uniform="panel_group") 
        self.grid_columnconfigure(1, weight=2, uniform="panel_group") 

        # --- Left Panel (Inputs) ---
        self.input_panel = ttk.LabelFrame(self, text="Input Parameters", padding="10")
        self.input_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.input_panel.grid_columnconfigure(0, weight=0) 
        self.input_panel.grid_columnconfigure(1, weight=1) 

        row_num_input = 0
        ttk.Label(self.input_panel, text="Exchange:").grid(row=row_num_input, column=0, sticky="w", pady=3)
        ttk.Label(self.input_panel, textvariable=self.exchange_var).grid(row=row_num_input, column=1, sticky="ew", pady=3)
        row_num_input += 1

        ttk.Label(self.input_panel, text="Spot Asset:").grid(row=row_num_input, column=0, sticky="w", pady=3)
        ttk.Label(self.input_panel, textvariable=self.spot_asset_var).grid(row=row_num_input, column=1, sticky="ew", pady=3)
        row_num_input += 1

        ttk.Label(self.input_panel, text="Order Type:").grid(row=row_num_input, column=0, sticky="w", pady=3)
        ttk.Label(self.input_panel, textvariable=self.order_type_var).grid(row=row_num_input, column=1, sticky="ew", pady=3)
        row_num_input += 1

        ttk.Label(self.input_panel, text="Quantity (USD):").grid(row=row_num_input, column=0, sticky="w", pady=3)
        ttk.Entry(self.input_panel, textvariable=self.quantity_usd_var).grid(row=row_num_input, column=1, sticky="ew", pady=3)
        row_num_input += 1

        ttk.Label(self.input_panel, text="Volatility (e.g., 0.02):").grid(row=row_num_input, column=0, sticky="w", pady=3)
        ttk.Entry(self.input_panel, textvariable=self.volatility_var).grid(row=row_num_input, column=1, sticky="ew", pady=3)
        row_num_input += 1
        
        ttk.Label(self.input_panel, text="Fee Tier:").grid(row=row_num_input, column=0, sticky="w", pady=3)
        fee_tier_options = ["Regular User LV1", "Regular User LV2", "Regular User LV3", 
                            "VIP 1", "VIP 2", "VIP 3", "VIP 4", "VIP 5", "VIP 6", "VIP 7", "VIP 8", "Custom"]
        fee_tier_combobox = ttk.Combobox(self.input_panel, textvariable=self.fee_tier_var, values=fee_tier_options, state="readonly")
        fee_tier_combobox.grid(row=row_num_input, column=1, sticky="ew", pady=3)
        fee_tier_combobox.set("Regular User LV1") 
        self.fee_tier_var.set("Regular User LV1") 
        row_num_input += 1
        
        self.input_panel.grid_rowconfigure(row_num_input, weight=1)

        # --- Right Panel (Outputs) ---
        self.output_panel = ttk.LabelFrame(self, text="Processed Outputs & Market Data", padding="10")
        self.output_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.output_panel.grid_columnconfigure(0, weight=0) 
        self.output_panel.grid_columnconfigure(1, weight=1)

        row_num_output = 0
        
        ttk.Label(self.output_panel, text="Market Data:", font=("Arial", 12, "bold")).grid(row=row_num_output, column=0, columnspan=2, sticky="w", pady=(0,5))
        row_num_output += 1
        
        ttk.Label(self.output_panel, text="Timestamp:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.timestamp_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Best Bid:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.current_best_bid_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Best Ask:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.current_best_ask_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1
        
        ttk.Label(self.output_panel, text="Spread:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.current_spread_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1
        
        ttk.Separator(self.output_panel, orient='horizontal').grid(row=row_num_output, column=0, columnspan=2, sticky='ew', pady=10)
        row_num_output +=1

        ttk.Label(self.output_panel, text="Transaction Cost Estimates:", font=("Arial", 12, "bold")).grid(row=row_num_output, column=0, columnspan=2, sticky="w", pady=(5,5))
        row_num_output += 1

        ttk.Label(self.output_panel, text="Expected Slippage:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.slippage_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Expected Fees:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.fees_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Expected Market Impact:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.market_impact_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Net Cost:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.net_cost_var, font=("Arial", 10, "bold")).grid(row=row_num_output, column=1, sticky="ew", pady=2) 
        row_num_output += 1
        
        ttk.Separator(self.output_panel, orient='horizontal').grid(row=row_num_output, column=0, columnspan=2, sticky='ew', pady=10)
        row_num_output +=1

        ttk.Label(self.output_panel, text="Other Metrics:", font=("Arial", 12, "bold")).grid(row=row_num_output, column=0, columnspan=2, sticky="w", pady=(5,5))
        row_num_output += 1

        ttk.Label(self.output_panel, text="Maker/Taker Proportion:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.maker_taker_proportion_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Internal Latency (ms):").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.internal_latency_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1
        
        self.output_panel.grid_rowconfigure(row_num_output, weight=1)

        # --- Status Bar ---
        self.status_bar_text = tk.StringVar(value="Status: Initializing...")
        self.status_bar = ttk.Label(self, textvariable=self.status_bar_text, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)


    def _start_websocket_connection(self):
        self.status_bar_text.set("Status: Connecting to WebSocket...")
        self.is_connected_with_symbol = False # Reset flag
        self.loop = asyncio.new_event_loop()
        
        self.websocket_thread = threading.Thread(
            target=self._run_websocket_loop, 
            args=(self.loop,), 
            daemon=True
        )
        self.websocket_thread.start()
        logger.info("WebSocket thread started.")

    def _run_websocket_loop(self, loop):
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                connect_and_listen(self.order_book, self.schedule_ui_update)
            )
        except Exception as e: # Catch any unexpected error from connect_and_listen if it wasn't caught internally
            logger.error(f"Critical exception in WebSocket run_until_complete: {e}")
        finally:
            if loop.is_running(): # Ensure loop is stopped if it's still running
                loop.call_soon_threadsafe(loop.stop)
            # loop.close() # Closing might be better handled in _on_closing or after join
            logger.info("Asyncio event loop tasks finished in WebSocket thread.")


    def schedule_ui_update(self, book_manager, status):
        self.after(0, self._update_ui_from_websocket, book_manager, status)

    def _update_ui_from_websocket(self, book_manager, status):
        if status == "connected":
            self.status_bar_text.set(f"Status: Connected to WebSocket. Waiting for data...")
            logger.info("UI updated: Connected")
        elif status == "data_update":
            if not self.is_connected_with_symbol and book_manager.symbol:
                self.status_bar_text.set(f"Status: Connected to WebSocket ({book_manager.symbol})")
                self.is_connected_with_symbol = True

            self.timestamp_var.set(book_manager.timestamp)
            best_bid = book_manager.get_best_bid()
            self.current_best_bid_var.set(f"{best_bid[0]:.2f} ({best_bid[1]:.2f})" if best_bid else "N/A")
            best_ask = book_manager.get_best_ask()
            self.current_best_ask_var.set(f"{best_ask[0]:.2f} ({best_ask[1]:.2f})" if best_ask else "N/A")
            spread = book_manager.get_spread()
            self.current_spread_var.set(f"{spread:.2f}" if spread is not None else "N/A")
            
        elif status == "disconnected_error":
            self.status_bar_text.set("Status: WebSocket Disconnected (Error).")
            self.is_connected_with_symbol = False
            self.timestamp_var.set("N/A"); self.current_best_bid_var.set("N/A"); self.current_best_ask_var.set("N/A"); self.current_spread_var.set("N/A")
            logger.warning("UI updated: Disconnected (Error)")
        elif status == "disconnected_clean":
            self.status_bar_text.set("Status: WebSocket Disconnected.")
            self.is_connected_with_symbol = False
            logger.info("UI updated: Disconnected (Cleanly)")

    def _on_closing(self):
        logger.info("Close button clicked. Initiating shutdown sequence...")
        
        # Stop the asyncio loop in the WebSocket thread
        if self.loop and self.loop.is_running():
            logger.info("Attempting to stop asyncio event loop...")
            # Schedule stop() to be called in the loop's thread
            self.loop.call_soon_threadsafe(self.loop.stop)
        else:
            logger.info("Asyncio event loop was not running or not initialized at close.")

        # Wait for the WebSocket thread to finish
        if self.websocket_thread and self.websocket_thread.is_alive():
            logger.info("Waiting for WebSocket thread to join...")
            self.websocket_thread.join(timeout=5.0) # Wait up to 5 seconds
            if self.websocket_thread.is_alive():
                logger.warning("WebSocket thread did not join in time. Forcing exit.")
            else:
                logger.info("WebSocket thread joined successfully.")
        else:
            logger.info("WebSocket thread was not alive or not initialized at close.")

        # Close the asyncio loop if it hasn't been closed yet and is not None
        if self.loop and not self.loop.is_closed():
            # This needs to be called from the thread that owns the loop,
            # or after ensuring it's stopped. Since we stop it above and join,
            # it should be safe to close if it's not already.
            # However, loop.close() should ideally be in the thread that ran it.
            # The _run_websocket_loop's finally block should handle loop.close()
            # For now, let's assume the thread's finally block closes its own loop.
            # We can add self.loop.call_soon_threadsafe(self.loop.close) if needed,
            # but that's risky if the loop is already stopping/stopped.
            logger.info("Asyncio loop is expected to be closed by its own thread.")


        logger.info("Destroying Tkinter window.")
        self.destroy()

    def run(self):
        self.status_bar_text.set("Status: UI Ready. Initializing WebSocket...")
        self.mainloop()

if __name__ == "__main__":
    app = TradingSimulatorApp()
    app.run()