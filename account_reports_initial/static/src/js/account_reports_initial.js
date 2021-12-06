odoo.define('account_reports_initial.account_report', function (require) {
'use strict';
var accountReportsWidget  = require('account_reports.account_report');


accountReportsWidget.include({
        events: _.extend({}, accountReportsWidget.prototype.events, {
            'change #initial_balance_check': '_onChangeInitialBalanceBool'
        }),
//        start: function() {
//            var self = this;
////            if (self.report_model == 'account.general.ledger' || self.report_model == 'account.coa.report' )
////                self.report_options['initial_balance'] = true;
////            else
////                self.report_options['initial_balance'] = false;
//            var extra_info = this._rpc({
//                    model: self.report_model,
//                    method: 'get_report_informations',
//                    args: [self.financial_id, self.report_options],
//                    context: self.odoo_context,
//                })
//                .then(function(result){
//                    return self.parse_reports_informations(result);
//                });
//            return Promise.all([extra_info, this._super.apply(this, arguments)]).then(function() {
//                self.render();
//            });
//        },
        _onChangeInitialBalanceBool: function (event) {
            var self = this;
            self.report_options['initial_balance'] = $('#initial_balance_check').prop("checked");
            self.reload();
        }
    });
});
