from odoo import models, fields

class StockReportWizard(models.TransientModel):
    _name = 'stock.report.wizard'
    _description = 'Wizard Stock Report by Warehouse'

    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        string="Warehouse",
        help="Kosongkan untuk semua warehouse"
    )

    kategori_selection = fields.Selection([
        ('all', 'All'),
        ('lokal', 'Lokal'),
        ('export', 'Export'),
    ], string="Kategori", default="all")

    def action_print_report(self):
        data = {
            'warehouse_ids': self.warehouse_ids.ids,
            'kategori_selection': self.kategori_selection,
        }
        return self.env.ref('export_stock_report.action_report_stock_by_warehouse').report_action(self, data=data)
