# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, timedelta
import base64
import xlsxwriter
from io import BytesIO


class ImportReportWizard(models.TransientModel):
    _name = 'foconnect.import.report.wizard'
    _description = 'Wizard pour générer des rapports d\'importation'

    date_from = fields.Date(string='Date de début', required=True,
                            default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='Date de fin', required=True, default=lambda self: fields.Date.today())
    supplier_ids = fields.Many2many('res.partner', string='Fournisseurs', domain=[('is_foreign_supplier', '=', True)])
    include_customs_info = fields.Boolean(string='Inclure les informations douanières', default=True)

    def action_generate_report(self):
        # Créer un fichier Excel en mémoire
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Rapport Importation')

        # Styles
        title_style = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        header_style = workbook.add_format({'bold': True, 'bg_color': '#AAAAAA', 'border': 1})
        cell_style = workbook.add_format({'border': 1})
        date_style = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})

        # Titre
        worksheet.merge_range('A1:H1', 'Rapport d\'Importation', title_style)
        worksheet.merge_range('A2:H2',
                              f'Période du {self.date_from.strftime("%d/%m/%Y")} au {self.date_to.strftime("%d/%m/%Y")}',
                              title_style)

        # En-têtes
        headers = ['N° BC', 'Date', 'Fournisseur', 'Montant', 'Taux de Change', 'Freight', 'Date Arrivée', 'Status']
        if self.include_customs_info:
            headers.extend(['Frais Douane', 'Transit', 'Magasinage'])

        for col, header in enumerate(headers):
            worksheet.write(3, col, header, header_style)

        # Construire le domaine de recherche
        domain = [
            ('order_type', '=', 'import'),
            ('date_created', '>=', self.date_from),
            ('date_created', '<=', self.date_to)
        ]

        if self.supplier_ids:
            domain.append(('partner_id', 'in', self.supplier_ids.ids))

        # Récupérer les données
        purchase_orders = self.env['purchase.order'].search(domain, order='date_created desc')

        # Remplir les données
        for row, po in enumerate(purchase_orders, start=4):
            worksheet.write(row, 0, po.po_number or '', cell_style)
            worksheet.write(row, 1, po.date_created, date_style)
            worksheet.write(row, 2, po.partner_id.name, cell_style)
            worksheet.write(row, 3, po.montant, cell_style)
            worksheet.write(row, 4, po.exchange_rate, cell_style)
            worksheet.write(row, 5, po.freight_reel, cell_style)
            worksheet.write(row, 6, po.arrival_date, date_style)
            worksheet.write(row, 7, dict(po._fields['state'].selection).get(po.state), cell_style)

            if self.include_customs_info:
                # Ajouter les informations douanières
                worksheet.write(row, 8, 0.0, cell_style)  # Placeholder pour les frais de douane
                worksheet.write(row, 9, po.transit, cell_style)
                worksheet.write(row, 10, po.local_warehouse, cell_style)

        workbook.close()

        # Créer un attachement
        xls_data = base64.b64encode(output.getvalue())
        filename = f'rapport_importation_{self.date_from.strftime("%Y%m%d")}_{self.date_to.strftime("%Y%m%d")}.xlsx'

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': xls_data,
            'res_model': self._name,
            'res_id': self.id,
        })

        # Retourner l'action pour télécharger le fichier
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class SalesReportWizard(models.TransientModel):
    _name = 'foconnect.sales.report.wizard'
    _description = 'Wizard pour générer des rapports de ventes'

    date_from = fields.Date(string='Date de début', required=True,
                            default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='Date de fin', required=True, default=lambda self: fields.Date.today())
    customer_ids = fields.Many2many('res.partner', string='Clients', domain=[('is_customer', '=', True)])
    customer_category = fields.Many2one('res.partner.category', string='Catégorie client')
    include_delivery_info = fields.Boolean(string='Inclure les informations de livraison', default=True)

    def action_generate_report(self):
        # Créer un fichier Excel en mémoire
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Rapport Ventes')

        # Styles
        title_style = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        header_style = workbook.add_format({'bold': True, 'bg_color': '#AAAAAA', 'border': 1})
        cell_style = workbook.add_format({'border': 1})
        date_style = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})

        # Titre
        worksheet.merge_range('A1:H1', 'Rapport de Ventes', title_style)
        worksheet.merge_range('A2:H2',
                              f'Période du {self.date_from.strftime("%d/%m/%Y")} au {self.date_to.strftime("%d/%m/%Y")}',
                              title_style)

        # En-têtes
        headers = ['N°', 'Date', 'Client', 'Montant HT', 'TVA', 'Montant TTC', 'État', 'Référence Client']
        if self.include_delivery_info:
            headers.extend(['Date Livraison Demandée', 'Date Livraison Effective'])

        for col, header in enumerate(headers):
            worksheet.write(3, col, header, header_style)

        # Construire le domaine de recherche
        domain = [
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to)
        ]

        if self.customer_ids:
            domain.append(('partner_id', 'in', self.customer_ids.ids))

        if self.customer_category:
            domain.append(('partner_id.category_id', 'in', [self.customer_category.id]))

        # Récupérer les données
        sale_orders = self.env['sale.order'].search(domain, order='date_order desc')

        # Remplir les données
        for row, so in enumerate(sale_orders, start=4):
            worksheet.write(row, 0, so.name, cell_style)
            worksheet.write(row, 1, so.date_order.date(), date_style)
            worksheet.write(row, 2, so.partner_id.name, cell_style)
            worksheet.write(row, 3, so.amount_untaxed, cell_style)
            worksheet.write(row, 4, so.amount_tax, cell_style)
            worksheet.write(row, 5, so.amount_total, cell_style)
            worksheet.write(row, 6, dict(so._fields['state'].selection).get(so.state), cell_style)
            worksheet.write(row, 7, so.customer_reference or '', cell_style)

            if self.include_delivery_info:
                worksheet.write(row, 8, so.requested_delivery_date, date_style)
                worksheet.write(row, 9, so.actual_delivery_date, date_style)

        workbook.close()

        # Créer un attachement
        xls_data = base64.b64encode(output.getvalue())
        filename = f'rapport_ventes_{self.date_from.strftime("%Y%m%d")}_{self.date_to.strftime("%Y%m%d")}.xlsx'

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': xls_data,
            'res_model': self._name,
            'res_id': self.id,
        })

        # Retourner l'action pour télécharger le fichier
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }