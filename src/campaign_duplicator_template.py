# -*- coding: utf-8 -*-
"""Template sanitizado de clonagem automatizada de campanhas via Meta Graph API v20.0."""

import json
import os
import datetime
import urllib.parse
import urllib.request


class MetaAdsCloner:
    def __init__(self, access_token: str, api_version: str = "v20.0"):
        self.token = access_token
        self.base_url = f"https://graph.facebook.com/{api_version}"

    def _request(self, endpoint: str, data: dict | None = None) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        if data is not None:
            payload = dict(data)
            payload["access_token"] = self.token
            encoded = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(url, data=encoded, method="POST")
        else:
            sep = "&" if "?" in url else "?"
            req = urllib.request.Request(f"{url}{sep}access_token={self.token}")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def build_clone_plan(self, source_camp_id: str, dest_account_id: str, lifetime_budget_cents: int = 10000) -> dict:
        """Constroi payload estruturado de duplicacao (execucao segura via dry-run ou live)."""
        now = datetime.datetime.now()
        return {
            "source_campaign_id": source_camp_id,
            "destination_account_id": dest_account_id,
            "status_inicial": "PAUSED",
            "lifetime_budget_cents": lifetime_budget_cents,
            "start_time": (now + datetime.timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S-0300"),
            "end_time": (now + datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S-0300"),
        }


if __name__ == "__main__":
    token = os.getenv("META_ACCESS_TOKEN", "YOUR_META_GRAPH_API_ACCESS_TOKEN")
    dest = os.getenv("META_AD_ACCOUNT_ID", "act_YOUR_AD_ACCOUNT_ID")
    cloner = MetaAdsCloner(token)
    plan = cloner.build_clone_plan(source_camp_id="120200000000000001", dest_account_id=dest)
    print("Plano de clonagem validado (Dry-Run):", json.dumps(plan, indent=2, ensure_ascii=False))
