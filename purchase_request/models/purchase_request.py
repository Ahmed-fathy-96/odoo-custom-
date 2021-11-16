from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _description = "Purchase Request Model"

    name = fields.Char(string="Request name", required=True)
    user_id = fields.Many2one('res.users', string="Requested by", required=True, default=lambda self: self.env.user)
    start_date = fields.Date(default=lambda self: fields.Datetime.today())
    end_date = fields.Date()

    rejection_reason = fields.Text()
    order_lines = fields.One2many('purchase.request.line', 'request_id', )
    total_price = fields.Float(compute="_compute_total_price")
    state = fields.Selection(
        default='draft',
        string="Status",
        selection=[('draft', 'draft'),
                   ('to_be_approved', 'to be approved'),
                   ('approve', 'approve'),
                   ('reject', 'reject'),
                   ('cancel', 'cancel')])

    @api.depends('order_lines')
    def _compute_total_price(self):
        for record in self:
            record.total_price = sum([l.total for l in record.order_lines])

    def submit_to_Approved_action(self):
        self.write({'state': 'to_be_approved'})

    def cancel_action(self):
        self.write({'state': 'cancel'})

    def approve_action(self):
        self.write({'state': 'approve'})
        template_id = self.env.ref('purchase_request.approve_purchase_email_template').id
        template = self.env['mail.template'].browse(template_id)
        template.send_mail(self.id, force_send=True)

    def confirm_reject(self):
        self.write({'state': 'reject'})

    def reset_action(self):
        self.write({'state': 'draft'})


class PurchaseRequestLine(models.Model):
    _name = "purchase.request.line"
    _description = "Purchase Request Line Model"

    product_id = fields.Many2one('product.product', string="Product", required=True)
    description = fields.Char(related='product_id.display_name', string="Description")
    quantity = fields.Float(default=1)
    cost_price = fields.Float()
    total = fields.Float(readonly=True)
    request_id = fields.Many2one('purchase.request')

    @api.onchange('quantity')
    def _onchange_quantity(self):
        self.total = self.quantity * self.cost_price

    @api.onchange('product_id')
    def _onchange_product(self):
        self.cost_price = self.product_id.lst_price
        self.total = self.quantity * self.cost_price
