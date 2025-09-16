from odoo import models, api
from collections import defaultdict
import time

class ReportExportStock(models.AbstractModel):
    _name = 'report.export_stock_report.report_export_stock'
    _description = 'Report Export Stock'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['export.stock.wizard'].browse(docids)

        # Ambil DO (Delivery Order) yang statusnya siap kirim (belum done/cancel)
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
                    lambda: defaultdict(lambda: {"box": 0, "cont": 0, "variant_values": []})
                )
            )
        )
        warehouses = set()
        products = set()

        for picking in pickings:
            salesperson = picking.user_id.name
            customer = picking.partner_id.name
            wh_name = picking.picking_type_id.warehouse_id.name
            warehouses.add(wh_name)

            for ml in picking.move_line_ids:
                prod = ml.product_id.display_name
                products.add(prod)
                variant_values = ml.product_id.product_template_variant_value_ids.mapped('name')

                qty = ml.quantity

                # Menghitung box dan cont sesuai dengan aturan yang diberikan
                box = qty  # Box = quantity
                cont = qty / 0.002  # Cont = quantity / 0.002

                # Menyimpan box dan cont ke dalam results
                results[salesperson][customer][prod][wh_name]["box"] += box
                results[salesperson][customer][prod][wh_name]["cont"] += cont
                results[salesperson][customer][prod][wh_name]["variant_values"] = variant_values

        return {
            "doc_ids": docids,
            "doc_model": "export.stock.report.wizard",
            "docs": wizard,
            "results": results,
            "warehouses": sorted(list(warehouses)),
            "products": sorted(list(products)),
            "time": time,
        }

