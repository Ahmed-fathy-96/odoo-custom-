from odoo import api, fields, models
from dateutil.relativedelta import relativedelta

class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "estate property offer"
    # _sql_constraints = [
    #     ('check_price', 'CHECK(price > 0)', 'An offer price must be strictly positive.')
    # ]

    price = fields.Float()
    status = fields.Selection(
        copy=False,
        selection=[('Accepted', 'Accepted'), ('Refused', 'Refused')]
    )
    validity = fields.Integer(default=7)
    date_deadline = fields.Date(compute="_compute_date_deadline")
    partner_id = fields.Many2one("res.partner", string="Partners")
    property_id = fields.Many2one("estate.property", string="Properties")

    @api.depends('create_date', 'validity')
    def _compute_date_deadline(self):
        for record in self:
            if record.create_date:
                record.date_deadline = record.create_date.add(record.validity,days=+record.validity)
                # + relativedelta(days=+ record.validity)
            else:
                record.date_deadline = fields.Date.today() + relativedelta(days=+ record.validity)

    def action_accepted_offer(self):
        for record in self:
            record.status = 'Accepted'
            record.property_id.buyer_id = record.partner_id
            record.property_id.selling_price = record.price


        return True

    def action_refused_offer(self):
        for record in self:
            record.status = 'Refused'
        return True
