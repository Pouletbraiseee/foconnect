# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Champ principal manquant qui cause l'erreur
    po_number = fields.Char(string='N° BC', help='Numéro de bon de commande')

    # Champs communs
    date_created = fields.Date(string='Date de création', default=fields.Date.today)
    edited_by = fields.Many2one('res.users', string='Édité par', default=lambda self: self.env.user)
    reception_status = fields.Selection([
        ('pending', 'En attente'),
        ('partial', 'Partielle'),
        ('complete', 'Complète')
    ], string='Statut de réception', default='pending')

    # Type de commande
    order_type = fields.Selection([
        ('local', 'Local'),
        ('import', 'Import')
    ], string='Type de commande', default='local')

    # Champs financiers
    montant = fields.Float(string='Montant HT', help='Montant Hors Taxes')
    amount_total_custom = fields.Float(string='Montant Total', help='Montant Total Personnalisé')

    # Champs d'origine
    origin_country = fields.Many2one('res.country', string='Pays d\'origine')

    # Champs logistiques
    transport_mode = fields.Selection([
        ('sea', 'Maritime'),
        ('air', 'Aérien'),
        ('road', 'Route'),
        ('rail', 'Ferroviaire')
    ], string='Mode de Transport')

    # Champs douane
    customs_declaration_number = fields.Char(string='Numéro de Déclaration en Douane')

    # Statut d'importation
    is_imported = fields.Boolean(
        string='Commande Importée',
        compute='_compute_is_imported',
        store=True
    )

    # Champs spécifiques importation
    freight_reel = fields.Float(string='Freight Réel')
    freight_ext = fields.Float(string='Freight Extérieur')
    ratio = fields.Float(string='Ratio', compute='_compute_ratio', store=True)
    exchange_rate = fields.Float(string='Taux de Change', default=1.0)
    payment_date = fields.Date(string='Date de Paiement')
    payment_reception_date = fields.Date(string='Date de Réception Paiement')
    bank = fields.Char(string='Bank')
    predate = fields.Date(string='Date Prête')
    transport_date = fields.Date(string='Date Transport')
    expedition_date = fields.Date(string='Date d\'Expédition')
    arrival_date = fields.Date(string='Date Arrivée')
    home_date = fields.Date(string='Date à Casa')
    storage_date = fields.Date(string='Date Stockage')
    transport_company = fields.Char(string='Transporteur')
    volume_eur = fields.Float(string='Volume EUR')
    weight_kg = fields.Float(string='Fret KG')
    local_warehouse = fields.Float(string='Magasinage Local')
    local_transport = fields.Float(string='Transport Local')
    transit = fields.Float(string='Transit')
    prepost = fields.Float(string='Pré/Post')
    ratio_final = fields.Float(string='Ratio Final')

    # Champs spécifiques achats locaux
    ht_amount = fields.Float(string='Montant HT')
    tva_amount = fields.Float(string='TVA')
    ttc_amount = fields.Float(string='TTC')
    is_paid = fields.Selection([
        ('oui', 'OUI'),
        ('non', 'NON')
    ], string='Réglé', default='non')
    check_number = fields.Char(string='Numéro de Chèque')
    check_date = fields.Date(string='Date du Chèque')
    reception_and_invoice_status = fields.Selection([
        ('oui', 'OUI'),
        ('non', 'NON')
    ], string='Réception BL & Facture', default='non')

    @api.depends('order_type')
    def _compute_is_imported(self):
        for order in self:
            order.is_imported = order.order_type == 'import'

    @api.depends('montant', 'freight_reel')
    def _compute_ratio(self):
        for order in self:
            if order.montant and order.montant > 0:
                order.ratio = order.freight_reel / order.montant
            else:
                order.ratio = 0.0

    # Validate order type consistency
    @api.constrains('order_type')
    def _check_order_type(self):
        for order in self:
            if order.order_type == 'import' and not order.origin_country:
                raise ValidationError(_('Pour les commandes importées, le pays d\'origine est obligatoire.'))

    # Compute custom amounts during order confirmation
    def button_confirm(self):
        for order in self:
            # Calculate custom amounts if not already set
            if order.order_type == 'import':
                if not order.montant:
                    order.montant = sum(line.price_subtotal for line in order.order_line)
                if not order.amount_total_custom:
                    order.amount_total_custom = order.amount_total
        return super(PurchaseOrder, self).button_confirm()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Additional tracking for purchase order lines
    origin_product_country = fields.Many2one('res.country', string='Pays de Production')

    # Customs and compliance fields
    hs_code = fields.Char(string='Code HS', help='Code Harmonisé')

    # Compute origin details
    @api.onchange('product_id')
    def _onchange_product_origin(self):
        if self.product_id:
            self.origin_product_country = self.product_id.origin_country_id

    # Optional: Extra validation for imported goods
    @api.constrains('product_id', 'order_id')
    def _validate_imported_product(self):
        for line in self:
            if line.order_id.order_type == 'import':
                if not line.origin_product_country:
                    raise ValidationError(
                        _('Pour les commandes importées, le pays d\'origine du produit est obligatoire.'))