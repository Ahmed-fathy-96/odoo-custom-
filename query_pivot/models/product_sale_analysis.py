from odoo import api, fields, models
from odoo import tools


class ProductSaleAnalysisPivot(models.Model):
    _name = "product.analysis.pvo"
    _description = "Product Sale Analysis"
    _auto = False

    product_id = fields.Many2one('product.product', string='Product')
    date = fields.Date('Invoice Date')
    quantity = fields.Float('Quantity')
    untaxed_total = fields.Float('Untaxed')
    total = fields.Float('Total')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
    ], readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled')
    ], string='Invoice Status', readonly=True)
    exclude_from_invoice_tab = fields.Boolean('Exclude from invoice')

    def init(self):
        tools.drop_view_if_exists(self._cr, "product_analysis_pvo")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW product_analysis_pvo AS (
                SELECT
                    row_number() OVER () AS id,
                    line.product_id,
                    line.date,
                    line.quantity,
                    line.untaxed_total,
                    line.total,
                    line.invoice_id,
                    line.partner_id,
                    line.user_id,
                    line.type,
                    line.state,
                    line.exclude_from_invoice_tab FROM (
                        SELECT
                            p.id as product_id,
                            am.invoice_date as date,
                            aml.quantity  as quantity,
                            aml.price_subtotal as untaxed_total,
                            aml.price_total as total,
                            aml.move_id as invoice_id,
                            am.partner_id as partner_id,
                            am.invoice_user_id as user_id,
                            am.move_type as type,
                            am.state as state,
                            aml.exclude_from_invoice_tab as exclude_from_invoice_tab
                        FROM product_product p
                        LEFT JOIN account_move_line aml ON (p.id = aml.product_id)
                        LEFT JOIN account_move am ON (aml.move_id = am.id)
                        
                    ) as line
                    WHERE
                        line.state = 'posted' AND
                        not line.exclude_from_invoice_tab AND
                        line.type in ('out_invoice', 'out_refund')
                )
        """)
