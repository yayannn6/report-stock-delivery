from odoo import models, api
from collections import defaultdict
import time
import re
import random


class ReportDalamPengiriman(models.AbstractModel):
    _name = 'report.export_stock_report.stock_report_pengiriman'
    _description = 'Stock Report Dalam Pengiriman (Internal Transfer - Ready)'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['pengiriman.report.wizard'].browse(docids)

        # ===== Domain picking: hanya internal & ready =====
        domain = [
            ('picking_type_code', '=', 'internal'),
            ('state', '=', 'assigned'),  # hanya status "Ready"
            ('scheduled_date', '<=', wizard.end_date),
        ]

        # Filter warehouse jika dipilih
        if wizard.warehouse_ids:
            domain.append(('picking_type_id.warehouse_id', 'in', wizard.warehouse_ids.ids))

        # Filter sales jika dipilih
        if wizard.sales_person_ids:
            domain.append(('sales_person_id', 'in', wizard.sales_person_ids.ids))

        pickings = self.env['stock.picking'].search(domain)

        # ===== Struktur hasil utama =====
        results = defaultdict(  # per salesperson
            lambda: defaultdict(  # per product
                lambda: defaultdict(lambda: {"box": 0, "cont": 0, "grade": None, "name_product": None})
            )
        )

        warehouses = set()
        products = set()
        grades = set()
        colors = ["#d97c7c", "#7c9bd9", "#7cd99b", "#d9b37c", "#9e7cd9"]
        bg_color = random.choice(colors)

        # ===== Totalan =====
        grand_totals = {"box": 0, "cont": 0}
        warehouse_totals = defaultdict(lambda: {"box": 0, "cont": 0})
        sales_totals = defaultdict(lambda: {"box": 0, "cont": 0})
        product_group_totals = defaultdict(lambda: defaultdict(lambda: {"box": 0, "cont": 0}))

        # ===== Loop picking & move line =====
        for picking in pickings:
            salesperson = picking.sales_person_id.name or "Tanpa Sales"
            wh_name = picking.picking_type_id.warehouse_id.name
            warehouses.add(wh_name)

            for ml in picking.move_line_ids:
                categ_name = (ml.product_id.categ_id.name or "").lower()

                # Filter kategori lokal / export jika dipilih
                if wizard.kategori_selection == "export" and categ_name != "export":
                    continue
                elif wizard.kategori_selection == "lokal" and categ_name != "lokal":
                    continue

                prod = ml.product_id.display_name
                products.add(prod)
                pr_name = ml.product_id.name

                # Ambil grade dari nama produk (contoh: "Product (A)")
                match = re.search(r'\((.*?)\)', prod)
                grade_from_display_name = match.group(1) if match else None
                if grade_from_display_name:
                    grades.add(grade_from_display_name)

                # Ambil qty dari move line
                qty = ml.qty_done or ml.product_uom_qty or 0.0

                # Hitung box & cont
                box = qty
                cont = qty / ml.product_id.container_capacity if ml.product_id.container_capacity else 0

                # Simpan ke results
                res = results[salesperson][prod][wh_name]
                res["box"] += box
                res["cont"] += cont
                res["grade"] = grade_from_display_name
                res["name_product"] = pr_name

                # Total per warehouse
                warehouse_totals[wh_name]["box"] += box
                warehouse_totals[wh_name]["cont"] += cont

                # Total per sales
                sales_totals[salesperson]["box"] += box
                sales_totals[salesperson]["cont"] += cont

                # Total global
                grand_totals["box"] += box
                grand_totals["cont"] += cont

        # ===== Hitung total per produk (tanpa varian/grade) =====
        for sp, prods in results.items():
            for prod_name, wh_data in prods.items():
                base_name = re.sub(r'\s*\(.*?\)', '', prod_name).strip()
                for wh_name, vals in wh_data.items():
                    product_group_totals[sp][base_name]["box"] += vals.get("box", 0)
                    product_group_totals[sp][base_name]["cont"] += vals.get("cont", 0)

        # ===== Konversi per UoM BOX =====
        uoms = self.env['uom.uom'].search([('category_id.name', '=', 'BOX')], order="factor ASC")

        warehouse_uom_totals = defaultdict(lambda: defaultdict(float))
        grand_uom_totals = defaultdict(float)

        for wh_name in warehouses:
            qty_box = warehouse_totals[wh_name]["box"]
            warehouse_uom_totals[wh_name]['total_count'] += qty_box
            grand_uom_totals['total_count'] += qty_box

            for uom in uoms:
                converted_qty = qty_box / uom.factor if uom.factor else 0
                warehouse_uom_totals[wh_name][uom.id] += converted_qty
                grand_uom_totals[uom.id] += converted_qty

        # ===== Return ke QWeb template =====
        return {
            "doc_ids": docids,
            "doc_model": "pengiriman.report.wizard",
            "docs": wizard,
            "results": results,
            "warehouses": sorted(list(warehouses)),
            "products": sorted(list(products)),
            "grades": sorted(list(grades)),
            "time": time,
            "bg_color": bg_color,
            "grand_totals": grand_totals,
            "warehouse_totals": warehouse_totals,
            "sales_totals": sales_totals,
            "uoms": [{"id": u.id, "name": u.name, "factor": u.factor} for u in uoms],
            "warehouse_uom_totals": warehouse_uom_totals,
            "grand_uom_totals": grand_uom_totals,
            "product_group_totals": product_group_totals,
        }
