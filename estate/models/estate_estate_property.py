from odoo import _, api, fields, models
from odoo.exceptions import UserError, AccessError, ValidationError


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate Property"
    # _sql_constraints = [
    #     ('check_expected_price', 'CHECK(expected_price > 0)',
    #      'A property expected price must be strictly positive'),
    #     ('check_selling_price', 'CHECK(selling_price > 0)',
    #      'A property expected price must be strictly positive'),
    # ]

    name = fields.Char(string="Title", required=True)
    description = fields.Text()
    postcode = fields.Char(string="Postcode")
    date_availability = fields.Date(string="Availability From", copy=False,
                                    default=lambda self: fields.Datetime.today())
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(readonly=True, copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer(string="Living Area (sqm)")
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer(string="Garden Area (sqm)")
    garden_orientation = fields.Selection(
        string="garden orientation",
        help="garden orientation  is used to separate Leads and Opportunities",
        selection=[('North', 'North'), ('South', 'South'), ('East', 'East'), ('West', 'West')])
    active = fields.Boolean(default=False, )
    state = fields.Selection(
        required=True,
        default='New',
        copy=True,
        selection=[('New', 'New'),
                   ('Offer Received', 'Offer Received'),
                   ('Offer Accepted', 'Offer Accepted'),
                   ('Sold', 'Sold'),

                   ('Canceled', 'Canceled')])
    property_type_id = fields.Many2one('estate.property.type', string="Property Type")
    buyer_id = fields.Many2one('res.partner', string="Buyer", copy=False)
    sales_person = fields.Many2one('res.users', index=True, default=lambda self: self.env.user)
    tag_ids = fields.Many2many("estate.property.tag", string="Tags")
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Offers")
    total_area = fields.Float(compute="_compute_total_area")
    best_price = fields.Float(compute="_compute_best_price")

    @api.constrains('selling_price')
    def _check_date_end(self):
        for record in self:
            if (record.selling_price / record.expected_price) > 90:
                raise ValidationError("The end date cannot be set in the past")
        # all records passed the test, don't return anything

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.depends('offer_ids.price')
    def _compute_best_price(self):
        for record in self:
            if record.mapped('offer_ids.price'):
                record.best_price = max(record.mapped('offer_ids.price'))
            else:
                record.best_price = 0

    @api.onchange("garden")
    def _onchange_partner_id(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = 'North'
        else:
            self.garden_area = 0
            self.garden_orientation = ''
            return {
                'warning': {
                    'title': "Warning",
                    'message': ('This option is not supported for Authorize.net')
                }
            }

    def sold_fun(self):
        for record in self:
            if record.state != 'Canceled':
                record.state = "Sold"
            else:
                raise UserError(_('this property is canceled'))
        return True

    def cancel_fun(self):
        for record in self:
            if record.state != "Sold":
                record.state = 'Canceled'
            else:
                if record.state == "Sold":
                    raise UserError('this property is sold')
        return True


