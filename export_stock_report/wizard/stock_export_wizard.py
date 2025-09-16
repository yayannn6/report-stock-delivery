from odoo import models, fields

class ExportStockWizard(models.TransientModel):
    _name = 'export.stock.wizard'
    _description = 'Export Stock Report Wizard'

    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        string='Warehouses'
    )
    sales_person_ids = fields.Many2many(
        'res.users',
        string='Sales Persons'
    )
    start_date = fields.Date(
        string="Start Date"
    )
    end_date = fields.Date(
        string="End Date"
    )

    def action_print_report(self):
        return self.env.ref(
            'export_stock_report.action_export_stock_report'
        ).report_action(self)
