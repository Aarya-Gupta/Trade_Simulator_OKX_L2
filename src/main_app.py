import tkinter as tk
from tkinter import ttk # Themed Tkinter widgets
import tkinter as tk
from tkinter import ttk # Themed Tkinter widgets

class TradingSimulatorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("GoQuant Trade Simulator")
        self.geometry("800x600")

        # --- Tkinter StringVars to hold input values ---
        self.exchange_var = tk.StringVar(value="OKX") # Fixed
        self.spot_asset_var = tk.StringVar(value="BTC-USDT-SWAP") # Default, can be changed if WS supports others
        self.order_type_var = tk.StringVar(value="Market") # Fixed
        self.quantity_usd_var = tk.StringVar(value="100") # Default
        self.volatility_var = tk.StringVar(value="0.02") # Example: 2% volatility, needs to be understood from OKX docs
        self.fee_tier_var = tk.StringVar(value="VIP1") # Example, OKX has tiers like VIP1, LV1 etc.

        # Configure main window grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1, uniform="group1") # Left panel
        self.grid_columnconfigure(1, weight=2, uniform="group1") # Right panel (give more space)

        # --- Left Panel (Inputs) ---
        self.input_panel = ttk.LabelFrame(self, text="Input Parameters", padding="10")
        self.input_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configure grid columns for labels and entries within input_panel
        self.input_panel.grid_columnconfigure(0, weight=0) # Labels
        self.input_panel.grid_columnconfigure(1, weight=1) # Entries

        # --- Input Widgets ---
        row_num = 0

        # 1. Exchange
        ttk.Label(self.input_panel, text="Exchange:").grid(row=row_num, column=0, sticky="w", pady=2)
        ttk.Label(self.input_panel, textvariable=self.exchange_var).grid(row=row_num, column=1, sticky="ew", pady=2)
        row_num += 1

        # 2. Spot Asset (Using Entry for now, as the provided WebSocket is specific)
        ttk.Label(self.input_panel, text="Spot Asset:").grid(row=row_num, column=0, sticky="w", pady=2)
        # If we were to connect to different assets, this could be an Entry or Combobox
        # For now, it's tied to the WebSocket URL, so display it.
        asset_label = ttk.Label(self.input_panel, textvariable=self.spot_asset_var)
        asset_label.grid(row=row_num, column=1, sticky="ew", pady=2)
        # ttk.Entry(self.input_panel, textvariable=self.spot_asset_var).grid(row=row_num, column=1, sticky="ew", pady=2)
        row_num += 1

        # 3. Order Type
        ttk.Label(self.input_panel, text="Order Type:").grid(row=row_num, column=0, sticky="w", pady=2)
        ttk.Label(self.input_panel, textvariable=self.order_type_var).grid(row=row_num, column=1, sticky="ew", pady=2)
        row_num += 1

        # 4. Quantity (USD)
        ttk.Label(self.input_panel, text="Quantity (USD):").grid(row=row_num, column=0, sticky="w", pady=2)
        qty_entry = ttk.Entry(self.input_panel, textvariable=self.quantity_usd_var)
        qty_entry.grid(row=row_num, column=1, sticky="ew", pady=2)
        row_num += 1

        # 5. Volatility
        # Note: The definition of "volatility" needs to be clarified from OKX docs.
        # This could be an annualized volatility (e.g., 0.5 for 50%), daily, or other.
        # Almgren-Chriss typically uses volatility per unit of time (e.g., daily or per-second).
        ttk.Label(self.input_panel, text="Volatility (e.g., 0.02 for 2%):").grid(row=row_num, column=0, sticky="w", pady=2)
        vol_entry = ttk.Entry(self.input_panel, textvariable=self.volatility_var)
        vol_entry.grid(row=row_num, column=1, sticky="ew", pady=2)
        row_num += 1

        # 6. Fee Tier
        # OKX fee tiers can be complex (e.g., based on trading volume, holdings).
        # For now, a text entry. Could be a Combobox if we have a predefined list.
        # Example OKX Spot Trading Fee Tiers: Regular users (LV1-LV5), Pro users (VIP1-VIP8)
        ttk.Label(self.input_panel, text="Fee Tier (e.g., VIP1, LV1):").grid(row=row_num, column=0, sticky="w", pady=2)
        # OKX Fee Tiers example: https://www.okx.com/fees/spot-coins
        # Let's use a Combobox with a few common examples
        fee_tier_options = ["Regular User LV1", "Regular User LV2", "Regular User LV3", 
                            "VIP 1", "VIP 2", "VIP 3", "VIP 4", "VIP 5", "VIP 6", "VIP 7", "VIP 8"]
        fee_tier_combobox = ttk.Combobox(self.input_panel, textvariable=self.fee_tier_var, values=fee_tier_options)
        fee_tier_combobox.grid(row=row_num, column=1, sticky="ew", pady=2)
        fee_tier_combobox.set("Regular User LV1") # Set a default from the list
        row_num += 1
        
        # Add some padding to the last row of input panel to push content up
        self.input_panel.grid_rowconfigure(row_num, weight=1)


        # --- Right Panel (Outputs) ---
        self.output_panel = ttk.LabelFrame(self, text="Processed Outputs", padding="10")
        self.output_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        # Placeholder for output panel (will be populated in the next stage)
        # output_label = ttk.Label(self.output_panel, text="Data will appear here...", font=("Arial", 12))
        # output_label.pack(pady=10, padx=10, anchor="nw")

        # --- Status Bar ---
        self.status_bar_text = tk.StringVar(value="Status: Initializing...")
        self.status_bar = ttk.Label(self, textvariable=self.status_bar_text, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)


    def run(self):
        """Starts the Tkinter main loop."""
        self.status_bar_text.set("Status: UI Ready. Waiting for data connection...")
        self.mainloop()

if __name__ == "__main__":
    app = TradingSimulatorApp()
    app.run()