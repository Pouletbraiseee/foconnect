# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, timedelta


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Champs pour le suivi des expéditions import
    is_import_shipment = fields.Boolean(string='Expédition d\'importation')
    is_in_transit = fields.Boolean(string='En transit')
    transit_start_date = fields.Datetime(string='Début du transit')
    transit_end_date = fields.Datetime(string='Fin du transit')
    transit_duration = fields.Float(string='Durée du transit (jours)', compute='_compute_transit_duration')
    is_received = fields.Boolean(string='Réceptionné')
    reception_date = fields.Datetime(string='Date de réception')
    invoice_received = fields.Boolean(string='Facture reçue')

    @api.depends('transit_start_date', 'transit_end_date')
    def _compute_transit_duration(self):
        for picking in self:
            if picking.transit_start_date and picking.transit_end_date:
                duration = picking.transit_end_date - picking.transit_start_date
                picking.transit_duration = duration.total_seconds() / (3600 * 24)  # Convertir en jours
            else:
                picking.transit_duration = 0.0

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and self.partner_id.is_foreign_supplier:
            self.is_import_shipment = True
        else:
            self.is_import_shipment = False

    def action_start_transit(self):
        for rec in self:
            rec.is_in_transit = True
            rec.transit_start_date = fields.Datetime.now()

    def action_end_transit(self):
        for rec in self:
            rec.is_in_transit = False
            rec.transit_end_date = fields.Datetime.now()
            rec.is_received = True
            rec.reception_date = fields.Datetime.now()

    # Hériter de la méthode button_validate pour marquer comme reçu
    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.picking_type_code == 'incoming':
            self.is_received = True
            self.reception_date = fields.Datetime.now()
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    # Traçabilité pour les produits importés
    origin_purchase_id = fields.Many2one(
        'purchase.order', string='Bon de commande d\'origine',
        related='purchase_line_id.order_id', store=True, readonly=True)

    origin_purchase_type = fields.Selection(
        string='Type d\'achat d\'origine',
        related='purchase_line_id.order_id.order_type', store=True, readonly=True)

    is_imported_product = fields.Boolean(
        string='Produit importé',
        compute='_compute_is_imported_product', store=True)

    @api.depends('origin_purchase_type')
    def _compute_is_imported_product(self):
        for move in self:
            move.is_imported_product = move.origin_purchase_type == 'import'


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    # Informations supplémentaires pour le stock
    last_reception_date = fields.Datetime(
        string='Date de dernière réception',
        compute='_compute_last_reception_date', store=True)

    days_in_stock = fields.Integer(
        string='Jours en stock',
        compute='_compute_days_in_stock')

    @api.depends('quantity', 'product_id')
    def _compute_last_reception_date(self):
        for quant in self:
            last_move = self.env['stock.move'].search([
                ('product_id', '=', quant.product_id.id),
                ('location_dest_id', '=', quant.location_id.id),
                ('state', '=', 'done')
            ], order='date desc', limit=1)
            quant.last_reception_date = last_move.date if last_move else False

    @api.depends('last_reception_date')
    def _compute_days_in_stock(self):
        today = fields.Datetime.now()
        for quant in self:
            if quant.last_reception_date:
                delta = today - quant.last_reception_date
                quant.days_in_stock = delta.days
            else:
                quant.days_in_stock = 0