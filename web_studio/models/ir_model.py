# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class IrModel(models.Model):
    _inherit = 'ir.model'

    mail_thread = fields.Boolean(compute='_compute_mail_thread',
                                 inverse='_inverse_mail_thread', store=True,
                                 help="Whether this model supports messages and notifications.")

    @api.depends('model')
    def _compute_mail_thread(self):
        MailThread = self.pool['mail.thread']
        for rec in self:
            if rec.model != 'mail.thread':
                Model = self.pool.get(rec.model)
                rec.mail_thread = Model and issubclass(Model, MailThread)

    def _inverse_mail_thread(self):
        pass        # do nothing; this enables to set the value of the field

    @api.multi
    def write(self, vals):
        res = super(IrModel, self).write(vals)
        if self and 'mail_thread' in vals:
            if not all(rec.state == 'manual' for rec in self):
                raise UserError(_('Only custom models can be modified.'))
            # one can only change mail_thread from False to True
            if not all(rec.mail_thread <= vals['mail_thread'] for rec in self):
                raise UserError(_('Field "Mail Thread" cannot be changed to "False".'))
            # setup models; this reloads custom models in registry
            self.pool.setup_models(self._cr, partial=(not self.pool.ready))
            # update database schema of models
            models = self.pool.descendants(self.mapped('model'), '_inherits')
            self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))
            self.pool.signal_registry_change()
        return res

    @api.model
    def _instanciate(self, model_data):
        model_class = super(IrModel, self)._instanciate(model_data)
        if model_data.get('mail_thread'):
            parents = model_class._inherit or []
            parents = [parents] if isinstance(parents, basestring) else parents
            model_class._inherit = parents + ['mail.thread']
        return model_class
