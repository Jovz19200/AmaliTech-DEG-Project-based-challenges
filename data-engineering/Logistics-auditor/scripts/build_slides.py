"""5-slide Veridi Logistics insight deck."""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation" / "Last_Mile_Veridi.pptx"
OUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = RGBColor(31, 78, 121)
INK = RGBColor(26, 26, 26)
RED = RGBColor(192, 57, 43)


def title(tf, text, size=32, color=NAVY):
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = True
    p.font.color.rgb = color
    p.font.name = "Calibri"


def body(tf, lines, size=18):
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(size)
        p.font.color.rgb = INK
        p.font.name = "Calibri"
        p.space_after = Pt(8)


import json
s = json.loads((ROOT / "data" / "processed" / "summary.json").read_text(encoding="utf-8"))

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

slide = prs.slides.add_slide(prs.slide_layouts[6])
box = slide.shapes.add_textbox(Inches(0.7), Inches(2.0), Inches(12), Inches(1.2))
title(box.text_frame, "The Last Mile Auditor", 40)
box2 = slide.shapes.add_textbox(Inches(0.7), Inches(3.2), Inches(12), Inches(2.2))
body(box2.text_frame, [
    "Are we failing specific regions, or is this nationwide?",
    "Veridi Logistics  ·  Olist Brazil  ·  {:,} delivered orders".format(s["n_delivered"]),
    f"Answer: regional. {s['worst_state']} {s['worst_state_pct_late']}% late vs São Paulo {s['sp_pct_late']}%.",
], 22)

slide = prs.slides.add_slide(prs.slide_layouts[6])
box = slide.shapes.add_textbox(Inches(0.7), Inches(0.4), Inches(12), Inches(0.8))
title(box.text_frame, "The promise is breaking in the North", 28)
box2 = slide.shapes.add_textbox(Inches(0.7), Inches(1.4), Inches(12), Inches(5.5))
body(box2.text_frame, [
    f"{s['pct_late']}% of delivered orders miss the estimated date; {s['pct_super_late']}% are more than 5 days late.",
    f"North/Northeast: {s['remote_pct_late']}% late. São Paulo hub: {s['sp_pct_late']}% late.",
    f"Worst state: {s['worst_state']} at {s['worst_state_pct_late']}% late ({s['worst_state_n']:,} orders).",
    "This is not a nationwide failure. ETAs and last-mile capacity fail away from the hub.",
])

slide = prs.slides.add_slide(prs.slide_layouts[6])
box = slide.shapes.add_textbox(Inches(0.7), Inches(0.4), Inches(12), Inches(0.8))
title(box.text_frame, "Late packages are the review problem", 28)
box2 = slide.shapes.add_textbox(Inches(0.7), Inches(1.4), Inches(12), Inches(5.5))
body(box2.text_frame, [
    f"On-time orders: {s['on_time_review']}/5. Late orders: {s['late_review']}/5. Gap: {s['review_gap']} points.",
    "Review score falls in every extra delay bucket. Logistics is the sentiment driver.",
    f"Average promise: {s['avg_promised_days']} days. Average actual: {s['avg_actual_days']} days.",
    "States above the diagonal on the promise chart are where we over-promise.",
])

slide = prs.slides.add_slide(prs.slide_layouts[6])
box = slide.shapes.add_textbox(Inches(0.7), Inches(0.4), Inches(12), Inches(0.8))
title(box.text_frame, "What to fix this week", 28, RED)
box2 = slide.shapes.add_textbox(Inches(0.7), Inches(1.4), Inches(12), Inches(5.5))
body(box2.text_frame, [
    s["recommendation"],
    "Add buffer to ETAs for North and Northeast. National average already has slack.",
    "Product category is not the driver: furniture and electronics late rates are almost equal.",
    "Do not run a national apology campaign. Repair Alagoas, Maranhão, Piauí first.",
], 20)

slide = prs.slides.add_slide(prs.slide_layouts[6])
box = slide.shapes.add_textbox(Inches(0.7), Inches(0.4), Inches(12), Inches(0.8))
title(box.text_frame, "How the audit was built", 28)
box2 = slide.shapes.add_textbox(Inches(0.7), Inches(1.4), Inches(12), Inches(5.5))
body(box2.text_frame, [
    "Joined orders → customers → latest review (one per order) → first item category.",
    "Days_Difference = estimated − actual. Super Late = more than 5 days late.",
    "Canceled and unavailable orders excluded from delay rates.",
    "Dashboard: dashboard/last_mile_dashboard.html  ·  Notebook in /notebooks",
])

prs.save(str(OUT))
print("wrote", OUT)
