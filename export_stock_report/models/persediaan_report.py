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

        # ===== Ambil data dari stock.quant langsung =====
        quant_domain = [
            ('location_id.usage', '=', 'internal'),
            ('quantity', '>', 0),
            ('product_id', '!=', False),
            ('location_id.warehouse_id', 'in',
             wizard.warehouse_ids.ids or self.env['stock.warehouse'].search([]).ids),
        ]

        quants = self.env['stock.quant'].search(quant_domain)

        # ===== Struktur hasil utama =====
        results = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(
                    lambda: defaultdict(lambda: {"box": 0, "cont": 0, "grade": None})
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
        customer_totals = defaultdict(lambda: defaultdict(lambda: {"box": 0, "cont": 0}))

        # ===== Loop quant =====
        for quant in quants:
            product = quant.product_id
            warehouse = quant.location_id.warehouse_id
            owner = quant.owner_id or False

            # Tentukan salesperson
            salesperson = (
                product.product_tmpl_id.responsible_id.name
                if product.product_tmpl_id.responsible_id
                else "Tanpa Sales"
            )
            customer = owner.name if owner else "Tanpa Customer"

            wh_name = warehouse.name
            warehouses.add(wh_name)

            prod_display = product.display_name
            products.add(prod_display)
            pr_name = product.name

            # Ambil grade dari nama produk
            match = re.search(r'\((.*?)\)', prod_display)
            grade = match.group(1) if match else None
            if grade:
                grades.add(grade)

            # Ambil qty langsung dari quant
            qty = quant.quantity
            box = qty
            cont = qty / product.container_capacity if product.container_capacity else 0

            # Simpan ke results
            results[salesperson][customer][prod_display][wh_name]["box"] += box
            results[salesperson][customer][prod_display][wh_name]["cont"] += cont
            results[salesperson][customer][prod_display][wh_name]["grade"] = grade
            results[salesperson][customer][prod_display][wh_name]["name_product"] = pr_name

            # Total per warehouse
            warehouse_totals[wh_name]["box"] += box
            warehouse_totals[wh_name]["cont"] += cont

            # Total per customer
            customer_totals[salesperson][customer]["box"] += box
            customer_totals[salesperson][customer]["cont"] += cont

            # Total global
            grand_totals["box"] += box
            grand_totals["cont"] += cont

        # ===== Hitung total per produk tanpa memperhatikan grade =====
        product_group_totals = defaultdict(lambda: defaultdict(lambda: {"box": 0, "cont": 0}))
        for sp, custs in results.items():
            for cust, prods in custs.items():
                for prod_name, wh_data in prods.items():
                    base_name = re.sub(r'\s*\(.*?\)', '', prod_name).strip()
                    for wh_name, vals in wh_data.items():
                        product_group_totals[cust][base_name]["box"] += vals.get("box", 0)
                        product_group_totals[cust][base_name]["cont"] += vals.get("cont", 0)

        # ===== Tambahan: Konversi per UoM BOX =====
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
            "uoms": [{"id": u.id, "name": u.name, "factor": u.factor} for u in uoms],
            "warehouse_uom_totals": warehouse_uom_totals,
            "grand_uom_totals": grand_uom_totals,
            "product_group_totals": product_group_totals,
        }
