from odoo import api, exceptions, fields, models


class ResPartnerExt(models.Model):
    _inherit = 'res.partner'
    age = fields.Integer()
