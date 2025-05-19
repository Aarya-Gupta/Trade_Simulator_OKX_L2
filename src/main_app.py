import tkinter as tk
from tkinter import ttk # Themed Tkinter widgets

class TradingSimulatorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("GoQuant Trade Simulator")
        self.geometry("800x600") # Adjusted for more content

        # --- Tkinter StringVars for Input values ---
        self.exchange_var = tk.StringVar(value="OKX")
        self.spot_asset_var = tk.StringVar(value="BTC-USDT-SWAP")
        self.order_type_var = tk.StringVar(value="Market")
        self.quantity_usd_var = tk.StringVar(value="100")
        self.volatility_var = tk.StringVar(value="0.02") # Example daily volatility
        self.fee_tier_var = tk.StringVar() # Will be set by combobox default

        # --- Tkinter StringVars for Output values ---
        self.slippage_var = tk.StringVar(value="N/A")
        self.fees_var = tk.StringVar(value="N/A")
        self.market_impact_var = tk.StringVar(value="N/A")
        self.net_cost_var = tk.StringVar(value="N/A")
        self.maker_taker_proportion_var = tk.StringVar(value="N/A")
        self.internal_latency_var = tk.StringVar(value="N/A")
        self.current_best_bid_var = tk.StringVar(value="N/A") # For live data display
        self.current_best_ask_var = tk.StringVar(value="N/A") # For live data display
        self.current_spread_var = tk.StringVar(value="N/A")   # For live data display
        self.timestamp_var = tk.StringVar(value="N/A")        # For live data display

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
        self.fee_tier_var.set("Regular User LV1") # Ensure var is also set
        row_num_input += 1
        
        self.input_panel.grid_rowconfigure(row_num_input, weight=1) # Push content up


        # --- Right Panel (Outputs) ---
        self.output_panel = ttk.LabelFrame(self, text="Processed Outputs & Market Data", padding="10")
        self.output_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.output_panel.grid_columnconfigure(0, weight=0) # Labels
        self.output_panel.grid_columnconfigure(1, weight=1) # Values

        row_num_output = 0
        
        # Market Data Section
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
        
        # Separator
        ttk.Separator(self.output_panel, orient='horizontal').grid(row=row_num_output, column=0, columnspan=2, sticky='ew', pady=10)
        row_num_output +=1

        # Calculated Outputs Section
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
        ttk.Label(self.output_panel, textvariable=self.net_cost_var, font=("Arial", 10, "bold")).grid(row=row_num_output, column=1, sticky="ew", pady=2) # Bold for emphasis
        row_num_output += 1
        
        # Separator
        ttk.Separator(self.output_panel, orient='horizontal').grid(row=row_num_output, column=0, columnspan=2, sticky='ew', pady=10)
        row_num_output +=1

        # Other Metrics Section
        ttk.Label(self.output_panel, text="Other Metrics:", font=("Arial", 12, "bold")).grid(row=row_num_output, column=0, columnspan=2, sticky="w", pady=(5,5))
        row_num_output += 1

        ttk.Label(self.output_panel, text="Maker/Taker Proportion:").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.maker_taker_proportion_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1

        ttk.Label(self.output_panel, text="Internal Latency (ms):").grid(row=row_num_output, column=0, sticky="w", pady=2)
        ttk.Label(self.output_panel, textvariable=self.internal_latency_var).grid(row=row_num_output, column=1, sticky="ew", pady=2)
        row_num_output += 1
        
        self.output_panel.grid_rowconfigure(row_num_output, weight=1) # Push content up

        # --- Status Bar ---
        self.status_bar_text = tk.StringVar(value="Status: Initializing...")
        self.status_bar = ttk.Label(self, textvariable=self.status_bar_text, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

    def run(self):
        self.status_bar_text.set("Status: UI Ready. Connect to WebSocket to see live data.")
        self.mainloop()

if __name__ == "__main__":
    app = TradingSimulatorApp()
    app.run()