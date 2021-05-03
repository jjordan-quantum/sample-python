from web3 import Web3
import time
import json
from pancake import Pancake
import pair_functions
from lib import key, abi

# TODO
# Check that tokenAMin and tokenBMin are less than the balances in wallet

'''
FARMS:
CUB-BUSD
bLEO-BNB
USDT-BUSD
'''
# CUB-BUSD:
#------------------------------------------------------------------
# CUB-BUSD LP Token
cubbusd_address = '0x0EF564D4F8D6C0ffE13348A32e21EFd55e508e84'
cubbusd_abi = json.loads(abi.cubbusd_abi)

lionsden_address = '0x227e79C83065edB8B954848c46ca50b96CB33E16'
lionsden_abi = json.loads(abi.lionsden_abi)

#------------------------------------------------------------------
# CONNECT TO BSC

#wallet_address = '0xcfB7624E20Dd39f373FC92fC447B1398bf40bd35'
wallet_address = '0xBaDe72bB36e39E3c201c2C6F645F683614CbAA7f'
private_key = key.key

# using wss provider - required for filters
#provider = 'wss://bsc-ws-node.nariox.org:443'
#web3 = Web3(Web3.WebsocketProvider(provider))

# using http provider
provider = 'https://bsc-dataseed.binance.org/'
web3 = Web3(Web3.HTTPProvider(provider))

# required for reading timestamps from block objects
'''
from web3.middleware import geth_poa_middleware
# inject the poa compatibility middleware to the innermost layer
web3.middleware_onion.inject(geth_poa_middleware, layer=0)
'''

#-------------------------------------------------------------------
# NEW IMPLEMENTATION
#-------------------------------------------------------------------
def run_test():
    # instantiate Pancake
    pancake = Pancake(wallet=wallet_address, private_key=private_key)
    router = pancake.router
    cubbusd = pancake.web3.eth.contract(address=cubbusd_address, abi=cubbusd_abi)
    cubbusd_token = pancake.Token("CUBBUSD-LP", pancake.web3, cubbusd_address, cubbusd_abi)

    # create local references to the desired Token objects
    cub = pancake.tokens["CUB"]     # reserve0
    busd = pancake.tokens["BUSD"]   # reserve1

    slippage = 0.95

    # ADD LIQUIDITY

    cub_balance = cub.getBalanceOf(wallet_address)
    busd_balance = busd.getBalanceOf(wallet_address)

    cubDesired = int(0.9*cub_balance)
    cubMin = int(float(cubDesired) * slippage)

    cubReserve = pair_functions.getReserve(pancake.web3, cubbusd_address, cubbusd_abi, 0)
    busdReserve = pair_functions.getReserve(pancake.web3, cubbusd_address, cubbusd_abi, 1)
    busdDesired = router.quote(cubDesired, cubReserve, busdReserve)
    busdMin = int(float(busdDesired) * slippage)

    if busd_balance < busdMin:
        busdMin = busd_balance

    approve_cub = cub.approve(sender=wallet_address,
                              spender=router.address,
                              amount=cubDesired,
                              private_key=private_key)

    print('Approve CUB txn:')
    print(pancake.web3.toHex(approve_cub))

    approve_busd = busd.approve(sender=wallet_address,
                                spender=router.address,
                                amount=busdDesired,
                                private_key=private_key)

    print('Approve BUSD txn:')
    print(pancake.web3.toHex(approve_busd))

    current_unix_time = int(time.time())
    unix_deadline = current_unix_time + 120

    nonce = pancake.web3.eth.get_transaction_count(wallet_address)

    txn = router.contract.functions.addLiquidity(
                    cub.address,
                    busd.address,
                    cubDesired,
                    busdDesired,
                    cubMin,
                    busdMin,
                    wallet_address,
                    unix_deadline
                ).buildTransaction({
                    'gas': 300000,
                    'gasPrice': pancake.web3.eth.gas_price,
                    'nonce': nonce
                })

    signed_txn = pancake.web3.eth.account.sign_transaction(txn, private_key=private_key)
    txn_hash = pancake.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    receipt = pancake.web3.eth.wait_for_transaction_receipt(txn_hash)

    print('Add liquidity txn:')
    print(pancake.web3.toHex(txn_hash))

    # STAKE ON CUB FARMS

    # CHECK APPROVAL OF LP-TOKENS and APPROVE IF NECESSARY

    #check balance of LP token
    cubbusd_balance = cubbusd_token.getBalanceOf(wallet_address)
    amount = cubbusd_balance

    #check allowance
    allowance = cubbusd_token.getAllowance(wallet_address, router.address)

    #lp.approve
    if allowance < amount:
        approve_lp = cubbusd_token.approve(sender=wallet_address,
                                           spender=router.address,
                                           amount=amount,
                                           private_key=private_key)
        print('Approve CUB-BUSD LP txn:')
        print(pancake.web3.toHex(approve_lp))

    # STAKE LP-TOKENS IN POOL

    # lionsden contract instance (main staking contract)
    lionsden = pancake.web3.eth.contract(address=lionsden_address, abi=lionsden_abi)

    # pool ID
    pid = 10 # CUB-BUSD pool

    # set nonce
    nonce = pancake.web3.eth.get_transaction_count(wallet_address)

    # build stake txn
    stake_txn = lionsden.functions.deposit(
                    pid,
                    amount
                ).buildTransaction({
                    'gas': 200000,
                    'gasPrice': pancake.web3.eth.gas_price,
                    'nonce': nonce
                })

    signed_txn = pancake.web3.eth.account.sign_transaction(stake_txn, private_key=private_key)
    txn_hash = pancake.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    receipt = pancake.web3.eth.wait_for_transaction_receipt(txn_hash)

    print('Stake on cubdefi pool txn:')
    print(pancake.web3.toHex(txn_hash))

    # UNSTAKE LP-TOKENS FROM POOL

    # get balance from pool
    result = lionsden.functions.userInfo(pid, wallet_address).call()
    pool_balance = result[0]
    amount = pool_balance

    # set nonce
    nonce = pancake.web3.eth.get_transaction_count(wallet_address)

    # build unstake txn
    unstake_txn = lionsden.functions.withdraw(
                    pid,
                    amount
                ).buildTransaction({
                    'gas': 200000,
                    'gasPrice': pancake.web3.eth.gas_price,
                    'nonce': nonce
                })

    signed_txn = pancake.web3.eth.account.sign_transaction(unstake_txn, private_key=private_key)
    txn_hash = pancake.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    receipt = pancake.web3.eth.wait_for_transaction_receipt(txn_hash)

    print('Unstake from cubdefi pool txn:')
    print(pancake.web3.toHex(txn_hash))

    # REMOVE LIQUIDITY


    cubbusd_balance = cubbusd_token.getBalanceOf(wallet_address)
    liquidity = cubbusd_balance

    approve_liquidity = cubbusd_token.approve(sender=wallet_address,
                                              spender=router.address,
                                              amount=liquidity,
                                              private_key=private_key)

    print('Approve LP-token txn:')
    print(pancake.web3.toHex(approve_liquidity))

    totalSupply = cubbusd.functions.totalSupply().call()
    percent_of_liquidity = float(liquidity) / totalSupply

    cubbusd_reserves = cubbusd.functions.getReserves().call()
    cub_reserve = cubbusd_reserves[0]
    busd_reserve = cubbusd_reserves[1]

    cubMin = int(slippage * percent_of_liquidity * cub_reserve)
    busdMin = int(slippage * percent_of_liquidity * busd_reserve)

    current_unix_time = int(time.time())
    unix_deadline = current_unix_time + 120

    nonce = pancake.web3.eth.get_transaction_count(wallet_address)

    txn = router.contract.functions.removeLiquidity(
                    cub.address,
                    busd.address,
                    liquidity,
                    cubMin,
                    busdMin,
                    wallet_address,
                    unix_deadline
                ).buildTransaction({
                    'gas': 300000,
                    'gasPrice': pancake.web3.eth.gas_price,
                    'nonce': nonce
                })

    signed_txn = pancake.web3.eth.account.sign_transaction(txn, private_key=private_key)
    txn_hash = pancake.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    receipt = pancake.web3.eth.wait_for_transaction_receipt(txn_hash)


    txn_hash = router.addLiquidity(sender=wallet_address,
                                   tokenA=cub.address,
                                   tokenB=busd.address,
                                   amountADesired=cubDesired,
                                   amountBDesired=busdDesired,
                                   amountAMin=cubMin,
                                   amountBMin=busdMin,
                                   private_key=private_key)

    print('Remove liquidity txn:')
    print(pancake.web3.toHex(txn_hash))

