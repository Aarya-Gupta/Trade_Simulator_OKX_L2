# src/financial_calculations.py
# Run to infer standalone tests :
# python -m src.financial_calculations
# will implement pytest later. 

import logging
from typing import Tuple, Optional, List # For type hinting

import sys
import os 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from .config import OKX_FEE_RATES, DEFAULT_TAKER_FEE_RATE, ASSUMED_DAILY_VOLUME_USD, MARKET_IMPACT_COEFFICIENT
# We'll need access to the OrderBookManager type for type hinting if not already imported
# from .order_book_manager import OrderBookManager # Assuming it's in the same directory
import numpy as np
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)

def calculate_expected_fees(quantity_usd: float, fee_tier: str) -> float:
    # ... (previous fee calculation code remains the same) ...
    if not isinstance(quantity_usd, (int, float)) or quantity_usd < 0:
        logger.warning(f"Invalid quantity_usd for fee calculation: {quantity_usd}")
        return 0.0
    tier_info = OKX_FEE_RATES.get(fee_tier)
    if tier_info:
        taker_fee_rate = tier_info.get("taker", DEFAULT_TAKER_FEE_RATE)
    else:
        logger.warning(f"Fee tier '{fee_tier}' not found. Using default taker fee rate: {DEFAULT_TAKER_FEE_RATE}")
        taker_fee_rate = DEFAULT_TAKER_FEE_RATE
    expected_fee = quantity_usd * taker_fee_rate
    return expected_fee

def calculate_slippage_walk_book(
    target_usd_to_spend: float,
    order_book # Type hint can be OrderBookManager if imported
) -> Tuple[Optional[float], Optional[float], float, float]:
    """
    Calculates slippage by simulating a BUY market order walking the ask side of the order book.
    Tries to spend `target_usd_to_spend`.

    Args:
        target_usd_to_spend (float): The amount in USD to try and spend.
        order_book (OrderBookManager): The current order book instance.

    Returns:
        Tuple[Optional[float], Optional[float], float, float]:
            - slippage_percentage (Optional[float]): Slippage in percentage. None if not calculable.
            - average_execution_price (Optional[float]): Average price at which the order was filled. None if not calculable.
            - total_asset_acquired (float): Actual amount of base asset acquired.
            - actual_usd_spent (float): Actual amount of USD spent.
    """
    if target_usd_to_spend <= 0:
        return 0.0, None, 0.0, 0.0 # No slippage, no price, no asset, no spend for 0 USD

    asks = order_book.asks # List of [price, quantity]
    bids = order_book.bids

    if not asks or not bids:
        logger.warning("Slippage calc: Asks or Bids are empty. Cannot calculate mid-price or execute.")
        return None, None, 0.0, 0.0

    initial_best_ask_price = asks[0][0]
    initial_best_bid_price = bids[0][0]
    
    if initial_best_ask_price <= initial_best_bid_price: # Should not happen in a healthy book
        logger.warning(f"Slippage calc: Best ask {initial_best_ask_price} <= best bid {initial_best_bid_price}. Book crossed?")
        # Fallback: use best ask as reference if mid-price is problematic
        mid_price_snapshot = initial_best_ask_price
    else:
        mid_price_snapshot = (initial_best_ask_price + initial_best_bid_price) / 2.0

    if mid_price_snapshot <= 0: # Should not happen
        logger.error("Slippage calc: Mid price is zero or negative, cannot calculate slippage.")
        return None, None, 0.0, 0.0

    total_asset_acquired = 0.0
    actual_usd_spent = 0.0
    remaining_usd_to_spend = target_usd_to_spend

    # logger.debug(f"Walking the book for BUY: target_usd_spend={target_usd_to_spend}, mid_snapshot={mid_price_snapshot}")
    # logger.debug(f"Available asks: {asks[:5]}") # Log first 5 ask levels

    for price_level, quantity_at_level in asks:
        if remaining_usd_to_spend <= 1e-9: # Effectively zero, considering float precision
            break

        cost_to_buy_at_level = price_level * quantity_at_level

        if remaining_usd_to_spend >= cost_to_buy_at_level:
            # Can consume the entire level
            asset_bought = quantity_at_level
            usd_spent_this_level = cost_to_buy_at_level
        else:
            # Consume part of the level
            asset_bought = remaining_usd_to_spend / price_level
            usd_spent_this_level = remaining_usd_to_spend
        
        total_asset_acquired += asset_bought
        actual_usd_spent += usd_spent_this_level
        remaining_usd_to_spend -= usd_spent_this_level
        
        # logger.debug(f"Level: P={price_level}, Q={quantity_at_level}. Bought: {asset_bought}, Spent: {usd_spent_this_level}. Remaining USD: {remaining_usd_to_spend}")


    if total_asset_acquired <= 1e-9: # Effectively zero asset acquired
        logger.warning(f"Slippage calc: No asset acquired. Target USD: {target_usd_to_spend}. Actual USD spent: {actual_usd_spent}. This might happen if asks are empty or prices are extremely high.")
        # If we spent some USD but got no asset (highly unlikely with valid prices), avg_exec_price is infinite.
        # If we spent no USD (e.g. target_usd_to_spend was too small for any level), treat as no trade.
        return 0.0 if actual_usd_spent == 0 else None, None, 0.0, actual_usd_spent

    average_execution_price = actual_usd_spent / total_asset_acquired
    
    slippage_value = average_execution_price - mid_price_snapshot # For a BUY, positive slippage is bad (paid more)
    slippage_percentage = (slippage_value / mid_price_snapshot) * 100.0
    
    # logger.debug(f"Slippage Result: AvgExecPrice={average_execution_price}, Slippage%={slippage_percentage}, AssetAcquired={total_asset_acquired}, USDSpent={actual_usd_spent}")

    return slippage_percentage, average_execution_price, total_asset_acquired, actual_usd_spent

def calculate_market_impact_cost(
    order_quantity_usd: float, 
    asset_volatility: float, 
    asset_symbol: str
) -> Optional[float]:
    """
    Calculates a simplified market impact cost.
    Formula: ImpactCost_USD = C * volatility * (OrderSizeUSD / DailyVolumeUSD) * OrderSizeUSD
    
    Args:
        order_quantity_usd (float): The USD value of the order.
        asset_volatility (float): The asset's volatility (e.g., daily, as decimal 0.02 for 2%).
        asset_symbol (str): The symbol of the asset (e.g., "BTC-USDT-SWAP") to fetch assumed daily volume.

    Returns:
        Optional[float]: Estimated market impact cost in USD. None if inputs are invalid.
    """
    if order_quantity_usd < 0 or asset_volatility < 0:
        logger.warning(f"Market Impact: Invalid inputs. Order Qty: {order_quantity_usd}, Vol: {asset_volatility}")
        return None
    if order_quantity_usd == 0:
        return 0.0

    daily_volume_usd = ASSUMED_DAILY_VOLUME_USD.get(asset_symbol)
    if not daily_volume_usd or daily_volume_usd <= 0:
        logger.warning(f"Market Impact: Daily volume for {asset_symbol} not found or invalid in config. Using a fallback of 1B.")
        daily_volume_usd = 1_000_000_000.0 # Fallback large volume

    # Fraction of daily volume
    volume_fraction = order_quantity_usd / daily_volume_usd

    # Simplified impact cost calculation
    # ImpactCost_USD = C * volatility * (OrderSizeUSD / DailyVolumeUSD) * OrderSizeUSD
    # This is equivalent to: Price_Impact_Percentage_of_Order_Value = C * volatility * volume_fraction
    # And ImpactCost = Price_Impact_Percentage_of_Order_Value * OrderSizeUSD
    market_impact_cost = MARKET_IMPACT_COEFFICIENT * asset_volatility * volume_fraction * order_quantity_usd
    
    # logger.debug(f"Market Impact for {asset_symbol}: OrderUSD={order_quantity_usd}, Volatility={asset_volatility}, "
    #              f"DailyVolUSD={daily_volume_usd}, VolumeFraction={volume_fraction:.6f}, ImpactCostUSD={market_impact_cost:.4f}")
    
    return market_impact_cost

# --- CODE for Regression Model ---
class SlippageRegressionModel:
    def __init__(self, min_samples_to_train=50, features_dim=3):
        self.model = LinearRegression()
        self.is_trained = False
        self.data_X = [] # List of feature lists
        self.data_y = [] # List of target slippage percentages
        self.min_samples_to_train = min_samples_to_train
        self.features_dim = features_dim # order_size_usd, spread_bps, depth_best_ask_usd
        logger.info("SlippageRegressionModel initialized.")

    def add_data_point(self, features: List[float], target_slippage_pct: float):
        if len(features) != self.features_dim:
            logger.warning(f"Incorrect feature dimension. Expected {self.features_dim}, got {len(features)}")
            return
        self.data_X.append(features)
        self.data_y.append(target_slippage_pct)
        # Optional: Limit data size to prevent memory issues for long runs
        # MAX_DATA_POINTS = 1000
        # if len(self.data_X) > MAX_DATA_POINTS:
        #     self.data_X.pop(0)
        #     self.data_y.pop(0)

    def train(self):
        if len(self.data_X) < self.min_samples_to_train:
            # logger.debug(f"Not enough samples to train regression model. Have {len(self.data_X)}, need {self.min_samples_to_train}.")
            self.is_trained = False
            return False
        
        try:
            X_train = np.array(self.data_X)
            y_train = np.array(self.data_y)
            
            # Reshape X if it's 1D (e.g. if only one feature was used, though we plan for multiple)
            if X_train.ndim == 1:
                X_train = X_train.reshape(-1, 1)

            self.model.fit(X_train, y_train)
            self.is_trained = True
            logger.info(f"Slippage regression model trained with {len(self.data_X)} samples.")
            # logger.info(f"Model coefficients: {self.model.coef_}, Intercept: {self.model.intercept_}")
            return True
        except Exception as e:
            logger.error(f"Error training slippage regression model: {e}", exc_info=True)
            self.is_trained = False
            return False

    def predict(self, features: List[float]) -> Optional[float]:
        if not self.is_trained:
            # logger.debug("Slippage model not trained yet. Cannot predict.")
            return None
        if len(features) != self.features_dim:
            logger.warning(f"Predict: Incorrect feature dimension. Expected {self.features_dim}, got {len(features)}")
            return None
            
        try:
            prediction = self.model.predict(np.array(features).reshape(1, -1))
            return prediction[0] # model.predict returns an array
        except Exception as e:
            logger.error(f"Error predicting slippage: {e}", exc_info=True)
            return None

if __name__ == '__main__':
    # Mock OrderBookManager for testing
    class MockOrderBookManager:
        def __init__(self, asks, bids):
            self.asks = sorted([(float(p), float(q)) for p, q in asks], key=lambda x: x[0])
            self.bids = sorted([(float(p), float(q)) for p, q in bids], key=lambda x: x[0], reverse=True)
            self.timestamp = "test_time"
            self.symbol = "TEST/USD"
            self.exchange = "TEST_EX"
        def get_best_ask(self): return self.asks[0] if self.asks else None
        def get_best_bid(self): return self.bids[0] if self.bids else None
        def get_spread(self): 
            ba = self.get_best_ask()
            bb = self.get_best_bid()
            return ba[0] - bb[0] if ba and bb else None


    logging.basicConfig(level=logging.DEBUG)
    print("--- Testing Fee Calculation ---")
    print(f"Fee for 100 USD, Regular User LV1: {calculate_expected_fees(100, 'Regular User LV1')} USD")
    
    print("\n--- Testing Slippage Calculation ---")
    # Test case 1: Simple book, full fill within one level
    book1 = MockOrderBookManager(asks=[(101, 10), (102, 5)], bids=[(100, 10)])
    # Mid price = (101+100)/2 = 100.5
    # Target spend 101 USD -> buy 1 BTC at 101. Avg exec = 101.
    # Slippage = (101 - 100.5) / 100.5 * 100 = 0.4975%
    slp1, avg_p1, ast1, usd1 = calculate_slippage_walk_book(101, book1)
    print(f"Test 1 (Spend 101 USD): Slippage={slp1:.4f}%, AvgPrice={avg_p1:.2f}, Asset={ast1:.2f}, SpentUSD={usd1:.2f}")

    # Test case 2: Spend across multiple levels
    book2 = MockOrderBookManager(asks=[(101, 2), (102, 3), (103, 5)], bids=[(100, 10)])
    # Mid price = 100.5
    # Target spend 400 USD:
    # Level 1: 2 BTC @ 101 = 202 USD spent, 2 BTC acquired
    # Level 2: 3 BTC @ 102 = 306 USD. Remaining to spend: 400-202 = 198 USD. Can't take full level.
    #   Buy 198/102 = 1.941176 BTC @ 102.
    # Total asset = 2 + 1.941176 = 3.941176
    # Total USD spent = 202 + 198 = 400
    # Avg exec price = 400 / 3.941176 = 101.4925
    # Slippage = (101.4925 - 100.5) / 100.5 * 100 = 0.9875%
    slp2, avg_p2, ast2, usd2 = calculate_slippage_walk_book(400, book2)
    print(f"Test 2 (Spend 400 USD): Slippage={slp2:.4f}%, AvgPrice={avg_p2:.2f}, Asset={ast2:.4f}, SpentUSD={usd2:.2f}")

    # Test case 3: Insufficient liquidity
    # Target spend 1000 USD, but only (2*101 + 3*102 + 5*103) = 202 + 306 + 515 = 1023 USD available depth
    # Actually, it's more like: 2@101 (202), 3@102 (306), 5@103 (515). Total asset 10. Total value 1023.
    # If we spend 1500 USD, we'll exhaust the book.
    slp3, avg_p3, ast3, usd3 = calculate_slippage_walk_book(1500, book2)
    # Expected: total_asset_acquired = 2+3+5 = 10. total_usd_spent = 101*2 + 102*3 + 103*5 = 202+306+515 = 1023
    # avg_exec_price = 1023 / 10 = 102.3
    # slippage = (102.3 - 100.5) / 100.5 * 100 = 1.7910%
    print(f"Test 3 (Spend 1500 USD, exhaust book): Slippage={slp3:.4f}%, AvgPrice={avg_p3:.2f}, Asset={ast3:.2f}, SpentUSD={usd3:.2f}")

    # Test case 4: Zero USD spend
    slp4, avg_p4, ast4, usd4 = calculate_slippage_walk_book(0, book1)
    print(f"Test 4 (Spend 0 USD): Slippage={slp4}, AvgPrice={avg_p4}, Asset={ast4}, SpentUSD={usd4}")

    # Test case 5: Empty asks
    book5 = MockOrderBookManager(asks=[], bids=[(100,10)])
    slp5, avg_p5, ast5, usd5 = calculate_slippage_walk_book(100, book5)
    print(f"Test 5 (Empty asks): Slippage={slp5}, AvgPrice={avg_p5}, Asset={ast5}, SpentUSD={usd5}")