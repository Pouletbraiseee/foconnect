# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Type de facture
    invoice_type = fields.Selection([
        ('normal', 'Facture Standard'),
        ('proforma', 'Facture Proforma'),
        ('commercial', 'Facture Commerciale'),
        ('avoir', 'Facture Avoir')
    ], string="Type de facture", default='normal')

    # Pour le suivi des achats - référence à la commande d'origine
    origin_purchase_id = fields.Many2one('purchase.order', string='Commande d\'origine')
    origin_purchase_type = fields.Selection(related='origin_purchase_id.order_type',
                                            string='Type d\'achat d\'origine',
                                            store=True, readonly=True)

    # Pour le suivi des paiements
    ht_amount = fields.Monetary(string='Montant HT', compute='_compute_ht_amount', store=True)
    tva_amount = fields.Monetary(string='Montant TVA', compute='_compute_tva_amount', store=True)
    ttc_amount = fields.Monetary(string='Montant TTC', compute='_compute_ttc_amount', store=True)
    is_paid = fields.Selection([
        ('oui', 'OUI'),
        ('non', 'NON')
    ], string='REGLE OU/NON', default='non')
    payment_mode = fields.Selection([
        ('cheque', 'Chèque'),
        ('virement', 'Virement'),
        ('especes', 'Espèces'),
        ('autre', 'Autre')
    ], string='Mode de Paiement')
    payment_reception_date = fields.Date(string='Date de Réception Paiement')
    payment_amount = fields.Monetary(string='Montant du Paiement')
    payment_due_date = fields.Date(string='Date d\'Échéance')
    payment_date = fields.Date(string='Date de Paiement')
    payment_bank = fields.Char(string='Banque')

    # Pour le suivi logistique
    transporter = fields.Char(string='Transporteur')
    expedition_number = fields.Char(string='N° d\'Expédition')
    invoice_received = fields.Boolean(string='Facture Reçue')

    @api.depends('invoice_line_ids', 'invoice_line_ids.price_subtotal')
    def _compute_ht_amount(self):
        for move in self:
            move.ht_amount = sum(line.price_subtotal for line in move.invoice_line_ids)

    @api.depends('invoice_line_ids', 'invoice_line_ids.tax_ids', 'invoice_line_ids.price_subtotal')
    def _compute_tva_amount(self):
        for move in self:
            move.tva_amount = move.amount_tax

    @api.depends('ht_amount', 'tva_amount')
    def _compute_ttc_amount(self):
        for move in self:
            move.ttc_amount = move.ht_amount + move.tva_amount

    @api.model_create_multi
    def create(self, vals_list):
        # Si facture fournisseur, chercher l'origine dans les commandes d'achat
        for vals in vals_list:
            if vals.get('move_type') in ['in_invoice', 'in_refund'] and vals.get('invoice_origin'):
                purchase = self.env['purchase.order'].search([
                    ('name', '=', vals.get('invoice_origin'))
                ], limit=1)
                if purchase:
                    vals['origin_purchase_id'] = purchase.id
        return super(AccountMove, self).create(vals_list)