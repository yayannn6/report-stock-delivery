from odoo import models, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class ReportStockWarehouse(models.AbstractModel):
    _name = 'report.export_stock_report.stock_report_template'
    _description = 'Stock Report by Warehouse'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.report.wizard'].browse(docids)
        date_now = datetime.now().strftime('%d-%m-%Y')

        # ambil warehouse sesuai pilihan wizard, kalau kosong ambil semua
        warehouses = docs.warehouse_ids or self.env['stock.warehouse'].search([])

        report_data = {}

        for wh in warehouses:
            # agregasi quant langsung di DB, exclude product archived
            quants = self.env['stock.quant'].read_group(
                domain=[
                    ('quantity', '>', 0),
                    ('location_id', 'child_of', wh.view_location_id.id),
                    ('location_id.usage', '=', 'internal'),
                    ('product_id.active', '=', True),   # <<-- hanya product aktif
                ],
                fields=['product_id', 'quantity:sum'],
                groupby=['product_id']
            )

            for q in quants:
                product_id = q['product_id'][0]
                qty = q['quantity']
                product = self.env['product.product'].browse(product_id)

                categ_name = (product.categ_id.name or "").lower()

                # filter kategori
                if docs.kategori_selection == "export" and "export" not in categ_name:
                    continue
                elif docs.kategori_selection == "lokal" and "lokal" not in categ_name:
                    continue

                if product not in report_data:
                    report_data[product] = {}

                if wh not in report_data[product]:
                    report_data[product][wh] = {"box": 0.0, "count": 0.0}

                container_capacity = product.container_capacity or 0
                report_data[product][wh]["box"] += qty
                report_data[product][wh]["count"] += qty / container_capacity if container_capacity else 0

                _logger.debug("Product: %s | WH: %s | Box=%.2f | Count=%.2f",
                              product.display_name, wh.name,
                              report_data[product][wh]["box"],
                              report_data[product][wh]["count"])

        # bersihkan product yang total semua warehouse = 0
        clean_data = {
            p: wh_vals for p, wh_vals in report_data.items()
            if any(v["box"] > 0 for v in wh_vals.values())
        }

        return {
            'doc_ids': docids,
            'doc_model': 'stock.report.wizard',
            'docs': docs,
            'date_now': date_now,
            'report_data': clean_data,
            'warehouses': warehouses,
        }
