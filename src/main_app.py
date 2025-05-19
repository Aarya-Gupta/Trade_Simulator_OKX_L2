import tkinter as tk
from tkinter import ttk
import threading
import asyncio
import logging
import time # For latency measurement later

import sys
import os 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.order_book_manager import OrderBookManager
from src.websocket_handler import connect_and_listen
from src.financial_calculations import calculate_expected_fees # Import new function

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - [%(name)s:%(threadName)s] - %(message)s')
logger = logging.getLogger(__name__)

class TradingSimulatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # ... (Most of __init__ remains the same) ...
        self.title("GoQuant Trade Simulator")
        self.geometry("850x650")

        self.order_book = OrderBookManager()
        self.websocket_thread = None
        self.loop = None
        self.is_connected_with_symbol = False 

        self.exchange_var = tk.StringVar(value="OKX")
        self.spot_asset_var = tk.StringVar(value="BTC-USDT-SWAP")
        self.order_type_var = tk.StringVar(value="Market")
        self.quantity_usd_var = tk.StringVar(value="100")
        self.volatility_var = tk.StringVar(value="0.02")
        self.fee_tier_var = tk.StringVar() 

        self.slippage_var = tk.StringVar(value="N/A")
        self.fees_var = tk.StringVar(value="N/A") # This will be updated
        self.market_impact_var = tk.StringVar(value="N/A")
        self.net_cost_var = tk.StringVar(value="N/A")
        self.maker_taker_proportion_var = tk.StringVar(value="N/A")
        self.internal_latency_var = tk.StringVar(value="N/A")
        
        self.timestamp_var = tk.StringVar(value="N/A")
        self.current_best_bid_var = tk.StringVar(value="N/A")
        self.current_best_ask_var = tk.StringVar(value="N/A")
        self.current_spread_var = tk.StringVar(value="N/A")

        self._setup_ui() # This will now include traces for input vars
        self._start_websocket_connection()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_ui(self):
        # ... (UI setup code as before) ...
        # --- Left Panel (Inputs) ---
        self.input_panel = ttk.LabelFrame(self, text="Input Parameters", padding="10")
        self.input_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.input_panel.grid_columnconfigure(0, weight=0) 
        self.input_panel.grid_columnconfigure(1, weight=1) 

        row_num_input = 0
        # ... (Exchange, Spot Asset, Order Type labels as before) ...
        ttk.Label(self.input_panel, text="Exchange:").grid(row=row_num_input, column=0, sticky="w", pady=3)
        ttk.Label(self.input_panel, textvariable=self.exchange_var).grid(row=row_num_input, column=1, sticky="ew", pady=3)
        row_num_input += 1

        ttk.Label(self.input_panel, text="Spot Asset:").grid(row=row_num_input, column=0, sticky="w", pady=3)
        ttk.Label(self.input_panel, textvariable=self.spot_asset_var).grid(row=row_num_input, column=1, sticky="ew", pady=3)
        row_num_input += 1

        ttk.Label(self.input_panel, text="Order Type:").grid(row=row_num_input, column=0, sticky="w", pady=3)
        ttk.Label(self.input_panel, textvariable=self.order_type_var).grid(row=row_num_input, column=1, sticky="ew", pady=3)
        row_num_input += 1

        # Quantity (USD) - Add trace
        ttk.Label(self.input_panel, text="Quantity (USD):").grid(row=row_num_input, column=0, sticky="w", pady=3)
        qty_entry = ttk.Entry(self.input_panel, textvariable=self.quantity_usd_var)
        qty_entry.grid(row=row_num_input, column=1, sticky="ew", pady=3)
        self.quantity_usd_var.trace_add("write", self._trigger_recalculation) # Trigger on change
        row_num_input += 1

        # Volatility - Add trace (though not used for fees, good for consistency)
        ttk.Label(self.input_panel, text="Volatility (e.g., 0.02):").grid(row=row_num_input, column=0, sticky="w", pady=3)
        vol_entry = ttk.Entry(self.input_panel, textvariable=self.volatility_var)
        vol_entry.grid(row=row_num_input, column=1, sticky="ew", pady=3)
        self.volatility_var.trace_add("write", self._trigger_recalculation) # Trigger on change
        row_num_input += 1
        
        # Fee Tier - Add trace
        ttk.Label(self.input_panel, text="Fee Tier:").grid(row=row_num_input, column=0, sticky="w", pady=3)
        fee_tier_options = ["Regular User LV1", "Regular User LV2", "Regular User LV3", 
                            "VIP 1", "VIP 2", "VIP 3", "VIP 4", "VIP 5", "VIP 6", "VIP 7", "VIP 8", "Custom"]
        fee_tier_combobox = ttk.Combobox(self.input_panel, textvariable=self.fee_tier_var, values=fee_tier_options, state="readonly")
        fee_tier_combobox.grid(row=row_num_input, column=1, sticky="ew", pady=3)
        default_fee_tier = "Regular User LV1"
        fee_tier_combobox.set(default_fee_tier) 
        self.fee_tier_var.set(default_fee_tier) 
        self.fee_tier_var.trace_add("write", self._trigger_recalculation) # Trigger on change
        row_num_input += 1
        
        self.input_panel.grid_rowconfigure(row_num_input, weight=1)

        # ... (Right Panel and Status Bar setup as before) ...
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

        ttk.Label(self.output_panel, text="Expected Fees (USD):").grid(row=row_num_output, column=0, sticky="w", pady=2) # Added (USD)
        ttk.Label(self.output_panel, textvariable=self.fees_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Expected Market Impact:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.market_impact_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Net Cost (USD):").grid(row=row_num_output, column=0, sticky="w", pady=2) # Added (USD)
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


    def _trigger_recalculation(self, *args):
        """
        Called when an input StringVar changes.
        Schedules the main recalculation logic.
        """
        # logger.debug(f"Input changed, triggering recalculation: {args}")
        self.after(50, self._recalculate_all_outputs) # Debounce slightly

    def _recalculate_all_outputs(self):
        """
        Reads all inputs and recalculates all output values.
        This will be expanded in subsequent stages.
        """
        # logger.debug("Recalculating all outputs...")
        try:
            # 1. Read Input: Quantity USD
            try:
                quantity_usd_val = float(self.quantity_usd_var.get())
                if quantity_usd_val < 0:
                    self.fees_var.set("Invalid Qty")
                    # Potentially clear other fields or show error
                    return 
            except ValueError:
                self.fees_var.set("Invalid Qty")
                # Potentially clear other fields or show error
                return # Stop calculation if quantity is invalid

            # 2. Read Input: Fee Tier
            fee_tier_val = self.fee_tier_var.get()

            # --- Calculate Expected Fees ---
            calculated_fees = calculate_expected_fees(quantity_usd_val, fee_tier_val)
            self.fees_var.set(f"{calculated_fees:.4f}") # Format to 4 decimal places

            # --- Placeholder for other calculations ---
            # self.slippage_var.set("Calculating...")
            # self.market_impact_var.set("Calculating...")
            # self.net_cost_var.set("Calculating...")
            # self.maker_taker_proportion_var.set("Calculating...")
            # self.internal_latency_var.set("Calculating...")

            logger.debug(f"Fees calculated: {calculated_fees} for Qty: {quantity_usd_val}, Tier: {fee_tier_val}")

        except Exception as e:
            logger.error(f"Error during recalculation: {e}", exc_info=True)
            self.fees_var.set("Error")
            # Potentially set other fields to "Error" as well

    def _update_ui_from_websocket(self, book_manager, status):
        # ... (This method largely stays the same for market data updates) ...
        if status == "connected":
            self.status_bar_text.set(f"Status: Connected to WebSocket. Waiting for data...")
            logger.info("UI updated: Connected")
            self._trigger_recalculation() # Initial calculation
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
            
            # Trigger recalculation of financial outputs with each new tick
            self._recalculate_all_outputs() # <-- ADDED THIS LINE

        elif status == "disconnected_error":
            self.status_bar_text.set("Status: WebSocket Disconnected (Error).")
            self.is_connected_with_symbol = False
            # Clear market data and potentially calculated fields
            self.timestamp_var.set("N/A"); self.current_best_bid_var.set("N/A")
            self.current_best_ask_var.set("N/A"); self.current_spread_var.set("N/A")
            self.fees_var.set("N/A") # Clear calculated fields too
            logger.warning("UI updated: Disconnected (Error)")
        elif status == "disconnected_clean":
            self.status_bar_text.set("Status: WebSocket Disconnected.")
            self.is_connected_with_symbol = False
            self.fees_var.set("N/A") # Clear calculated fields too
            logger.info("UI updated: Disconnected (Cleanly)")


    # --- WebSocket and Shutdown methods remain the same ---
    def _start_websocket_connection(self):
        self.status_bar_text.set("Status: Connecting to WebSocket...")
        self.is_connected_with_symbol = False 
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
        except Exception as e:
            logger.error(f"Critical exception in WebSocket run_until_complete: {e}")
        finally:
            if loop.is_running(): 
                loop.call_soon_threadsafe(loop.stop)
            logger.info("Asyncio event loop tasks finished in WebSocket thread.")

    def schedule_ui_update(self, book_manager, status):
        self.after(0, self._update_ui_from_websocket, book_manager, status)

    def _on_closing(self):
        logger.info("Close button clicked. Initiating shutdown sequence...")
        if self.loop and self.loop.is_running():
            logger.info("Attempting to stop asyncio event loop...")
            self.loop.call_soon_threadsafe(self.loop.stop)
        else:
            logger.info("Asyncio event loop was not running or not initialized at close.")

        if self.websocket_thread and self.websocket_thread.is_alive():
            logger.info("Waiting for WebSocket thread to join...")
            self.websocket_thread.join(timeout=5.0) 
            if self.websocket_thread.is_alive():
                logger.warning("WebSocket thread did not join in time. Forcing exit.")
            else:
                logger.info("WebSocket thread joined successfully.")
        else:
            logger.info("WebSocket thread was not alive or not initialized at close.")
        
        logger.info("Destroying Tkinter window.")
        self.destroy()

    def run(self):
        self.status_bar_text.set("Status: UI Ready. Initializing WebSocket...")
        # Trigger an initial calculation based on default input values
        self.after(100, self._trigger_recalculation) # Schedule after UI is fully up
        self.mainloop()

if __name__ == "__main__":
    app = TradingSimulatorApp()
    app.run()