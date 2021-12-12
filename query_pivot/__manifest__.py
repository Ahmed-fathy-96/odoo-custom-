{
    'name': 'Query Pivot',
    'summary': 'training module create pivot view from a query.',
    'depends': [
        'base',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_sale_analysis_pivot.xml',
    ],
}
