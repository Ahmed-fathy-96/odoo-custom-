from odoo import api, exceptions, fields, models, _


class AccountMoveExt(models.Model):
    _inherit = "account.move"

    def add_j_line(self,check_product, total_discount, sequence):
        for invoice in self:
            allowed_discount_product = invoice.company_id.allowed_discount_product
            allowed_discount_account = invoice.company_id.allowed_discount_account

            if check_product:
                new_terms_lines = self.env['account.move.line']
                create_line = self.env['account.move.line'].new or self.env['account.move.line'].create

                candidate = create_line({
                    'name': f' {allowed_discount_product.name} discount',
                    'debit': total_discount,
                    'credit': 0.0,
                    'quantity': 1.0,
                    'move_id': invoice.id,
                    'currency_id': invoice.currency_id.id,
                    'account_id': allowed_discount_account.id,
                    'sequence': sequence,
                    'exclude_from_invoice_tab': True,
                })
                new_terms_lines += candidate

    def journal_discount_line(self):
        for invoice in self:
            allowed_discount_product = invoice.company_id.allowed_discount_product
            partner_discount =  invoice.partner_id.allowed_discount
            if invoice.partner_id.allowed_discount > 0 and invoice.move_type == 'out_invoice':
                total_discount = 0
                check_product = False
                for line in invoice.line_ids:
                    if line.product_id.id == allowed_discount_product.id:
                        check_product = True
                        total_discount = line.quantity * (allowed_discount_product.list_price * ( partner_discount / 100))
                        line.credit += total_discount
                        sequence = line.sequence + 1
                        self.add_j_line(check_product, total_discount, sequence)

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        ''' Recompute all lines that depend of others.

        For example, tax lines depends of base lines (lines having tax_ids set). This is also the case of cash rounding
        lines that depend of base lines or tax lines depending the cash rounding strategy. When a payment term is set,
        this method will auto-balance the move with payment term lines.

        :param recompute_all_taxes: Force the computation of taxes. If set to False, the computation will be done
                                    or not depending of the field 'recompute_tax_line' in lines.
        '''
        for invoice in self:
            # Dispatch lines and pre-compute some aggregated values like taxes.
            for line in invoice.line_ids:
                if line.recompute_tax_line:
                    recompute_all_taxes = True
                    line.recompute_tax_line = False

            # Compute taxes.
            if recompute_all_taxes:
                invoice._recompute_tax_lines()
            if recompute_tax_base_amount:
                invoice._recompute_tax_lines(recompute_tax_base_amount=True)

            if invoice.is_invoice(include_receipts=True):

                # Compute cash rounding.
                invoice._recompute_cash_rounding_lines()


                # Compute payment terms.
                invoice._recompute_payment_terms_lines()

                # Only synchronize one2many in onchange.
                if invoice != invoice._origin:
                    invoice.invoice_line_ids = invoice.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)

                # Compute cash rounding.
                invoice.journal_discount_line()
