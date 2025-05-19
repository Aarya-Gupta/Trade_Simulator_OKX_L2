# src/financial_calculations.py
import logging
from .config import OKX_FEE_RATES, DEFAULT_TAKER_FEE_RATE # Use . for relative import

logger = logging.getLogger(__name__)

def calculate_expected_fees(quantity_usd: float, fee_tier: str) -> float:
    """
    Calculates the expected trading fees based on the quantity in USD and fee tier.
    Assumes market orders are always Taker orders.

    Args:
        quantity_usd (float): The total value of the order in USD.
        fee_tier (str): The selected fee tier from the UI.

    Returns:
        float: The calculated fee in USD.
    """
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
    # logger.debug(f"Calculated fee: {expected_fee} USD for quantity {quantity_usd} USD at tier '{fee_tier}' (rate: {taker_fee_rate})")
    return expected_fee

if __name__ == '__main__':
    # Test cases
    print(f"Fee for 100 USD, Regular User LV1: {calculate_expected_fees(100, 'Regular User LV1')} USD") # Expected 0.1 USD
    print(f"Fee for 1000 USD, VIP 8: {calculate_expected_fees(1000, 'VIP 8')} USD")       # Expected 0.1 USD
    print(f"Fee for 100 USD, Unknown Tier: {calculate_expected_fees(100, 'Random Tier')} USD")# Expected 0.1 USD
    print(f"Fee for 0 USD, VIP 1: {calculate_expected_fees(0, 'VIP 1')} USD")            # Expected 0.0 USD
    print(f"Fee for -100 USD, VIP 1: {calculate_expected_fees(-100, 'VIP 1')} USD")       # Expected 0.0 USD