from odoo import models, api
from collections import defaultdict
import time
import re  # Jangan lupa impor re untuk regex

class ReportExportStock(models.AbstractModel):
    _name = 'report.export_stock_report.report_export_stock'
    _description = 'Report Export Stock'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['export.stock.wizard'].browse(docids)

        pickings = self.env['stock.picking'].search([
            ('picking_type_code', '=', 'outgoing'),
            ('state', 'in', ['waiting', 'confirmed', 'assigned']),
            ('picking_type_id.warehouse_id', 'in', wizard.warehouse_ids.ids or self.env['stock.warehouse'].search([]).ids),
            ('scheduled_date', '>=', wizard.start_date), 
            ('scheduled_date', '<=', wizard.end_date),  
        ])

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

        for picking in pickings:
            salesperson = picking.user_id.name
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
                cont = qty / 0.002

                # Simpan hasil ke results
                results[salesperson][customer][prod][wh_name]["box"] += box
                results[salesperson][customer][prod][wh_name]["cont"] += cont
                results[salesperson][customer][prod][wh_name]["grade"] = grade_from_display_name
                results[salesperson][customer][prod][wh_name]["name_product"] = pr_name

        return {
            "doc_ids": docids,
            "doc_model": "export.stock.report.wizard",
            "docs": wizard,
            "results": results,
            "warehouses": sorted(list(warehouses)),
            "products": sorted(list(products)),
            "grades": sorted(list(grades)),  # Bisa juga dikirim ke report
            "time": time,
        }
