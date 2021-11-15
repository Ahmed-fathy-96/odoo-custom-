from odoo import fields, models


class TestModel(models.Model):
    _name = "test.model"
    _description = "Test Model"

    name = fields.Char(default="Unknown")
    last_seen = fields.Datetime(default=lambda self: fields.Datetime.now())
