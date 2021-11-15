from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError, ValidationError


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _description = "Purchase Request Model"

    name = fields.Char(string="Request name", required=True)
    user_ids = fields.Many2one('res.users', string="Requested by", required=True, default=lambda self: self.env.user)
    start_date = fields.Date(default=lambda self: fields.Datetime.today())
    end_date = fields.Date()

    rejection_reason = fields.Text()
    order_lines = fields.One2many('purchase.request.line', 'request_id', string="Order Lines")
    total_price = fields.Float(compute="_compute_total_price")
    state = fields.Selection(
        default='draft',
        string="Status",
        selection=[('draft', 'draft'),
                   ('to be approved', 'to be approved'),
                   ('approve', 'approve'),
                   ('reject', 'reject'),
                   ('cancel', 'cancel')])

    @api.depends('order_lines')
    def _compute_total_price(self):
        for record in self:
            if record.mapped('order_lines.total'):
                record.total_price = sum(record.mapped('order_lines.total'))
            else:
                record.total_price = 0

    def submit_to_Approved(self):
        for record in self:
            record.state = 'to be approved'
        return True

    def cancel_fun(self):
        for record in self:
            record.state = 'cancel'
        return True

    def approve_fun(self):
        for record in self:
            record.state = 'approve'
        return True

    def confirm_reject(self):
        for record in self:
            record.state = 'reject'
        return True

    def reset_fun(self):
        for record in self:
            record.state = 'draft'
        return True

