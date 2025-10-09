{
    "name": "Export Stock Report",
    "version": "18.0.1.0.0",
    "author": "Yayan H",
    "website": "",
    "category": "Inventory",
    "summary": "Custom Export Stock Report with PDF",
    "depends": ["stock"],
    "data": [
        # "views/warehouse_button.xml",
        # "views/export_stock_report_menu.xml",
        "views/stock_picking.xml",
        "wizard/export_stock_wizard_views.xml",
        "wizard/stock_quant.xml",
        "reports/export_stock_report.xml",
        "reports/report_export_stock_template.xml",
        "reports/stock_quant_report.xml",
        "reports/dalam_pengiriman.xml",
        "security/ir.model.access.csv",
        
    ],
    "installable": True,
    "application": False,
}
