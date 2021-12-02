from odoo import api, exceptions, fields, models, _


class AccountReportExt(models.AbstractModel):
    _inherit = 'account.report'

    filter_initial_balance = None


class AccountGeneralLedgerReportExt(models.AbstractModel):
    _inherit = "account.general.ledger"

    filter_initial_balance = True

    @api.model
    def _get_general_ledger_lines(self, options, line_id=None):
        ''' Get lines for the whole report or for a specific line.
        :param options: The report options.
        :return:        A list of lines, each one represented by a dictionary.
        '''
        lines = []
        aml_lines = []
        options_list = self._get_options_periods_list(options)
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])
        initial_balance = options.get('initial_balance') or None
        date_from = fields.Date.from_string(options['date']['date_from'])
        company_currency = self.env.company.currency_id

        expanded_account = line_id and self.env['account.account'].browse(int(line_id[8:]))
        accounts_results, taxes_results = self._do_query(options_list, expanded_account=expanded_account)

        total_debit = total_credit = total_balance = 0.0
        for account, periods_results in accounts_results:
            # No comparison allowed in the General Ledger. Then, take only the first period.
            results = periods_results[0]

            is_unfolded = 'account_%s' % account.id in options['unfolded_lines']

            # account.account record line.
            account_sum = results.get('sum', {})
            account_un_earn = results.get('unaffected_earnings', {})

            # Check if there is sub-lines for the current period.
            max_date = account_sum.get('max_date')
            has_lines = max_date and max_date >= date_from or False

            amount_currency = account_sum.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0)
            debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
            credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0)
            balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0)

            lines.append(
                self._get_account_title_line(options, account, amount_currency, debit, credit, balance, has_lines))
            total_debit += debit
            total_credit += credit
            total_balance += balance

            if has_lines and (unfold_all or is_unfolded):
                # Initial balance line.
                if initial_balance:
                    account_init_bal = results.get('initial_balance', {})
                    cumulated_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
                    lines.append(self._get_initial_balance_line(
                        options, account,
                        account_init_bal.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0),
                        account_init_bal.get('debit', 0.0) + account_un_earn.get('debit', 0.0),
                        account_init_bal.get('credit', 0.0) + account_un_earn.get('credit', 0.0),
                        cumulated_balance,
                    ))
                else:
                    account_init_bal = results.get('initial_balance', {})
                    cumulated_balance = account_init_bal.get('balance', 0.0)

                # account.move.line record lines.
                amls = results.get('lines', [])

                load_more_remaining = len(amls)
                load_more_counter = self._context.get('print_mode') and load_more_remaining or self.MAX_LINES

                for aml in amls:
                    # Don't show more line than load_more_counter.
                    if load_more_counter == 0:
                        break

                    cumulated_balance += aml['balance']
                    lines.append(self._get_aml_line(options, account, aml, company_currency.round(cumulated_balance)))

                    load_more_remaining -= 1
                    load_more_counter -= 1
                    aml_lines.append(aml['id'])

                if load_more_remaining > 0:
                    # Load more line.
                    lines.append(self._get_load_more_line(
                        options, account,
                        self.MAX_LINES,
                        load_more_remaining,
                        cumulated_balance,
                    ))

                if self.env.company.totals_below_sections:
                    # Account total line.
                    lines.append(self._get_account_total_line(
                        options, account,
                        account_sum.get('amount_currency', 0.0),
                        account_sum.get('debit', 0.0),
                        account_sum.get('credit', 0.0),
                        account_sum.get('balance', 0.0),
                    ))

        if not line_id:
            # Report total line.
            lines.append(self._get_total_line(
                options,
                total_debit,
                total_credit,
                company_currency.round(total_balance),
            ))

            # Tax Declaration lines.
            journal_options = self._get_options_journals(options)
            if len(journal_options) == 1 and journal_options[0]['type'] in ('sale', 'purchase'):
                lines += self._get_tax_declaration_lines(
                    options, journal_options[0]['type'], taxes_results
                )
        if self.env.context.get('aml_only'):
            return aml_lines
        # print("lines = ", lines)
        return lines

    # @api.model
    # def _get_account_title_line(self, options, account, amount_currency, debit, credit, balance, has_lines):
    #     has_foreign_currency = account.currency_id and account.currency_id != account.company_id.currency_id or False
    #     unfold_all = self._context.get('print_mode') and not options.get('unfolded_lines')
    #
    #     name = '%s %s' % (account.code, account.name)
    #     max_length = self._context.get('print_mode') and 100 or 60
    #     if len(name) > max_length and not self._context.get('no_format'):
    #         name = name[:max_length] + '...'
    #     columns = [
    #         {'name': self.format_value(debit), 'class': 'number'},
    #         {'name': self.format_value(credit), 'class': 'number'},
    #         {'name': self.format_value(balance), 'class': 'number'},
    #     ]
    #     if self.user_has_groups('base.group_multi_currency'):
    #         columns.insert(0, {
    #             'name': has_foreign_currency and self.format_value(amount_currency, currency=account.currency_id,
    #                                                                blank_if_zero=True) or '', 'class': 'number'})
    #     print("account_title = ", {
    #         'id': 'account_%d' % account.id,
    #         'name': name,
    #         'title_hover': name,
    #         'columns': columns,
    #         'level': 2,
    #         'unfoldable': has_lines,
    #         'unfolded': has_lines and 'account_%d' % account.id in options.get('unfolded_lines') or unfold_all,
    #         'colspan': 4,
    #         'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
    #     })
    #     return {
    #         'id': 'account_%d' % account.id,
    #         'name': name,
    #         'title_hover': name,
    #         'columns': columns,
    #         'level': 2,
    #         'unfoldable': has_lines,
    #         'unfolded': has_lines and 'account_%d' % account.id in options.get('unfolded_lines') or unfold_all,
    #         'colspan': 4,
    #         'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
    #     }


class AccountChartOfAccountReportExt(models.AbstractModel):
    _inherit = "account.coa.report"

    filter_initial_balance = True

    @api.model
    def _get_columns(self, options):
        headers = super(AccountChartOfAccountReportExt, self)._get_columns(options)
        # check the initial balance
        if not options.get('initial_balance'):
            # headers without initial balance
            headers[0] = [{'name': '', 'style': 'width:40%'}, ] + [
                {'name': period['string'], 'class': 'number', 'colspan': 2}
                for period in reversed(options['comparison'].get('periods', []))] + [
                             {'name': options['date']['string'], 'class': 'number', 'colspan': 2},
                             {'name': _('Total'), 'class': 'number', 'colspan': 2},
                         ]
            headers[1] = [
                {'name': '', 'style': 'width:40%'},
            ]
            if options.get('comparison') and options['comparison'].get('periods'):
                headers[1] += [
                                  {'name': _('Debit'), 'class': 'number o_account_coa_column_contrast'},
                                  {'name': _('Credit'), 'class': 'number o_account_coa_column_contrast'},
                              ] * len(options['comparison']['periods'])
            headers[1] += [
                {'name': _('Debit'), 'class': 'number o_account_coa_column_contrast'},
                {'name': _('Credit'), 'class': 'number o_account_coa_column_contrast'},
                {'name': _('Debit'), 'class': 'number o_account_coa_column_contrast'},
                {'name': _('Credit'), 'class': 'number o_account_coa_column_contrast'},
            ]
        return headers

    @api.model
    def _get_lines(self, options, line_id=None):
        new_options = options.copy()
        new_options['unfold_all'] = True
        options_list = self._get_options_periods_list(new_options)
        accounts_results, taxes_results = self.env['account.general.ledger']._do_query(options_list, fetch_lines=False)

        lines = []
        totals = [0.0] * (2 * (len(options_list) + 2))

        # Add lines, one per account.account record.
        for account, periods_results in accounts_results:
            sums = []
            account_balance = 0.0
            for i, period_values in enumerate(reversed(periods_results)):
                account_sum = period_values.get('sum', {})
                account_un_earn = period_values.get('unaffected_earnings', {})
                account_init_bal = period_values.get('initial_balance', {})

                if i == 0:
                    # Append the initial balances.
                    initial_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
                    sums += [
                        initial_balance > 0 and initial_balance or 0.0,
                        initial_balance < 0 and -initial_balance or 0.0,
                    ]
                    account_balance += initial_balance

                # Append the debit/credit columns.
                sums += [
                    account_sum.get('debit', 0.0) - account_init_bal.get('debit', 0.0),
                    account_sum.get('credit', 0.0) - account_init_bal.get('credit', 0.0),
                ]
                account_balance += sums[-2] - sums[-1]

            # Append the totals.
            sums += [
                account_balance > 0 and account_balance or 0.0,
                account_balance < 0 and -account_balance or 0.0,
            ]

            # account.account report line.
            columns = []
            for i, value in enumerate(sums):
                # Update totals.
                totals[i] += value
                # Create columns.
                columns.append(
                    {'name': self.format_value(value, blank_if_zero=True), 'class': 'number', 'no_format_name': value})

            name = account.name_get()[0][1]
            if len(name) > 40 and not self._context.get('print_mode'):
                name = name[:40] + '...'

            lines.append({
                'id': account.id,
                'name': name,
                'title_hover': name,
                'columns': columns,
                'unfoldable': False,
                'caret_options': 'account.account',
                'class': 'o_account_searchable_line o_account_coa_column_contrast',
            })

        # Total report line.
        lines.append({
            'id': 'grouped_accounts_total',
            'name': _('Total'),
            'class': 'total o_account_coa_column_contrast',
            'columns': [{'name': self.format_value(total), 'class': 'number', 'no_format_name': total} for total in
                        totals],
            'level': 1,
        })

        if options.get('initial_balance'):
            return lines
        else:
            return list(map(self.get_lines_without_initial_balance, lines))

    def get_lines_without_initial_balance(self, line):
        # get lines without initial balance reassignment the total of lines .
        cols = line['columns']
        for i in range(len(cols)):
            if i == 0 and 'no_format_name' in cols[-2]:
                cols[-2]['no_format_name'] = cols[-2]['no_format_name'] - cols[i]['no_format_name']
                cols[-2]['name'] = self.format_value(cols[-2]['no_format_name']) if cols[-2]['no_format_name'] else ''
            elif i == 1 and 'no_format_name' in cols[-1]:
                cols[-1]['no_format_name'] = cols[-1]['no_format_name'] - cols[i]['no_format_name']
                cols[-1]['name'] = self.format_value(cols[-1]['no_format_name']) if cols[-1]['no_format_name'] else ''

        line['columns'] = cols[2:]
        return line


account_title = {'id': 'account_6', 'name': '121000 Account Receivable', 'title_hover': '121000 Account Receivable',
                 'columns': [
                     {'name': '$ 1,043,625.00', 'class': 'number'},
                     {'name': '$ 0.00', 'class': 'number'},
                     {'name': '$ 1,043,625.00', 'class': 'number'}
                 ], 'level': 2, 'unfoldable': True,
                 'unfolded': True, 'colspan': 4, 'class': 'o_account_reports_totals_below_sections'}

lines = [{'id': 'account_40', 'name': '101401 Bank', 'title_hover': '101401 Bank',
          'columns': [
              {'name': '$ 4,874.45', 'class': 'number'},
              {'name': '$ 32.58', 'class': 'number'},
              {'name': '$ 4,841.87', 'class': 'number'}
          ]
             , 'level': 2, 'unfoldable': False, 'unfolded': None,
          'colspan': 4, 'class': 'o_account_reports_totals_below_sections'},
         {'id': 'account_36', 'name': '101702 Bank Suspense Account', 'title_hover': '101702 Bank Suspense Account',
          'columns': [{'name': '$ 32.58', 'class': 'number'}, {'name': '$ 4,874.45', 'class': 'number'},
                      {'name': '$ -4,841.87', 'class': 'number'}], 'level': 2, 'unfoldable': False, 'unfolded': None,
          'colspan': 4, 'class': 'o_account_reports_totals_below_sections'},
         {'id': 'account_6', 'name': '121000 Account Receivable', 'title_hover': '121000 Account Receivable',
          'columns': [
              {'name': '$ 1,043,625.00', 'class': 'number'},
              {'name': '$ 0.00', 'class': 'number'},
              {'name': '$ 1,043,625.00', 'class': 'number'}
          ], 'level': 2, 'unfoldable': True, 'unfolded': True,
          'colspan': 4, 'class': 'o_account_reports_totals_below_sections'},
         {'id': 'initial_6', 'class': 'o_account_reports_initial_balance', 'name': 'Initial Balance',
          'parent_id': 'account_6',
          'columns': [{'name': '$ 365,125.00', 'class': 'number'},
                      {'name': '$ 0.00', 'class': 'number'},
                      {'name': '$ 365,125.00', 'class': 'number'}], 'colspan': 4},
         {'id': 17, 'caret_options': 'account.move', 'class': 'top-vertical-align', 'parent_id': 'account_6',
          'name': 'INV/2021/12/0001',
          'columns': [{'name': '12/01/2021', 'class': 'date'},
                      {'name': 'INV/2021/12/0001', 'title': 'INV/2021/12/0001',
                       'class': 'whitespace_print o_account_report_line_ellipsis'},
                      {'name': 'Azure Interior', 'title': 'Azure Interior',
                       'class': 'whitespace_print'},
                      {'name': '$ 365,125.00', 'class': 'number'},
                      {'name': '', 'class': 'number'},
                      {'name': '$ 730,250.00', 'class': 'number'}], 'level': 2},
         {'id': 20, 'caret_options': 'account.move', 'class': 'top-vertical-align', 'parent_id': 'account_6',
          'name': 'INV/2021/12/0002', 'columns': [{'name': '12/08/2021', 'class': 'date'},
                                                  {'name': 'INV/2021/12/0002', 'title': 'INV/2021/12/0002',
                                                   'class': 'whitespace_print o_account_report_line_ellipsis'},
                                                  {'name': 'Deco Addict', 'title': 'Deco Addict',
                                                   'class': 'whitespace_print'},
                                                  {'name': '$ 169,625.00', 'class': 'number'},
                                                  {'name': '', 'class': 'number'},
                                                  {'name': '$ 899,875.00', 'class': 'number'}], 'level': 2},
         {'id': 23, 'caret_options': 'account.move', 'class': 'top-vertical-align', 'parent_id': 'account_6',
          'name': 'INV/2021/12/0003', 'columns': [{'name': '12/08/2021', 'class': 'date'},
                                                  {'name': 'INV/2021/12/0003', 'title': 'INV/2021/12/0003',
                                                   'class': 'whitespace_print o_account_report_line_ellipsis'},
                                                  {'name': 'Deco Addict', 'title': 'Deco Addict',
                                                   'class': 'whitespace_print'},
                                                  {'name': '$ 143,750.00', 'class': 'number'},
                                                  {'name': '', 'class': 'number'},
                                                  {'name': '$ 1,043,625.00', 'class': 'number'}], 'level': 2},
         {'id': 'total_6', 'class': 'o_account_reports_domain_total', 'parent_id': 'account_6',
          'name': 'Total 121000 Account Receivable',
          'columns': [{'name': '$ 1,043,625.00', 'class': 'number'}, {'name': '$ 0.00', 'class': 'number'},
                      {'name': '$ 1,043,625.00', 'class': 'number'}], 'colspan': 4},
         {'id': 'account_14', 'name': '211000 Account Payable', 'title_hover': '211000 Account Payable',
          'columns': [{'name': '$ 0.00', 'class': 'number'}, {'name': '$ 541.10', 'class': 'number'},
                      {'name': '$ -541.10', 'class': 'number'}], 'level': 2, 'unfoldable': False, 'unfolded': None,
          'colspan': 4, 'class': 'o_account_reports_totals_below_sections'},
         {'id': 'account_16', 'name': '251000 Tax Received', 'title_hover': '251000 Tax Received',
          'columns': [{'name': '$ 0.00', 'class': 'number'}, {'name': '$ 136,125.00', 'class': 'number'},
                      {'name': '$ -136,125.00', 'class': 'number'}], 'level': 2, 'unfoldable': True, 'unfolded': True,
          'colspan': 4, 'class': 'o_account_reports_totals_below_sections'},
         {'id': 'initial_16', 'class': 'o_account_reports_initial_balance', 'name': 'Initial Balance',
          'parent_id': 'account_16',
          'columns': [{'name': '$ 0.00', 'class': 'number'}, {'name': '$ 47,625.00', 'class': 'number'},
                      {'name': '$ -47,625.00', 'class': 'number'}], 'colspan': 4},
         {'id': 32, 'caret_options': 'account.move', 'class': 'top-vertical-align', 'parent_id': 'account_16',
          'name': 'INV/2021/12/0001', 'columns': [{'name': '12/01/2021', 'class': 'date'},
                                                  {'name': 'INV/2021/12/0001-Tax 15.00%', 'title': 'Tax 15.00%',
                                                   'class': 'whitespace_print o_account_report_line_ellipsis'},
                                                  {'name': 'Azure Interior', 'title': 'Azure Interior',
                                                   'class': 'whitespace_print'}, {'name': '', 'class': 'number'},
                                                  {'name': '$ 47,625.00', 'class': 'number'},
                                                  {'name': '$ -95,250.00', 'class': 'number'}], 'level': 2},
         {'id': 33, 'caret_options': 'account.move', 'class': 'top-vertical-align', 'parent_id': 'account_16',
          'name': 'INV/2021/12/0002', 'columns': [{'name': '12/08/2021', 'class': 'date'},
                                                  {'name': 'INV/2021/12/0002-Tax 15.00%', 'title': 'Tax 15.00%',
                                                   'class': 'whitespace_print o_account_report_line_ellipsis'},
                                                  {'name': 'Deco Addict', 'title': 'Deco Addict',
                                                   'class': 'whitespace_print'}, {'name': '', 'class': 'number'},
                                                  {'name': '$ 22,125.00', 'class': 'number'},
                                                  {'name': '$ -117,375.00', 'class': 'number'}], 'level': 2},
         {'id': 34, 'caret_options': 'account.move', 'class': 'top-vertical-align', 'parent_id': 'account_16',
          'name': 'INV/2021/12/0003', 'columns': [{'name': '12/08/2021', 'class': 'date'},
                                                  {'name': 'INV/2021/12/0003-Tax 15.00%', 'title': 'Tax 15.00%',
                                                   'class': 'whitespace_print o_account_report_line_ellipsis'},
                                                  {'name': 'Deco Addict', 'title': 'Deco Addict',
                                                   'class': 'whitespace_print'}, {'name': '', 'class': 'number'},
                                                  {'name': '$ 18,750.00', 'class': 'number'},
                                                  {'name': '$ -136,125.00', 'class': 'number'}], 'level': 2},
         {'id': 'total_16', 'class': 'o_account_reports_domain_total', 'parent_id': 'account_16',
          'name': 'Total 251000 Tax Received',
          'columns': [{'name': '$ 0.00', 'class': 'number'}, {'name': '$ 136,125.00', 'class': 'number'},
                      {'name': '$ -136,125.00', 'class': 'number'}], 'colspan': 4},
         {'id': 'account_21', 'name': '400000 Product Sales', 'title_hover': '400000 Product Sales',
          'columns': [{'name': '$ 0.00', 'class': 'number'}, {'name': '$ 907,500.00', 'class': 'number'},
                      {'name': '$ -907,500.00', 'class': 'number'}], 'level': 2, 'unfoldable': True, 'unfolded': None,
          'colspan': 4, 'class': 'o_account_reports_totals_below_sections'},
         {'id': 'account_43', 'name': '999999 Undistributed Profits/Losses',
          'title_hover': '999999 Undistributed Profits/Losses',
          'columns': [{'name': '$ 541.10', 'class': 'number'}, {'name': '$ 0.00', 'class': 'number'},
                      {'name': '$ 541.10', 'class': 'number'}], 'level': 2, 'unfoldable': False, 'unfolded': None,
          'colspan': 4, 'class': 'o_account_reports_totals_below_sections'},
         {'id': 'general_ledger_total_1', 'name': 'Total', 'class': 'total', 'level': 1,
          'columns': [{'name': '$ 1,049,073.13', 'class': 'number'}, {'name': '$ 1,049,073.13', 'class': 'number'},
                      {'name': '$ 0.00', 'class': 'number'}], 'colspan': 4}]
