import asyncio
import websockets
import json
import logging
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from order_book_manager import OrderBookManager # Assuming it's in the same src directory

# Configure basic logging
# If you want to see DEBUG logs from OrderBookManager, set level=logging.DEBUG
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
logger = logging.getLogger(__name__) # Logger for this module

WEBSOCKET_URL = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"

async def connect_and_listen(book_manager: OrderBookManager):
    """
    Connects to the WebSocket server, listens for messages,
    and updates the OrderBookManager.
    """
    logger.info(f"Attempting to connect to WebSocket: {WEBSOCKET_URL}")
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            logger.info("Successfully connected to WebSocket.")
            logger.info("Listening for L2 order book data...")
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    book_manager.update_book(data)
                    
                    # Print some info from the book manager
                    # logger.info(f"Updated Book: Best Ask: {book_manager.get_best_ask()}, Best Bid: {book_manager.get_best_bid()}")
                    # Or use the __str__ method for more details
                    logger.info(f"\n{book_manager}")

                except json.JSONDecodeError:
                    logger.error(f"Could not decode JSON: {message}")
                except Exception as e:
                    # The OrderBookManager's update_book method has its own error handling for parsing issues
                    logger.error(f"Error processing message in connect_and_listen: {e} - Data: {message}")

    except websockets.exceptions.ConnectionClosedError as e:
        logger.error(f"WebSocket connection closed unexpectedly: {e}")
    except websockets.exceptions.InvalidURI:
        logger.error(f"Invalid WebSocket URI: {WEBSOCKET_URL}")
    except ConnectionRefusedError:
        logger.error(f"Connection refused. Ensure the server is running and accessible (VPN?).")
    except Exception as e:
        logger.error(f"An unexpected error occurred during WebSocket connection: {e}")
    finally:
        logger.info("WebSocket connection process finished or attempt failed.")

async def main():
    """
    Main function to initialize OrderBookManager and start WebSocket listener.
    """
    order_book = OrderBookManager()
    await connect_and_listen(order_book)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user. Exiting.")