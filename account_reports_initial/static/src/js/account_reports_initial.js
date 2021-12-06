odoo.define('account_reports_initial.account_report', function (require) {
'use strict';
var accountReportsWidget  = require('account_reports.account_report');


accountReportsWidget.include({
        events: _.extend({}, accountReportsWidget.prototype.events, {
            'change #initial_balance_check': '_onChangeInitialBalanceBool'
        }),
        _onChangeInitialBalanceBool: function (event) {
            var self = this;
            self.report_options['initial_balance'] = $('#initial_balance_check').prop("checked");
            self.reload();
        }
    });
});
