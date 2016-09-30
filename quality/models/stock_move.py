# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.multi
    def action_confirm(self):
        moves = super(StockMove, self).action_confirm()
        pick_moves = defaultdict(lambda: self.env['stock.move'])
        for move in moves:
            pick_moves[move.picking_id] |= move
        for picking, moves in pick_moves.iteritems():
            quality_points = self.env['quality.point'].sudo().search([
                ('picking_type_id', '=', picking.picking_type_id.id),
                '|', ('product_id', 'in', moves.mapped('product_id').ids),
                '&', ('product_id', '=', False), ('product_tmpl_id', 'in', moves.mapped('product_id').mapped('product_tmpl_id').ids)])
            for point in quality_points:
                if point.check_execute_now():  # TODO: if there is a check already for a certain product, no reason to create another one in the picking
                    if point.product_id:
                        self.env['quality.check'].sudo().create({
                            'picking_id': picking.id,
                            'point_id': point.id,
                            'team_id': point.team_id.id,
                            'product_id': point.product_id.id,
                        })
                    else:
                        products = picking.move_lines.filtered(lambda move: move.product_id.product_tmpl_id == point.product_tmpl_id).mapped('product_id')
                        for product in products:
                            self.env['quality.check'].sudo().create({
                                'picking_id': picking.id,
                                'point_id': point.id,
                                'team_id': point.team_id.id,
                                'product_id': product.id,
                            })
        return moves

    @api.multi
    def action_done(self):
        # It is good to put the check at the lowest level
        if self.mapped('picking_id').mapped('check_ids').filtered(lambda x: x.quality_state == 'none'):
            raise UserError(_('You still need to do the quality checks!'))
        super(StockMove, self).action_done()
