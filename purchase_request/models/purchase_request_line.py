from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError, ValidationError


class PurchaseRequestLine(models.Model):
    _name = "purchase.request.line"
    _description = "Purchase Request Line Model"

    product_id = fields.Many2one('product.product', string="Product", required=True)
    description = fields.Char(related='product_id.display_name')
    quantity = fields.Float(default=1)
    cost_price = fields.Float(related='product_id.list_price', string='Cost Price')
    total = fields.Float(compute="_compute_total")
    request_id = fields.Many2one('purchase.request')

    @api.depends('cost_price', 'quantity')
    def _compute_total(self):
        for record in self:
            record.total = record.quantity * record.cost_price
