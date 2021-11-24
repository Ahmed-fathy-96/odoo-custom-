from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _description = "Purchase Request Model"

    name = fields.Char(string="Request name", required=True, default='New')
    user_id = fields.Many2one('res.users', string="Requested by", required=True, default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', required=True, string="Vendor")
    start_date = fields.Date(default=lambda self: fields.Datetime.today())
    end_date = fields.Date()
    rejection_reason = fields.Text()
    order_lines = fields.One2many('purchase.request.line', 'request_id', )
    order_ids = fields.One2many('purchase.order', 'request_id')
    total_price = fields.Float(compute="_compute_total_price", store=True)
    state = fields.Selection(
        default='draft',
        string="Status",
        selection=[('draft', 'draft'),
                   ('to_be_approved', 'to be approved'),
                   ('approve', 'approve'),
                   ('reject', 'reject'),
                   ('cancel', 'cancel'),
                   ])
    out_of_stock = fields.Boolean(compute="_compute_out_of_stock")
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company.id)

    @api.depends('order_lines')
    def _compute_total_price(self):
        for record in self:
            record.total_price = sum([l.total for l in record.order_lines])

    @api.depends('order_ids')
    def _compute_out_of_stock(self):
        orders_products = {}
        for record in self:
            if sum(record.get_stock_purchase().values()):
                record.out_of_stock = False
            else:
                record.out_of_stock = True

    def get_stock_purchase(self):
        stock_units = {}
        orders_products_quantity = {}

        # quantities  of the old orders
        old_orders = self.order_ids
        for order in old_orders:
            if order.state == 'purchase':
                for product in order.order_line:
                    pqty = product.product_qty
                    pid = product.product_id.id
                    orders_products_quantity[pid] = pqty if pid not in orders_products_quantity.keys() else \
                        orders_products_quantity[pid] + pqty

        # stock of units
        order_lines = self.order_lines
        for line in order_lines:
            pid = line.product_id.id
            stock_unite = line.quantity - orders_products_quantity[pid] if orders_products_quantity else line.quantity
            stock_units[pid] = stock_unite if stock_unite > 0 else 0

        return stock_units

    def submit_to_Approved_action(self):
        for record in self:
            record.write({'state': 'to_be_approved'})

    def cancel_action(self):
        for record in self:
            record.write({'state': 'cancel'})

    def approve_action(self):
        template_id = self.env.ref('purchase_request.approve_purchase_email_template').id
        template = self.env['mail.template'].browse(template_id)
        category = self.env.ref('base.module_category_inventory_purchase', raise_if_not_found=False)
        users = self.env['res.groups'].search([('category_id', '=', category.id)]).users
        for u in users:
            if u.id != self._uid:
                template.write({'email_to': u.id})
        template.send_mail(self.id, force_send=True)
        self.write({'state': 'approve'})

    def confirm_reject(self):
        for record in self:
            record.write({'state': 'reject'})

    def reset_action(self):
        for record in self:
            record.write({'state': 'draft'})

    def create_purchase_order_action(self):
        new_order_lines = []
        stock_units = self.get_stock_purchase()

        for line in self.order_lines:
            if 1 <= stock_units[line.product_id.id]:
                new_order_lines.append((0, 0, {
                    'product_qty': 1,
                    'price_unit': line.price_unit,
                    'product_id': line.product_id.id,
                    'price_subtotal': line.total,
                }))
            elif stock_units[line.product_id.id] != 0:
                raise UserError(
                    f'the quantity  of {line.product_id.display_name}, only can get {stock_units[line.product_id.id]}')
            else:
                raise UserError(f'{line.product_id.display_name} is out of stock')

        vals = {
            'name': 'New',
            'partner_id': self.partner_id.id,
            'company_id': self.env.company.id,
            'user_id': self.user_id.id,
            'order_line': new_order_lines,
            'request_id': self.id
        }
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.name.sequence') or 'New'

        self.env['purchase.order'].create(vals)

    def orders_smart_button(self):
        return {
            'name': 'Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('request_id', '=', self.id)],
        }

    def bills_smart_button(self):
        return {
            'name': 'Bills',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [],
        }

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request.name.sequence') or 'Pr'
        return super(PurchaseRequest, self).create(vals)


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

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    discount = fields.Float(string='Discount (%)')

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount')
    def _compute_amount(self):
        for line in self:
            vals = line._prepare_compute_all_values()
            taxes = line.taxes_id.compute_all(
                vals['price_unit'],
                vals['currency_id'],
                vals['product_qty'],
                vals['product'],
                vals['partner'])
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'] - line.discount * taxes['total_included'],
                'price_subtotal': taxes['total_excluded'] - line.discount * taxes['total_excluded'],
            })

    def _prepare_account_move_line(self, move=False):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line()
        res['discount'] = self.discount
        return res
