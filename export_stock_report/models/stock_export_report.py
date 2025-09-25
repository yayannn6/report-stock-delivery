from odoo import models, api
from collections import defaultdict
import time
import re  # Jangan lupa impor re untuk regex
import random

class ReportExportStock(models.AbstractModel):
    _name = 'report.export_stock_report.report_export_stock'
    _description = 'Report Export Stock'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['export.stock.wizard'].browse(docids)

        # ===== Filter status picking berdasarkan kategori =====
        if wizard.kategori_selection == "all":
            state_domain = [('state', 'not in', ['draft', 'cancel'])]
        elif wizard.kategori_selection == "export":
            state_domain = [('state', '=', 'done')]
        elif wizard.kategori_selection == "lokal":
            state_domain = [('state', '=', 'assigned')]
        else:
            state_domain = []

        domain = [
            ('picking_type_code', '=', 'outgoing'),
            ('scheduled_date', '>=', wizard.start_date),
            ('scheduled_date', '<=', wizard.end_date),
            ('picking_type_id.warehouse_id', 'in', wizard.warehouse_ids.ids or self.env['stock.warehouse'].search([]).ids),
            ('sales_person_id', 'in', wizard.sales_person_ids.ids or self.env['res.users'].search([]).ids),
        ] + state_domain

        pickings = self.env['stock.picking'].search(domain)

        results = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(
                    lambda: defaultdict(lambda: {"box": 0, "cont": 0, "grade": None})  # Tambah field grade
                )
            )
        )
        warehouses = set()
        products = set()
        grades = set()
        name_products = set()
        colors = ["#d97c7c", "#7c9bd9", "#7cd99b", "#d9b37c", "#9e7cd9"]
        bg_color = random.choice(colors)

        grand_totals = {"box": 0, "cont": 0}
        warehouse_totals = defaultdict(lambda: {"box": 0, "cont": 0})

        for picking in pickings:
            salesperson = picking.sales_person_id.name
            customer = picking.partner_id.name
            wh_name = picking.picking_type_id.warehouse_id.name
            warehouses.add(wh_name)

            for ml in picking.move_line_ids:
                prod = ml.product_id.display_name
                products.add(prod)
                pr_name = ml.product_id.name
                name_products.add(pr_name)

                # Ambil grade dari display_name, misal "Product (A)"
                match = re.search(r'\((.*?)\)', prod)
                grade_from_display_name = match.group(1) if match else None

                if grade_from_display_name:
                    grades.add(grade_from_display_name)

                qty = ml.quantity

                # Menghitung box dan cont sesuai aturan
                box = qty
                cont = qty / ml.product_id.container_capacity if ml.product_id.container_capacity else 0

                # Simpan hasil ke results
                results[salesperson][customer][prod][wh_name]["box"] += box
                results[salesperson][customer][prod][wh_name]["cont"] += cont
                results[salesperson][customer][prod][wh_name]["grade"] = grade_from_display_name
                results[salesperson][customer][prod][wh_name]["name_product"] = pr_name

                # Tambahkan ke total per warehouse
                warehouse_totals[wh_name]["box"] += box
                warehouse_totals[wh_name]["cont"] += cont

                # Tambahkan ke grand total
                grand_totals["box"] += box
                grand_totals["cont"] += cont

        return {
            "doc_ids": docids,
            "doc_model": "export.stock.report.wizard",
            "docs": wizard,
            "results": results,
            "warehouses": sorted(list(warehouses)),
            "products": sorted(list(products)),
            "grades": sorted(list(grades)),  # Bisa juga dikirim ke report
            "time": time,
            "bg_color": bg_color,
            "grand_totals": grand_totals,
            "warehouse_totals": warehouse_totals,
        }


