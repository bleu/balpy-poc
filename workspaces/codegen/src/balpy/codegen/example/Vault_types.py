from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Tuple

from balpy.chains import Chain
from balpy.contracts.base_contract import BalancerContractFactory, BaseContract
from hexbytes import HexBytes

from .Vault_TODO import *


@dataclass
class FundManagement:
    sender: str
    fromInternalBalance: bool
    recipient: str
    toInternalBalance: bool


@dataclass
class ExitPoolRequest:
    assets: List[str]
    minAmountsOut: List[int]
    userData: HexBytes
    toInternalBalance: bool


@dataclass
class JoinPoolRequest:
    assets: List[str]
    maxAmountsIn: List[int]
    userData: HexBytes
    fromInternalBalance: bool


@dataclass
class SingleSwap:
    poolId: HexBytes
    kind: SwapKind
    assetIn: str
    assetOut: str
    amount: int
    userData: HexBytes


class BaseMixin(ABC):
    @abstractmethod
    def _method_from_base(self, method_name, *args, **kwargs):
        raise NotImplementedError


class VaultMixin(BaseMixin):
    def WETH(
        self,
    ) -> str:
        return self._method_from_base(
            "WETH",
        )

    def batchSwap(
        self,
        kind: SwapKind,
        swaps: List[Any],
        assets: List[str],
        funds: FundManagement,
        limits: List[int],
        deadline: int,
    ) -> List[int]:
        return self._method_from_base(
            "batchSwap",
            kind.value,
            swaps,
            assets,
            (
                funds.sender,
                funds.fromInternalBalance,
                funds.recipient,
                funds.toInternalBalance,
            ),
            limits,
            deadline,
        )

    def deregisterTokens(self, pool_id: HexBytes, tokens: List[str]) -> None:
        return self._method_from_base("deregisterTokens", pool_id, tokens)

    def exitPool(
        self, pool_id: HexBytes, sender: str, recipient: str, request: ExitPoolRequest
    ) -> None:
        return self._method_from_base(
            "exitPool",
            pool_id,
            sender,
            recipient,
            (
                request.assets,
                request.minAmountsOut,
                request.userData,
                request.toInternalBalance,
            ),
        )

    def flashLoan(
        self, recipient: str, tokens: List[str], amounts: List[int], user_data: HexBytes
    ) -> None:
        return self._method_from_base(
            "flashLoan", recipient, tokens, amounts, user_data
        )

    def getActionId(self, selector: HexBytes) -> HexBytes:
        return self._method_from_base("getActionId", selector)

    def getAuthorizer(
        self,
    ) -> str:
        return self._method_from_base(
            "getAuthorizer",
        )

    def getDomainSeparator(
        self,
    ) -> HexBytes:
        return self._method_from_base(
            "getDomainSeparator",
        )

    def getInternalBalance(self, user: str, tokens: List[str]) -> List[int]:
        return self._method_from_base("getInternalBalance", user, tokens)

    def getNextNonce(self, user: str) -> int:
        return self._method_from_base("getNextNonce", user)

    def getPausedState(
        self,
    ) -> Tuple[bool, int, int]:
        return self._method_from_base(
            "getPausedState",
        )

    def getPool(self, pool_id: HexBytes) -> Tuple[str, PoolSpecialization]:
        return self._method_from_base("getPool", pool_id)

    def getPoolTokenInfo(
        self, pool_id: HexBytes, token: str
    ) -> Tuple[int, int, int, str]:
        return self._method_from_base("getPoolTokenInfo", pool_id, token)

    def getPoolTokens(self, pool_id: HexBytes) -> Tuple[List[str], List[int], int]:
        return self._method_from_base("getPoolTokens", pool_id)

    def getProtocolFeesCollector(
        self,
    ) -> str:
        return self._method_from_base(
            "getProtocolFeesCollector",
        )

    def hasApprovedRelayer(self, user: str, relayer: str) -> bool:
        return self._method_from_base("hasApprovedRelayer", user, relayer)

    def joinPool(
        self, pool_id: HexBytes, sender: str, recipient: str, request: JoinPoolRequest
    ) -> None:
        return self._method_from_base(
            "joinPool",
            pool_id,
            sender,
            recipient,
            (
                request.assets,
                request.maxAmountsIn,
                request.userData,
                request.fromInternalBalance,
            ),
        )

    def managePoolBalance(self, ops: List[Any]) -> None:
        return self._method_from_base("managePoolBalance", ops)

    def manageUserBalance(self, ops: List[Any]) -> None:
        return self._method_from_base("manageUserBalance", ops)

    def queryBatchSwap(
        self, kind: SwapKind, swaps: List[Any], assets: List[str], funds: FundManagement
    ) -> List[int]:
        return self._method_from_base(
            "queryBatchSwap",
            kind.value,
            swaps,
            assets,
            (
                funds.sender,
                funds.fromInternalBalance,
                funds.recipient,
                funds.toInternalBalance,
            ),
        )

    def registerPool(self, specialization: PoolSpecialization) -> HexBytes:
        return self._method_from_base("registerPool", specialization.value)

    def registerTokens(
        self, pool_id: HexBytes, tokens: List[str], asset_managers: List[str]
    ) -> None:
        return self._method_from_base("registerTokens", pool_id, tokens, asset_managers)

    def setAuthorizer(self, new_authorizer: str) -> None:
        return self._method_from_base("setAuthorizer", new_authorizer)

    def setPaused(self, paused: bool) -> None:
        return self._method_from_base("setPaused", paused)

    def setRelayerApproval(self, sender: str, relayer: str, approved: bool) -> None:
        return self._method_from_base("setRelayerApproval", sender, relayer, approved)

    def swap(
        self, single_swap: SingleSwap, funds: FundManagement, limit: int, deadline: int
    ) -> int:
        return self._method_from_base(
            "swap",
            (
                single_swap.poolId,
                single_swap.kind,
                single_swap.assetIn,
                single_swap.assetOut,
                single_swap.amount,
                single_swap.userData,
            ),
            (
                funds.sender,
                funds.fromInternalBalance,
                funds.recipient,
                funds.toInternalBalance,
            ),
            limit,
            deadline,
        )


class Vault(BaseContract, VaultMixin):
    def __init__(self, chain: Chain):
        contract_instance = BalancerContractFactory.create(chain, "Vault")
        super().__init__(contract_instance.contract_address, chain)

    def _method_from_base(self, method_name, *args, **kwargs):
        return BaseContract.__getattr__(self, method_name)(*args, **kwargs)
