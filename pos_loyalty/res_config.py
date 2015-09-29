from openerp.osv import fields, osv

class pos_configuration(osv.TransientModel):
    _inherit = 'pos.config.settings'

    _columns = {
        'module_pos_loyalty': fields.selection([
            (0, "No loyalty programs"),
            (1, "Use loyalty programs")
            ], "Loyalty",
            help='Allows you to define a loyalty program in the point of sale, where the customers earn loyalty points and get rewards'),
    }
