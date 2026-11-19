# -*- coding: utf-8 -*-
"""Meta Ads BI Extractor & Funnel Analyzer (Graph API v20.0 + Modo Demo Sintetico)."""

import argparse
import json
import os
import urllib.parse
import urllib.request
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "sample_campaigns_insights.json")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


def fetch_live_insights(token: str, ad_account_id: str, api_version: str = "v20.0") -> dict:
    fields = "campaign_name,objective,impressions,reach,clicks,spend,actions,action_values"
    params = urllib.parse.urlencode({
        "fields": fields,
        "date_preset": "last_14d",
        "access_token": token,
    })
    url = f"https://graph.facebook.com/{api_version}/{ad_account_id}/insights?level=campaign&{params}"
    with urllib.request.urlopen(url, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def compute_metrics(campaigns: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(campaigns)
    df["CPM"] = (df["spend"] / df["impressions"]) * 1000
    df["CTR_pct"] = (df["clicks"] / df["impressions"]) * 100
    df["CPC"] = df["spend"] / df["clicks"].replace(0, 1)
    df["CPA"] = df["spend"] / df["purchases"].replace(0, 1)
    df["ROAS"] = df["revenue"] / df["spend"].replace(0, 1)
    df["Custo_Conversa"] = df.apply(
        lambda r: round(r["spend"] / r["conversations_started"], 2) if r["conversations_started"] > 0 else 0.0,
        axis=1,
    )
    return df


def format_executive_report(df: pd.DataFrame, account_label: str) -> str:
    tot_spend = df["spend"].sum()
    tot_rev = df["revenue"].sum()
    tot_purchases = int(df["purchases"].sum())
    tot_clicks = int(df["clicks"].sum())
    tot_imp = int(df["impressions"].sum())
    lines = [
        f"*RELATORIO SEMANAL DE PERFORMANCE — META ADS*",
        f"*Conta:* {account_label}",
        "",
        "*1. RESUMO CONSOLIDADO*",
        f"- Investimento Total: R$ {tot_spend:,.2f}",
        f"- Faturamento Atribuido: R$ {tot_rev:,.2f} (ROAS Global: {tot_rev / tot_spend:.2f}x)",
        f"- Impressoes / Cliques: {tot_imp:,} / {tot_clicks:,} (CTR: {tot_clicks / tot_imp * 100:.2f}%)",
        f"- Compras Finalizadas / CPA Medio: {tot_purchases} / R$ {tot_spend / tot_purchases:,.2f}",
        "",
        "*2. DETALHAMENTO POR CAMPANHA*",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"- {row['campaign_name']}: Gasto R$ {row['spend']:.2f} | Receita R$ {row['revenue']:.2f} | ROAS {row['ROAS']:.2f}x | CTR {row['CTR_pct']:.2f}%"
        )
    return "\n".join(lines)


def dispatch_webhook(report_text: str, webhook_url: str | None) -> None:
    if not webhook_url or "example.com" in webhook_url:
        print("[Dry-Run] WEBHOOK_URL_WHATSAPP nao configurada (modo demonstracao ativo).")
        return
    payload = json.dumps({"relatorio": report_text}).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        print("Webhook enviado:", resp.status)


def generate_chart(df: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    labels = [c.split("—")[0].strip() for c in df["campaign_name"]]
    x = range(len(labels))
    w = 0.35
    axes[0].bar([i - w/2 for i in x], df["spend"], w, label="Investimento (R$)", color="#64748b")
    axes[0].bar([i + w/2 for i in x], df["revenue"], w, label="Receita (R$)", color="#2563eb")
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels(labels, rotation=10, fontsize=8.5)
    axes[0].set_title("Investimento vs. Faturamento por Campanha", fontweight="bold")
    axes[0].legend()

    colors = ["#10b981" if r >= 5 else "#3b82f6" for r in df["ROAS"]]
    axes[1].bar(labels, df["ROAS"], color=colors)
    axes[1].axhline(3.0, color="#dc2626", linestyle="--", label="ROAS Alvo (3,0x)")
    axes[1].set_xticklabels(labels, rotation=10, fontsize=8.5)
    axes[1].set_ylabel("ROAS (x)")
    axes[1].set_title("Retorno sobre Investimento em Mídia (ROAS)", fontweight="bold")
    axes[1].legend()
    plt.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "meta_ads_performance_funil.png"), dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Busca dados reais usando META_ACCESS_TOKEN do ambiente.")
    args = parser.parse_args()

    token = os.getenv("META_ACCESS_TOKEN", "")
    acc_id = os.getenv("META_AD_ACCOUNT_ID", "act_YOUR_AD_ACCOUNT_ID")

    if args.live and token and not token.startswith("YOUR_"):
        raw = fetch_live_insights(token, acc_id)
        campaigns = raw.get("data", [])
        label = acc_id
    else:
        payload = json.load(open(DATA_PATH, "r", encoding="utf-8"))
        campaigns = payload["campaigns"]
        label = payload["account_name"]

    df = compute_metrics(campaigns)
    df.to_csv(os.path.join(OUT_DIR, "metricas_consolidadas.csv"), index=False, encoding="utf-8")
    report = format_executive_report(df, label)
    with open(os.path.join(OUT_DIR, "relatorio_semanal.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    generate_chart(df)
    dispatch_webhook(report, os.getenv("WEBHOOK_URL_WHATSAPP"))
    print(report)


if __name__ == "__main__":
    main()
