# src/config.py

# OKX Spot Trading Fee Rates (Taker fees, as market orders are Takers)
# These are examples. Refer to the latest OKX documentation for accuracy.
# Format: "Fee Tier Name": taker_fee_rate (as a decimal, e.g., 0.001 for 0.1%)
OKX_FEE_RATES = {
    # Regular Users (based on KSM holdings, simplified here)
    "Regular User LV1": {"taker": 0.0010},  # 0.10%
    "Regular User LV2": {"taker": 0.0009},  # 0.09% (example)
    "Regular User LV3": {"taker": 0.0008},  # 0.08% (example)
    # VIP Tiers (based on 30-day trading volume and asset balance)
    "VIP 1": {"taker": 0.0008},    # 0.08%
    "VIP 2": {"taker": 0.0007},    # 0.07%
    "VIP 3": {"taker": 0.0006},    # 0.06%
    "VIP 4": {"taker": 0.0005},    # 0.05%
    "VIP 5": {"taker": 0.0004},    # 0.04%
    "VIP 6": {"taker": 0.0003},    # 0.03%
    "VIP 7": {"taker": 0.0002},    # 0.02%
    "VIP 8": {"taker": 0.0001},    # 0.01%
    # A default/custom if tier not found, or if user selects "Custom"
    "Custom": {"taker": 0.0010}    # Default to 0.10% if custom or not found
}

# Default fee if a tier is not found in the map
DEFAULT_TAKER_FEE_RATE = 0.0010 # 0.10%