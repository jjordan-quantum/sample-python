import time
import json
import re
from web3 import Web3


######################################################################################
# ACCOUNTS AND CONTRACTS:
######################################################################################


with open('config.json', 'r') as read_file:
    config = json.load(read_file)

ACCOUNT = config["account"]
PRIVATE_KEY = config["private_key"]
PROVIDER = config["provider"]
ROUTER_ADDRESS = config["router_address"]
FACTORY_ADDRESS = config["factory_address"]
STAKING_CONTRACT_ADDRESS = config["staking_contract_address"]
STAKING_CONTRACT_ABI_FILENAME = config["staking_contract_abi_filename"]
SLIPPAGE = config["slippage"]
GAS_PRICE_MULTIPLIER = config["gas_price_multiplier"]
MAX_APPROVAL_HEX = "0x" + "f" * 64
MAX_APPROVAL_INT = int(MAX_APPROVAL_HEX, 16)

cubbusd_address = '0x0EF564D4F8D6C0ffE13348A32e21EFd55e508e84'
cub_address = '0x50D809c74e0B8e49e7B4c65BB3109AbE3Ff4C1C1'
busd_address = '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'


######################################################################################
# CONNECT TO WEB3
######################################################################################


if re.match(r'^https*:', PROVIDER):
    provider_object = Web3.HTTPProvider(PROVIDER, request_kwargs={"timeout": 60})
elif re.match(r'^ws*:', PROVIDER):
    provider_object = Web3.WebsocketProvider(PROVIDER)
elif re.match(r'^/', PROVIDER):
    provider_object = Web3.IPCProvider(PROVIDER)
else:
    raise RuntimeError("Unknown provider type " + PROVIDER)
web3 = Web3(provider_object)


######################################################################################
# CREATE CONTRACT INSTANCES
######################################################################################


# get staking contract ABI
with open('lib/'+STAKING_CONTRACT_ABI_FILENAME, 'r') as read_file:
    STAKING_ABI = json.load(read_file)['abi']

# get ERC20 ABI
with open('lib/IUniswapV2ERC20.json', 'r') as read_file:
    ERC20_ABI = json.load(read_file)['abi']

# get pair ABI
with open('lib/IUniswapV2Pair.json', 'r') as read_file:
    PAIR_ABI = json.load(read_file)['abi']

# get router ABI
with open('lib/IUniswapV2Router02.json', 'r') as read_file:
    ROUTER_ABI = json.load(read_file)['abi']

router = web3.eth.contract(address=ROUTER_ADDRESS, abi=ROUTER_ABI)
staking_contract = web3.eth.contract(address=STAKING_CONTRACT_ADDRESS, abi=STAKING_ABI)


def main():

    run_test()


def run_test():

    add_liquidity(cub_address, busd_address, cubbusd_address)
    stake_lp_tokens(10)
    unstake_lp_tokens(10)
    remove_liquidity(cub_address, busd_address, cubbusd_address)


def add_liquidity(token0_address, token1_address, pair_address, amount0=None, amount1=None, deadline=120):

    txns = []

    # get balance of token0 and token1 in wallet
    token0_balance = get_balance_of(token0_address, ACCOUNT)
    token1_balance = get_balance_of(token1_address, ACCOUNT)

    # debugging
    print(f'token0_balance: {token0_balance}')
    print(f'token1_balance: {token1_balance}')

    # set desired amount to add to liquidity for token0
    if amount0:
        if amount0 > token0_balance:
            amount0_desired = token0_balance
        else:
            amount0_desired = amount0
    else:
        amount0_desired = token0_balance

    # get reserves to determine ideal ratio for adding liquidity
    reserves = get_reserves(pair_address)
    token0_reserve = reserves[0]
    token1_reserve = reserves[1]

    # set amount1_desired, based on amount0_desired and reserve ratio
    amount1_desired = int((token1_reserve / token0_reserve) * amount0_desired)

    # if required, reduce both amounts at the current reserve ratio, to ensure they
    # are both below the wallet's balance of each token
    if amount1_desired > token1_balance:
        amount1_desired = token1_balance
        amount0_desired = int((token0_reserve / token1_reserve) * amount1_desired)

    # set minimum amounts for txn based on slippage
    amount0_min = int(float(amount0_desired) * SLIPPAGE)
    amount1_min = int(float(amount1_desired) * SLIPPAGE)

    # approve router to spend token0
    approve_token0 = _approve(token0_address, max_approval=amount0_desired)

    print('Approve token0 txn:')
    print(approve_token0)
    txns.append(approve_token0)

    # approve router to spend token1
    approve_token1 = _approve(token1_address, max_approval=amount1_desired)

    print('Approve token1 txn:')
    print(approve_token1)
    txns.append(approve_token1)

    # set deadline for the add liquidity transaction
    current_unix_time = int(time.time())
    unix_deadline = current_unix_time + deadline

    # get nonce value for account
    nonce = web3.eth.get_transaction_count(ACCOUNT)

    # build add liquidity txn
    txn = router.functions.addLiquidity(
        token0_address,
        token1_address,
        amount0_desired,
        amount1_desired,
        amount0_min,
        amount1_min,
        ACCOUNT,
        unix_deadline
    ).buildTransaction({
        'gas': 300000,
        'gasPrice': int(web3.eth.gas_price*GAS_PRICE_MULTIPLIER),
        'nonce': nonce
    })

    # sign and send txn
    signed_txn = web3.eth.account.sign_transaction(txn, private_key=get_key())
    txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)

    # wait for txn receipt
    receipt = web3.eth.wait_for_transaction_receipt(txn_hash)

    print('Add liquidity txn:')
    print(web3.toHex(txn_hash))
    txns.append(web3.toHex(txn_hash))
    return txns

def stake_lp_tokens(pid, amount=None, private_key=None):

    txns = []

    # Get LP Token address and create Token instance
    lp_token_address = get_lp_token_address(pid)

    # APPROVE LP TOKENS FOR SPEND BY ROUTER

    # get balance of LP tokens in wallet
    lp_token_balance = get_balance_of(lp_token_address, ACCOUNT)

    # Set amounts
    if not amount or amount > lp_token_balance:
        amount = lp_token_balance

    # approve router to spend LP tokens
    approve_lp_txn = _approve(lp_token_address, max_approval=amount)

    print('Approve LP Token txn:')
    print(approve_lp_txn)
    txns.append(approve_lp_txn)

    # STAKE LP-TOKENS IN POOL

    # set nonce
    nonce = web3.eth.get_transaction_count(ACCOUNT)

    # build stake txn
    stake_txn = staking_contract.functions.deposit(
        pid,
        amount
    ).buildTransaction({
        'gas': 200000,
        'gasPrice': int(web3.eth.gas_price*GAS_PRICE_MULTIPLIER),
        'nonce': nonce
    })

    # sign and send txn
    signed_txn = web3.eth.account.sign_transaction(stake_txn, private_key=get_key())
    txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    receipt = web3.eth.wait_for_transaction_receipt(txn_hash)

    print(f'Stake in pool {pid} txn:')
    print(web3.toHex(txn_hash))
    txns.append(web3.toHex(txn_hash))
    return txns

def unstake_lp_tokens(pid, amount=None, private_key=None):

    txns = []

    # get balance from pool
    result = staking_contract.functions.userInfo(pid, ACCOUNT).call()
    pool_balance = result[0]
    amount = pool_balance

    if amount > 0:
        # set nonce
        nonce = web3.eth.get_transaction_count(ACCOUNT)

        # build unstake txn
        unstake_txn = staking_contract.functions.withdraw(
            pid,
            amount
        ).buildTransaction({
            'gas': 200000,
            'gasPrice': int(web3.eth.gas_price*GAS_PRICE_MULTIPLIER),
            'nonce': nonce
        })

        # sign and send txn
        signed_txn = web3.eth.account.sign_transaction(unstake_txn, private_key=get_key())
        txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = web3.eth.wait_for_transaction_receipt(txn_hash)

        print('Unstake from cubdefi pool txn:')
        print(web3.toHex(txn_hash))
        txns.append(web3.toHex(txn_hash))
    return txns

def remove_liquidity(token0_address, token1_address, pair_address, liquidity=None, deadline=120):

    txns = []

    # get balance of LP tokens in wallet
    lp_token_balance = get_balance_of(pair_address, ACCOUNT)

    # if amount to remove not specified, use full LP token balance
    if not liquidity or liquidity > lp_token_balance:
        liquidity = lp_token_balance

    # approve router to spend LP tokens
    approve_liquidity_txn = _approve(pair_address, max_approval=liquidity)

    print('Approve LP-token txn:')
    print(approve_liquidity_txn)
    txns.append(approve_liquidity_txn)

    # determine desired and minimum amounts of cub and busd
    total_supply = get_total_supply(pair_address)
    percent_of_liquidity = float(liquidity) / total_supply

    reserves = get_reserves(pair_address)
    token0_reserve = reserves[0]
    token1_reserve = reserves[1]

    token0_min = int(SLIPPAGE * percent_of_liquidity * token0_reserve)
    token1_min = int(SLIPPAGE * percent_of_liquidity * token1_reserve)

    # set deadline for txn
    current_unix_time = int(time.time())
    unix_deadline = current_unix_time + deadline

    # get wallet's nonce value
    nonce = web3.eth.get_transaction_count(ACCOUNT)

    # build remove liquidity txn
    txn = router.functions.removeLiquidity(
        token0_address,
        token1_address,
        liquidity,
        token0_min,
        token1_min,
        ACCOUNT,
        unix_deadline
    ).buildTransaction({
        'gas': 300000,
        'gasPrice': int(web3.eth.gas_price*GAS_PRICE_MULTIPLIER),
        'nonce': nonce
    })
    # sign and send txn
    signed_txn = web3.eth.account.sign_transaction(txn, private_key=get_key())
    txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    receipt = web3.eth.wait_for_transaction_receipt(txn_hash)

    print('Remove liquidity txn:')
    print(web3.toHex(txn_hash))
    txns.append(web3.toHex(txn_hash))
    return txns


def harvest(pid):

    txns = []

    # set amount for deposit to 0 - this triggers a harvest
    amount = 0

    # set nonce
    nonce = web3.eth.get_transaction_count(ACCOUNT)

    # build stake txn
    harvest_txn = staking_contract.functions.deposit(
        pid,
        amount
    ).buildTransaction({
        'gas': 200000,
        'gasPrice': int(web3.eth.gas_price*GAS_PRICE_MULTIPLIER),
        'nonce': nonce
    })

    # sign and send txn
    signed_txn = web3.eth.account.sign_transaction(harvest_txn, private_key=get_key())
    txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    receipt = web3.eth.wait_for_transaction_receipt(txn_hash)

    print('Stake on cubdefi pool txn:')
    print(web3.toHex(txn_hash))
    txns.append(web3.toHex(txn_hash))
    return txns


######################################################################################
# CONTRACT HELPER FUNCTIONS:
######################################################################################


def get_lp_token_address(pid):
    # returns the lp token address for the given pool # ID

    return staking_contract.functions.poolInfo(pid).call()[0]


def get_reserve_ratio(pair):
    # return the current reserve ratio for the LP pool with the given address

    reserves = get_reserves(pair)
    return float(reserves[1]) / reserves[0]


def get_reserves(pair):
    # return the current reserves

    contract = web3.eth.contract(address=pair, abi=PAIR_ABI)
    return contract.functions.getReserves().call()


def get_total_supply(token):
    # return the totalSupply

    contract = web3.eth.contract(address=token, abi=ERC20_ABI)
    return contract.functions.totalSupply().call()


def get_balance_of(token, account):
    # return balanceOf for the given address

    contract = web3.eth.contract(address=token, abi=ERC20_ABI)
    return contract.functions.balanceOf(account).call()


######################################################################################
# SWAP FUNCTIONS:
######################################################################################


def swap_exact_tokens_for_tokens(self, amount, min_out, path, to, deadline, gas=None, gas_price=None):
    """
    Swaps an exact amount of input tokens for as many output tokens as
    possible, along the route determined by the path. The first element of
    path is the input token, the last is the output token, and any intermediate
    elements represent intermediate pairs to trade through (if for example,
    a direct pair does not exist)

    :param amount: Amount of input tokens to send.
    :param min_out: Minimum amount of output tokens that must be received for the transaction not to revert.
    :param path: Array of token addresses (pools of consecutive pair of addresses must exist and have liquidity).
    :param to: Address of the recipient for the output tokens.
    :param deadline: Unix timestamp after which the transaction will revert.
    :return: Transaction receipt.
    """

    func = self.router.functions.swapExactTokensForTokens(amount, min_out, path, to, deadline)
    params = self._create_transaction_params(gas=gas, gas_price=gas_price)
    txn_receipt = self._send_transaction(func, params)
    return txn_receipt

def swap_tokens_for_exact_tokens(self, amount_out, amount_in_max, path, to, deadline, gas=None, gas_price=None):
    """
    Receive an exact amount of output tokens for as few input tokens as
    possible, along the route determined by the path. The first element of
    path is the input token, the last is the output token, and any intermediate
    elements represent intermediate pairs to trade through (if for example,
    a direct pair does not exist).

    :param amount_out: Amount of tokens to receive.
    :param amount_in_max: Maximum amount of input tokens that can be required before the transaction reverts.
    :param path: Array of token addresses (pools of consecutive pair of addresses must exist and have liquidity).
    :param to: Address of the recipient for the output tokens.
    :param deadline: Unix timestamp after which the transaction will revert.
    :return: Transaction receipt.
    """

    func = self.router.functions.swapTokensForExactTokens(amount_out, amount_in_max, path, to, deadline)
    params = self._create_transaction_params(gas=gas, gas_price=gas_price)
    txn_receipt = self._send_transaction(func, params)
    return txn_receipt


######################################################################################
# APPROVAL FUNCTIONS:
######################################################################################


def _is_approved(token, amount):

    erc20_contract = web3.eth.contract(
        address=Web3.toChecksumAddress(token), abi=ERC20_ABI)
    print(erc20_contract, token)
    approved_amount = erc20_contract.functions.allowance(ACCOUNT, ROUTER_ADDRESS).call()
    return approved_amount >= amount


def is_approved(token, amount):
    print("Checking allowance....")
    return _is_approved(token, amount)


def _approve(token, max_approval=None, gas=150000, gas_price=None):

    if not max_approval:
        max_approval = MAX_APPROVAL_INT
    else:
        max_approval = int(max_approval)
    if _is_approved(token, max_approval):
        print("Approval complete!")
        return

    if not gas_price:
        gas_price = int(web3.eth.gas_price*GAS_PRICE_MULTIPLIER)

    print("Approving {} of {}".format(max_approval, token))
    erc20_contract = web3.eth.contract(address=Web3.toChecksumAddress(token), abi=ERC20_ABI)

    function = erc20_contract.functions.approve(ROUTER_ADDRESS, max_approval)
    params = _create_transaction_params(gas=gas, gas_price=gas_price)
    txn = _send_transaction(function, params)

    print("Approval complete!")
    return txn


######################################################################################
# TRANSACTION UTILITIES:
######################################################################################


def _create_transaction_params(value=0, gas=None, gas_price=None):

    print("Creating transaction parameters....")
    if not gas:
        gas = 500000
    if not gas_price:
        gas_price = int(web3.eth.gas_price*GAS_PRICE_MULTIPLIER)
    return {
        "from": ACCOUNT,
        "value": value,
        'gasPrice': gas_price,
        "gas": gas,
        "nonce": web3.eth.get_transaction_count(ACCOUNT),
    }


def _send_transaction(function, params):

    print("Sending transaction....")
    txn = function.buildTransaction(params)
    signed_txn = web3.eth.account.sign_transaction(txn, private_key=get_key())
    # ------------------ WAIT FOR TXN RECEIPT ------------------------------ #
    txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    receipt = web3.eth.wait_for_transaction_receipt(txn_hash, timeout=300)
    return web3.toHex(txn_hash)


####################################################################
# UTILITIES
####################################################################


def get_key():

    # this can be updated with various security features if desired
    return PRIVATE_KEY


####################################################################
# RUN MAIN
####################################################################


if __name__=='__main__':
    main()
