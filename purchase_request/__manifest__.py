{
    'name': 'Purchase Request',
    'summary': 'training model Purchase Request',
    'depends': [
        # 'purchase',
        'product'],
    'data': [
        'wizards/reject_purchase_request.xml',
        'views/purchase_request_views.xml',
        'views/purchase_request_menus_views.xml',

        'security/ir.model.access.csv',
    ],
}
