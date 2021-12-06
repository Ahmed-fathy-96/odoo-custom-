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
        # initial  balance option
        initial_balance = options.get('initial_balance') or None
        date_from = fields.Date.from_string(options['date']['date_from'])
        company_currency = self.env.company.currency_id
        expanded_account = line_id and self.env['account.account'].browse(int(line_id[8:]))
        accounts_results, taxes_results = self._do_query(options_list, expanded_account=expanded_account)

        total_debit = total_credit = total_balance = 0.0
        total_initial_debit = total_initial_credit = total_initial_balance = 0.0
        for account, periods_results in accounts_results:
            # No comparison allowed in the General Ledger. Then, take only the first period.
            results = periods_results[0]

            is_unfolded = 'account_%s' % account.id in options['unfolded_lines']

            # account.account record line.
            account_sum = results.get('sum', {})
            account_un_earn = results.get('unaffected_earnings', {})
            account_init_bal = results.get('initial_balance', {})

            # Check if there is sub-lines for the current period.
            max_date = account_sum.get('max_date')
            has_lines = max_date and max_date >= date_from or False

            # calculation of the sum of line with initial or without
            # check the initial balance option
            if initial_balance:
                amount_currency = account_sum.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0)
                debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
                credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0)
                balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
            else:

                amount_currency = account_sum.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0) - account_init_bal.get(
                    'amount_currency', 0.0)
                debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0) - account_init_bal.get(
                    'debit', 0.0)
                credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0) - account_init_bal.get(
                    'credit', 0.0)
                balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0) - account_init_bal.get(
                    'balance',
                    0.0)
            # add title line
            lines.append(
                self._get_account_title_line(options, account, amount_currency, debit, credit, balance, has_lines))
            total_debit += debit
            total_credit += credit
            total_balance += balance

            # check if there are lines
            if has_lines and (unfold_all or is_unfolded):
                # Initial balance line.
                if initial_balance:
                    cumulated_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
                    lines.append(self._get_initial_balance_line(
                        options, account,
                        account_init_bal.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0),
                        account_init_bal.get('debit', 0.0) + account_un_earn.get('debit', 0.0),
                        account_init_bal.get('credit', 0.0) + account_un_earn.get('credit', 0.0),
                        cumulated_balance,
                    ))
                else:
                    cumulated_balance = account_init_bal.get('balance', 0.0)

                # account.move.line record lines.
                amls = results.get('lines', [])

                load_more_remaining = len(amls)
                load_more_counter = self._context.get('print_mode') and load_more_remaining or self.MAX_LINES

                # loop for account lines
                for i, aml in enumerate(amls):
                    # Don't show more line than load_more_counter.
                    if load_more_counter == 0:
                        break
                    if i == 0 and not initial_balance:
                        cumulated_balance = aml['balance']
                    else:
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

                # totals without initial balance
                total_initial_debit += account_init_bal.get('debit', 0.0)
                total_initial_credit += account_init_bal.get('credit', 0.0)
                total_initial_balance += account_init_bal.get('balance', 0.0)

                if self.env.company.totals_below_sections:
                    # Account total line.
                    #check the initial balance
                    if not initial_balance:
                        lines.append(self._get_account_total_line(
                            options, account,
                            account_sum.get('amount_currency', 0.0) - account_init_bal.get('amount_currency', 0.0),
                            account_sum.get('debit', 0.0) - account_init_bal.get('debit', 0.0),
                            account_sum.get('credit', 0.0) - account_init_bal.get('credit', 0.0),
                            account_sum.get('balance', 0.0) - account_init_bal.get('balance', 0.0),
                        ))
                    else:
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
        return lines

    @api.model
    def _get_query_sums(self, options_list, expanded_account=None):
        ''' Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all accounts.
        - sums for the initial balances.
        - sums for the unaffected earnings.
        - sums for the tax declaration.
        :param options_list:        The report options list, first one being the current dates range, others being the
                                    comparisons.
        :param expanded_account:    An optional account.account record that must be specified when expanding a line
                                    with of without the load more.
        :return:                    (query, params)
        '''
        options = options_list[0]
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        params = []
        queries = []

        # Create the currency table.
        # As the currency table is the same whatever the comparisons, create it only once.
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        # ============================================
        # 1) Get sums for all accounts.
        # ============================================

        domain = [('account_id', '=', expanded_account.id)] if expanded_account else []
        for i, options_period in enumerate(options_list):
            # The period domain is expressed as:
            # [
            #   ('date' <= options['date_to']),
            #   '|',
            #   ('date' >= fiscalyear['date_from']),
            #   ('account_id.user_type_id.include_initial_balance', '=', True),
            # ]

            new_options = self._get_options_sum_balance(options_period)
            tables, where_clause, where_params = self._query_get(new_options, domain=domain)
            params += where_params
            queries.append('''
                SELECT
                    account_move_line.account_id                            AS groupby,
                    'sum'                                                   AS key,
                    MAX(account_move_line.date)                             AS max_date,
                    %s                                                      AS period_number,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                FROM %s
                LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                WHERE %s
                GROUP BY account_move_line.account_id
            ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 2) Get sums for the unaffected earnings.
        # ============================================

        domain = [('account_id.user_type_id.include_initial_balance', '=', False)]
        if expanded_account:
            domain.append(('company_id', '=', expanded_account.company_id.id))

        # Compute only the unaffected earnings for the oldest period.

        i = len(options_list) - 1
        options_period = options_list[-1]

        # The period domain is expressed as:
        # [
        #   ('date' <= fiscalyear['date_from'] - 1),
        #   ('account_id.user_type_id.include_initial_balance', '=', False),
        # ]

        new_options = self._get_options_unaffected_earnings(options_period)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        queries.append('''
            SELECT
                account_move_line.company_id                            AS groupby,
                'unaffected_earnings'                                   AS key,
                NULL                                                    AS max_date,
                %s                                                      AS period_number,
                COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
            FROM %s
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            WHERE %s
            GROUP BY account_move_line.company_id
        ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 3) Get sums for the initial balance.
        # ============================================
        domain = None
        if expanded_account:
            domain = [('account_id', '=', expanded_account.id)]
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain = [('account_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]
        # if domain is not None:
        for i, options_period in enumerate(options_list):
            # The period domain is expressed as:
            # [
            #   ('date' <= options['date_from'] - 1),
            #   '|',
            #   ('date' >= fiscalyear['date_from']),
            #   ('account_id.user_type_id.include_initial_balance', '=', True)
            # ]

            new_options = self._get_options_initial_balance(options_period)
            tables, where_clause, where_params = self._query_get(new_options, domain=domain)
            params += where_params
            queries.append('''
                SELECT
                    account_move_line.account_id                            AS groupby,
                    'initial_balance'                                       AS key,
                    NULL                                                    AS max_date,
                    %s                                                      AS period_number,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                FROM %s
                LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                WHERE %s
                GROUP BY account_move_line.account_id
            ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 4) Get sums for the tax declaration.
        # ============================================

        journal_options = self._get_options_journals(options)
        if not expanded_account and len(journal_options) == 1 and journal_options[0]['type'] in ('sale', 'purchase'):
            for i, options_period in enumerate(options_list):
                tables, where_clause, where_params = self._query_get(options_period)
                params += where_params + where_params
                queries += ['''
                    SELECT
                        tax_rel.account_tax_id                  AS groupby,
                        'base_amount'                           AS key,
                        NULL                                    AS max_date,
                        %s                                      AS period_number,
                        0.0                                     AS amount_currency,
                        0.0                                     AS debit,
                        0.0                                     AS credit,
                        SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                    FROM account_move_line_account_tax_rel tax_rel, %s
                    LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                    WHERE account_move_line.id = tax_rel.account_move_line_id AND %s
                    GROUP BY tax_rel.account_tax_id
                ''' % (i, tables, ct_query, where_clause), '''
                    SELECT
                    account_move_line.tax_line_id               AS groupby,
                    'tax_amount'                                AS key,
                        NULL                                    AS max_date,
                        %s                                      AS period_number,
                        0.0                                     AS amount_currency,
                        0.0                                     AS debit,
                        0.0                                     AS credit,
                        SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                    FROM %s
                    LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                    WHERE %s
                    GROUP BY account_move_line.tax_line_id
                ''' % (i, tables, ct_query, where_clause)]

        return ' UNION ALL '.join(queries), params


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
