from odoo import fields, models


class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "estate property tag"
    _sql_constrains = [
        ('UNIQUE_constrains',
         'UNIQUE(name)',
         'A property tag name and property type name must be unique')]

    name = fields.Char(required=True)
