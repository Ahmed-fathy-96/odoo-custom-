{
    'name': 'Purchase Request',
    'summary': 'training model Purchase Request',
    'depends': [
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/reject_purchase_request.xml',
        'data/mail_template.xml',
        'views/purchase_request.xml',
        'views/menus.xml',
    ],
}
