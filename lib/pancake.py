from web3 import Web3
from lib import pancake_contracts
import time
import json


class Pancake:

    def __init__(
        self,
        wallet,
        private_key,
        router_address = pancake_contracts.default_router_address,
        router_abi = pancake_contracts.default_router_abi,
        factory_address = pancake_contracts.default_factory_address,
        factory_abi = pancake_contracts.default_factory_abi,
        http_provider = pancake_contracts.default_http_provider,
        web3=None
        ):

        self.wallet = wallet
        self.private_key = private_key

        if web3:
            self.web3 = web3
        else:
            self.web3 = Web3(Web3.HTTPProvider(http_provider))

        self.factory = self.web3.eth.contract(address=factory_address, abi=json.loads(factory_abi))
        self.router = self.Router(router_address, router_abi, self.factory, self.web3, self.wallet, self.private_key)

        self.tokens = {}
        self.addTokens()

    def toWei(self, etherValue):
        return self.web3.toWei(etherValue, 'ether')

    def fromWei(self, weiValue):
        return self.web3.fromWei(weiValue, 'ether')

    # returns BNB balance of address, in token value
    def getBalance(self, address):
        return float(self.fromWei(self.getBalanceWei(address)))

    def getBalanceWei(self, address):
        return self.web3.eth.get_balance(address)

    def addTokens(self):
        file_name = "lib/pancake_info.json"
        with open(file_name) as f:
            token_library = json.load(f)

        for token_name in token_library:
            address = token_library[token_name]['address']
            abi = token_library[token_name]['abi']
            if abi == "Contract source code not verified":
                continue
            self.tokens[token_name] = Pancake.Token(token_name, self.web3, address, abi)
            self.tokens[address] = self.tokens[token_name]

    def getSwapRate(self, fromToken, toToken):
        # returns the amount of tokenOut, from an input of 1 tokenIn token (in token values)
        # parameters are token address or token name
        if fromToken == "BNB":
            fromToken = "WBNB"
        if toToken == "BNB":
            toToken = "WBNB"
        tokenA = self.tokens[fromToken]
        tokenB = self.tokens[toToken]
        path0 = self.web3.toChecksumAddress(tokenA.address)
        path1 = self.web3.toChecksumAddress(tokenB.address)
        path = [path0, path1]
        amountIn = tokenA.fromTokenToWei(1)
        amountsOut = self.router.getAmountsOut(amountIn, path)
        amountOut = amountsOut[1]
        return tokenB.fromWeiToToken(amountOut)

    def getAmountOut(self, amountIn, fromToken, toToken):
        # returns the amount of tokenOut, from an input of amountIn tokenIn (in token values)
        # parameters are token address or token name
        if fromToken == "BNB":
            fromToken = "WBNB"
        if toToken == "BNB":
            toToken = "WBNB"
        tokenA = self.tokens[fromToken]
        tokenB = self.tokens[toToken]
        address0 = tokenA.getAddress()
        address1 = tokenB.getAddress()
        assert self.web3.isAddress(address0), "address0 in getAmountOut not an address"
        assert self.web3.isAddress(address1), "address1 in getAmountOut not an address"
        path0 = self.web3.toChecksumAddress(address0)
        path1 = self.web3.toChecksumAddress(address1)
        path = [path0, path1]
        amountInWei = tokenA.fromTokenToWei(amountIn)
        amountsOut = self.router.getAmountsOut(amountInWei, path)
        tokenBOutWei = amountsOut[1]
        return tokenB.fromWeiToToken(tokenBOutWei)

    def swapAtMarket(self,
                     amount,
                     fromToken,
                     toToken,
                     gas=300000,
                     gasPrice=None,
                     deadline=None,
                     slippage=None):
        if fromToken == "BNB":
            return self.swapAtMarketFromETHToTokens(amount, toToken, gas, gasPrice, deadline, slippage)
        if toToken == "BNB":
            return self.swapAtMarketFromTokensToETH(amount, fromToken, gas, gasPrice, deadline, slippage)
        return self.swapAtMarketFromTokensToTokens(amount, fromToken, toToken, gas, gasPrice, deadline, slippage)

    def swapAtMarketFromETHToTokens(self,
                                    amount,
                                    toToken,
                                    gas=300000,
                                    gasPrice=None,
                                    deadline=None,
                                    slippage=None):
        tokenB = self.tokens[toToken]
        amountIn = self.tokens["WBNB"].fromTokenToWei(amount)
        tokens_transferred = self.router.swapETHForTokensAtMarket(sender=self.wallet,
                                                                  amountIn=amountIn,
                                                                  toToken=tokenB,
                                                                  gas=gas,
                                                                  gasPrice=gasPrice,
                                                                  deadline=deadline,
                                                                  slippage=slippage)

        return tokenB.fromWeiToToken(tokens_transferred)

    def swapAtMarketFromTokensToETH(self,
                                    amount,
                                    fromToken,
                                    gas=300000,
                                    gasPrice=None,
                                    deadline=None,
                                    slippage=None):
        tokenA = self.tokens[fromToken]
        amountIn = tokenA.fromTokenToWei(amount)
        tokens_transferred = self.router.swapTokensForETHAtMarket(sender=self.wallet,
                                                                  amountIn=amountIn,
                                                                  fromToken=tokenA,
                                                                  gas=gas,
                                                                  gasPrice=gasPrice,
                                                                  deadline=deadline,
                                                                  slippage=slippage)

        return self.tokens["WBNB"].fromWeiToToken(tokens_transferred)

    def swapAtMarketFromTokensToTokens(self,
                                       amount,
                                       fromToken,
                                       toToken,
                                       gas=300000,
                                       gasPrice=None,
                                       deadline=None,
                                       slippage=None):
        tokenA = self.tokens[fromToken]
        tokenB = self.tokens[toToken]
        amountIn = tokenA.fromTokenToWei(amount)
        tokens_transferred = self.router.swapTokensAtMarket(sender=self.wallet,
                                                            amountIn=amountIn,
                                                            fromToken=tokenA,
                                                            toToken=tokenB,
                                                            gas=gas,
                                                            gasPrice=gasPrice,
                                                            deadline=deadline,
                                                            slippage=slippage)
        return tokenB.fromWeiToToken(tokens_transferred)

    def swapAtAmountOut(self,
                        amountIn,
                        fromToken,
                        toToken,
                        amountOut,
                        gas=300000,
                        gasPrice=None,
                        deadline=None,
                        slippage=None):
        if fromToken == "BNB":
            return self.swapAtAmountOutFromETHToTokens(amountIn, toToken, amountOut, gas, gasPrice, deadline, slippage)
        if toToken == "BNB":
            return self.swapAtAmountOutFromTokensToETH(amountIn, fromToken, amountOut, gas, gasPrice, deadline,
                                                       slippage)
        return self.swapAtAmountOutFromTokensToTokens(amountIn, fromToken, toToken, amountOut, gas, gasPrice, deadline,
                                                      slippage)

    def swapAtAmountOutFromETHToTokens(self,
                                       amountIn,
                                       toToken,
                                       amountOut,
                                       gas=300000,
                                       gasPrice=None,
                                       deadline=None,
                                       slippage=None):
        tokenB = self.tokens[toToken]
        path = [self.tokens["WBNB"].address, tokenB.address]
        amountInWei = self.tokens["WBNB"].fromTokenToWei(amountIn)
        amountOutWei = tokenB.fromTokenToWei(amountOut)
        amountOutMin = self.router.getAmountOutMin(amountOutWei, slippage)
        tokens_transferred = self.router.swapExactETHForTokens(sender=self.wallet,
                                                               amountIn=amountInWei,
                                                               amountOutMin=amountOutMin,
                                                               path=path,
                                                               gas=gas,
                                                               gasPrice=gasPrice,
                                                               deadline=deadline)

        return tokenB.fromWeiToToken(tokens_transferred)

    def swapAtAmountOutFromTokensToETH(self,
                                       amountIn,
                                       fromToken,
                                       amountOut,
                                       gas=300000,
                                       gasPrice=None,
                                       deadline=None,
                                       slippage=None):
        tokenA = self.tokens[fromToken]
        path = [tokenA.address, self.tokens["WBNB"].address]
        amountInWei = tokenA.fromTokenToWei(amountIn)
        amountOutWei = self.tokens["WBNB"].fromTokenToWei(amountOut)
        amountOutMin = self.router.getAmountOutMin(amountOutWei, slippage)
        tokens_transferred = self.router.swapExactTokensForETH(sender=self.wallet,
                                                               amountIn=amountInWei,
                                                               amountOutMin=amountOutMin,
                                                               path=path,
                                                               gas=gas,
                                                               gasPrice=gasPrice,
                                                               deadline=deadline)

        return self.tokens["WBNB"].fromWeiToToken(tokens_transferred)

    def swapAtAmountOutFromTokensToTokens(self,
                                          amountIn,
                                          fromToken,
                                          toToken,
                                          amountOut,
                                          gas=300000,
                                          gasPrice=None,
                                          deadline=None,
                                          slippage=None):
        tokenA = self.tokens[fromToken]
        tokenB = self.tokens[toToken]
        path = [tokenA.address, tokenB.address]
        amountInWei = tokenA.fromTokenToWei(amountIn)
        amountOutWei = tokenB.fromTokenToWei(amountOut)
        amountOutMin = self.router.getAmountOutMin(amountOutWei, slippage)
        tokens_transferred = self.router.swapExactTokensForTokens(sender=self.wallet,
                                                                  amountIn=amountInWei,
                                                                  amountOutMin=amountOutMin,
                                                                  path=path,
                                                                  gas=gas,
                                                                  gasPrice=gasPrice,
                                                                  deadline=deadline)
        return tokenB.fromWeiToToken(tokens_transferred)

    class Router:

        def __init__(self, address, abi, factory, web3, wallet, private_key):

            self.web3 = web3
            self.address = address
            self.abi = abi
            self.json_abi = json.loads(abi)
            self.contract = web3.eth.contract(address=address, abi=self.json_abi)
            self.factory = factory
            self.deadline = 60
            self.slippage = 0.95
            self.wallet = wallet
            self.private_key = private_key

        '''
        START LIQUIDITY FUNCTIONS
        '''

        def addLiquidity(self,
                         sender,
                         tokenA,
                         tokenB,
                         amountADesired,
                         amountBDesired,
                         amountAMin,
                         amountBMin,
                         to=None,
                         gas=300000,
                         gasPrice=None,
                         deadline=None,
                         private_key=None):
            # assumes correct ratio of tokenA and tokenB have been calculated
            # assumes router has been approved for spending amountA of tokenA and amountB of tokenB

            # set 'to' address to 'sender' if argument not provided
            if not to:
                to = sender

            # calculate deadline in unix time
            unix_deadline = self.getUnixDeadline(deadline)

            # estimate gasPrice if argument not provided
            if not gasPrice:
                gasPrice = self.web3.eth.gas_price

            # get wallet's latest nonce - used in txn for preventing double-spend
            nonce = self.web3.eth.get_transaction_count(sender)

            # set private_key for txns
            private_key = self.usePrivateKey(private_key)

            # build addLiquidity txn
            addLiquidity_txn = self.contract.functions.addLiquidity(
                tokenA,
                tokenB,
                amountADesired,
                amountBDesired,
                amountAMin,
                amountBMin,
                to,
                unix_deadline
            ).buildTransaction({
                'gas': gas,
                'gasPrice': gasPrice,
                'nonce': nonce
            })

            # sign txn
            signed_txn = self.web3.eth.account.sign_transaction(addLiquidity_txn,
                                                                private_key=private_key)
            # send txn
            txn_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # wait for txn receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(txn_hash)

            # return txn hash
            return txn_hash

            # return txn receipt
            #return receipt

            # return value of LP tokens transferred from transaction, returns '0' if failed
            #return self.getValueFromReceipt(receipt, pair_address, sender)

        def quote(self, amountA, reserveA, reserveB):
            return self.contract.functions.quote(amountA, reserveA, reserveB).call()

        '''
        START SWAPPING FUNCTIONS
        '''

        def setDeadline(self, deadline):
            # sets the default deadline for txns in seconds
            self.deadline = deadline

        def getUnixDeadline(self, deadline):
            # calculates and returns deadline in unix time
            current_unix_time = int(time.time())
            if deadline:
                unix_deadline = current_unix_time + deadline
            else:
                unix_deadline = current_unix_time + self.deadline
            return unix_deadline

        def setSlippage(self, slippage):
            # sets the default slippage for swaps
            # this should be a fraction of 1 in decimal format
            # for example if the least you want to receive is 95% of the calculated amountOut,
            # then you will set slippage to 0.95
            self.slippage = slippage

        def getAmountsOut(self, amountIn, path):
            # returns a list of the amountsOut for the given path
            for i in range(len(path)):
                assert self.web3.isAddress(path[i]), f"address{i} in getAmountsOut not an address"
            return self.contract.functions.getAmountsOut(amountIn, [path[0], path[1]]).call()

        def getAmountOutMin(self, amountOut, slippage):
            # returns the amountOutMin, based on the amountOut * slippage
            if slippage:
                amountOutMin = int(amountOut * slippage)
            else:
                amountOutMin = int(amountOut * self.slippage)
            return amountOutMin

        def usePrivateKey(self, private_key):
            if private_key:
                return private_key
            else:
                return self.private_key

        def swapTokensAtMarket(self,
                               sender,
                               amountIn,
                               fromToken,
                               toToken,
                               gas=300000,
                               gasPrice=None,
                               deadline=None,
                               slippage=None,
                               private_key=None):

            # determine amountOutMin
            path = [fromToken.address, toToken.address]
            amountsOut = self.getAmountsOut(amountIn=amountIn,
                                                      path=path)
            toToken_amountOut = amountsOut[1]
            amountOutMin = self.getAmountOutMin(toToken_amountOut, slippage)

            # check balance
            balance = fromToken.getBalanceOf(sender)
            if balance < amountIn:
                return -1

            # set private_key for txns
            private_key = self.usePrivateKey(private_key)

            # approve spend
            approve_txn_hash = fromToken.approve(sender=sender,
                                                spender=self.address,
                                                amount=amountIn,
                                                private_key=private_key)
            # swap
            swap = self.swapExactTokensForTokens(sender=sender,
                                                 amountIn=amountIn,
                                                 amountOutMin=amountOutMin,
                                                 path=path,
                                                 to=sender,
                                                 gas=gas,
                                                 gasPrice=gasPrice,
                                                 deadline=deadline,
                                                 private_key=private_key)
            return swap

        def swapExactTokensForTokens(self,
                                     sender,
                                     amountIn,
                                     amountOutMin,
                                     path,
                                     to=None,
                                     gas=300000,
                                     gasPrice=None,
                                     deadline=None,
                                     private_key=None):

            # set 'to' address to 'sender' if argument not provided
            if not to:
                to = sender

            # calculate deadline in unix time
            unix_deadline = self.getUnixDeadline(deadline)

            # estimate gasPrice if argument not provided
            if not gasPrice:
                gasPrice = self.web3.eth.gas_price

            # get wallet's latest nonce - used in txn for preventing double-spend
            nonce = self.web3.eth.get_transaction_count(sender)

            # set private_key for txns
            private_key = self.usePrivateKey(private_key)

            # build swap txn
            swap_txn = self.contract.functions.swapExactTokensForTokens(
                amountIn,
                amountOutMin,
                path,
                to,
                unix_deadline
            ).buildTransaction({
                'gas': gas,
                'gasPrice': gasPrice,
                'nonce': nonce
            })

            # sign swap txn
            signed_txn = self.web3.eth.account.sign_transaction( swap_txn,
                                                                 private_key=private_key)
            # send swap txn
            txn_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # wait for txn receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(txn_hash)

            # return value of tokens transferred from transaction, returns '0' if failed
            return self.getValueFromReceipt(receipt, path[-1], sender)

        def swapTokensForETHAtMarket(self,
                                     sender,
                                     amountIn,
                                     fromToken,
                                     gas=300000,
                                     gasPrice=None,
                                     deadline=None,
                                     slippage=None,
                                     private_key=None):

            # determine amountOutMin
            path = [fromToken.address, pancake_contracts.wbnb_address]
            amountsOut = self.getAmountsOut(amountIn=amountIn,
                                            path=path)
            toToken_amountOut = amountsOut[1]
            amountOutMin = self.getAmountOutMin(toToken_amountOut, slippage)

            # check balance
            balance = fromToken.getBalanceOf(sender)
            if balance < amountIn:
                return -1

            # set private_key for txns
            private_key = self.usePrivateKey(private_key)

            # approve spend
            approve_txn_hash = fromToken.approve(sender=sender,
                                                spender=self.address,
                                                amount=amountIn,
                                                private_key=private_key)
            # swap
            swap = self.swapExactTokensForETH(sender=sender,
                                              amountIn=amountIn,
                                              amountOutMin=amountOutMin,
                                              path=path,
                                              to=sender,
                                              gas=gas,
                                              gasPrice=gasPrice,
                                              deadline=deadline,
                                              private_key=private_key)
            return swap

        def swapExactTokensForETH(self,
                                  sender,
                                  amountIn,
                                  amountOutMin,
                                  path,
                                  to=None,
                                  gas=300000,
                                  gasPrice=None,
                                  deadline=None,
                                  private_key=None):

            # set 'to' address to 'sender' if argument not provided
            if not to:
                to = sender

            # calculate deadline in unix time
            unix_deadline = self.getUnixDeadline(deadline)

            # estimate gasPrice if argument not provided
            if not gasPrice:
                gasPrice = self.web3.eth.gas_price

            # get wallet's latest nonce - used in txn for preventing double-spend
            nonce = self.web3.eth.get_transaction_count(sender)

            # set private_key for txns
            private_key = self.usePrivateKey(private_key)

            # build swap txn
            swap_txn = self.contract.functions.swapExactTokensForETH(
                amountIn,
                amountOutMin,
                path,
                to,
                unix_deadline
            ).buildTransaction({
                'gas': gas,
                'gasPrice': gasPrice,
                'nonce': nonce
            })

            # sign swap txn
            signed_txn = self.web3.eth.account.sign_transaction(swap_txn,
                                                                private_key=private_key)
            # send swap txn
            txn_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # wait for txn receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(txn_hash)

            # return value of tokens transferred from transaction, returns '0' if failed
            return self.getValueFromReceipt(receipt, path[-1], sender)

        def swapETHForTokensAtMarket(self,
                                     sender,
                                     amountIn,
                                     toToken,
                                     gas=300000,
                                     gasPrice=None,
                                     deadline=None,
                                     slippage=None,
                                     private_key=None):

            # determine amountOutMin
            path = [pancake_contracts.wbnb_address, toToken.address]
            amountsOut = self.getAmountsOut(amountIn=amountIn,
                                            path=path)
            toToken_amountOut = amountsOut[1]
            amountOutMin = self.getAmountOutMin(toToken_amountOut, slippage)

            # check balance
            balance = self.web3.eth.get_balance(sender)
            if balance < amountIn:
                return -1

            # set private_key for txns
            private_key = self.usePrivateKey(private_key)

            '''
            # approve spend - not required for spending BNB/ETH - value gets sent to router with txn
            approve_txn_hash = fromToken.approve(sender=sender,
                                                spender=self.address,
                                                amount=amountIn,
                                                private_key=private_key)
            '''
            # swap
            swap = self.swapExactETHForTokens(sender=sender,
                                              amountIn=amountIn,
                                              amountOutMin=amountOutMin,
                                              path=path,
                                              to=sender,
                                              gas=gas,
                                              gasPrice=gasPrice,
                                              deadline=deadline,
                                              private_key=private_key)
            return swap

        def swapExactETHForTokens(self,
                                  sender,
                                  amountIn,
                                  amountOutMin,
                                  path,
                                  to=None,
                                  gas=300000,
                                  gasPrice=None,
                                  deadline=None,
                                  private_key=None):

            # set 'to' address to 'sender' if argument not provided
            if not to:
                to = sender

            # calculate deadline in unix time
            unix_deadline = self.getUnixDeadline(deadline)

            # estimate gasPrice if argument not provided
            if not gasPrice:
                gasPrice = self.web3.eth.gas_price

            # get wallet's latest nonce - used in txn for preventing double-spend
            nonce = self.web3.eth.get_transaction_count(sender)

            # set private_key for txns
            private_key = self.usePrivateKey(private_key)

            # build swap txn
            swap_txn = self.contract.functions.swapExactETHForTokens(
                amountOutMin,
                path,
                to,
                unix_deadline
            ).buildTransaction({
                'gas': gas,
                'gasPrice': gasPrice,
                'nonce': nonce,
                'value': amountIn
            })

            # sign swap txn
            signed_txn = self.web3.eth.account.sign_transaction(swap_txn,
                                                                private_key=private_key)
            # send swap txn
            txn_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # wait for txn receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(txn_hash)

            # return value of tokens transferred from transaction, returns '0' if failed
            return self.getValueFromReceipt(receipt, path[-1], sender)

        def getValueFromReceipt(self, txn_receipt, toTokenAddress, sender):
            logs = txn_receipt['logs']
            value = 0
            for log in logs:
                if log['address'] == toTokenAddress:
                    value = self.web3.toInt(hexstr=log['data'])
            return value

        def getTransactionStatus(self, txn_receipt):
            status = txn_receipt['logsBloom'][1]
            return status

    class Token:

        def __init__(self, name, web3, address, abi):
            self.name = name
            self.web3 = web3
            self.address = address
            self.abi = abi
            #self.json_abi = json.loads(abi)
            self.json_abi = abi # assumes argument is already a loaded json
            self.contract = web3.eth.contract(address=address, abi=self.json_abi)
            self.decimals = None  # this is assigned upon first call to getDecimals

        # return the name of the token
        def getName(self):
            return self.name

        # return the address of the token
        def getAddress(self):
            return str(self.address)

        # return the decimals of the token
        def getDecimals(self):
            if not self.decimals:
                self.decimals = self.contract.functions.decimals().call()
            return self.decimals

        # return the token value from the wei value
        # wei here is referring to the smallest indivisible unit of the token
        def fromWeiToToken(self, wei_value):
            return float(wei_value) / (10 ** self.getDecimals())

        # return the wei value from the wei value
        # wei here is referring to the smallest indivisible unit of the token
        def fromTokenToWei(self, token_value):
            return int(token_value * (10 ** self.getDecimals()))

        # return the allowance of a spender on behalf of an owner
        def getAllowance(self, owner, spender):
            return self.contract.functions.allowance(owner,
                                                     spender).call()

        # return the balance of a given address, in the smallest unit
        def getBalanceOf(self, address):
            return self.contract.functions.balanceOf(address).call()

        # return the balance of a given address, in the token value
        def getBalance(self, address):
            return self.fromWeiToToken(self.getBalanceOf(address))

        # approve a spender on behalf of token owner (sender)
        def approve(self, sender, spender, amount, private_key, gas=100000, gasPrice=None):
            # estimate gasPrice if argument not provided
            if not gasPrice:
                gasPrice = self.web3.eth.gas_price

            nonce = self.web3.eth.get_transaction_count(sender)
            approval_txn = self.contract.functions.approve(
                spender,
                amount
            ).buildTransaction({
                'gas': gas,
                'gasPrice': gasPrice,
                'nonce': nonce
            })

            signed_txn = self.web3.eth.account.sign_transaction( approval_txn,
                                                                 private_key=private_key)
            txn_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(txn_hash)
            return txn_hash

    class PancakePair(Token):


        def __init__(self, name, web3, address, abi):
            super().__init__(name, web3, address, abi)

        # return the current reserve of reserve<n> ...n must be 0 or 1
        def getReserve(self, n):
            reserves = self.contract.functions.getReserves().call()
            return reserves[n]


        # return the current reserve ratio (price) for the pancake-pair
        def getReserveRatio(self):
            reserves = self.contract.functions.getReserves().call()
            return float(reserves[1]) / reserves[0]
            
        # get last cumulative price0
        def getPrice0CumulativeLast(self):
            return self.contract.functions.price0CumulativeLast().call()

            


