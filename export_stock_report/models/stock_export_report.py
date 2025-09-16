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
            ('state', 'not in', ['cancel', 'done']),
            ('picking_type_id.warehouse_id', 'in', wizard.warehouse_ids.ids or self.env['stock.warehouse'].search([]).ids),
        ])

        results = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(
                    lambda: defaultdict(lambda: {"qty": 0, "uom": ""})
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
                prod = ml.product_id.name
                products.add(prod)

                qty = ml.quantity
                uom = ml.product_uom_id.name or ml.product_id.uom_id.name

                results[salesperson][customer][prod][wh_name]["qty"] += qty
                results[salesperson][customer][prod][wh_name]["uom"] = uom

        return {
            "doc_ids": docids,
            "doc_model": "export.stock.report.wizard",
            "docs": wizard,
            "results": results,
            "warehouses": sorted(list(warehouses)),
            "products": sorted(list(products)),
            "time": time,
        }
