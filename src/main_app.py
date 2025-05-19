# src/main_app.py
import tkinter as tk
from tkinter import ttk
import threading
import asyncio
import logging
import time

import sys
import os 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.order_book_manager import OrderBookManager
from src.websocket_handler import connect_and_listen
# Import new function AND the existing one
from src.financial_calculations import calculate_expected_fees, calculate_slippage_walk_book, calculate_market_impact_cost

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

        # To store results from slippage calculation for other models
        self.avg_execution_price = None
        self.actual_asset_traded = None
        self.actual_usd_spent_slippage = None # USD spent during slippage walk
        self.slippage_percentage_val = None # Store numeric slippage percentage
        self.fee_cost_usd_val = None        # Store numeric fee cost
        self.market_impact_usd_val = None   # Store numeric market impact cost


        self.exchange_var = tk.StringVar(value="OKX")
        self.spot_asset_var = tk.StringVar(value="BTC-USDT-SWAP")
        self.order_type_var = tk.StringVar(value="Market")
        self.quantity_usd_var = tk.StringVar(value="100")
        self.volatility_var = tk.StringVar(value="0.02")
        self.fee_tier_var = tk.StringVar() 

        self.slippage_var = tk.StringVar(value="N/A") # This will be updated
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
        # ... (UI setup code as before, including traces) ...
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
        qty_entry = ttk.Entry(self.input_panel, textvariable=self.quantity_usd_var)
        qty_entry.grid(row=row_num_input, column=1, sticky="ew", pady=3)
        self.quantity_usd_var.trace_add("write", self._trigger_recalculation)
        row_num_input += 1

        ttk.Label(self.input_panel, text="Volatility (e.g., 0.02):").grid(row=row_num_input, column=0, sticky="w", pady=3)
        vol_entry = ttk.Entry(self.input_panel, textvariable=self.volatility_var)
        vol_entry.grid(row=row_num_input, column=1, sticky="ew", pady=3)
        self.volatility_var.trace_add("write", self._trigger_recalculation)
        row_num_input += 1
        
        ttk.Label(self.input_panel, text="Fee Tier:").grid(row=row_num_input, column=0, sticky="w", pady=3)
        fee_tier_options = ["Regular User LV1", "Regular User LV2", "Regular User LV3", 
                            "VIP 1", "VIP 2", "VIP 3", "VIP 4", "VIP 5", "VIP 6", "VIP 7", "VIP 8", "Custom"]
        fee_tier_combobox = ttk.Combobox(self.input_panel, textvariable=self.fee_tier_var, values=fee_tier_options, state="readonly")
        fee_tier_combobox.grid(row=row_num_input, column=1, sticky="ew", pady=3)
        default_fee_tier = "Regular User LV1"
        fee_tier_combobox.set(default_fee_tier) 
        self.fee_tier_var.set(default_fee_tier) 
        self.fee_tier_var.trace_add("write", self._trigger_recalculation)
        row_num_input += 1
        
        self.input_panel.grid_rowconfigure(row_num_input, weight=1)

        # --- Right Panel (Outputs) ---
        self.output_panel = ttk.LabelFrame(self, text="Processed Outputs & Market Data", padding="10")
        self.output_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        # ... (rest of output panel setup as before) ...
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

        ttk.Label(self.output_panel, text="Expected Slippage (%):").grid(row=row_num_output, column=0, sticky="w", pady=2) # Added (%)
        ttk.Label(self.output_panel, textvariable=self.slippage_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Expected Fees (USD):").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.fees_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Expected Market Impact:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.market_impact_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Net Cost (USD):").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.net_cost_var).grid(row=row_num_output, column=1, sticky="ew", pady=2) 
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
        self.after(50, self._recalculate_all_outputs)

    def _recalculate_all_outputs(self):
        # --- Start Latency Measurement ---
        calc_start_time = time.perf_counter()

        # Reset numeric values at the start of each calculation attempt
        self.slippage_percentage_val = None
        self.fee_cost_usd_val = None
        self.market_impact_usd_val = None
        self.avg_execution_price = None
        self.actual_asset_traded = None
        self.actual_usd_spent_slippage = None # Important to reset this

        current_latency = "N/A" # Default latency display

        try:
            # 1. Read Input: Quantity USD
            try:
                quantity_usd_val = float(self.quantity_usd_var.get())
                if quantity_usd_val < 0: # Allow 0 for no trade scenario
                    for var in [self.fees_var, self.slippage_var, self.market_impact_var, self.net_cost_var]: 
                        var.set("Invalid Qty")
                    # Reset stored values
                    self.avg_execution_price = None #
                    self.actual_asset_traded = None #
                    self.actual_usd_spent_slippage = None #
                    return 
            except ValueError:
                for var in [self.fees_var, self.slippage_var, self.market_impact_var, self.net_cost_var]: 
                    var.set("Invalid Qty")
                self.avg_execution_price = None #
                self.actual_asset_traded = None #
                self.actual_usd_spent_slippage = None #
                return

            # 2. Read Input: Fee Tier
            fee_tier_val = self.fee_tier_var.get()

            # 3. Read Input: Volatility
            try:
                volatility_val = float(self.volatility_var.get())
                if volatility_val < 0:
                     self.market_impact_var.set("Invalid Vol")
                     self.net_cost_var.set("Invalid Vol");
                     return
            except ValueError:
                self.market_impact_var.set("Invalid Vol")
                self.net_cost_var.set("Invalid Vol");
                return
            
            # 4. Read Input: Asset Symbol (from fixed var for now)
            asset_symbol_val = self.spot_asset_var.get()

            # --- Calculate Slippage (Walk the Book) ---
            # Requires live order book data, so self.order_book must be up-to-date
            slippage_cost_usd = 0.0 # Default to 0 if not calculable
            if not self.order_book.asks or not self.order_book.bids: # Check if book has data
                self.slippage_var.set("No book data")
                self.avg_execution_price = None #
                self.actual_asset_traded = None #
                self.actual_usd_spent_slippage = None #
            else:
                slp_pct, avg_exec_p, asset_acq, usd_spent = calculate_slippage_walk_book(
                    quantity_usd_val, self.order_book
                )
                # Store these values for other calculations (e.g. market impact)
                self.avg_execution_price = avg_exec_p
                self.actual_asset_traded = asset_acq
                self.actual_usd_spent_slippage = usd_spent

                if slp_pct is not None:
                    self.slippage_percentage_val = slp_pct # Store numeric value
                    self.slippage_var.set(f"{slp_pct:.4f}%")
                    # Calculate slippage cost in USD.
                    # Slippage cost is the difference between what you actually paid (usd_spent)
                    # and what you would have paid at the mid-price for the asset_acquired.
                    # mid_price_snapshot used inside calculate_slippage_walk_book for asset_acquired:
                    if self.order_book.get_best_ask() and self.order_book.get_best_bid():
                        mid_price = (self.order_book.get_best_ask()[0] + self.order_book.get_best_bid()[0]) / 2
                        if asset_acq > 0 : # if any asset was acquired 
                            slippage_cost_usd = usd_spent - asset_acq * mid_price
                        # If slp_pct is positive (paid more), slippage_cost_usd will be positive.
                    # Alternative simpler slippage cost based on target USD, but less accurate if fill is partial:
                    # slippage_cost_usd = (slp_pct / 100.0) * quantity_usd_val 

                else:
                    if quantity_usd_val > 0 and asset_acq == 0 : # Tried to buy but got nothing
                         self.slippage_var.set("Depth Exceeded?")
                    elif quantity_usd_val == 0:
                         self.slippage_var.set("0.0000%") # No slippage for no trade
                    else: # Other error cases from slippage function
                         self.slippage_var.set("Error/No Trade")
                logger.debug(f"Slippage: {slp_pct}%, AvgPrice: {avg_exec_p}, Asset: {asset_acq}, Spent: {usd_spent}")
            
            # --- Calculate Expected Fees ---
            # Fees should ideally be based on the actual USD spent if slippage is significant
            # or if the order couldn't be fully filled for target_usd_val.
            # For now, let's use target quantity_usd_val for simplicity as per problem statement.
            # Or, use self.actual_usd_spent_slippage if available.
            # Let's use quantity_usd_val as it's the "target".
            calculated_fees = calculate_expected_fees(quantity_usd_val, fee_tier_val)
            self.fees_var.set(f"{calculated_fees:.4f}")
            self.fee_cost_usd_val = calculated_fees

            # --- Calculate Market Impact Cost ---
            # Use actual USD spent from slippage calculation if available and valid, else target quantity
            # For simplicity, assignment implies using the input "Quantity (~100 USD equivalent)"
            # Let's use quantity_usd_val (target order size) for market impact calculation as well.
            market_impact_usd = calculate_market_impact_cost(quantity_usd_val, volatility_val, asset_symbol_val)
            if market_impact_usd is not None:
                self.market_impact_var.set(f"{market_impact_usd:.4f}")
            else:
                self.market_impact_var.set("Error")
            self.market_impact_usd_val = market_impact_usd

            # --- Calculate Net Cost ---
            if self.fee_cost_usd_val is not None and \
               self.market_impact_usd_val is not None and \
               self.slippage_percentage_val is not None: # Check if all components are valid
                
                # If quantity_usd_val is 0, all costs should be 0
                if quantity_usd_val == 0:
                    net_total_cost_usd = 0.0
                    slippage_cost_usd = 0.0 # Ensure this is zero for zero quantity
                else:
                    net_total_cost_usd = slippage_cost_usd + self.fee_cost_usd_val + self.market_impact_usd_val
                
                self.net_cost_var.set(f"{net_total_cost_usd:.4f}")
            else:
                self.net_cost_var.set("Error")

            # --- Maker/Taker Proportion ---
            if quantity_usd_val == 0:
                 self.maker_taker_proportion_var.set("N/A (No Trade)")
            else:
                 self.maker_taker_proportion_var.set("100% Taker")
            
            # --- End Latency Measurement & Update UI ---
            calc_end_time = time.perf_counter()
            processing_time_ms = (calc_end_time - calc_start_time) * 1000
            current_latency = f"{processing_time_ms:.3f}" # Store as string for UI
            logger.debug(f"Internal processing latency: {processing_time_ms:.3f} ms")

        except Exception as e:
            logger.error(f"Error during recalculation: {e}", exc_info=True)
            self.fees_var.set("Error")
            self.slippage_var.set("Error")
            self.market_impact_var.set("Error")
            self.net_cost_var.set("Error")
            self.maker_taker_proportion_var.set("Error")
            self.slippage_var.set("Error")
        finally:
            # This ensures latency is updated even if an error occurred mid-calculation,
            # showing the time taken up to the error point or full calculation.
            self.internal_latency_var.set(current_latency)

    def _update_ui_from_websocket(self, book_manager, status):
        # ... (This method largely stays the same) ...
        if status == "connected":
            self.status_bar_text.set(f"Status: Connected to WebSocket. Waiting for data...")
            logger.info("UI updated: Connected")
            self.after(100, self._trigger_recalculation) # Initial calculation after connection
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
            
            self._recalculate_all_outputs() # Recalculate on each tick

        elif status == "disconnected_error":
            self.status_bar_text.set("Status: WebSocket Disconnected (Error).")
            self.is_connected_with_symbol = False
            for var in [self.timestamp_var, self.current_best_bid_var, self.current_best_ask_var, self.current_spread_var, self.fees_var, self.slippage_var, self.market_impact_var, self.net_cost_var, self.maker_taker_proportion_var, self.internal_latency_var]: 
                var.set("N/A")
            logger.warning("UI updated: Disconnected (Error)")
        elif status == "disconnected_clean":
            for var in [self.timestamp_var, self.current_best_bid_var, self.current_best_ask_var, self.current_spread_var, self.fees_var, self.slippage_var, self.market_impact_var, self.net_cost_var, self.maker_taker_proportion_var, self.internal_latency_var]: 
                var.set("N/A")
            logger.info("UI updated: Disconnected (Cleanly)")

    # --- WebSocket and Shutdown methods remain the same ---
    def _start_websocket_connection(self):
        # ...
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
        # ...
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
        # ...
        self.after(0, self._update_ui_from_websocket, book_manager, status)

    def _on_closing(self):
        # ...
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
        # ...
        self.status_bar_text.set("Status: UI Ready. Initializing WebSocket...")
        self.after(100, self._trigger_recalculation) 
        self.mainloop()

if __name__ == "__main__":
    app = TradingSimulatorApp()
    app.run()