import csv
import json
import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.analytics.dataset_analytics import (
    engagement,
    hashtags_intelligence,
    insights,
    load_active_dataframe_with_record,
    overview,
    platforms_comparison,
    sentiment,
    trends,
)
from app.core.config import PROJECT_ROOT, settings
from app.models.system import ReportRecord
from app.services.activity_service import record_event
from app.services.cloud_storage import delete_object, upload_bytes

REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

VALID_REPORT_TYPES = {"overall", "sentiment", "engagement", "platforms", "hashtags", "trends"}
VALID_FORMATS = {"pdf", "csv", "xlsx", "json"}

REPORT_LABELS = {
    "overall": "Overall Analytics Intelligence Report",
    "sentiment": "Sentiment & Emotion Intelligence Report",
    "engagement": "Engagement Performance Report",
    "platforms": "Cross-Platform Comparison Report",
    "hashtags": "Hashtag Intelligence Report",
    "trends": "Trend & Topic Velocity Report",
}


def _clean_xml_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    return escape(text)


def _col_letter(col_idx: int) -> str:
    result = ""
    n = col_idx
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def _build_worksheet_xml(rows: list[list[Any]]) -> str:
    xml_rows = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        style_attr = ' s="1"' if r_idx == 1 else ""
        for c_idx, val in enumerate(row, start=1):
            ref = f"{_col_letter(c_idx)}{r_idx}"
            if isinstance(val, (int, float)) and not isinstance(val, bool) and val == val:
                cells.append(f'<c r="{ref}"{style_attr} t="n"><v>{val}</v></c>')
            else:
                cells.append(
                    f'<c r="{ref}"{style_attr} t="inlineStr"><is><t>{_clean_xml_text(val)}</t></is></c>'
                )
        xml_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        "</worksheet>"
    )


def _write_xlsx(path: Path, sheets: list[tuple[str, list[list[Any]]]]) -> None:
    normalized_sheets = []
    seen_names: set[str] = set()
    for raw_name, rows in sheets:
        clean_name = re.sub(r"[\[\]:*?/\\]", "_", raw_name)[:28].strip() or "Sheet"
        candidate = clean_name
        idx = 2
        while candidate in seen_names:
            candidate = f"{clean_name[:25]}_{idx}"
            idx += 1
        seen_names.add(candidate)
        normalized_sheets.append((candidate, rows or [["No data"]]))

    content_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(normalized_sheets) + 1)
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.workbook+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        f"{content_overrides}</Types>"
    )

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    wb_sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
        for i, (name, _) in enumerate(normalized_sheets, start=1)
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{wb_sheets}</sheets>"
        "</workbook>"
    )

    wb_rels_items = "".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(normalized_sheets) + 1)
    )
    style_rid = len(normalized_sheets) + 1
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{wb_rels_items}"
        f'<Relationship Id="rId{style_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )

    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
        "</styleSheet>"
    )

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/styles.xml", styles_xml)
        for i, (_, rows) in enumerate(normalized_sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", _build_worksheet_xml(rows))


def _assemble_report_payload(
    db: Session,
    *,
    report_type: str,
    dataset_id: int | None,
    user_id: int | None,
    platform: str | None,
    start_date: str | None,
    end_date: str | None,
    title: str | None,
) -> dict[str, Any]:
    _, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    dataset_name = record.name if record else "SocialPulse Benchmark Dataset"

    ov = overview(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )
    ins = insights(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )
    tr = trends(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )
    sent = sentiment(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )
    eng = engagement(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
        limit=15,
    )
    plats = platforms_comparison(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        selected_platforms=platform,
        start_date=start_date,
        end_date=end_date,
    )
    tags = hashtags_intelligence(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    final_title = (title or "").strip() or REPORT_LABELS[report_type]

    section_rows: list[dict[str, Any]] = []
    if report_type == "sentiment":
        section_rows = sent["by_topic"]
    elif report_type == "engagement":
        section_rows = eng["top_posts"]
    elif report_type == "platforms":
        section_rows = [
            {
                "platform": p["name"],
                "posts": p["posts"],
                "share_pct": p["post_share_pct"],
                "total_engagement": p["engagement"],
                "avg_engagement": p["avg_engagement"],
                "likes": p["likes"],
                "shares": p["shares"],
                "comments": p["comments"],
                "positive_pct": p["sentiment"]["Positive"],
                "negative_pct": p["sentiment"]["Negative"],
            }
            for p in plats["platforms"]
        ]
    elif report_type == "hashtags":
        section_rows = [
            {
                "hashtag": h["name"],
                "count": h["count"],
                "total_engagement": h["engagement"],
                "avg_engagement": h["avg_engagement"],
                "positive_pct": h["positive_pct"],
                "negative_pct": h["negative_pct"],
                "top_platform": h["top_platform"],
            }
            for h in tags["hashtags"][:40]
        ]
    elif report_type == "trends":
        section_rows = tr["topics"]
    else:
        section_rows = ov["platforms"]

    recommendations = [
        {"title": item["title"], "observation": item["observation"], "recommendation": item["recommendation"]}
        for item in ins["structured_insights"]
    ]

    return {
        "title": final_title,
        "report_type": report_type,
        "dataset_id": record.id if record else None,
        "dataset_name": dataset_name,
        "generated_at": generated_at,
        "filters": {
            "platform": platform or "All",
            "start_date": start_date or ov["meta"].get("date_min"),
            "end_date": end_date or ov["meta"].get("date_max"),
        },
        "summary_kpis": ov["kpis"],
        "key_findings": ins["insights"],
        "recommendations": recommendations,
        "primary_table": section_rows,
        "overview": ov,
        "sentiment": sent,
        "engagement": eng,
        "platforms": plats["platforms"],
        "hashtags": tags["hashtags"][:30],
        "trends": tr,
    }


def _write_csv_report(path: Path, payload: dict[str, Any]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Report Title", payload["title"]])
        writer.writerow(["Dataset Name", payload["dataset_name"]])
        writer.writerow(["Generated At", payload["generated_at"]])
        writer.writerow(["Report Type", payload["report_type"]])
        writer.writerow([])
        writer.writerow(["KPI Metric", "Value"])
        for key, val in payload["summary_kpis"].items():
            writer.writerow([key, "" if val is None else val])
        writer.writerow([])

        rows = payload["primary_table"]
        if rows:
            headers = list(rows[0].keys())
            writer.writerow(headers)
            for row in rows:
                writer.writerow([
                    json.dumps(row.get(h)) if isinstance(row.get(h), (list, dict)) else row.get(h, "")
                    for h in headers
                ])
            writer.writerow([])

        writer.writerow(["Insight Title", "Observation", "Actionable Recommendation"])
        for rec in payload["recommendations"]:
            writer.writerow([rec["title"], rec["observation"], rec["recommendation"]])


def _write_xlsx_report(path: Path, payload: dict[str, Any]) -> None:
    summary_rows: list[list[Any]] = [
        ["Field", "Value"],
        ["Report Title", payload["title"]],
        ["Dataset Name", payload["dataset_name"]],
        ["Generated At", payload["generated_at"]],
        ["Report Type", payload["report_type"]],
        ["Platform Filter", payload["filters"]["platform"]],
        [],
        ["KPI Metric", "Value"],
    ]
    for key, val in payload["summary_kpis"].items():
        summary_rows.append([key, "N/A" if val is None else val])

    breakdown_rows: list[list[Any]] = []
    table = payload["primary_table"]
    if table:
        headers = list(table[0].keys())
        breakdown_rows.append(headers)
        for item in table:
            breakdown_rows.append([
                ", ".join(map(str, item.get(h, [])))
                if isinstance(item.get(h), list)
                else (json.dumps(item.get(h)) if isinstance(item.get(h), dict) else item.get(h, ""))
                for h in headers
            ])

    top_posts_rows: list[list[Any]] = [["post_id", "platform", "topic", "sentiment", "likes", "shares", "comments", "engagement", "content"]]
    for p in payload["engagement"].get("top_posts", []):
        top_posts_rows.append([
            p["post_id"],
            p["platform"],
            p["topic"],
            p["sentiment"],
            p["likes"],
            p["shares"],
            p["comments"],
            p["engagement"],
            p["content"][:200],
        ])

    rec_rows: list[list[Any]] = [["Title", "Observation", "Recommendation"]]
    for rec in payload["recommendations"]:
        rec_rows.append([rec["title"], rec["observation"], rec["recommendation"]])

    _write_xlsx(
        path,
        [
            ("Summary", summary_rows),
            ("Breakdown", breakdown_rows),
            ("Top_Posts", top_posts_rows),
            ("Recommendations", rec_rows),
        ],
    )


def _write_pdf_report(path: Path, payload: dict[str, Any]) -> None:
    kpis = payload["summary_kpis"]
    with PdfPages(path) as pdf:
        # Page 1: Executive Summary & Recommendations
        fig = plt.figure(figsize=(11, 8.5), facecolor="#FFFFFF")
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
        ax.axis("off")

        ax.text(0.0, 0.96, "SOCIALPULSE AI INTELLIGENCE", fontsize=10, fontweight="bold", color="#7C5CFC")
        ax.text(0.0, 0.91, payload["title"], fontsize=20, fontweight="bold", color="#0F172A")
        ax.text(
            0.0,
            0.87,
            f"Dataset: {payload['dataset_name']}   |   Generated: {payload['generated_at']}   |   Platform Scope: {payload['filters']['platform']}",
            fontsize=10,
            color="#475569",
        )

        # KPI Summary Strip
        kpi_boxes = [
            ("Total Posts", f"{kpis.get('total_posts', 0):,}"),
            ("Total Engagement", f"{kpis.get('total_engagement', 0):,}"),
            ("Avg Engagement", f"{kpis.get('avg_engagement', 0)}"),
            ("Positive Sentiment", f"{kpis.get('positive_sentiment', 0)}%"),
            ("Top Platform", f"{kpis.get('top_platform', 'N/A')}"),
        ]
        for idx, (label, val) in enumerate(kpi_boxes):
            x0 = idx * 0.2
            rect = plt.Rectangle((x0, 0.74), 0.185, 0.095, facecolor="#F8FAFC", edgecolor="#CBD5E1", linewidth=1)
            ax.add_patch(rect)
            ax.text(x0 + 0.012, 0.805, label.upper(), fontsize=8, fontweight="bold", color="#64748B")
            ax.text(x0 + 0.012, 0.76, str(val)[:18], fontsize=12, fontweight="bold", color="#0F172A")

        ax.text(0.0, 0.69, "Key Findings & Grounded Recommendations", fontsize=13, fontweight="bold", color="#0F172A")
        y = 0.64
        for rec in payload["recommendations"][:5]:
            ax.text(0.0, y, f"• {rec['title']}", fontsize=10.5, fontweight="bold", color="#1E293B")
            y -= 0.032
            obs_text = rec["observation"][:135] + ("..." if len(rec["observation"]) > 135 else "")
            act_text = rec["recommendation"][:135] + ("..." if len(rec["recommendation"]) > 135 else "")
            ax.text(0.02, y, f"Observation: {obs_text}", fontsize=9, color="#334155")
            y -= 0.028
            ax.text(0.02, y, f"Action: {act_text}", fontsize=9, color="#0369A1")
            y -= 0.045
            if y < 0.1:
                break

        ax.text(
            0.0,
            0.02,
            "All metrics computed from the active uploaded or bundled CSV dataset. Historical observations are not live API feeds.",
            fontsize=8,
            color="#64748B",
        )
        pdf.savefig(fig)
        plt.close(fig)

        # Page 2: Visual Charts
        fig2, axes = plt.subplots(2, 2, figsize=(11, 8.5), facecolor="#FFFFFF")
        fig2.suptitle(f"{payload['title']} — Analytical Charts", fontsize=14, fontweight="bold", color="#0F172A", y=0.97)

        # Chart 1: Platform Engagement
        plats = payload["platforms"][:6]
        ax1 = axes[0, 0]
        if plats:
            ax1.bar([p["name"] for p in plats], [p["engagement"] for p in plats], color="#7C5CFC")
            ax1.set_title("Engagement by Platform", fontsize=11, fontweight="bold")
            ax1.tick_params(axis="x", labelsize=8)
        else:
            ax1.text(0.5, 0.5, "No platform data", ha="center", va="center")

        # Chart 2: Sentiment Distribution
        ax2 = axes[0, 1]
        sent_dist = payload["overview"].get("sentiment", [])
        if sent_dist:
            ax2.pie(
                [s["value"] for s in sent_dist],
                labels=[f"{s['name']} ({s['percentage']}%)" for s in sent_dist],
                colors=["#22C55E", "#EF4444", "#94A3B8"][: len(sent_dist)],
                startangle=130,
                wedgeprops={"width": 0.45},
            )
            ax2.set_title("Sentiment Distribution", fontsize=11, fontweight="bold")
        else:
            ax2.text(0.5, 0.5, "No sentiment data", ha="center", va="center")

        # Chart 3: Top Topics
        ax3 = axes[1, 0]
        topics = payload["trends"].get("topics", [])[:7]
        if topics:
            names = [t["name"][:24] for t in reversed(topics)]
            counts = [t["posts"] for t in reversed(topics)]
            ax3.barh(names, counts, color="#00B4D8")
            ax3.set_title("Top Discussed Topics", fontsize=11, fontweight="bold")
            ax3.tick_params(axis="y", labelsize=8)
        else:
            ax3.text(0.5, 0.5, "No topic data", ha="center", va="center")

        # Chart 4: Top Hashtags
        ax4 = axes[1, 1]
        tags = payload["hashtags"][:8]
        if tags:
            names = [t["name"] for t in reversed(tags)]
            counts = [t["count"] for t in reversed(tags)]
            ax4.barh(names, counts, color="#22C55E")
            ax4.set_title("Top Hashtags by Frequency", fontsize=11, fontweight="bold")
            ax4.tick_params(axis="y", labelsize=8)
        else:
            ax4.text(0.5, 0.5, "No hashtag data", ha="center", va="center")

        plt.tight_layout(rect=[0, 0.02, 1, 0.94])
        pdf.savefig(fig2)
        plt.close(fig2)


def generate_report(
    db: Session,
    *,
    report_type: str,
    fmt: str,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    title: str | None = None,
) -> ReportRecord:
    clean_type = report_type.strip().lower()
    clean_fmt = fmt.strip().lower()
    if clean_type not in VALID_REPORT_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported report_type '{report_type}'.")
    if clean_fmt not in VALID_FORMATS:
        raise HTTPException(status_code=422, detail=f"Unsupported format '{fmt}'.")

    payload = _assemble_report_payload(
        db,
        report_type=clean_type,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
        title=title,
    )

    filename = f"socialpulse_{clean_type}_{uuid.uuid4().hex[:10]}.{clean_fmt}"
    out_path = REPORTS_DIR / filename

    if clean_fmt == "json":
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=str)
    elif clean_fmt == "csv":
        _write_csv_report(out_path, payload)
    elif clean_fmt == "xlsx":
        _write_xlsx_report(out_path, payload)
    elif clean_fmt == "pdf":
        _write_pdf_report(out_path, payload)

    media_types = {
        "pdf": "application/pdf",
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
    }
    if settings.supabase_url and settings.supabase_service_key:
        upload_bytes(settings.supabase_report_bucket, filename, out_path.read_bytes(), media_types[clean_fmt])

    record = ReportRecord(
        user_id=user_id,
        dataset_id=payload["dataset_id"],
        dataset_name=payload["dataset_name"],
        report_type=clean_type,
        format=clean_fmt,
        filename=filename,
        title=payload["title"],
        summary_json=json.dumps(payload["summary_kpis"]),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    record_event(
        db,
        action="report_generated",
        title="Report Ready for Download",
        message=f"Generated {clean_fmt.upper()} report '{record.title}' for '{record.dataset_name}'.",
        category="report",
        severity="success",
        target_type="report",
        target_name=record.title,
        user_id=user_id,
        meta={"report_id": record.id, "format": clean_fmt},
    )
    return record


def list_reports(db: Session, user_id: int | None = None) -> list[ReportRecord]:
    query = db.query(ReportRecord)
    if user_id is None:
        query = query.filter(ReportRecord.user_id.is_(None))
    else:
        query = query.filter(or_(ReportRecord.user_id.is_(None), ReportRecord.user_id == user_id))
    return query.order_by(ReportRecord.created_at.desc()).all()


def get_report(db: Session, report_id: int, user_id: int | None = None) -> ReportRecord:
    record = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    if record.user_id is not None and record.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied for this report.")
    return record


def delete_report(db: Session, report_id: int, user_id: int | None = None) -> dict[str, Any]:
    record = get_report(db, report_id, user_id=user_id)
    if user_id is not None and record.user_id != user_id:
        raise HTTPException(status_code=403, detail="Only the report owner can delete this report.")
    if settings.supabase_url and settings.supabase_service_key:
        delete_object(settings.supabase_report_bucket, record.filename)
    db.delete(record)
    db.commit()
    file_path = REPORTS_DIR / record.filename
    if file_path.exists():
        file_path.unlink()
    return {"deleted_id": report_id}

