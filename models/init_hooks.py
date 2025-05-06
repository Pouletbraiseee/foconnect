# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """Script exécuté après l'installation du module"""
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Vérifier/créer le journal de vente
    sale_journal = env['account.journal'].search([
        ('type', '=', 'sale'),
        ('company_id', '=', env.company.id)
    ], limit=1)

    if not sale_journal:
        # Chercher un compte de revenu
        revenue_account = env['account.account'].search([
            ('company_id', '=', env.company.id),
            ('account_type', '=', 'income')
        ], limit=1)

        if revenue_account:
            env['account.journal'].create({
                'name': 'Journal des ventes',
                'code': 'SALE',
                'type': 'sale',
                'company_id': env.company.id,
                'default_account_id': revenue_account.id,
            })

    # Vérifier/créer le journal d'achat
    purchase_journal = env['account.journal'].search([
        ('type', '=', 'purchase'),
        ('company_id', '=', env.company.id)
    ], limit=1)

    if not purchase_journal:
        # Chercher un compte de dépense
        expense_account = env['account.account'].search([
            ('company_id', '=', env.company.id),
            ('account_type', '=', 'expense')
        ], limit=1)

        if expense_account:
            env['account.journal'].create({
                'name': 'Journal des achats',
                'code': 'PURCH',
                'type': 'purchase',
                'company_id': env.company.id,
                'default_account_id': expense_account.id,
            })