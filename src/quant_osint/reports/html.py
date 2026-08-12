"""Self-contained HTML reports for saved research runs."""

# ruff: noqa: E501

from __future__ import annotations

import json
from html import escape

import pandas as pd


def _line_points(frame: pd.DataFrame, column: str) -> list[list[object]]:
    if frame.empty:
        return []
    sample = frame.iloc[:: max(1, len(frame) // 750)]
    return [
        [pd.Timestamp(row["date"]).strftime("%Y-%m-%d"), round(float(row[column]), 6)]
        for _, row in sample.iterrows()
    ]


def _histogram(values: pd.Series, bins: int = 30) -> list[dict[str, float | int]]:
    if values.empty:
        return []
    counts, edges = pd.cut(values, bins=bins, include_lowest=True, retbins=True)
    frequencies = counts.value_counts(sort=False)
    return [
        {
            "start": round(float(edges[index]), 6),
            "end": round(float(edges[index + 1]), 6),
            "count": int(frequencies.iloc[index]),
        }
        for index in range(len(edges) - 1)
    ]


def chart_data(equity: pd.DataFrame, trades: pd.DataFrame) -> dict[str, object]:
    """Aggregate report data so a result bundle stays compact and portable."""
    equity = equity.copy()
    if not equity.empty:
        equity["date"] = pd.to_datetime(equity["date"])
        equity["drawdown"] = equity["equity"] / equity["equity"].cummax() - 1
        monthly = (
            equity.set_index("date")["daily_return"]
            .resample("ME")
            .apply(lambda returns: (1 + returns).prod() - 1)
        )
        monthly_data = [
            [timestamp.strftime("%Y-%m"), round(float(value), 6)]
            for timestamp, value in monthly.dropna().items()
        ]
    else:
        monthly_data = []
    return {
        "equity": _line_points(equity, "equity"),
        "drawdown": _line_points(equity, "drawdown"),
        "monthly": monthly_data,
        "tradeHistogram": _histogram(trades["net_return"].dropna())
        if "net_return" in trades
        else [],
    }


def build_report(
    run_id: str,
    metadata: dict[str, object],
    metrics: dict[str, object],
    equity: pd.DataFrame | None = None,
    trades: pd.DataFrame | None = None,
) -> str:
    metric_rows = "".join(
        f"<tr><th>{escape(str(key).replace('_', ' '))}</th><td>{escape(str(value))}</td></tr>"
        for key, value in metrics.items()
    )
    data = chart_data(
        equity if equity is not None else pd.DataFrame(),
        trades if trades is not None else pd.DataFrame(),
    )
    encoded_data = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{escape(run_id)}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:1100px;margin:2.5rem auto;padding:0 1rem;color:#1f2937}}
h1{{margin-bottom:.2rem}} .subtle{{color:#64748b}} .charts{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.5rem}}
.chart{{min-width:0}} svg{{width:100%;height:270px;border:1px solid #cbd5e1;background:#fff}} .axis{{stroke:#94a3b8;stroke-width:1}}
.grid{{stroke:#e2e8f0;stroke-width:1}} .label{{font-size:11px;fill:#475569}} .line{{fill:none;stroke:#2563eb;stroke-width:2}}
.drawdown{{fill:#dc2626;fill-opacity:.16;stroke:#dc2626;stroke-width:1.5}} .bar-positive{{fill:#16a34a}} .bar-negative{{fill:#dc2626}}
.hist{{fill:#7c3aed}} th,td{{padding:.4rem .8rem;text-align:left;border-bottom:1px solid #e2e8f0}} th{{text-transform:capitalize}}
@media(max-width:720px){{.charts{{grid-template-columns:1fr}}}}
</style></head><body>
<h1>Quant-OSINT technical baseline</h1><p class='subtle'>Run: <code>{escape(run_id)}</code> · signals at close, execution at next open</p>
<section class='charts'><div class='chart'><h2>Equity curve</h2><svg id='equity-chart' role='img' aria-label='Cumulative equity curve'></svg></div>
<div class='chart'><h2>Drawdown</h2><svg id='drawdown-chart' role='img' aria-label='Portfolio drawdown over time'></svg></div>
<div class='chart'><h2>Monthly returns</h2><svg id='monthly-chart' role='img' aria-label='Monthly portfolio returns'></svg></div>
<div class='chart'><h2>Trade return distribution</h2><svg id='trade-chart' role='img' aria-label='Histogram of net trade returns'></svg></div></section>
<h2>Metrics</h2><table>{metric_rows}</table><h2>Lineage</h2><pre>{escape(json.dumps(metadata, indent=2, sort_keys=True))}</pre>
<script>const reportData={encoded_data};
const ns='http://www.w3.org/2000/svg';
function element(tag,attrs={{}}){{const node=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([key,value])=>node.setAttribute(key,value));return node}}
function frame(svg,values,kind){{const width=Math.max(360,svg.clientWidth||500),height=270,pad={{left:56,right:12,top:14,bottom:34}};svg.setAttribute('viewBox',`0 0 ${{width}} ${{height}}`);svg.replaceChildren();if(!values.length){{const noData=element('text',{{x:width/2,y:height/2,'text-anchor':'middle',class:'label'}});noData.textContent='No data';svg.append(noData);return null}}const ys=values.map(value=>value[1]),min=Math.min(0,...ys),max=Math.max(0,...ys),spread=max-min||1;const x=index=>pad.left+index*(width-pad.left-pad.right)/Math.max(values.length-1,1),y=value=>height-pad.bottom-(value-min)/spread*(height-pad.top-pad.bottom);for(let i=0;i<4;i++){{const yy=pad.top+i*(height-pad.top-pad.bottom)/3;svg.append(element('line',{{x1:pad.left,x2:width-pad.right,y1:yy,y2:yy,class:'grid'}}));const label=element('text',{{x:pad.left-6,y:yy+4,'text-anchor':'end',class:'label'}});label.textContent=`${{((max-i*spread/3)*100).toFixed(1)}}%`;svg.append(label)}}svg.append(element('line',{{x1:pad.left,x2:width-pad.right,y1:height-pad.bottom,y2:height-pad.bottom,class:'axis'}}));svg.append(element('line',{{x1:pad.left,x2:pad.left,y1:pad.top,y2:height-pad.bottom,class:'axis'}}));return {{width,height,pad,x,y,min,max}}}}
function lineChart(id,values,area){{const svg=document.getElementById(id),state=frame(svg,values);if(!state)return;const points=values.map((value,index)=>`${{state.x(index)}},${{state.y(value[1])}}`).join(' ');svg.append(element(area?'polygon':'polyline',{{points, class:area?'drawdown':'line'}}));if(area){{const areaPoints=`${{state.pad.left}},${{state.height-state.pad.bottom}} ${{points}} ${{state.width-state.pad.right}},${{state.height-state.pad.bottom}}`;svg.lastChild.setAttribute('points',areaPoints)}}}}
function barChart(id,values,histogram){{const svg=document.getElementById(id),state=frame(svg,values);if(!state)return;const plotWidth=state.width-state.pad.left-state.pad.right;const barWidth=Math.max(1,plotWidth/values.length-1);values.forEach((value,index)=>{{const base=histogram?0:0,zero=state.y(base),top=state.y(value[1]);svg.append(element('rect',{{x:state.x(index)-barWidth/2,y:Math.min(top,zero),width:barWidth,height:Math.max(1,Math.abs(zero-top)),class:histogram?'hist':value[1]>=0?'bar-positive':'bar-negative'}}))}})}}
function draw(){{lineChart('equity-chart',reportData.equity,false);lineChart('drawdown-chart',reportData.drawdown,true);barChart('monthly-chart',reportData.monthly,false);barChart('trade-chart',reportData.tradeHistogram.map(bin=>[(bin.start+bin.end)/2,bin.count]),true)}}
draw();new ResizeObserver(draw).observe(document.querySelector('.charts'));</script></body></html>"""
