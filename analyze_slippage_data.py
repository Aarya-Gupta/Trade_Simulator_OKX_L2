# analyze_slippage_data.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# --- Configuration ---
DATA_LOG_FILE = "slippage_regression_log.csv"
PERFORMANCE_LOG_FILE = "model_performance_log.csv"
PLOT_OUTPUT_DIR = "output_plots"

# Ensure plot output directory exists
if not os.path.exists(PLOT_OUTPUT_DIR):
    os.makedirs(PLOT_OUTPUT_DIR)

def plot_model_performance_evolution(df_perf):
    """Plots MSE and R2 score over training iterations."""
    if df_perf.empty or 'num_training_samples' not in df_perf.columns:
        print("Performance log is empty or missing required columns.")
        return

    df_perf = df_perf.sort_values(by='num_training_samples').dropna(subset=['test_mse', 'test_r2_score'])
    if df_perf.empty:
        print("No valid performance data to plot after sorting/dropping NaNs.")
        return

    fig, ax1 = plt.subplots(figsize=(12, 6))

    color = 'tab:red'
    ax1.set_xlabel('Number of Training Samples')
    ax1.set_ylabel('Test MSE', color=color)
    ax1.plot(df_perf['num_training_samples'], df_perf['test_mse'], color=color, marker='o', linestyle='-')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_yscale('log') # MSE can vary a lot, log scale might be better

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    color = 'tab:blue'
    ax2.set_ylabel('Test R2 Score', color=color)  # we already handled the x-label with ax1
    ax2.plot(df_perf['num_training_samples'], df_perf['test_r2_score'], color=color, marker='x', linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.set_ylim([-0.1, 1.05]) # R2 typically between 0 and 1, allow slightly outside for visibility

    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.title('Slippage Model Performance Evolution')
    plt.savefig(os.path.join(PLOT_OUTPUT_DIR, "model_performance_evolution.png"))
    plt.close(fig)
    print(f"Saved model_performance_evolution.png to {PLOT_OUTPUT_DIR}")


def plot_feature_vs_slippage(df_probes):
    """Plots relationships between features and true slippage for probe data."""
    if df_probes.empty:
        print("Probe data is empty, cannot plot feature relationships.")
        return

    features_to_plot = ['probe_order_size_usd', 'market_spread_bps', 'market_depth_best_ask_usd']
    
    for feature in features_to_plot:
        if feature not in df_probes.columns:
            print(f"Feature {feature} not found in probe data.")
            continue
        
        plt.figure(figsize=(10, 6))
        # Use a sample if data is too large to avoid overplotting
        sample_df = df_probes.sample(n=min(5000, len(df_probes)), random_state=1) if len(df_probes) > 5000 else df_probes
        
        sns.scatterplot(data=sample_df, x=feature, y='true_slippage_pct_walk_the_book', alpha=0.5)
        plt.title(f'{feature} vs. True Slippage (Probes)')
        plt.xlabel(feature)
        plt.ylabel('True Slippage % (Walk-the-Book)')
        plt.grid(True)
        plt.savefig(os.path.join(PLOT_OUTPUT_DIR, f"{feature}_vs_true_slippage.png"))
        plt.close()
        print(f"Saved {feature}_vs_true_slippage.png to {PLOT_OUTPUT_DIR}")

def plot_slippage_distribution(df_probes):
    """Plots the distribution of true slippage for probe data."""
    if df_probes.empty or 'true_slippage_pct_walk_the_book' not in df_probes.columns:
        print("Probe data is empty or missing slippage column, cannot plot distribution.")
        return

    plt.figure(figsize=(10, 6))
    sns.histplot(df_probes['true_slippage_pct_walk_the_book'], kde=True, bins=50)
    plt.title('Distribution of True Slippage % (Probes)')
    plt.xlabel('True Slippage % (Walk-the-Book)')
    plt.ylabel('Frequency')
    plt.grid(True)
    # Zoom in if values are very concentrated around zero
    # slippage_median = df_probes['true_slippage_pct_walk_the_book'].median()
    # slippage_std = df_probes['true_slippage_pct_walk_the_book'].std()
    # if slippage_std > 0:
    #     plt.xlim([slippage_median - 5*slippage_std, slippage_median + 5*slippage_std])
    plt.savefig(os.path.join(PLOT_OUTPUT_DIR, "true_slippage_distribution.png"))
    plt.close()
    print(f"Saved true_slippage_distribution.png to {PLOT_OUTPUT_DIR}")


def plot_predicted_vs_actual_for_user_orders(df_user_pred):
    """
    This is tricky because we don't have 'true' slippage for user orders in the same way.
    Instead, we can plot predicted slippage vs. features for user orders.
    """
    if df_user_pred.empty:
        print("User prediction data is empty.")
        return

    # Need to reconstruct features for user orders if they are not directly logged
    # Current CSV for user predictions mainly logs the prediction itself and order size.
    # For a more meaningful plot, we'd need the spread_bps and depth_ask_usd at the time of user prediction.
    # This requires extending the CSV logging for user predictions.
    # For now, let's plot Predicted Slippage vs. User Order Size.
    
    if 'user_order_size_usd' in df_user_pred.columns and 'predicted_slippage_pct_regression' in df_user_pred.columns:
        plt.figure(figsize=(10, 6))
        sample_df = df_user_pred.sample(n=min(5000, len(df_user_pred)), random_state=1) if len(df_user_pred) > 5000 else df_user_pred
        sns.scatterplot(data=sample_df, x='user_order_size_usd', y='predicted_slippage_pct_regression', alpha=0.5)
        plt.title('Predicted Slippage (Regression) vs. User Order Size')
        plt.xlabel('User Order Size (USD)')
        plt.ylabel('Predicted Slippage % (Regression)')
        plt.grid(True)
        plt.savefig(os.path.join(PLOT_OUTPUT_DIR, "predicted_slippage_vs_user_order_size.png"))
        plt.close()
        print(f"Saved predicted_slippage_vs_user_order_size.png to {PLOT_OUTPUT_DIR}")
    else:
        print("User prediction data missing required columns for plotting.")


def main():
    print(f"Analyzing data from {DATA_LOG_FILE} and {PERFORMANCE_LOG_FILE}")

    # --- Load Probe Data (for feature analysis and slippage distribution) ---
    try:
        df_all = pd.read_csv(DATA_LOG_FILE)
        # Filter for rows that represent probe data (where 'probe_order_size_usd' is not NaN)
        df_probes = df_all[df_all['probe_order_size_usd'].notna()].copy()
        df_probes['probe_order_size_usd'] = pd.to_numeric(df_probes['probe_order_size_usd'], errors='coerce')
        df_probes['market_spread_bps'] = pd.to_numeric(df_probes['market_spread_bps'], errors='coerce')
        df_probes['market_depth_best_ask_usd'] = pd.to_numeric(df_probes['market_depth_best_ask_usd'], errors='coerce')
        df_probes['true_slippage_pct_walk_the_book'] = pd.to_numeric(df_probes['true_slippage_pct_walk_the_book'], errors='coerce')
        df_probes.dropna(subset=['probe_order_size_usd', 'market_spread_bps', 'market_depth_best_ask_usd', 'true_slippage_pct_walk_the_book'], inplace=True)
        
        # Filter out extreme outliers in true_slippage_pct if necessary for better visualization
        # For example, cap at 50% or something reasonable if walk-the-book yields huge numbers
        # df_probes = df_probes[df_probes['true_slippage_pct_walk_the_book'].abs() < 50]


        print(f"Loaded {len(df_probes)} valid probe data points.")
    except FileNotFoundError:
        print(f"Error: {DATA_LOG_FILE} not found.")
        df_probes = pd.DataFrame()
    except Exception as e:
        print(f"Error loading or processing {DATA_LOG_FILE}: {e}")
        df_probes = pd.DataFrame()

    # --- Load User Prediction Data ---
    try:
        # Filter for rows that represent user predictions
        df_user_pred = df_all[df_all['user_order_size_usd'].notna()].copy()
        df_user_pred['user_order_size_usd'] = pd.to_numeric(df_user_pred['user_order_size_usd'], errors='coerce')
        df_user_pred['predicted_slippage_pct_regression'] = pd.to_numeric(df_user_pred['predicted_slippage_pct_regression'], errors='coerce')
        df_user_pred.dropna(subset=['user_order_size_usd', 'predicted_slippage_pct_regression'], inplace=True)
        print(f"Loaded {len(df_user_pred)} valid user prediction data points.")
    except FileNotFoundError: # Already handled above, but keep for structure
        df_user_pred = pd.DataFrame()
    except Exception as e: # If df_all failed to load
        print(f"Error accessing data for user predictions (likely from initial load fail): {e}")
        df_user_pred = pd.DataFrame()


    # --- Load Model Performance Data ---
    try:
        df_perf = pd.read_csv(PERFORMANCE_LOG_FILE)
        df_perf['num_training_samples'] = pd.to_numeric(df_perf['num_training_samples'], errors='coerce')
        df_perf['test_mse'] = pd.to_numeric(df_perf['test_mse'], errors='coerce')
        df_perf['test_r2_score'] = pd.to_numeric(df_perf['test_r2_score'], errors='coerce')
        print(f"Loaded {len(df_perf)} model performance records.")
    except FileNotFoundError:
        print(f"Error: {PERFORMANCE_LOG_FILE} not found.")
        df_perf = pd.DataFrame()
    except Exception as e:
        print(f"Error loading or processing {PERFORMANCE_LOG_FILE}: {e}")
        df_perf = pd.DataFrame()

    # --- Generate Plots ---
    if not df_perf.empty:
        plot_model_performance_evolution(df_perf)
    
    if not df_probes.empty:
        plot_feature_vs_slippage(df_probes)
        plot_slippage_distribution(df_probes)
    
    if not df_user_pred.empty:
        plot_predicted_vs_actual_for_user_orders(df_user_pred) # Name is a bit misleading now

    print(f"\nAnalysis complete. Plots saved to '{PLOT_OUTPUT_DIR}' directory.")

if __name__ == "__main__":
    main()