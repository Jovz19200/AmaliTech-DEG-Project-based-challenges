# Last Mile Auditor — Veridi Logistics

**Are we failing specific regions, or is this nationwide?** Regional. Not nationwide.

## A. Executive summary

We joined 99,441 Olist orders to customers, the latest review per order, and English product categories, then audited **96,470 delivered** shipments. **8.1%** missed the estimated date and **4.4%** were more than five days late. That failure is concentrated in the North and Northeast: **Alagoas is 23.9% late** versus **5.9% in São Paulo**. Late deliveries cause the review spike: on-time orders score **4.29/5**, late orders score **2.57/5**. The CEO is wrong about nationwide over-promising — the average promise is 23 days and the actual is 12 — but that buffer is still not enough in remote Northeast states. Fix ETAs and last-mile capacity in AL, MA, PI, CE first.

## B. Project links

- **Repo:** https://github.com/Jovz19200/AmaliTech-DEG-Project-based-challenges/tree/main/data-engineering/Logistics-auditor
- **Notebook:** https://github.com/Jovz19200/AmaliTech-DEG-Project-based-challenges/blob/main/data-engineering/Logistics-auditor/notebooks/last_mile_audit.ipynb
- **Colab:** https://colab.research.google.com/github/Jovz19200/AmaliTech-DEG-Project-based-challenges/blob/main/data-engineering/Logistics-auditor/notebooks/last_mile_audit.ipynb
- **Notebook HTML:** https://github.com/Jovz19200/AmaliTech-DEG-Project-based-challenges/blob/main/data-engineering/Logistics-auditor/exports/last_mile_audit.html
- **Dashboard:** https://jovz19200.github.io/last-mile-auditor/
- **Presentation:** https://docs.google.com/presentation/d/1G2zUW_YKvmHdRIcJtwbE2TMPH4mhZ4N6SChsHg6aMT8/edit?usp=sharing

## C. Technical explanation

### Data cleaning and joins

Olist is split across tables. The grain of the audit is **one row per delivered order**.

- Reviews are 1-to-many. I keep the latest review per `order_id` so a second survey cannot duplicate a shipment. After the joins, duplicated orders = **0**.
- Products join through `order_items` (first item per order), then `product_category_name_translation.csv` for English names.
- Canceled and unavailable orders are excluded from delay rates. They never arrived, so they are a different failure from "late".
- Empty names are not an issue here. The order table always has an `order_id`.
- `Days_Difference = estimated delivery − actual delivery`. On Time ≥ 0. Late is −5 to −1. Super Late is less than −5.

Raw CSVs are downloaded at runtime into `data/raw/` with relative paths. They are not in this repo.

### Candidate's choice

A comparison of **promised transit days vs actual transit days by state**. Nationally we already pad the ETA. If a Northeast state is still late after a 30-day promise, the fix is last-mile capacity, not a nationwide rewrite of the estimate.

### How to run

```text
pip install -r requirements.txt
# from this folder, or open the notebook in Colab (it clones the repo first)
```

The Colab notebook clones this folder, then `scripts/analyze.py` downloads the Olist tables if they are missing.
