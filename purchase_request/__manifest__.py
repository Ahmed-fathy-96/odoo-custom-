{
    'name': 'Purchase Request',
    'summary': 'training model Purchase Request',
    'category': 'Inventory/Purchase',
    'depends': [
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/reject_purchase_request.xml',
        'data/mail_template.xml',
        'report/purchase_request_report_template.xml',
        'report/purchase_request_reports.xml',
        'views/purchase_request.xml',
        'views/purchase_order.xml',
        'views/menus.xml',

    ],
}
