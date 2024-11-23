# buysell_fast.py

import requests
import json
import base64
import time
from solders.keypair import Keypair
from solders.transaction import Transaction, VersionedTransaction
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.message import Message
from solders.hash import Hash
import base58  # Required for decoding Base58-encoded keys
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solders.instruction import CompiledInstruction
from solders.message import MessageV0
import temporal_keys as tk  # Import your temporal keys
from solana.rpc.commitment import Commitment
from solana.transaction import AccountMeta
from solders.system_program import ID as SYS_PROGRAM_ID
from solders.instruction import Instruction

# Constants
LAMPORTS_PER_SOL = 1_000_000_000

MIN_TIP_AMOUNT = 1_000_000  # 0.001 SOL in lamports
USDC_TOKEN = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
NOZOMI_TIP = Pubkey.from_string("9eja7sHKA3PhvcghxiMz9pCktgaYxDDopZYbZxscNsHG")
NUM_ORDERS = 5  # 🌙 MoonDev's magic number - number of orders to place

def temporal_market_buy(token_address, loop_count=1, amount=1_000_000, slippage=50, PRIORITY_FEE=1000000):
    """
    Executes a market buy using Jupiter API and Temporal RPC for transaction submission
    """
    import dontshare as d
    import temporal_keys as tk
    import requests
    import json
    import base64
    from solders.keypair import Keypair
    from solders.transaction import VersionedTransaction
    from solders.message import MessageV0
    
    # Constants
    USDC_TOKEN = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    NOZOMI_TIP = Pubkey.from_string("TEMPaMeCRFAS9EKF53Jd6KpHxgL47uWLcpFArU1Fanq")
    
    try:
        print("\n🔄 Initializing...")
        helius_client = Client(d.helius_key)
        temporal_url = tk.east_key
        KEY = Keypair.from_base58_string(d.sol_key)
        print(f"🌙 MoonDev's Keypair loaded! Public Key: {KEY.pubkey()}")

        for i in range(loop_count):
            print(f"\n🔄 Starting transaction {i+1}/{loop_count}...")
            
            # Get Jupiter quote and swap data
            print("\n💫 Getting Jupiter quote...")
            quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={USDC_TOKEN}&outputMint={token_address}&amount={amount}'
            swap_url = 'https://quote-api.jup.ag/v6/swap'
            
            quote = requests.get(quote_url).json()
            print(f"📊 Expected output: {quote.get('outAmount', 'Unknown')} tokens")
            print(f"🔍 Quote details: {json.dumps(quote, indent=2)}")

            # Get swap transaction
            print("\n🔄 Getting swap transaction...")
            swap_data = {
                "quoteResponse": quote,
                "userPublicKey": str(KEY.pubkey()),
                "prioritizationFeeLamports": PRIORITY_FEE,
                "dynamicSlippage": {"minBps": 50, "maxBps": slippage}
            }
            print(f"📝 Swap request data: {json.dumps(swap_data, indent=2)}")
            
            tx_response = requests.post(swap_url, headers={"Content-Type": "application/json"}, json=swap_data).json()
            print(f"📬 Received swap response: {json.dumps(tx_response, indent=2)}")
            
            print("\n🎯 Creating new transaction with tip and swap...")
            
            # Create tip instruction
            tip_ix = transfer(
                TransferParams(
                    from_pubkey=KEY.pubkey(),
                    to_pubkey=NOZOMI_TIP,
                    lamports=MIN_TIP_AMOUNT
                )
            )
            print("💰 Created tip instruction")
            
            # Get Jupiter's instruction(s)
            print("🔄 Decoding Jupiter transaction...")
            swap_tx_data = base64.b64decode(tx_response['swapTransaction'])
            jupiter_tx = VersionedTransaction.from_bytes(swap_tx_data)
            print(f"📦 Jupiter transaction decoded, contains {len(jupiter_tx.message.instructions)} instructions")

            # Convert CompiledInstructions to regular Instructions
            print("🔄 Converting Jupiter instructions...")
            jupiter_instructions = []
            for compiled_ix in jupiter_tx.message.instructions:
                program_id = jupiter_tx.message.account_keys[compiled_ix.program_id_index]
                
                # Debug prints
                print(f"🔍 Processing instruction with {len(compiled_ix.accounts)} accounts")
                print(f"📊 Available account keys: {len(jupiter_tx.message.account_keys)}")
                print(f"🔑 Account indices: {compiled_ix.accounts}")
                
                # Validate account indices before creating AccountMeta objects
                accounts = []
                for idx in compiled_ix.accounts:
                    if idx >= len(jupiter_tx.message.account_keys):
                        print(f"⚠️ Warning: Account index {idx} out of range, skipping...")
                        continue
                        
                    is_signer = idx < jupiter_tx.message.header.num_required_signatures
                    
                    accounts.append(
                        AccountMeta(
                            pubkey=jupiter_tx.message.account_keys[idx],
                            is_signer=is_signer,
                            is_writable=True  # Assume writable for safety
                        )
                    )
                
                if accounts:  # Only add instruction if we have valid accounts
                    jupiter_instructions.append(
                        Instruction(
                            program_id=program_id,
                            accounts=accounts,
                            data=compiled_ix.data
                        )
                    )
                    print(f"✨ Converted instruction {len(jupiter_instructions)} with {len(accounts)} accounts")
                    print(f"🔑 Program: {program_id}")
                    print(f"📝 Account count: {len(accounts)}")
                    print(f"💫 Writable accounts: {sum(1 for a in accounts if a.is_writable)}")
                else:
                    print("⚠️ Skipping instruction with no valid accounts")

            print(f"✅ Converted {len(jupiter_instructions)} Jupiter instructions")

            # Create new versioned transaction
            print("\n🔄 Getting recent blockhash...")
            blockhash_response = helius_client.get_latest_blockhash(commitment="finalized")
            recent_blockhash = blockhash_response.value.blockhash
            print(f"📍 Blockhash: {recent_blockhash}")

            print("\n🔨 Building final versioned transaction...")
            
            # First, compile all instructions
            from solders.instruction import CompiledInstruction
            
            # Get all unique pubkeys that will be used
            all_pubkeys = list(set([KEY.pubkey(), NOZOMI_TIP] + [acc.pubkey for ix in jupiter_instructions for acc in ix.accounts]))
            
            # Helper function to find pubkey index
            def get_pubkey_index(pubkey):
                try:
                    return all_pubkeys.index(pubkey)
                except ValueError:
                    all_pubkeys.append(pubkey)
                    return len(all_pubkeys) - 1

            # Helper function to convert list to bytes
            def list_to_bytes(lst):
                return bytes(lst)

            # Compile tip instruction
            compiled_tip = CompiledInstruction(
                program_id_index=get_pubkey_index(tip_ix.program_id),
                accounts=list_to_bytes([get_pubkey_index(meta.pubkey) for meta in tip_ix.accounts]),  # Convert to bytes
                data=tip_ix.data
            )

            # Compile Jupiter instructions
            compiled_jupiter = [
                CompiledInstruction(
                    program_id_index=get_pubkey_index(ix.program_id),
                    accounts=list_to_bytes([get_pubkey_index(meta.pubkey) for meta in ix.accounts]),  # Convert to bytes
                    data=ix.data
                )
                for ix in jupiter_instructions
            ]

            print(f"🔧 Compiled {len(compiled_jupiter) + 1} instructions")
            
            # Create MessageV0 with compiled instructions
            message = MessageV0(
                header=jupiter_tx.message.header,
                account_keys=all_pubkeys,
                recent_blockhash=recent_blockhash,
                instructions=[compiled_tip] + compiled_jupiter,
                address_table_lookups=jupiter_tx.message.address_table_lookups
            )
            
            # Sign the message
            message_bytes = bytes(message)
            signature = KEY.sign_message(message_bytes)
            
            # Create transaction bytes
            tx_bytes = bytearray()
            tx_bytes.extend(bytes([1]))  # signature count
            tx_bytes.extend(bytes(signature))
            tx_bytes.extend(message_bytes)
            
            # Create VersionedTransaction from bytes
            final_tx = VersionedTransaction.from_bytes(bytes(tx_bytes))
            
            print("✅ Transaction created and signed with 🌙 MoonDev's key")
            print(f"🔑 Signature: {base58.b58encode(bytes(signature)).decode('utf-8')[:20]}...")

            print("\n🚀 Sending transaction through Temporal...")
            print(f"💸 Tip amount: {MIN_TIP_AMOUNT/LAMPORTS_PER_SOL:.3f} SOL")  # Fixed to show correct amount
            print(f"🔄 Total instructions: {len(jupiter_instructions) + 1}")
            
            # Send through Temporal
            encoded_tx = base64.b64encode(bytes(final_tx)).decode('utf-8')
            print(f"📝 Encoded transaction length: {len(encoded_tx)}")
            
            response = requests.post(
                temporal_url,
                headers={"Content-Type": "application/json"},
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        encoded_tx,
                        {
                            "encoding": "base64",
                            "skipPreflight": True,
                            "maxRetries": 1,
                            "preflightCommitment": "processed"
                        }
                    ]
                }
            ).json()

            if "result" in response:
                print(f"\n✨ Transaction {i+1} successful!")
                print(f"🔍 Transaction: https://solscan.io/tx/{response['result']}")
            else:
                print(f"\n❌ Transaction {i+1} failed: {response.get('error', 'Unknown error')}")
                return

    except Exception as e:
        print(f"\n❌ Error occurred:")
        print(f"Type: {type(e).__name__}")
        print(f"Details: {str(e)}")
        print("Stack trace:")
        import traceback
        traceback.print_exc()
        return

def decode_base64_padded(b64_string):
    """
    Decodes a Base64 string, adding padding if necessary.
    """
    b64_string_clean = ''.join(b64_string.split())
    missing_padding = len(b64_string_clean) % 4
    if missing_padding:
        b64_string_clean += '=' * (4 - missing_padding)
    try:
        return base64.b64decode(b64_string_clean)
    except Exception as e:
        print(f"Base64 decoding failed: {e}")
        return None

def determine_transaction_type(b64_tx):
    """
    Determines whether a transaction is a VersionedTransaction or Legacy Transaction.
    Returns 'Versioned', 'Legacy', or 'Unknown'.
    """
    tx_bytes = decode_base64_padded(b64_tx)
    if tx_bytes is None:
        return 'Invalid Base64'

    # Attempt to deserialize as VersionedTransaction
    try:
        versioned_tx = VersionedTransaction.deserialize(tx_bytes)
        print("Transaction is a Versioned Transaction.")
        return 'Versioned'
    except Exception as e:
        print(f"Failed to deserialize as VersionedTransaction: {e}")

    # Attempt to deserialize as Legacy Transaction
    try:
        legacy_tx = Transaction.from_bytes(tx_bytes)
        print("Transaction is a Legacy Transaction.")
        return 'Legacy'
    except Exception as e:
        print(f"Failed to deserialize as Legacy Transaction: {e}")

    print("Unable to determine transaction type.")
    return 'Unknown'

# ---------------------- Execution ----------------------

if __name__ == "__main__":
    # BONK token address
    BONK_ADDRESS = "2qEHjDLDLbuBgRYvsxhc5D6uDWAivNFZGan56P1tpump"
    
    # Run multiple buy orders
    temporal_market_buy(BONK_ADDRESS, loop_count=NUM_ORDERS)  # 🌙 Will try NUM_ORDERS times
