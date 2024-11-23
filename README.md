# JupiterBot

JupiterBot is a Solana trading bot that uses the Jupiter API for market buys, Temporal RPC for transaction submission, and a built-in tipping system.

## How to Use
1. Populate `temporal_keys.py` with your Temporal RPC URLs.
2. Populate `dontshare.py` with your Helius API key and Solana private key.
3. Run the bot using `python main.py`.

## Dependencies
- Python 3.9 or later
- `requests`, `solders`, `base58`

## Run Instructions
```bash
python main.py

# JupiterBot

Original code is inspired by @moondevonyt
