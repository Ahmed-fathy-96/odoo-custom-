from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _description = "Purchase Request Model"

    name = fields.Char(string="Request name", required=True)
    user_id = fields.Many2one('res.users', string="Requested by", required=True, default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', required=True, string="Vendor")
    start_date = fields.Date(default=lambda self: fields.Datetime.today())
    end_date = fields.Date()
    rejection_reason = fields.Text()
    order_lines = fields.One2many('purchase.request.line', 'request_id', )
    order_ids = fields.One2many('purchase.order', 'request_id')
    total_price = fields.Float(compute="_compute_total_price")
    state = fields.Selection(
        default='draft',
        string="Status",
        selection=[('draft', 'draft'),
                   ('to_be_approved', 'to be approved'),
                   ('approve', 'approve'),
                   ('reject', 'reject'),
                   ('out_of_stock', 'out of stock'),
                   ('cancel', 'cancel'),
                   ])

    @api.depends('order_lines')
    def _compute_total_price(self):
        for record in self:
            record.total_price = sum([l.total for l in record.order_lines])

    def submit_to_Approved_action(self):
        self.write({'state': 'to_be_approved'})

    def cancel_action(self):
        self.write({'state': 'cancel'})

    def approve_action(self):
        template_id = self.env.ref('purchase_request.approve_purchase_email_template').id
        template = self.env['mail.template'].browse(template_id)
        users = self.env['res.groups'].search([('category_id', '=', 19)]).users
        for u in users:
            if u.id != self._uid:
                template.write({'email_to': u.id})
        template.send_mail(self.id, force_send=True)

        self.write({'state': 'approve'})

    def confirm_reject(self):
        self.write({'state': 'reject'})

    def reset_action(self):
        self.write({'state': 'draft'})

    def create_purchase_order_action(self):
        new_order_lines = []
        request_products = {}
        orders_products = {}
        all_stock = -1
        stock_unite = 0

        # get old orders
        old_orders = self.env['purchase.order'].search([('request_id', '=', self.id), ('state', '=', 'purchase')])
        for order in old_orders:
            for product in order.order_line:
                pqty = product.product_qty
                pid = product.product_id.id
                orders_products[pid] = pqty if pid not in orders_products.keys() else orders_products[pid] + pqty

        for line in self.order_lines:
            request_products[line.product_id.id] = line.quantity
            if orders_products:
                stock_unite = line.quantity - orders_products[line.product_id.id]
                all_stock += stock_unite if stock_unite > 0 else 0
                if 1 <= stock_unite :  # check if can make order with required quantity
                    new_order_lines.append((0, 0, {
                        'product_qty': 1,
                        'price_unit': line.price_unit,
                        'product_id': line.product_id.id,
                        'price_subtotal': line.total,
                    }))
                elif stock_unite != 0:
                    raise UserError(f'not available quantity of {line.product_id.display_name} only can get {stock_unite}')
                else:
                    raise UserError(f'{line.product_id.display_name} is out of stock')
            else:
                new_order_lines.append((0, 0, {
                    'product_qty': 1,
                    'price_unit': line.price_unit,
                    'product_id': line.product_id.id,
                    'price_subtotal': line.total,
                }))

        if all_stock == 0:
            self.write({'state': 'out_of_stock'})
            return False
        else:
            vals = {
                'name': f'{self.name} / {len(old_orders) + 1}',
                'partner_id': self.partner_id.id,
                'company_id': self.env.company.id,
                'user_id': self.user_id.id,
                'order_line': new_order_lines,
                'request_id': self.id
            }
            self.env['purchase.order'].create(vals)
            print(".........order created ........." )


    def orders_smart_button(self):
         return {
            'name': 'Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
             'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('request_id', '=', self.id)],
        }

class PurchaseRequestLine(models.Model):
    _name = "purchase.request.line"
    _description = "Purchase Request Line Model"

    product_id = fields.Many2one('product.product', string="Product", required=True)
    description = fields.Char(related='product_id.display_name', string="Description")
    quantity = fields.Float(default=1)
    price_unit = fields.Float()
    total = fields.Float()
    request_id = fields.Many2one('purchase.request')

    @api.onchange('quantity', 'price_unit')
    def _onchange_quantity(self):
        self.total = self.quantity * self.price_unit

    @api.onchange('product_id')
    def _onchange_product(self):
        self.price_unit = self.product_id.lst_price


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    request_id = fields.Many2one('purchase.request')
