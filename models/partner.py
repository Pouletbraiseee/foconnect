# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Types de partenaires
    is_foreign_supplier = fields.Boolean(string='Est un fournisseur étranger')
    is_local_supplier = fields.Boolean(string='Est un fournisseur local')
    is_customer = fields.Boolean(string='Est un client')

    # Informations communes
    supplier_reference = fields.Char(string='Référence fournisseur/client')
    contact_name = fields.Char(string='Nom du contact')
    fix_number = fields.Char(string='Numéro fixe')
    mobile_number = fields.Char(string='Numéro mobile')

    # Champs fournisseur étranger
    delivery_delay = fields.Integer(string='Délai de livraison (jours)')
    parts_to_supply = fields.Text(string='Pièces à fournir')

    # Champs fournisseur local
    service = fields.Char(string='Service')

    # Champs client
    poste = fields.Char(string='Poste')
    observation = fields.Text(string='Observation')
    credit_limit = fields.Monetary(string='Limite de crédit', default=0.0)
    outstanding_balance = fields.Monetary(string='Solde courant', compute='_compute_outstanding_balance')

    @api.depends()
    def _compute_outstanding_balance(self):
        """Calcule le solde courant du client"""
        for partner in self:
            domain = [
                ('partner_id', '=', partner.id),
                ('state', '=', 'posted'),
                ('payment_state', 'not in', ['paid', 'in_payment']),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
            ]
            invoices = self.env['account.move'].search(domain)
            balance = sum(inv.amount_residual for inv in invoices)
            partner.outstanding_balance = balance

    @api.onchange('is_foreign_supplier')
    def _onchange_is_foreign_supplier(self):
        """Mise à jour des autres types de partenaires"""
        if self.is_foreign_supplier:
            self.supplier_rank = self.supplier_rank + 1 if not self.supplier_rank else 1

    @api.onchange('is_local_supplier')
    def _onchange_is_local_supplier(self):
        """Mise à jour des autres types de partenaires"""
        if self.is_local_supplier:
            self.supplier_rank = self.supplier_rank + 1 if not self.supplier_rank else 1

    @api.onchange('is_customer')
    def _onchange_is_customer(self):
        """Mise à jour des autres types de partenaires"""
        if self.is_customer:
            self.customer_rank = self.customer_rank + 1 if not self.customer_rank else 1

    # Méthode pour calculer le risque de crédit
    def calculate_credit_risk(self):
        """Calcule le niveau de risque de crédit du partenaire"""
        self.ensure_one()
        risk_level = 'low'

        if self.credit_limit > 0 and self.outstanding_balance > 0:
            ratio = self.outstanding_balance / self.credit_limit
            if ratio >= 0.8:
                risk_level = 'high'
            elif ratio >= 0.5:
                risk_level = 'medium'

        return risk_level