from odoo import models, fields

class ExportCekCL(models.TransientModel):
    _name = 'report.cek.cl.wizard'
    _description = 'Report Cek CL Wizard'

    kategori_selection = fields.Selection(
        [
            ('export', 'Export'), 
            ('lokal', 'Lokal')],
        string='Kategori Produk', default='export')
    
    def action_print_report(self):
        return self.env.ref(
            'export_stock_report.action_report_cek_cl'
        ).report_action(self)