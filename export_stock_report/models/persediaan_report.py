from odoo import models, api
from collections import defaultdict
import time
import re
import random


class ReportStockWarehouse(models.AbstractModel):
    _name = 'report.export_stock_report.stock_report_template'
    _description = 'Stock Report by Warehouse'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['stock.report.wizard'].browse(docids)

        # ===== Domain picking =====
        domain = [
            ('picking_type_code', '=', 'incoming'),
            ('scheduled_date', '<=', wizard.end_date),
            ('picking_type_id.warehouse_id', 'in',
             wizard.warehouse_ids.ids or self.env['stock.warehouse'].search([]).ids),
            ('sales_person_id', 'in',
             wizard.sales_person_ids.ids or self.env['res.users'].search([]).ids),
            ('state', 'not in', ['draft', 'cancel'])
        ]

        pickings = self.env['stock.picking'].search(domain)

        # ===== Struktur hasil utama =====
        results = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(
                    lambda: defaultdict(lambda: {"box": 0, "cont": 0, "grade": None, "name_product": None})
                )
            )
        )

        warehouses = set()
        products = set()
        grades = set()
        colors = ["#d97c7c", "#7c9bd9", "#7cd99b", "#d9b37c", "#9e7cd9"]
        bg_color = random.choice(colors)

        grand_totals = {"box": 0, "cont": 0}
        warehouse_totals = defaultdict(lambda: {"box": 0, "cont": 0})
        customer_totals = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"box": 0, "cont": 0})))

        # ===== Loop picking & move line =====
        seen_quant = set()
        for picking in pickings:
            salesperson = picking.sales_person_id.name or "-"
            wh = picking.picking_type_id.warehouse_id
            wh_name = wh.name
            warehouses.add(wh_name)

            for ml in picking.move_line_ids:
                categ_name = (ml.product_id.categ_id.name or "").lower()
                if wizard.kategori_selection == "export" and categ_name != "export":
                    continue
                elif wizard.kategori_selection == "lokal" and categ_name != "lokal":
                    continue

                prod = ml.product_id.display_name
                products.add(prod)
                pr_name = ml.product_id.name

                match = re.search(r'\((.*?)\)', prod)
                grade_from_display_name = match.group(1) if match else None
                if grade_from_display_name:
                    grades.add(grade_from_display_name)

                owner = ml.owner_id or picking.owner_id or picking.partner_id
                owner_id = owner.id if owner else False
                customer = owner.name if owner and owner.name else (picking.partner_id.name or "Unknown Customer")

                seen_key = (ml.product_id.id, owner_id, wh.id)
                if seen_key in seen_quant:
                    continue
                seen_quant.add(seen_key)

                quant_domain = [
                    ('product_id', '=', ml.product_id.id),
                    ('location_id', 'child_of', wh.view_location_id.id),
                ]
                if owner_id:
                    quant_domain.append(('owner_id', '=', owner_id))

                qty_onhand = sum(self.env['stock.quant'].search(quant_domain).mapped('quantity'))
                qty = qty_onhand

                box = qty
                cont = qty / ml.product_id.container_capacity if ml.product_id.container_capacity else 0

                data_dict = results[salesperson][customer][prod][wh_name]
                data_dict["box"] += box
                data_dict["cont"] += cont
                data_dict["grade"] = grade_from_display_name
                data_dict["name_product"] = pr_name

                warehouse_totals[wh_name]["box"] += box
                warehouse_totals[wh_name]["cont"] += cont

                customer_totals[salesperson][customer][wh_name]["box"] += box
                customer_totals[salesperson][customer][wh_name]["cont"] += cont
                customer_totals[salesperson][customer]["total"]["box"] += box
                customer_totals[salesperson][customer]["total"]["cont"] += cont

                grand_totals["box"] += box
                grand_totals["cont"] += cont

        # ===== Hitung total per produk =====
        product_group_totals = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"box": 0, "cont": 0})))
        for sp, custs in results.items():
            for cust, prods in custs.items():
                for prod_name, wh_data in prods.items():
                    base_name = re.sub(r'\s*\(.*?\)', '', prod_name).strip()
                    for wh_name, vals in wh_data.items():
                        product_group_totals[cust][base_name][wh_name]["box"] += vals.get("box", 0)
                        product_group_totals[cust][base_name][wh_name]["cont"] += vals.get("cont", 0)
                        product_group_totals[cust][base_name]["total"]["box"] += vals.get("box", 0)
                        product_group_totals[cust][base_name]["total"]["cont"] += vals.get("cont", 0)

        # ===== Tambahan UoM BOX lama (tetap, untuk perbandingan lain) =====
        uoms = self.env['uom.uom'].search([('category_id.name', '=', 'BOX')], order="factor ASC")
        warehouse_uom_totals = defaultdict(lambda: defaultdict(float))
        grand_uom_totals = defaultdict(float)
        warehouse_uom_totals_count = defaultdict(lambda: defaultdict(float))
        grand_uom_totals_count = defaultdict(float)

        for wh_name in warehouses:
            qty_box = warehouse_totals[wh_name]["box"]
            qty_cont = warehouse_totals[wh_name]["cont"]

            warehouse_uom_totals[wh_name]['total_count'] += qty_box
            grand_uom_totals['total_count'] += qty_box

            for uom in uoms:
                converted_qty = qty_box / uom.factor if uom.factor else 0
                warehouse_uom_totals[wh_name][uom.id] += converted_qty
                grand_uom_totals[uom.id] += converted_qty

            warehouse_uom_totals_count[wh_name]['total_count'] += qty_cont
            grand_uom_totals_count['total_count'] += qty_cont

            for uom in uoms:
                converted_qty_count = qty_cont / uom.factor if uom.factor else 0
                warehouse_uom_totals_count[wh_name][uom.id] += converted_qty_count
                grand_uom_totals_count[uom.id] += converted_qty_count

        # ===== TOTAL KESELURUHAN PER WAREHOUSE (revisi utama) =====
        stock_domain = [
            ('date', '<=', wizard.end_date),
            ('state', '=', 'done'),
            ('location_id.warehouse_id', 'in',
             wizard.warehouse_ids.ids or self.env['stock.warehouse'].search([]).ids),
        ]
        move_lines = self.env['stock.move.line'].search(stock_domain)

        total_warehouse_summary = defaultdict(lambda: defaultdict(float))
        grand_total_summary = defaultdict(float)
        all_uoms = set()

        for line in move_lines:
            wh = line.location_id.warehouse_id
            if not wh:
                continue
            wh_name = wh.name
            uom_name = line.product_uom_id.name or 'Unknown'

            total_warehouse_summary[wh_name][uom_name] += line.qty_done
            total_warehouse_summary[wh_name]['Total Count (BOX)'] += line.qty_done
            all_uoms.add(uom_name)

        # === Hitung GRAND TOTAL ===
        for wh_data in total_warehouse_summary.values():
            for uom_name, qty in wh_data.items():
                grand_total_summary[uom_name] += qty

        total_warehouse_summary['GRAND TOTAL'] = grand_total_summary
        total_warehouse_summary = dict(sorted(total_warehouse_summary.items(), key=lambda x: x[0].lower()))

        # === UoM yang muncul di data saja ===
        uoms_used = [{'name': name} for name in sorted(all_uoms)]

        # ===== Return all =====
        return {
            "doc_ids": docids,
            "doc_model": "stock.report.wizard",
            "docs": wizard,
            "results": results,
            "warehouses": sorted(list(warehouses)),
            "products": sorted(list(products)),
            "grades": sorted(list(grades)),
            "time": time,
            "bg_color": bg_color,
            "grand_totals": grand_totals,
            "warehouse_totals": warehouse_totals,
            "customer_totals": customer_totals,
            "uoms": uoms_used,  # hanya dari move_line nyata
            "warehouse_uom_totals": warehouse_uom_totals,
            "grand_uom_totals": grand_uom_totals,
            "grand_uom_totals_count": grand_uom_totals_count,
            "product_group_totals": product_group_totals,
            "total_per_uom_warehouse": {},
            "total_warehouse_summary": total_warehouse_summary,
        }
