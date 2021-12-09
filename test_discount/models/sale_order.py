from odoo import api, exceptions, fields, models, _


class ResPartnerExt(models.Model):
    _inherit = 'res.partner'

    allowed_discount = fields.Float()


class ResCompany(models.Model):
    _inherit = "res.company"

    allowed_discount_account = fields.Many2one('account.account', required=True, store=True)
    allowed_discount_product = fields.Many2one('product.product', required=True, store=True,
                                               domain="[('type', '=', 'service')]")


class ResConfigSettingsExt(models.TransientModel):
    _inherit = 'res.config.settings'

    allowed_discount_account = fields.Many2one(related='company_id.allowed_discount_account', required=True,
                                               readonly=False)
    allowed_discount_product = fields.Many2one(related='company_id.allowed_discount_product', required=True,
                                               readonly=False)


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def _change_customer_check(self):
        new_order_lines = []
        for rec in self:
            partner_discount = rec.partner_id.allowed_discount
            if partner_discount:
                allowed_discount_account = rec.company_id.allowed_discount_account
                allowed_discount_product = rec.company_id.allowed_discount_product
                total_discount = allowed_discount_product.list_price * (partner_discount / 100)
                new_order_lines.append((0, 0, {
                    'name': allowed_discount_product.name,
                    'price_unit': allowed_discount_product.list_price - total_discount,
                    'product_id': allowed_discount_product,
                    'product_uom': allowed_discount_product.uom_id,
                }))
            rec.order_line = new_order_lines
