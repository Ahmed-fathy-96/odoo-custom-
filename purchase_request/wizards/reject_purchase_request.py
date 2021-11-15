from odoo import fields, models, api


class RejectPurchaseRequest(models.TransientModel):
    _name = "reject.purchase.request"
    _description = "reject purchase request model"

    rejection_reason = fields.Text(requried=True)

    def reject_confirm_action(self):
        print("................................")
        req_id = self._context.get('active_id')
        current_request = self.env['purchase.request'].search([('id', '=', req_id)])
        if current_request:
            current_request.state = "reject"
            current_request.rejection_reason = self.rejection_reason
        else:
            print("ahmed error ")
        return True