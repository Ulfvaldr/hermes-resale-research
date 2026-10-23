"""Fail-closed eBay evidence adapters.

The Browse API is an active-listing API.  This module deliberately never maps an
active asking price to sold-price evidence.
"""
from __future__ import annotations

import base64
import json
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .evidence import normalize_resale_evidence
from .models import ResaleEvidence


class EbayEvidenceAdapter(Protocol):
    def fetch_active_listings(self, query: str) -> ResaleEvidence: ...
    def fetch_sold_evidence(self, query: str) -> ResaleEvidence: ...


def _unavailable(reason: str, query: str | None = None) -> ResaleEvidence:
    provenance = {"adapter": "ebay", "reason": reason}
    if query is not None:
        provenance["query"] = query
    return ResaleEvidence(evidence_type="UNAVAILABLE", provenance=provenance)


@dataclass(frozen=True)
class UnavailableEbayAdapter:
    reason: str = "LIVE_EBAY_ACCESS_NOT_CONFIGURED"

    def fetch_active_listings(self, query: str) -> ResaleEvidence:
        return _unavailable(self.reason, query)

    def fetch_sold_evidence(self, query: str) -> ResaleEvidence:
        return _unavailable(self.reason, query)


@dataclass(frozen=True)
class FakeEbayEvidenceAdapter:
    """Deterministic adapter for tests; it performs no network access."""
    active: ResaleEvidence | Mapping[str, Any] | None = None
    sold: ResaleEvidence | Mapping[str, Any] | None = None
    manual_sold: ResaleEvidence | Mapping[str, Any] | None = None

    def fetch_active_listings(self, query: str) -> ResaleEvidence:
        if self.active is None:
            return _unavailable("FAKE_ACTIVE_EVIDENCE_NOT_CONFIGURED", query)
        data = dict(self.active) if isinstance(self.active, Mapping) else self.active.__dict__
        data["provenance"] = {**dict(data.get("provenance", {})), "adapter": "fake", "query": query,
                               "evidence_scope": "ACTIVE_ASKING"}
        return normalize_resale_evidence(data)

    def fetch_sold_evidence(self, query: str) -> ResaleEvidence:
        value = self.manual_sold if self.manual_sold is not None else self.sold
        if value is None:
            return _unavailable("SOLD_HISTORY_NOT_AVAILABLE", query)
        data = dict(value) if isinstance(value, Mapping) else value.__dict__
        provenance = {**dict(data.get("provenance", {})), "adapter": "fake", "query": query}
        if provenance.get("source") is None and provenance.get("source_url") is None:
            return _unavailable("MANUAL_SOLD_PROVENANCE_REQUIRED", query)
        data["provenance"] = provenance
        return normalize_resale_evidence(data)


@dataclass
class LiveEbayBrowseAdapter:
    """eBay Browse API ACTIVE-listing adapter using application credentials."""
    client_id: str | None = None
    client_secret: str | None = None
    api_env: str | None = None
    marketplace_id: str | None = None
    timeout: float = 10.0
    opener: Callable[..., Any] = urlopen
    manual_sold_source: ResaleEvidence | Mapping[str, Any] | None = None
    _token: str | None = field(default=None, init=False, repr=False)
    _token_expires_at: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        env = os.environ
        self.client_id = self.client_id if self.client_id is not None else env.get("EBAY_CLIENT_ID")
        self.client_secret = self.client_secret if self.client_secret is not None else env.get("EBAY_CLIENT_SECRET")
        self.api_env = (self.api_env or env.get("EBAY_API_ENV") or "production").lower()
        self.marketplace_id = self.marketplace_id or env.get("EBAY_MARKETPLACE_ID") or "EBAY_US"
        if self.api_env not in {"production", "sandbox"}:
            self.api_env = "invalid"

    def _base(self) -> str:
        host = "api.sandbox.ebay.com" if self.api_env == "sandbox" else "api.ebay.com"
        return f"https://{host}"

    def _request_json(self, request: Request) -> Mapping[str, Any]:
        with self.opener(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_token(self, force: bool = False) -> str:
        import time
        if not force and self._token and time.time() < self._token_expires_at - 60:
            return self._token
        if not self.client_id or not self.client_secret or self.api_env == "invalid":
            raise RuntimeError("MISSING_EBAY_CREDENTIALS")
        raw = f"{self.client_id}:{self.client_secret}".encode()
        request = Request(self._base() + "/identity/v1/oauth2/token", data=b"grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope", method="POST", headers={
            "Authorization": "Basic " + base64.b64encode(raw).decode("ascii"),
            "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
        payload = self._request_json(request)
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("EBAY_AUTH_FAILED")
        self._token = str(token)
        self._token_expires_at = time.time() + float(payload.get("expires_in", 7200))
        return self._token

    def fetch_active_listings(self, query: str) -> ResaleEvidence:
        if not isinstance(query, str) or not query.strip():
            return _unavailable("QUERY_REQUIRED", query)
        try:
            token = self._get_token()
            params = urlencode({"q": query, "limit": "200", "filter": "buyingOptions:{FIXED_PRICE|AUCTION|CLASSIFIED_AD}"})
            request = Request(self._base() + "/buy/browse/v1/item_summary/search?" + params, headers={
                "Authorization": "Bearer " + token, "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
                "Accept": "application/json"})
            payload = self._request_json(request)
            items = payload.get("itemSummaries") or []
            prices: list[Decimal] = []
            sellers: set[str] = set()
            estimated = 0
            for item in items:
                price = (item.get("price") or {}).get("value")
                try:
                    if price is not None: prices.append(Decimal(str(price)))
                except (InvalidOperation, ValueError):
                    pass
                seller = (item.get("seller") or {}).get("username")
                if seller: sellers.add(str(seller))
                try: estimated += int(item.get("estimatedSoldQuantity") or 0)
                except (TypeError, ValueError): pass
            provenance = {"adapter": "ebay_browse", "query": query, "evidence_scope": "ACTIVE_ASKING",
                          "api_environment": self.api_env, "marketplace_id": self.marketplace_id,
                          "timestamp_quality": "PROVIDER_ASSERTED"}
            data: dict[str, Any] = {"evidence_type": "OBSERVED", "active_listing_count": int(payload.get("total", len(items))),
                "seller_count": len(sellers) or None, "evidence_observed_at": datetime.now(timezone.utc),
                "provenance": provenance}
            if prices:
                data["asking_price"] = statistics.median(prices)
                data["asking_currency"] = ((items[0].get("price") or {}).get("currency"))
            if estimated: data["estimated_sold_quantity"] = estimated
            return normalize_resale_evidence(data)
        except Exception as exc:
            # Do not expose exception text: it can contain URLs, headers, or secrets.
            reason = "EBAY_API_UNAVAILABLE"
            if isinstance(exc, HTTPError):
                reason = "EBAY_RATE_LIMITED" if exc.code == 429 else ("EBAY_AUTH_FAILED" if exc.code in (400, 401, 403) else "EBAY_API_UNAVAILABLE")
            return _unavailable(reason, query)

    def fetch_sold_evidence(self, query: str) -> ResaleEvidence:
        if self.manual_sold_source is None:
            return _unavailable("SOLD_HISTORY_NOT_AVAILABLE", query)
        data = dict(self.manual_sold_source) if isinstance(self.manual_sold_source, Mapping) else self.manual_sold_source.__dict__
        provenance = {**dict(data.get("provenance", {})), "query": query}
        if not (provenance.get("source") or provenance.get("source_url") or provenance.get("provider")):
            return _unavailable("MANUAL_SOLD_PROVENANCE_REQUIRED", query)
        data["provenance"] = provenance
        return normalize_resale_evidence(data)