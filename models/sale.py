# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_reference = fields.Char(string='Référence Client')
    requested_delivery_date = fields.Date(string='Date de livraison demandée')
    actual_delivery_date = fields.Date(string='Date de livraison effective')
    invoice_type = fields.Selection([
        ('normal', 'Facture Standard'),
        ('proforma', 'Facture Proforma'),
        ('commercial', 'Facture Commerciale'),
        ('avoir', 'Facture Avoir')
    ], string="Type de facture", default='normal')

    # Champ pour marquer les commandes avec retours
    has_return = fields.Boolean(string='A des retours', compute='_compute_has_return', store=True)

    # Calcul de la limite de crédit
    credit_limit_exceeded = fields.Boolean(
        string='Limite de crédit dépassée',
        compute='_compute_credit_limit_exceeded',
        store=True,
    )

    @api.depends('partner_id', 'amount_total')
    def _compute_credit_limit_exceeded(self):
        for order in self:
            exceeded = False
            if order.partner_id and hasattr(order.partner_id, 'credit_limit') and order.partner_id.credit_limit > 0:
                # Calculer le crédit utilisé (factures existantes + cette commande)
                partner_credit = order.partner_id.credit + order.amount_total
                exceeded = partner_credit > order.partner_id.credit_limit
            order.credit_limit_exceeded = exceeded

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_has_return(self):
        for order in self:
            return_pickings = order.picking_ids.filtered(
                lambda p: p.picking_type_code == 'incoming' and p.state != 'cancel')
            order.has_return = bool(return_pickings)

    # Vérification de la disponibilité des produits
    @api.onchange('order_line')
    def _onchange_order_line(self):
        for line in self.order_line:
            line._compute_available_qty()
            line._compute_estimated_delivery_date()

    @api.model
    def _ensure_sale_journal_exists(self):
        """S'assure qu'un journal de vente existe"""
        sale_journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not sale_journal:
            # Chercher un compte de revenu
            revenue_account = self.env['account.account'].search([
                ('company_id', '=', self.env.company.id),
                ('account_type', '=', 'income')
            ], limit=1)

            if not revenue_account:
                return False

            # Créer le journal
            sale_journal = self.env['account.journal'].create({
                'name': 'Journal des ventes',
                'code': 'SALE',
                'type': 'sale',
                'company_id': self.env.company.id,
                'default_account_id': revenue_account.id,
            })

        return sale_journal.id

    # Méthodes pour créer les différents types de factures
    def action_create_proforma(self):
        """Crée une facture proforma à partir de la commande"""
        # Vérifier l'existence d'un journal de vente
        sale_journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not sale_journal:
            # Créer un journal de vente si nécessaire
            revenue_account = self.env['account.account'].search([
                ('company_id', '=', self.env.company.id),
                ('account_type', '=', 'income')
            ], limit=1)

            if not revenue_account:
                raise UserError(_("Aucun compte de revenu trouvé. Veuillez créer un compte de type 'Revenu' d'abord."))

            sale_journal = self.env['account.journal'].create({
                'name': 'Journal des ventes',
                'code': 'SALE',
                'type': 'sale',
                'company_id': self.env.company.id,
                'default_account_id': revenue_account.id,
            })

        # Créer la facture proforma
        invoices = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_type': 'proforma',
            'partner_id': self.partner_id.id,
            'journal_id': sale_journal.id,  # Spécifier explicitement le journal
            'invoice_date': fields.Date.today(),
            'invoice_origin': self.name,
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_id.ids)],
                'discount': line.discount,
            }) for line in self.order_line],
        })

        return {
            'name': _('Facture Proforma'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoices.id,
            'type': 'ir.actions.act_window',
        }

    def action_create_commercial(self):
        """Crée une facture commerciale à partir de la commande"""
        # Vérifier l'existence d'un journal de vente
        sale_journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not sale_journal:
            # Créer un journal de vente si nécessaire
            revenue_account = self.env['account.account'].search([
                ('company_id', '=', self.env.company.id),
                ('account_type', '=', 'income')
            ], limit=1)

            if not revenue_account:
                raise UserError(_("Aucun compte de revenu trouvé. Veuillez créer un compte de type 'Revenu' d'abord."))

            sale_journal = self.env['account.journal'].create({
                'name': 'Journal des ventes',
                'code': 'SALE',
                'type': 'sale',
                'company_id': self.env.company.id,
                'default_account_id': revenue_account.id,
            })

        invoices = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_type': 'commercial',
            'partner_id': self.partner_id.id,
            'journal_id': sale_journal.id,  # Spécifier explicitement le journal
            'invoice_date': fields.Date.today(),
            'invoice_origin': self.name,
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_id.ids)],
                'discount': line.discount,
            }) for line in self.order_line],
        })

        return {
            'name': _('Facture Commerciale'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoices.id,
            'type': 'ir.actions.act_window',
        }

    def action_create_avoir(self):
        """Crée une facture avoir à partir de la commande"""
        # Vérifier l'existence d'un journal de vente
        sale_journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not sale_journal:
            # Créer un journal de vente si nécessaire
            revenue_account = self.env['account.account'].search([
                ('company_id', '=', self.env.company.id),
                ('account_type', '=', 'income')
            ], limit=1)

            if not revenue_account:
                raise UserError(_("Aucun compte de revenu trouvé. Veuillez créer un compte de type 'Revenu' d'abord."))

            sale_journal = self.env['account.journal'].create({
                'name': 'Journal des ventes',
                'code': 'SALE',
                'type': 'sale',
                'company_id': self.env.company.id,
                'default_account_id': revenue_account.id,
            })

        invoices = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_type': 'avoir',
            'partner_id': self.partner_id.id,
            'journal_id': sale_journal.id,  # Spécifier explicitement le journal
            'invoice_date': fields.Date.today(),
            'invoice_origin': self.name,
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_id.ids)],
                'discount': line.discount,
            }) for line in self.order_line],
        })

        return {
            'name': _('Facture Avoir'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoices.id,
            'type': 'ir.actions.act_window',
        }

    # Override les méthodes standard pour mettre à jour nos champs
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        # Mise à jour de la date de livraison sur les bons de livraison
        for picking in self.picking_ids:
            picking.scheduled_date = self.requested_delivery_date
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    available_qty = fields.Float(string='Quantité disponible', compute='_compute_available_qty')
    estimated_delivery_date = fields.Date(string='Date de livraison estimée',
                                          compute='_compute_estimated_delivery_date')

    @api.depends('product_id')
    def _compute_available_qty(self):
        """Calcule la quantité disponible en stock pour ce produit"""
        for line in self:
            if line.product_id and line.product_id.type == 'product':
                qty_available = line.product_id.with_context(warehouse=line.order_id.warehouse_id.id).qty_available
                line.available_qty = qty_available
            else:
                line.available_qty = 0.0

    @api.depends('product_id', 'available_qty', 'product_uom_qty')
    def _compute_estimated_delivery_date(self):
        """Calcule une date de livraison estimée basée sur la disponibilité"""
        today = fields.Date.today()
        for line in self:
            if line.product_id and line.product_id.type == 'product':
                if line.available_qty >= line.product_uom_qty:
                    # Si le stock est suffisant, livraison dans 2 jours
                    line.estimated_delivery_date = today + fields.date.timedelta(days=2)
                else:
                    # Si stock insuffisant, calcul basé sur le délai du fournisseur
                    supplier_info = self.env['product.supplierinfo'].search([
                        ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)
                    ], limit=1)
                    delay = supplier_info.delay if supplier_info else 7
                    line.estimated_delivery_date = today + fields.date.timedelta(days=delay)
            else:
                line.estimated_delivery_date = today + fields.date.timedelta(days=5)