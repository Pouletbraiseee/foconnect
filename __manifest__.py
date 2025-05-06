{
    'name': 'FOconnect',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Gestion des achats et approvisionnements',
    'description': """
    Module de gestion des achats, approvisionnements et stock pour l'entreprise.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'purchase',
        'stock',
        'account',
        'sale_management',
    ],
    'data': [
    'security/foconnect_security.xml',
    'security/ir.model.access.csv',
    'data/account_data.xml',
    'views/partner_views.xml',
    'views/purchase_views.xml',
    'views/sale_views.xml',
    'views/stock_views.xml',
    'views/account_views.xml',
    'wizard/report_wizards_view.xml',  
    'views/main_menu.xml',
    'views/submenu_views.xml',
    'data/foconnect_data.xml',
],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',

}